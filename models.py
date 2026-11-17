# ==============================================================================
# PROYECTO: MEGASEG SEGURIDAD INTEGRAL - MODELO DE USUARIOS Y AUTENTICACIÓN
# ==============================================================================
# Implementa el modelo de usuario para Flask-Login y control de acceso.
# ==============================================================================

from flask_login import UserMixin
from werkzeug.security import check_password_hash
import bcrypt


class User(UserMixin):
    """
    Modelo de Usuario compatible con Flask-Login.
    Representa a los administradores del sistema Megaseg.
    """
    def __init__(self, id, usuario, password=None, rol="Administrador", nombre="Admin", email=""):
        self.id = id
        self.usuario = usuario
        self.password = password
        self.rol = rol or "Administrador"
        self.nombre = nombre or usuario
        self.email = email or ""

    def is_admin(self):
        """Indica si el usuario cuenta con privilegios administrativos."""
        return (self.rol or "").lower() in ("admin", "administrador")

    def has_role(self, *roles):
        """Comprueba si el usuario pertenece a uno de los roles solicitados."""
        roles_limpios = [r.lower() for r in roles]
        return (self.rol or "").lower() in roles_limpios

    def verificar_password(self, password_plana):
        """Verifica hashes almacenados con Werkzeug o Bcrypt; nunca texto plano."""
        if not self.password or not password_plana:
            return False

        # Intento 1: Werkzeug Hash (scrypt / pbkdf2)
        try:
            if check_password_hash(self.password, password_plana):
                return True
        except (TypeError, ValueError):
            pass

        # Intento 2: Bcrypt
        try:
            hash_bytes = self.password.encode('utf-8') if isinstance(self.password, str) else self.password
            pass_bytes = password_plana.encode('utf-8') if isinstance(password_plana, str) else password_plana
            if bcrypt.checkpw(pass_bytes, hash_bytes):
                return True
        except (TypeError, ValueError):
            pass

        return False

    @staticmethod
    def get_by_id(user_id):
        """Recupera un usuario por su ID numérico."""
        from conexion.conexion import get_db_connection
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM usuarios WHERE id = %s", (user_id,))
        fila = cursor.fetchone()
        cursor.close()
        if fila:
            return User(
                id=fila['id'],
                usuario=fila['usuario'],
                password=fila['password'],
                rol=fila.get('rol', 'Administrador'),
                nombre=fila.get('nombre', 'Administrador'),
                email=fila.get('email', '')
            )
        return None

    @staticmethod
    def get_by_usuario(username_o_email):
        """Recupera un usuario por su nombre de usuario o email."""
        from conexion.conexion import get_db_connection
        conn = get_db_connection()
        cursor = conn.cursor()
        valor = (username_o_email or "").strip().lower()
        cursor.execute("SELECT * FROM usuarios WHERE LOWER(usuario) = %s OR LOWER(email) = %s", (valor, valor))
        fila = cursor.fetchone()
        cursor.close()
        if fila:
            return User(
                id=fila['id'],
                usuario=fila['usuario'],
                password=fila['password'],
                rol=fila.get('rol', 'Administrador'),
                nombre=fila.get('nombre', 'Administrador'),
                email=fila.get('email', '')
            )
        return None
