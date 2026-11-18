"""Reinicia de forma segura la base SQLite local de Megaseg."""

import argparse
from datetime import datetime, timezone
from getpass import getpass
from pathlib import Path
import os
import secrets
import shutil
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv, set_key

from conexion.conexion import DB_PATH, get_db_connection
ENV_PATH = PROJECT_ROOT / '.env'
BACKUPS_PATH = PROJECT_ROOT / 'backups'


def actualizar_env(clave, valor):
    """Crea o actualiza una variable sin escribirla con formato inseguro."""
    set_key(str(ENV_PATH), clave, valor, quote_mode='always')


def main():
    parser = argparse.ArgumentParser(
        description='Crea una base SQLite nueva y una cuenta administradora nueva.'
    )
    parser.add_argument(
        '--confirm-reset',
        action='store_true',
        help='Confirma que la base local actual puede archivarse y reemplazarse.'
    )
    parser.add_argument(
        '--admin-user',
        default='',
        help='Nombre de usuario administrador; si se omite, se solicita de forma interactiva.'
    )
    args = parser.parse_args()

    if not args.confirm_reset:
        parser.error(
            'Esta operación reemplaza la base local. Usa --confirm-reset para confirmarla.'
        )

    load_dotenv(ENV_PATH, override=True)
    if os.getenv('DATABASE_URL') or (
        (os.getenv('USE_POSTGRES') or '').strip().lower() in ('1', 'true', 'yes')
        and (os.getenv('USE_SQLITE') or '').strip().lower() not in ('1', 'true', 'yes')
    ):
        raise SystemExit(
            'Este asistente solo reinicia SQLite y no modifica PostgreSQL. '
            'No se cambió ninguna base de datos.'
        )

    usuario = args.admin_user.strip()
    if not usuario:
        usuario = input('Usuario administrador nuevo: ').strip()
    if not usuario:
        raise SystemExit('El usuario administrador no puede estar vacio.')

    password = getpass('Nueva contraseña (mínimo 14 caracteres): ')
    confirmacion = getpass('Repite la nueva contraseña: ')
    if len(password) < 14:
        raise SystemExit('La contraseña debe tener al menos 14 caracteres.')
    if password != confirmacion:
        raise SystemExit('Las contraseñas no coinciden.')

    if not ENV_PATH.exists():
        ENV_PATH.write_text('', encoding='utf-8')

    actualizar_env('FLASK_ENV', 'development')
    actualizar_env('SECRET_KEY', secrets.token_urlsafe(48))
    actualizar_env('ADMIN_USERNAME', usuario)
    actualizar_env('ADMIN_PASSWORD', password)
    actualizar_env('SESSION_COOKIE_SECURE', 'false')
    actualizar_env('DATABASE_URL', '')
    actualizar_env('USE_POSTGRES', 'false')
    actualizar_env('USE_SQLITE', 'true')

    BACKUPS_PATH.mkdir(parents=True, exist_ok=True)
    if DB_PATH.exists():
        sello = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
        respaldo = BACKUPS_PATH / f'megaseg-pre-reset-{sello}.db'
        shutil.copy2(DB_PATH, respaldo)
        print(f'Respaldo creado: {respaldo}')
        DB_PATH.unlink()

    load_dotenv(ENV_PATH, override=True)
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            'SELECT COUNT(*) AS total FROM usuarios'
        )
        usuarios = cursor.fetchone()['total']
        cursor.execute(
            'SELECT COUNT(*) AS total FROM tipos_servicio'
        )
        categorias = cursor.fetchone()['total']
        cursor.execute(
            'SELECT COUNT(*) AS total FROM servicios'
        )
        servicios = cursor.fetchone()['total']
    finally:
        cursor.close()
        conn.close()

    print('Base SQLite reinicializada correctamente.')
    print(f'Usuarios: {usuarios}; categorias: {categorias}; servicios: {servicios}.')
    print('Ejecuta: python app.py')


if __name__ == '__main__':
    main()
