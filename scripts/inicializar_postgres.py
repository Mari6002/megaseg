"""Migra los datos locales de SQLite a PostgreSQL y activa PostgreSQL en .env."""

import os
from datetime import datetime, timezone
from pathlib import Path
import shutil
import sqlite3
import sys

from dotenv import load_dotenv, set_key

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
load_dotenv(PROJECT_ROOT / '.env')

SOURCE_DB = PROJECT_ROOT / 'megaseg.db'
BACKUPS_DIR = PROJECT_ROOT / 'backups'
SCHEMA_FILE = PROJECT_ROOT / 'sql' / 'esquema_postgres.sql'
ENV_FILE = PROJECT_ROOT / '.env'
TABLES = (
    'roles',
    'usuarios',
    'tipos_servicio',
    'servicios',
    'logs_actividad',
    'facturas',
    'detalles_factura',
)
SERIAL_TABLES = TABLES
RETIRED_ROLE = 'Facturador / Operador'


def _postgres_connection():
    import psycopg2
    from psycopg2 import sql

    if os.getenv('DATABASE_URL'):
        raise RuntimeError(
            'DATABASE_URL está configurada. Elimina o comenta esa URL para migrar '
            'a la instancia PostgreSQL local definida por DB_HOST/DB_PORT.'
        )

    params = {
        'host': os.getenv('DB_HOST', 'localhost'),
        'port': int(os.getenv('DB_PORT', '5432')),
        'user': os.getenv('DB_USER', 'postgres'),
        'password': os.getenv('DB_PASSWORD', ''),
        'connect_timeout': 5,
    }
    dbname = os.getenv('DB_NAME', 'megaseg')

    try:
        return psycopg2.connect(dbname=dbname, **params)
    except UnicodeDecodeError as error:
        raise RuntimeError(
            'PostgreSQL rechazó o no pudo interpretar la conexión. Verifica el '
            'usuario y DB_PASSWORD en .env; no se modificaron las bases existentes.'
        ) from error
    except psycopg2.OperationalError as error:
        if getattr(error, 'pgcode', None) != '3D000':
            raise

    with psycopg2.connect(dbname='postgres', **params) as admin:
        admin.autocommit = True
        with admin.cursor() as cursor:
            cursor.execute(
                sql.SQL('CREATE DATABASE {}').format(sql.Identifier(dbname))
            )
    return psycopg2.connect(dbname=dbname, **params)


def _crear_respaldo():
    BACKUPS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    backup = BACKUPS_DIR / f'megaseg-pre-postgres-{timestamp}.db'
    shutil.copy2(SOURCE_DB, backup)
    return backup


def _leer_datos_sqlite():
    source = sqlite3.connect(SOURCE_DB.resolve().as_uri() + '?mode=ro', uri=True)
    source.row_factory = sqlite3.Row
    try:
        existing = {
            row['name']
            for row in source.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
        missing = set(TABLES) - existing
        if missing:
            raise RuntimeError(
                'La base SQLite no contiene las tablas esperadas: '
                + ', '.join(sorted(missing))
            )

        return {
            table: [dict(row) for row in source.execute(f'SELECT * FROM "{table}" ORDER BY id')]
            for table in TABLES
        }
    finally:
        source.close()


def _crear_administrador_inicial(cursor):
    from werkzeug.security import generate_password_hash

    username = (os.getenv('ADMIN_USERNAME') or '').strip()
    password = os.getenv('ADMIN_PASSWORD') or ''
    if not username or len(password) < 14:
        raise RuntimeError(
            'Configura ADMIN_USERNAME y ADMIN_PASSWORD (mínimo 14 caracteres) '
            'en .env para inicializar una base PostgreSQL vacía.'
        )
    cursor.execute(
        '''
        INSERT INTO usuarios (usuario, password, rol, nombre, email, activo)
        VALUES (%s, %s, 'Administrador', 'Administrador Megaseg', 'contacto@megaseg.ec', TRUE)
        ''',
        (username, generate_password_hash(password)),
    )


def _migrar_datos(cursor, datos):
    from psycopg2 import sql

    migrated_counts = {}
    for table in TABLES:
        rows = datos[table]
        if table == 'roles':
            rows = [
                row for row in rows
                if (row.get('nombre') or '').casefold() != RETIRED_ROLE.casefold()
            ]

        columns = list(rows[0]) if rows else []
        if not rows:
            migrated_counts[table] = 0
            continue

        statement = sql.SQL('INSERT INTO {} ({}) VALUES ({})').format(
            sql.Identifier(table),
            sql.SQL(', ').join(sql.Identifier(column) for column in columns),
            sql.SQL(', ').join(sql.Placeholder() for _ in columns),
        )

        for row in rows:
            if table == 'usuarios' and (row.get('rol') or '').casefold() == RETIRED_ROLE.casefold():
                row['activo'] = False
            if table == 'usuarios' and 'activo' in row:
                row['activo'] = bool(row['activo'])
            if table == 'servicios':
                for column in ('disponible', 'destacado'):
                    if column in row:
                        row[column] = bool(row[column])
            if table == 'logs_actividad' and row.get('entidad_id') is not None:
                row['entidad_id'] = str(row['entidad_id'])
            cursor.execute(statement, [row[column] for column in columns])

        migrated_counts[table] = len(rows)
    return migrated_counts


def _verificar_destino_vacio(cursor):
    cursor.execute(
        "SELECT table_name FROM information_schema.tables "
        "WHERE table_schema = 'public' AND table_type = 'BASE TABLE'"
    )
    tables = {row[0] for row in cursor.fetchall()}
    occupied = {}
    for table in TABLES:
        if table in tables:
            cursor.execute(f'SELECT COUNT(*) FROM "{table}"')
            count = cursor.fetchone()[0]
            if count:
                occupied[table] = count
    if occupied:
        resumen = ', '.join(f'{table}: {count}' for table, count in occupied.items())
        raise RuntimeError(
            'La base PostgreSQL de destino ya contiene datos (' + resumen + '). '
            'No se sobrescribió nada. Configura una base de datos local vacía y vuelve a ejecutar.'
        )


def _actualizar_secuencias(cursor):
    from psycopg2 import sql

    for table in SERIAL_TABLES:
        cursor.execute(
            sql.SQL(
                "SELECT setval(pg_get_serial_sequence(%s, 'id'), "
                "COALESCE(MAX(id), 1), COUNT(*) > 0) FROM {}"
            ).format(sql.Identifier(table)),
            (f'public.{table}',),
        )


def main():
    if not SCHEMA_FILE.is_file():
        raise RuntimeError(f'No se encontró el esquema PostgreSQL: {SCHEMA_FILE}')

    if SOURCE_DB.is_file():
        backup = _crear_respaldo()
        print(f'Respaldo SQLite creado: {backup}')
        datos = _leer_datos_sqlite()
    else:
        backup = None
        datos = None
        print('No hay SQLite local; se creará una instalación PostgreSQL nueva.')

    schema = SCHEMA_FILE.read_text(encoding='utf-8')
    if datos is None:
        initialization_sql = schema
    else:
        initialization_sql = schema.split('-- DATOS INICIALES', 1)[0]
    if not initialization_sql:
        raise RuntimeError('No se pudo identificar la sección DDL del esquema PostgreSQL.')

    connection = _postgres_connection()
    try:
        with connection:
            with connection.cursor() as cursor:
                _verificar_destino_vacio(cursor)
                cursor.execute(initialization_sql)
                if datos is not None:
                    cursor.execute('ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS telefono VARCHAR(50)')
                    cursor.execute('ALTER TABLE servicios ADD COLUMN IF NOT EXISTS tipo_producto VARCHAR(100)')
                    cursor.execute('ALTER TABLE servicios ADD COLUMN IF NOT EXISTS garantia TEXT')
                    cursor.execute('ALTER TABLE servicios ADD COLUMN IF NOT EXISTS zona_cobertura TEXT')
                    cursor.execute('ALTER TABLE servicios ADD COLUMN IF NOT EXISTS disponibilidad_atencion TEXT')
                    cursor.execute('ALTER TABLE servicios ADD COLUMN IF NOT EXISTS modalidad_pago TEXT')
                    cursor.execute('ALTER TABLE servicios ADD COLUMN IF NOT EXISTS ficha_tecnica TEXT')
                    cursor.execute('ALTER TABLE servicios ADD COLUMN IF NOT EXISTS whatsapp_msg TEXT')
                    migrated_counts = _migrar_datos(cursor, datos)
                    _actualizar_secuencias(cursor)
                cursor.execute('SELECT COUNT(*) FROM usuarios')
                if cursor.fetchone()[0] == 0:
                    _crear_administrador_inicial(cursor)
    finally:
        connection.close()

    set_key(str(ENV_FILE), 'USE_POSTGRES', 'true', quote_mode='never')
    set_key(str(ENV_FILE), 'USE_SQLITE', 'false', quote_mode='never')
    if backup:
        print('Migración completada; megaseg.db se conservó sin cambios.')
        for table, count in migrated_counts.items():
            print(f'{table}: {count} registros')
    else:
        print('PostgreSQL inicializado; se creó el administrador desde las credenciales de .env.')
    print('PostgreSQL local quedó habilitado en .env (USE_POSTGRES=true).')


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        print(f'ERROR: {error}')
        print('No se eliminó ni modificó la base SQLite original.')
        raise SystemExit(1) from error
