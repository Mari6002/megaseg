"""Adapta la columna de rol de PostgreSQL al esquema que usa Megaseg."""

import argparse
from datetime import datetime, timezone
import os
from pathlib import Path
import shutil
import subprocess

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ENV_PATH = PROJECT_ROOT / '.env'
BACKUPS_PATH = PROJECT_ROOT / 'backups'


def _pg_dump_path():
    """Localiza pg_dump en PATH o en la instalación estándar de Windows."""
    executable = shutil.which('pg_dump')
    if executable:
        return executable

    candidates = sorted(
        Path('C:/Program Files/PostgreSQL').glob('*/bin/pg_dump.exe'),
        reverse=True,
    )
    if candidates:
        return str(candidates[0])

    raise RuntimeError(
        'No se encontró pg_dump. Instala las herramientas de PostgreSQL antes de migrar.'
    )


def _backup_database():
    """Guarda un respaldo completo antes de modificar el esquema."""
    BACKUPS_PATH.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    backup_path = BACKUPS_PATH / f'megaseg-pre-rol-migration-{timestamp}.dump'
    environment = os.environ.copy()
    environment['PGPASSWORD'] = os.getenv('DB_PASSWORD', '')

    command = [
        _pg_dump_path(),
        '--no-password',
        '--format=custom',
        '--host', os.getenv('DB_HOST', 'localhost'),
        '--port', os.getenv('DB_PORT', '5432'),
        '--username', os.getenv('DB_USER', 'postgres'),
        '--dbname', os.getenv('DB_NAME', 'megaseg'),
        '--file', str(backup_path),
    ]
    try:
        subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True,
            env=environment,
        )
    except subprocess.CalledProcessError as error:
        backup_path.unlink(missing_ok=True)
        details = (error.stderr or '').strip()
        raise RuntimeError(
            'No se pudo crear el respaldo PostgreSQL; no se modificó la base.'
            + (f' Detalle: {details}' if details else '')
        ) from error

    return backup_path


def main():
    parser = argparse.ArgumentParser(
        description=(
            'Migra usuarios.rol_id a usuarios.rol para que el registro y los roles '
            'sean compatibles con la aplicación Megaseg.'
        )
    )
    parser.add_argument(
        '--apply',
        action='store_true',
        help='Crea un respaldo y aplica la migración transaccional.',
    )
    args = parser.parse_args()

    load_dotenv(ENV_PATH, override=True)
    if (os.getenv('DATABASE_URL') or '').strip():
        raise SystemExit(
            'La migración está limitada a PostgreSQL local configurado con DB_HOST/DB_PORT.'
        )
    if (os.getenv('USE_POSTGRES') or '').strip().lower() not in ('1', 'true', 'yes'):
        raise SystemExit('Configura USE_POSTGRES=true en .env.')
    if (os.getenv('USE_SQLITE') or '').strip().lower() in ('1', 'true', 'yes'):
        raise SystemExit('Configura USE_SQLITE=false en .env.')

    import psycopg2

    connection = psycopg2.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        port=int(os.getenv('DB_PORT', '5432')),
        dbname=os.getenv('DB_NAME', 'megaseg'),
        user=os.getenv('DB_USER', 'postgres'),
        password=os.getenv('DB_PASSWORD', ''),
        connect_timeout=5,
    )
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_schema = 'public' AND table_name = 'usuarios'"
            )
            columns = {row[0] for row in cursor.fetchall()}
            if not {'id', 'rol_id'}.issubset(columns):
                if 'rol' in columns:
                    print('La tabla usuarios ya usa la columna rol de Megaseg; no hay cambios.')
                    return
                raise RuntimeError(
                    'La tabla usuarios no tiene el esquema esperado (id y rol_id). '
                    'No se modificó la base.'
                )
            if 'rol' in columns:
                raise RuntimeError(
                    'La tabla tiene rol y rol_id a la vez. Revisa manualmente sus valores; '
                    'no se modificó la base.'
                )

            cursor.execute(
                'SELECT COUNT(*) FROM usuarios u '
                'LEFT JOIN roles r ON r.id = u.rol_id '
                'WHERE r.id IS NULL OR r.nombre IS NULL'
            )
            invalid_roles = cursor.fetchone()[0]
            cursor.execute('SELECT COUNT(*) FROM usuarios')
            user_count = cursor.fetchone()[0]

        print(
            f'PostgreSQL {os.getenv("DB_NAME", "megaseg")}: '
            f'{user_count} usuario(s); {invalid_roles} rol(es) sin correspondencia.'
        )
        if invalid_roles:
            raise RuntimeError(
                'Hay usuarios sin un rol válido. Corrige esas referencias antes de migrar.'
            )
        if not args.apply:
            print(
                'Revisión completada sin cambios. Con --apply se respaldará la base '
                'y se copiarán los nombres de rol antes de retirar usuarios.rol_id.'
            )
            return

        backup_path = _backup_database()
        try:
            with connection:
                with connection.cursor() as cursor:
                    cursor.execute(
                        'ALTER TABLE usuarios ADD COLUMN rol VARCHAR(50)'
                    )
                    cursor.execute(
                        'UPDATE usuarios u SET rol = r.nombre '
                        'FROM roles r WHERE r.id = u.rol_id'
                    )
                    cursor.execute(
                        'SELECT COUNT(*) FROM usuarios WHERE rol IS NULL OR rol = %s',
                        ('',),
                    )
                    if cursor.fetchone()[0]:
                        raise RuntimeError(
                            'No se pudo copiar el rol de todas las cuentas; '
                            'se revirtió la migración.'
                        )
                    cursor.execute(
                        "ALTER TABLE usuarios ALTER COLUMN rol SET DEFAULT 'Cliente'"
                    )
                    cursor.execute(
                        'ALTER TABLE usuarios ALTER COLUMN rol SET NOT NULL'
                    )
                    cursor.execute(
                        'ALTER TABLE usuarios DROP COLUMN rol_id'
                    )
        except Exception:
            print(f'La migración se revirtió. Respaldo disponible en: {backup_path}')
            raise

        print('Migración completada: usuarios.rol_id se convirtió a usuarios.rol.')
        print(f'Respaldo creado: {backup_path}')
    finally:
        connection.close()


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        print(f'ERROR: {error}')
        raise SystemExit(1) from error
