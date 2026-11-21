"""Inicializa PostgreSQL sin importar datos de la base SQLite local."""

import os
from pathlib import Path
import sys

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
from security.passwords import hash_password

load_dotenv(PROJECT_ROOT / '.env')

SCHEMA_FILE = PROJECT_ROOT / 'sql' / 'esquema_postgres.sql'


def _postgres_connection():
    import psycopg2
    from psycopg2 import sql

    db_url = (os.getenv('DATABASE_URL') or '').strip()
    if db_url:
        if db_url.startswith('postgres://'):
            db_url = db_url.replace('postgres://', 'postgresql://', 1)
        try:
            return psycopg2.connect(db_url, connect_timeout=10)
        except Exception as error:
            raise RuntimeError(
                'No se pudo conectar a PostgreSQL usando DATABASE_URL.'
            ) from error

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


def _crear_administrador_inicial(cursor):
    username = (os.getenv('ADMIN_USERNAME') or '').strip()
    password = os.getenv('ADMIN_PASSWORD') or ''
    if not username or len(password) < 14:
        raise RuntimeError(
            'Configura ADMIN_USERNAME y ADMIN_PASSWORD (mínimo 14 caracteres) '
            'en .env para inicializar una base PostgreSQL vacía.'
        )
    cursor.execute("SELECT id FROM roles WHERE nombre = 'Administrador'")
    administrador = cursor.fetchone()
    if not administrador:
        raise RuntimeError('No existe el rol Administrador en PostgreSQL.')
    rol_administrador_id = administrador['id'] if isinstance(administrador, dict) else administrador[0]
    cursor.execute(
        '''
        INSERT INTO usuarios (usuario, password, rol_id, nombre, email, activo)
        VALUES (%s, %s, %s, 'Administrador Megaseg', 'contacto@megaseg.ec', TRUE)
        ''',
        (username, hash_password(password), rol_administrador_id),
    )


def main():
    if not SCHEMA_FILE.is_file():
        raise RuntimeError(f'No se encontró el esquema PostgreSQL: {SCHEMA_FILE}')

    connection = _postgres_connection()
    try:
        with connection:
            with connection.cursor() as cursor:
                cursor.execute(SCHEMA_FILE.read_text(encoding='utf-8'))
                cursor.execute('SELECT COUNT(*) FROM usuarios')
                if cursor.fetchone()[0] == 0:
                    _crear_administrador_inicial(cursor)
    finally:
        connection.close()

    print('Esquema PostgreSQL inicializado. No se importaron datos desde megaseg.db.')


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        print(f'ERROR: {error}')
        print('No se importaron ni modificaron datos de megaseg.db.')
        raise SystemExit(1) from error
