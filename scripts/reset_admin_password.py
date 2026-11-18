"""Cambia de forma interactiva la contraseña del administrador."""

from getpass import getpass
from pathlib import Path
import os
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv, set_key
from werkzeug.security import generate_password_hash

from conexion.conexion import get_db_connection


ENV_PATH = PROJECT_ROOT / '.env'


def main():
    load_dotenv(ENV_PATH, override=True)
    usuario = (os.getenv('ADMIN_USERNAME') or '').strip()
    if not usuario:
        raise SystemExit('Configura ADMIN_USERNAME en .env antes de continuar.')

    nueva = getpass('Nueva contraseña (mínimo 14 caracteres): ')
    confirmacion = getpass('Repite la nueva contraseña: ')
    if len(nueva) < 14:
        raise SystemExit('La contraseña debe tener al menos 14 caracteres.')
    if nueva != confirmacion:
        raise SystemExit('Las contraseñas no coinciden.')

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            'UPDATE usuarios SET password = %s WHERE LOWER(usuario) = %s',
            (generate_password_hash(nueva), usuario.lower())
        )
        if cursor.rowcount != 1:
            conn.rollback()
            raise SystemExit('No se encontró exactamente una cuenta con ese usuario.')
        conn.commit()
        set_key(str(ENV_PATH), 'ADMIN_PASSWORD', nueva, quote_mode='always')
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()

    print('Contraseña actualizada y guardada en .env.')


if __name__ == '__main__':
    main()
