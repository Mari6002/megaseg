"""Crea el esquema local y agrega datos iniciales sin reemplazar registros."""

import os
from pathlib import Path

from werkzeug.security import generate_password_hash

from conexion.datos_iniciales import CATEGORIAS_INICIALES, SERVICIOS_INICIALES


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def inicializar_base_datos(conn):
    """Aplica el esquema y completa las tablas que aún no tienen sus datos base."""
    esquema_path = PROJECT_ROOT / 'sql' / 'esquema.sql'
    with esquema_path.open(encoding='utf-8') as archivo_esquema:
        conn.connection.executescript(archivo_esquema.read())

    conn.commit()
    _crear_administrador_si_no_existe(conn)
    _crear_categorias_si_no_existen(conn)
    _crear_catalogo_si_no_existe(conn)


def _crear_administrador_si_no_existe(conn):
    """Crea la cuenta inicial solo con credenciales privadas configuradas en .env."""
    cursor = conn.cursor()
    try:
        cursor.execute('SELECT COUNT(*) AS total FROM usuarios')
        fila = cursor.fetchone()
        if not fila or fila['total'] != 0:
            return

        usuario = (os.getenv('ADMIN_USERNAME') or '').strip()
        password = os.getenv('ADMIN_PASSWORD') or ''
        if not usuario or len(password) < 14:
            return

        cursor.execute(
            '''
            INSERT INTO usuarios (usuario, password, rol, nombre, email)
            VALUES (%s, %s, %s, %s, %s)
            ''',
            (
                usuario,
                generate_password_hash(password),
                'Administrador',
                'Administrador Megaseg',
                '',
            )
        )
        conn.commit()
    finally:
        cursor.close()


def _crear_categorias_si_no_existen(conn):
    """Inserta únicamente las categorías faltantes, respetando las ya existentes."""
    cursor = conn.cursor()
    try:
        cursor.execute('SELECT nombre FROM tipos_servicio')
        nombres_existentes = {fila['nombre'] for fila in cursor.fetchall()}

        for nombre, descripcion in CATEGORIAS_INICIALES:
            if nombre not in nombres_existentes:
                cursor.execute(
                    'INSERT INTO tipos_servicio (nombre, descripcion) VALUES (%s, %s)',
                    (nombre, descripcion)
                )

        conn.commit()
    finally:
        cursor.close()


def _crear_catalogo_si_no_existe(conn):
    """Carga el catálogo de ejemplo solo si no existe ningún servicio."""
    cursor = conn.cursor()
    try:
        cursor.execute('SELECT COUNT(*) AS total FROM servicios')
        fila = cursor.fetchone()
        if not fila or fila['total'] != 0:
            return

        cursor.execute('SELECT id, nombre FROM tipos_servicio')
        categoria_por_nombre = {
            categoria['nombre']: categoria['id']
            for categoria in cursor.fetchall()
        }

        categorias_requeridas = {servicio[0] for servicio in SERVICIOS_INICIALES}
        categorias_faltantes = categorias_requeridas - categoria_por_nombre.keys()
        if categorias_faltantes:
            nombres = ', '.join(sorted(categorias_faltantes))
            raise RuntimeError(f'Faltan categorías requeridas para el catálogo inicial: {nombres}')

        consulta = '''
            INSERT INTO servicios (
                tipo_servicio_id, nombre, precio_base, imagen, descripcion,
                disponible, es_producto, destacado
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        '''
        for servicio in SERVICIOS_INICIALES:
            nombre_categoria, nombre, precio, imagen, descripcion, disponible, es_producto, destacado = servicio
            cursor.execute(
                consulta,
                (
                    categoria_por_nombre[nombre_categoria], nombre, precio, imagen,
                    descripcion, disponible, es_producto, destacado,
                )
            )

        conn.commit()
    finally:
        cursor.close()
