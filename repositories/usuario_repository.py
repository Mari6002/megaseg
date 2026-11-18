"""Repositorio de persistencia y consultas para Usuarios y Roles del Sistema."""

from werkzeug.security import generate_password_hash
from conexion.conexion import get_db_connection


def listar_usuarios():
    """Recupera la lista de usuarios registrados con sus roles asignados."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT id, usuario, rol, nombre, email, telefono, activo, creado_en FROM usuarios ORDER BY id ASC')
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
    
    password_val = datos['password']
    if not (password_val.startswith('scrypt:') or password_val.startswith('pbkdf2:') or password_val.startswith('$2b$')):
        password_val = generate_password_hash(password_val)

    cursor.execute(
        '''
        INSERT INTO usuarios (usuario, password, rol, nombre, email, telefono, activo)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        RETURNING id
        ''',
        (
            datos['usuario'].strip(),
            password_val,
            datos.get('rol', 'Cliente'),
            datos['nombre'].strip(),
            (datos.get('email') or '').strip().lower(),
            (datos.get('telefono') or '').strip(),
            bool(datos.get('activo', True))
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


def obtener_usuario_por_id(usuario_id):
    """Obtiene un usuario por su identificador numérico."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT id, usuario, rol, nombre, email, telefono, activo, creado_en FROM usuarios WHERE id = %s', (usuario_id,))
    usuario = cursor.fetchone()
    cursor.close()
    return usuario
