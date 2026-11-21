"""Repositorio de persistencia y consultas para Usuarios y Roles del Sistema."""

from conexion.conexion import get_db_connection
from security.passwords import hash_password


def listar_usuarios():
    """Recupera la lista de usuarios registrados con sus roles asignados."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            '''
            SELECT u.id, u.usuario, r.nombre AS rol, u.nombre, u.email,
                   u.telefono, u.activo, u.creado_en
            FROM usuarios u
            JOIN roles r ON r.id = u.rol_id
            ORDER BY u.id ASC
            '''
        )
        usuarios = cursor.fetchall()
    except Exception:
        cursor.execute(
            'SELECT id, usuario, rol, nombre, email, telefono, activo, creado_en '
            'FROM usuarios ORDER BY id ASC'
        )
        usuarios = cursor.fetchall()
    cursor.close()
    return usuarios


def obtener_roles():
    """Devuelve los roles disponibles en el sistema con sus descripciones."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM roles ORDER BY id ASC')
    roles = cursor.fetchall()
    cursor.close()
    return roles


def existe_usuario(username):
    """Comprueba si un nombre de usuario ya está registrado."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT 1 FROM usuarios WHERE LOWER(usuario) = LOWER(%s)', (username.strip(),))
    existe = cursor.fetchone() is not None
    cursor.close()
    return existe


def existe_email(email):
    """Comprueba si un correo ya está registrado."""
    if not email or not email.strip():
        return False
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT 1 FROM usuarios WHERE LOWER(email) = LOWER(%s)', (email.strip(),))
    existe = cursor.fetchone() is not None
    cursor.close()
    return existe


def crear_usuario(datos):
    """Inserta un nuevo usuario en la base de datos asegurando el hash de contraseña."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    password_hash = hash_password(datos['password'])

    try:
        cursor.execute(
            'SELECT id FROM roles WHERE nombre = %s',
            (datos.get('rol', 'Cliente'),)
        )
        rol = cursor.fetchone()
        if not rol:
            raise RuntimeError('El rol seleccionado no existe.')
        cursor.execute(
            '''
            INSERT INTO usuarios (usuario, password, rol_id, nombre, email, telefono, activo)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id
            ''',
            (
                datos['usuario'].strip(), password_hash, rol['id'],
                datos['nombre'].strip(), (datos.get('email') or '').strip().lower(),
                (datos.get('telefono') or '').strip(), bool(datos.get('activo', True))
            )
        )
    except Exception:
        cursor.execute(
            '''
            INSERT INTO usuarios (usuario, password, rol, nombre, email, telefono, activo)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id
            ''',
            (
                datos['usuario'].strip(), password_hash, datos.get('rol', 'Cliente'),
                datos['nombre'].strip(), (datos.get('email') or '').strip().lower(),
                (datos.get('telefono') or '').strip(), bool(datos.get('activo', True))
            )
        )
    nuevo_id = cursor.fetchone()['id']
    conn.commit()
    cursor.close()
    return nuevo_id


def actualizar_rol(usuario_id, nuevo_rol):
    """Actualiza el rol asignado a un usuario."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('SELECT id FROM roles WHERE nombre = %s', (nuevo_rol,))
        rol = cursor.fetchone()
        if not rol:
            raise RuntimeError('El rol seleccionado no existe.')
        cursor.execute(
            'UPDATE usuarios SET rol_id = %s WHERE id = %s',
            (rol['id'], usuario_id)
        )
    except Exception:
        cursor.execute(
            'UPDATE usuarios SET rol = %s WHERE id = %s',
            (nuevo_rol, usuario_id)
        )
    conn.commit()
    cursor.close()


def cambiar_estado(usuario_id, activo):
    """Habilita o deshabilita el acceso a un usuario."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        'UPDATE usuarios SET activo = %s WHERE id = %s',
        (bool(activo), usuario_id)
    )
    conn.commit()
    cursor.close()


def actualizar_password(usuario_id, password_hash):
    """Reemplaza la contraseña de una cuenta por un nuevo hash."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        'UPDATE usuarios SET password = %s WHERE id = %s',
        (password_hash, usuario_id)
    )
    filas = cursor.rowcount
    conn.commit()
    cursor.close()
    return filas


def obtener_usuario_por_id(usuario_id):
    """Obtiene un usuario por su identificador numérico."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            '''
            SELECT u.id, u.usuario, r.nombre AS rol, u.nombre, u.email,
                   u.telefono, u.activo, u.creado_en
            FROM usuarios u
            JOIN roles r ON r.id = u.rol_id
            WHERE u.id = %s
            ''',
            (usuario_id,)
        )
        usuario = cursor.fetchone()
    except Exception:
        cursor.execute(
            'SELECT id, usuario, rol, nombre, email, telefono, activo, creado_en '
            'FROM usuarios WHERE id = %s',
            (usuario_id,)
        )
        usuario = cursor.fetchone()
    cursor.close()
    return usuario


def obtener_usuario_por_usuario_o_email(valor):
    """Obtiene una cuenta activa por usuario o correo para recuperación segura."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            '''
            SELECT u.id, u.usuario, u.nombre, u.email, u.activo, r.nombre AS rol
            FROM usuarios u
            JOIN roles r ON r.id = u.rol_id
            WHERE LOWER(u.usuario) = %s OR LOWER(u.email) = %s
            ''',
            (valor.strip().lower(), valor.strip().lower())
        )
        usuario = cursor.fetchone()
    except Exception:
        conn.rollback()
        cursor.execute(
            '''
            SELECT id, usuario, nombre, email, activo, rol
            FROM usuarios
            WHERE LOWER(usuario) = %s OR LOWER(email) = %s
            ''',
            (valor.strip().lower(), valor.strip().lower())
        )
        usuario = cursor.fetchone()
    cursor.close()
    return usuario
