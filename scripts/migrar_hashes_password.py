"""Convierte contraseñas heredadas en texto plano a hashes scrypt."""

import argparse
import os
from pathlib import Path
import re
import sys

from dotenv import load_dotenv, set_key
from werkzeug.security import check_password_hash

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from security.passwords import hash_password

ENV_PATH = PROJECT_ROOT / '.env'
WERKZEUG_HASH = re.compile(
    r'^(?:scrypt:\d+:\d+:\d+|pbkdf2:[a-z0-9_]+:\d+)'
    r'\$[A-Za-z0-9_-]+\$[A-Za-z0-9_+/=-]+$'
)
BCRYPT_HASH = re.compile(r'^\$2[aby]\$\d{2}\$[./A-Za-z0-9]{53}$')
LEGACY_DIGEST = re.compile(r'^(?:[0-9a-fA-F]{32}|[0-9a-fA-F]{40}|[0-9a-fA-F]{64}|[0-9a-fA-F]{128})$')


def _formato_hash(password):
    """Reconoce los hashes que el modelo de usuario puede verificar."""
    return bool(
        WERKZEUG_HASH.fullmatch(password)
        or BCRYPT_HASH.fullmatch(password)
    )


def main():
    parser = argparse.ArgumentParser(
        description=(
            'Detecta contraseñas heredadas de usuarios; por defecto no modifica '
            'la base de datos.'
        )
    )
    parser.add_argument(
        '--apply',
        action='store_true',
        help='Aplica dentro de una transacción los hashes pendientes.',
    )
    args = parser.parse_args()

    load_dotenv(ENV_PATH, override=True)
    use_postgres = (os.getenv('USE_POSTGRES') or '').strip().lower() in ('1', 'true', 'yes')
    use_sqlite = (os.getenv('USE_SQLITE') or '').strip().lower() in ('1', 'true', 'yes')
    if use_sqlite or not (use_postgres or (os.getenv('DATABASE_URL') or '').strip()):
        raise SystemExit(
            'La migración requiere PostgreSQL habilitado en .env; no se modificó ninguna base.'
        )

    from conexion.conexion import get_db_connection

    connection = get_db_connection()
    cursor = connection.cursor()
    try:
        cursor.execute('SELECT id, password FROM usuarios ORDER BY id')
        rows = cursor.fetchall()
        pendientes = []
        formatos_no_soportados = 0

        for row in rows:
            password = row['password']
            if not isinstance(password, str):
                raise RuntimeError(
                    'Se encontró una contraseña con formato de almacenamiento inesperado; '
                    'no se modificó la base.'
                )
            if _formato_hash(password):
                continue
            if password.startswith('$argon2') or LEGACY_DIGEST.fullmatch(password):
                formatos_no_soportados += 1
                continue
            pendientes.append((row['id'], password))

        if formatos_no_soportados:
            raise RuntimeError(
                f'Hay {formatos_no_soportados} contraseña(s) con un hash heredado '
                'que la aplicación no reconoce. No se modificó la base; '
                'restablece esas contraseñas antes de continuar.'
            )

        if not args.apply:
            print(f'Cuentas revisadas: {len(rows)}.')
            print(f'Contraseñas que ya tienen un hash compatible: {len(rows) - len(pendientes)}.')
            print(f'Contraseñas heredadas que necesitan hash: {len(pendientes)}.')
            if pendientes:
                print('Para convertirlas conservando su contraseña actual, ejecuta:')
                print('python scripts/migrar_hashes_password.py --apply')
            return

        for user_id, plain_password in pendientes:
            password_hash = hash_password(plain_password)
            if not check_password_hash(password_hash, plain_password):
                raise RuntimeError(
                    'No se pudo verificar un hash generado; se cancelaron todos los cambios.'
                )
            cursor.execute(
                'UPDATE usuarios SET password = %s WHERE id = %s AND password = %s',
                (password_hash, user_id, plain_password),
            )
            if cursor.rowcount != 1:
                raise RuntimeError(
                    'Una cuenta cambió durante la migración; se cancelaron todos los cambios.'
                )

        connection.commit()
        if pendientes and ENV_PATH.exists():
            set_key(str(ENV_PATH), 'ADMIN_PASSWORD', '', quote_mode='always')
        print(f'Migración completada: {len(pendientes)} contraseña(s) convertida(s) a scrypt.')
        print(f'Cuentas que ya tenían un hash compatible: {len(rows) - len(pendientes)}.')
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()
        connection.close()


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        print(f'ERROR: {error}')
        raise SystemExit(1) from error
