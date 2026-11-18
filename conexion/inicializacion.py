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
    _migrar_columnas_faltantes(conn)
    _crear_roles_si_no_existen(conn)
    _crear_administrador_si_no_existe(conn)
    _crear_categorias_si_no_existen(conn)
    _crear_catalogo_si_no_existe(conn)
    _actualizar_datos_plantilla_servicios(conn)
    _retirar_rol_facturador(conn)


def _migrar_columnas_faltantes(conn):
    """Asegura que la tabla servicios y usuarios tengan todas las columnas necesarias."""
    cursor = conn.cursor()
    try:
        # 1. Columnas para servicios
        cursor.execute("PRAGMA table_info(servicios)")
        cols_servicios = {fila['name'] for fila in cursor.fetchall()}

        columnas_nuevas_servicios = [
            ('tipo_producto', "VARCHAR(100) DEFAULT 'Servicio Operativo'"),
            ('garantia', "TEXT DEFAULT 'Soporte técnico directo en Lago Agrio y garantía certificada por Megaseg.'"),
            ('zona_cobertura', "TEXT DEFAULT 'Nueva Loja (Lago Agrio), Shushufindi, Cascales, Cuyabeno y toda la provincia de Sucumbíos.'"),
            ('disponibilidad_atencion', "TEXT DEFAULT 'Central de monitoreo y respuesta operativa activa 24 horas, los 365 días del año.'"),
            ('modalidad_pago', "TEXT DEFAULT 'Emisión de factura autorizada por SRI, transferencias bancarias y planes empresariales.'"),
            ('ficha_tecnica', "TEXT"),
            ('whatsapp_msg', "TEXT"),
        ]

        for col_nombre, col_tipo in columnas_nuevas_servicios:
            if col_nombre not in cols_servicios:
                cursor.execute(f"ALTER TABLE servicios ADD COLUMN {col_nombre} {col_tipo}")

        # 2. Columnas para usuarios
        cursor.execute("PRAGMA table_info(usuarios)")
        cols_usuarios = {fila['name'] for fila in cursor.fetchall()}
        if 'activo' not in cols_usuarios:
            cursor.execute("ALTER TABLE usuarios ADD COLUMN activo INTEGER NOT NULL DEFAULT 1")
        if 'telefono' not in cols_usuarios:
            cursor.execute("ALTER TABLE usuarios ADD COLUMN telefono VARCHAR(50)")

        conn.commit()
    finally:
        cursor.close()

def _crear_roles_si_no_existen(conn):
    """Crea los roles estándar de acceso al sistema (RBAC)."""
    roles_base = [
        ('Administrador', 'Control total del sistema: catálogo, auditoría y gestión de usuarios'),
        ('Gestor de Catálogo', 'Encargado de publicar, actualizar y editar servicios, productos, imágenes y fichas técnicas'),
        ('Supervisor', 'Supervisión operativa, edición de catálogo y consulta de auditoría'),
        ('Cliente', 'Consulta del catálogo y solicitud de cotizaciones'),
        ('Auditor', 'Visualización exclusiva de registros de auditoría y reportes del sistema')
    ]
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT nombre FROM roles")
        existentes = {r['nombre'] for r in cursor.fetchall()}
        for nombre, desc in roles_base:
            if nombre not in existentes:
                cursor.execute("INSERT INTO roles (nombre, descripcion) VALUES (%s, %s)", (nombre, desc))
            else:
                cursor.execute("UPDATE roles SET descripcion = %s WHERE nombre = %s", (desc, nombre))
        conn.commit()
    finally:
        cursor.close()


def _retirar_rol_facturador(conn):
    """Desactiva cuentas del rol retirado y elimina su opción del catálogo de roles."""
    cursor = conn.cursor()
    try:
        cursor.execute(
            "UPDATE usuarios SET activo = 0 WHERE LOWER(rol) = LOWER(%s)",
            ('Facturador / Operador',)
        )
        cursor.execute(
            "DELETE FROM roles WHERE LOWER(nombre) = LOWER(%s)",
            ('Facturador / Operador',)
        )
        conn.commit()
    finally:
        cursor.close()


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
            INSERT INTO usuarios (usuario, password, rol, nombre, email, activo)
            VALUES (%s, %s, %s, %s, %s, 1)
            ''',
            (
                usuario,
                generate_password_hash(password),
                'Administrador',
                'Administrador Megaseg',
                'contacto@megaseg.ec',
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
                disponible, es_producto, destacado, tipo_producto, garantia,
                zona_cobertura, disponibilidad_atencion, modalidad_pago, ficha_tecnica, whatsapp_msg
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        '''

        for servicio in SERVICIOS_INICIALES:
            tipo_nombre, nombre, precio, imagen, descripcion, disponible, es_prod, dest = servicio
            tipo_id = categoria_por_nombre[tipo_nombre]
            tipo_producto = 'Equipo Físico' if es_prod else 'Servicio Operativo'
            garantia = '1 año de soporte técnico directo en Lago Agrio y garantía oficial.' if es_prod else 'Soporte técnico directo en Lago Agrio y garantía certificada por Megaseg.'
            zona = 'Nueva Loja (Lago Agrio), Shushufindi, Cascales, Cuyabeno y toda la provincia de Sucumbíos.'
            atencion = 'Central de monitoreo y respuesta operativa activa 24 horas, los 365 días del año.'
            pago = 'Emisión de factura autorizada por SRI, transferencias bancarias y planes empresariales.'
            ficha = f'Detalles técnicos y equipamiento homologado para {nombre}.'
            wa = f'Hola Megaseg, deseo cotizar {nombre}'

            cursor.execute(
                consulta,
                (
                    tipo_id, nombre, precio, imagen, descripcion, disponible,
                    es_prod, dest, tipo_producto, garantia, zona, atencion, pago, ficha, wa
                )
            )

        conn.commit()
    finally:
        cursor.close()


def _actualizar_datos_plantilla_servicios(conn):
    """Actualiza registros existentes que no tengan ficha técnica o garantía configurada."""
    cursor = conn.cursor()
    try:
        cursor.execute('''
            UPDATE servicios
            SET tipo_producto = CASE WHEN es_producto = 1 THEN 'Equipo Físico' ELSE 'Servicio Operativo' END
            WHERE tipo_producto IS NULL OR tipo_producto = ''
        ''')

        cursor.execute('''
            UPDATE servicios
            SET garantia = 'Soporte técnico directo en Lago Agrio y garantía certificada por Megaseg.'
            WHERE garantia IS NULL OR garantia = ''
        ''')

        cursor.execute('''
            UPDATE servicios
            SET zona_cobertura = 'Nueva Loja (Lago Agrio), Shushufindi, Cascales, Cuyabeno y toda la provincia de Sucumbíos.'
            WHERE zona_cobertura IS NULL OR zona_cobertura = ''
        ''')

        cursor.execute('''
            UPDATE servicios
            SET disponibilidad_atencion = 'Central de monitoreo y respuesta operativa activa 24 horas, los 365 días del año.'
            WHERE disponibilidad_atencion IS NULL OR disponibilidad_atencion = ''
        ''')

        cursor.execute('''
            UPDATE servicios
            SET modalidad_pago = 'Emisión de factura autorizada por SRI, transferencias bancarias y planes empresariales.'
            WHERE modalidad_pago IS NULL OR modalidad_pago = ''
        ''')

        cursor.execute('''
            UPDATE servicios
            SET whatsapp_msg = 'Hola Megaseg, deseo cotizar ' || nombre
            WHERE whatsapp_msg IS NULL OR whatsapp_msg = ''
        ''')

        # Si existe el Kit de 4 cámaras inicial y no tiene ficha técnica, enriquecemos sus datos
        cursor.execute('''
            UPDATE servicios
            SET ficha_tecnica = 'Incluye: 4 Cámaras Hikvision ColorVu Full HD con visión nocturna a color 24/7, 1 Grabador DVR pentahíbrido de 4 canales, 1 Disco Duro 1TB Western Digital Purple para grabación continua, 4 pares de video baluns, 4 fuentes de poder 12V e instalación configurada en smartphone.',
                tipo_producto = 'Equipo Físico',
                garantia = '1 año de garantía oficial de fábrica con soporte técnico directo en Lago Agrio.',
                es_producto = 1
            WHERE nombre LIKE '%Kit 4 Cámaras%' AND (ficha_tecnica IS NULL OR ficha_tecnica = '')
        ''')

        conn.commit()
    finally:
        cursor.close()


