# ==============================================================================
# PROYECTO: MEGASEG SEGURIDAD INTEGRAL - MODELO DE USUARIOS Y AUTENTICACIÓN
# ==============================================================================
# Implementa el modelo de usuario para Flask-Login y control de acceso (RBAC).
# ==============================================================================

from flask_login import UserMixin
from werkzeug.security import check_password_hash
import bcrypt


class User(UserMixin):
    """
    Modelo de Usuario compatible con Flask-Login.
    Representa a clientes, gestores de catálogo, operadores y administradores de Megaseg.
    """
    def __init__(self, id, usuario, password=None, rol="Cliente", nombre="Usuario", email="", telefono="", activo=1):
        self.id = id
        self.usuario = usuario
        self.password = password
        self.rol = rol or "Cliente"
        self.nombre = nombre or usuario
        self.email = email or ""
        self.telefono = telefono or ""
        self.activo = bool(activo)

    @property
    def is_active(self):
        """Requerido por Flask-Login: determina si la cuenta está habilitada."""
        return self.activo

    def is_admin(self):
        """Indica si el usuario cuenta con privilegios administrativos totales."""
        return (self.rol or "").lower() in ("admin", "administrador")

    def can_manage_catalog(self):
        """Indica si el usuario tiene permiso para crear, editar o actualizar el catálogo."""
        return self.has_role('Administrador', 'Gestor de Catálogo', 'Gestor de Catalogo', 'Supervisor')

    def has_role(self, *roles):
        """Comprueba si el usuario pertenece a uno de los roles solicitados."""
        roles_limpios = [r.lower().replace('á', 'a').replace('é', 'e').replace('í', 'i').replace('ó', 'o').replace('ú', 'u') for r in roles]
        mi_rol = (self.rol or "").lower().replace('á', 'a').replace('é', 'e').replace('í', 'i').replace('ó', 'o').replace('ú', 'u')
        return mi_rol in roles_limpios

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
                rol=fila.get('rol', 'Cliente'),
                nombre=fila.get('nombre', fila['usuario']),
                email=fila.get('email', ''),
                telefono=fila.get('telefono', ''),
                activo=fila.get('activo', 1)
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
                rol=fila.get('rol', 'Cliente'),
                nombre=fila.get('nombre', fila['usuario']),
                email=fila.get('email', ''),
                telefono=fila.get('telefono', ''),
                activo=fila.get('activo', 1)
            )
        return None
