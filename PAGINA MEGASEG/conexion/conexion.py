# ==============================================================================
# PROYECTO: MEGASEG SEGURIDAD INTEGRAL - CONEXIÓN A BASE DE DATOS
# ==============================================================================
# Este módulo administra la conexión centralizada con soporte dual:
# 1. PostgreSQL cuando se configura DATABASE_URL.
# 2. SQLite local para desarrollo y pruebas.
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
            # Intento de operación rápida para saber si está abierta
            self.connection.total_changes
            return False
        except Exception:
            return True


def get_db_connection():
    """
    Obtiene una conexión activa a la base de datos.
    Usa PostgreSQL cuando DATABASE_URL está configurada y SQLite para desarrollo local.
    Un fallo de PostgreSQL se propaga; nunca cambia silenciosamente a otra base.
    """
    if has_app_context():
        conexion_actual = getattr(g, 'megaseg_db_connection', None)
        if conexion_actual is not None and not getattr(conexion_actual, 'closed', False):
            return conexion_actual

    db_url = (os.getenv('DATABASE_URL') or '').strip()

    # Opción 1: Conexión PostgreSQL (si está configurada)
    if db_url:
        try:
            import psycopg2
            from psycopg2.extras import RealDictCursor
        except ImportError as error:
            raise RuntimeError(
                'DATABASE_URL está configurada, pero falta instalar psycopg2.'
            ) from error

        if db_url.startswith('postgres://'):
            db_url = db_url.replace('postgres://', 'postgresql://', 1)

        try:
            conexion = psycopg2.connect(
                dsn=db_url,
                cursor_factory=RealDictCursor,
                connect_timeout=10,
                application_name='megaseg-web'
            )
        except Exception as error:
            raise RuntimeError(
                'No se pudo conectar a PostgreSQL configurado en DATABASE_URL. '
                'Se cancela la operación para evitar usar otra base de datos.'
            ) from error

        if has_app_context():
            g.megaseg_db_connection = conexion
        return conexion

    # Opción 2: Conexión SQLite local (megaseg.db)
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


