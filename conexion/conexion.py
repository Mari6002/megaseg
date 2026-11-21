# ==============================================================================
# PROYECTO: MEGASEG SEGURIDAD INTEGRAL - CONEXIÓN A BASE DE DATOS
# ==============================================================================
# Este módulo usa PostgreSQL según DATABASE_URL o USE_POSTGRES=true y permite
# SQLite explícitamente con USE_SQLITE=true para pruebas y desarrollo aislado.
# ==============================================================================

import os
import sqlite3
from pathlib import Path
from flask import g, has_app_context
from dotenv import load_dotenv
from conexion.inicializacion import inicializar_base_datos

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / '.env')

DB_PATH = PROJECT_ROOT / 'megaseg.db'


class SQLiteDictCursor:
    """Cursor envoltorio para SQLite que permite acceder a campos como diccionarios."""
    def __init__(self, cursor):
        self.cursor = cursor

    def execute(self, query, params=None):
        # Convertir placeholders de PostgreSQL (%s) a SQLite (?) si es necesario
        if params is not None:
            query = query.replace('%s', '?')
            return self.cursor.execute(query, params)
        return self.cursor.execute(query)

    def fetchone(self):
        row = self.cursor.fetchone()
        return dict(row) if row else None

    def fetchall(self):
        rows = self.cursor.fetchall()
        return [dict(r) for r in rows]

    def close(self):
        self.cursor.close()

    @property
    def lastrowid(self):
        return self.cursor.lastrowid

    @property
    def rowcount(self):
        return self.cursor.rowcount


class SQLiteConnectionWrapper:
    """Envoltorio de conexión SQLite compatible con la API de psycopg2."""
    def __init__(self, connection):
        self.connection = connection
        self.connection.row_factory = sqlite3.Row

    def cursor(self):
        return SQLiteDictCursor(self.connection.cursor())

    def commit(self):
        self.connection.commit()

    def rollback(self):
        self.connection.rollback()

    def close(self):
        self.connection.close()

    @property
    def closed(self):
        try:
            self.connection.total_changes
            return False
        except Exception:
            return True


def get_db_connection():
    """
    Obtiene una conexión activa a la base de datos.
    - Usa PostgreSQL cuando DATABASE_URL está configurada o USE_POSTGRES=true.
    - Usa SQLite únicamente cuando USE_SQLITE=true.
    - Falla explícitamente si no se configuró un motor de base de datos.
    """
    if has_app_context():
        conexion_actual = getattr(g, 'megaseg_db_connection', None)
        if conexion_actual is not None and not getattr(conexion_actual, 'closed', False):
            return conexion_actual

    db_url = (os.getenv('DATABASE_URL') or '').strip()
    use_postgres = (os.getenv('USE_POSTGRES') or '').strip().lower() in ('1', 'true', 'yes')
    use_sqlite = (os.getenv('USE_SQLITE') or '').strip().lower() in ('1', 'true', 'yes')

    if use_sqlite and (db_url or use_postgres):
        raise RuntimeError(
            'Configuración de base de datos ambigua: elige PostgreSQL o SQLite, no ambos.'
        )

    # Opción 1: Conexión PostgreSQL (DATABASE_URL o USE_POSTGRES=true).
    if db_url or use_postgres:
        try:
            import psycopg2
            from psycopg2.extras import RealDictCursor
        except ImportError as error:
            raise RuntimeError(
                'PostgreSQL está configurado pero falta instalar psycopg2.'
            ) from error

        parametros = {}
        application_name = 'megaseg-web'

        if db_url:
            if db_url.startswith('postgres://'):
                db_url = db_url.replace('postgres://', 'postgresql://', 1)
            parametros['dsn'] = db_url
        else:
            parametros = {
                'host': os.getenv('DB_HOST', 'localhost'),
                'port': int(os.getenv('DB_PORT', 5432)),
                'dbname': os.getenv('DB_NAME', 'megaseg'),
                'user': os.getenv('DB_USER', 'postgres'),
                'password': os.getenv('DB_PASSWORD', ''),
            }

        try:
            conexion = psycopg2.connect(
                **parametros,
                cursor_factory=RealDictCursor,
                connect_timeout=10,
                application_name=application_name
            )
        except Exception as error:
            dest = db_url if db_url else f"{parametros.get('host')}:{parametros.get('port')}/{parametros.get('dbname')}"
            raise RuntimeError(
                f'No se pudo conectar a PostgreSQL en [{dest}]. '
                'Verifica que el servicio esté corriendo en tu equipo y que la contraseña en .env sea correcta.'
            ) from error

        if has_app_context():
            g.megaseg_db_connection = conexion
        return conexion

    if not use_sqlite:
        raise RuntimeError(
            'No hay una base de datos configurada. Define USE_POSTGRES=true para PostgreSQL '
            'o USE_SQLITE=true para SQLite local.'
        )

    # Opción 2: SQLite se permite únicamente con USE_SQLITE=true explícito.
    conn = sqlite3.connect(str(DB_PATH), timeout=10)
    conn.execute('PRAGMA foreign_keys = ON')
    conn_wrapper = SQLiteConnectionWrapper(conn)

    # Verificar e inicializar tablas en SQLite
    inicializar_base_datos(conn_wrapper)

    if has_app_context():
        g.megaseg_db_connection = conn_wrapper
    return conn_wrapper


def close_db_connection(exception=None):
    """Cierra la conexión al finalizar el ciclo de vida de la solicitud Flask."""
    conexion = getattr(g, 'megaseg_db_connection', None)
    if conexion is not None:
        try:
            conexion.close()
        except Exception:
            pass
    g.megaseg_db_connection = None
