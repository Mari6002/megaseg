"""Hash seguro y uniforme de las contraseñas de Megaseg."""

from werkzeug.security import generate_password_hash


def hash_password(plain_password: str) -> str:
    """Convierte una contraseña recibida en texto plano a un hash scrypt."""
    if not isinstance(plain_password, str) or not plain_password:
        raise ValueError('La contraseña debe ser un texto no vacío.')

    return generate_password_hash(plain_password, method='scrypt')
