"""Pruebas de roles, aprobación administrativa y retiro del módulo de facturación."""

import os
from pathlib import Path
from tempfile import TemporaryDirectory

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent
load_dotenv(PROJECT_ROOT / '.env')
os.environ.update({
    'USE_POSTGRES': 'false',
    'USE_SQLITE': 'true',
    'ADMIN_USERNAME': 'test_admin',
    'ADMIN_PASSWORD': 'TestAdminPassword_123!'
})

import conexion.conexion as database

test_database = TemporaryDirectory(prefix='megaseg-access-test-')
database.DB_PATH = Path(test_database.name) / 'megaseg-test.db'

import app

app.app.config['TESTING'] = True
app.app.config['WTF_CSRF_ENABLED'] = False
client = app.app.test_client()


def register(username, role, email):
    return client.post('/registro', data={
        'usuario': username,
        'nombre': f'Test {username}',
        'email': email,
        'telefono': '0981112233',
        'rol': role,
        'password': 'TestPassword123!',
        'confirm_password': 'TestPassword123!'
    }, follow_redirects=True)


def login(username, password='TestAdminPassword_123!'):
    return client.post('/login', data={
        'usuario': username,
        'password': password
    }, follow_redirects=True)


connection = None
cursor = None
try:
    response = login('test_admin')
    assert response.status_code == 200
    assert b'Bienvenido' in response.data

    response = client.get('/admin/usuarios')
    assert response.status_code == 200
    assert b'Facturador / Operador' not in response.data
    print('Roles retirados del panel de administración.')

    response = client.get('/facturacion')
    assert response.status_code == 404
    print('Rutas de facturación retiradas.')

    client.post('/logout', follow_redirects=True)
    response = register('cliente_test', 'Cliente', 'cliente@test.com')
    assert response.status_code == 200
    assert b'Bienvenido a Megaseg' in response.data
    connection = database.get_db_connection()
    cursor = connection.cursor()
    cursor.execute("SELECT id, activo FROM usuarios WHERE usuario = %s", ('cliente_test',))
    client_user = cursor.fetchone()
    assert client_user and bool(client_user['activo'])
    client.post('/logout', follow_redirects=True)
    print('Cliente activo inmediatamente.')

    response = register('gestor_test', 'Gestor de Catálogo', 'gestor@test.com')
    assert response.status_code == 200
    assert b'requiere ser admitido por cualquier Administrador' in response.data
    cursor.execute("SELECT id, activo FROM usuarios WHERE usuario = %s", ('gestor_test',))
    manager = cursor.fetchone()
    assert manager and not bool(manager['activo'])

    response = login('gestor_test', 'TestPassword123!')
    assert b'inactiva' in response.data
    login('test_admin')
    response = client.post(
        f"/admin/cambiar-estado/{manager['id']}",
        follow_redirects=True
    )
    assert response.status_code == 200
    assert b'ha sido ADMITIDO exitosamente' in response.data
    cursor.execute('SELECT activo FROM usuarios WHERE id = %s', (manager['id'],))
    assert bool(cursor.fetchone()['activo'])
    print('Rol operativo bloqueado hasta la admisión administrativa.')

    client.post('/logout', follow_redirects=True)
    response = register('admin_pendiente', 'Administrador', 'admin-pendiente@test.com')
    assert response.status_code == 200
    cursor.execute("SELECT activo FROM usuarios WHERE usuario = %s", ('admin_pendiente',))
    assert not bool(cursor.fetchone()['activo'])

    login('test_admin')
    response = client.post(
        f"/admin/cambiar-rol/{manager['id']}",
        data={'nuevo_rol': 'Facturador / Operador'},
        follow_redirects=True
    )
    assert 'El rol seleccionado no es válido'.encode('utf-8') in response.data
    cursor.execute('SELECT rol FROM usuarios WHERE id = %s', (manager['id'],))
    assert cursor.fetchone()['rol'] == 'Gestor de Catálogo'
    print('Roles inválidos rechazados.')

    client.post('/logout', follow_redirects=True)
    original_db_path = database.DB_PATH
    original_admin = os.environ.get('ADMIN_USERNAME')
    original_password = os.environ.get('ADMIN_PASSWORD')
    with TemporaryDirectory(prefix='megaseg-first-admin-test-') as empty_db_dir:
        database.DB_PATH = Path(empty_db_dir) / 'empty.db'
        os.environ['ADMIN_USERNAME'] = ''
        os.environ['ADMIN_PASSWORD'] = ''
        response = register(
            'first_admin_request',
            'Administrador',
            'first-admin@test.com'
        )
        assert b'requiere ser admitido' in response.data
        connection.close()
        connection = database.get_db_connection()
        cursor = connection.cursor()
        cursor.execute(
            "SELECT activo FROM usuarios WHERE usuario = %s",
            ('first_admin_request',)
        )
        assert not bool(cursor.fetchone()['activo'])
        login_response = login('first_admin_request', 'TestPassword123!')
        assert b'inactiva' in login_response.data
        cursor.close()
        cursor = None
        connection.close()
        connection = None
    database.DB_PATH = original_db_path
    os.environ['ADMIN_USERNAME'] = original_admin or ''
    os.environ['ADMIN_PASSWORD'] = original_password or ''

    print('Registro público no crea un primer Administrador sin aprobación.')
finally:
    if cursor:
        cursor.close()
    if connection:
        connection.close()
    try:
        with app.app.app_context():
            app.close_db_connection(None)
    except Exception:
        pass
    test_database.cleanup()

print('Todas las pruebas de acceso y roles pasaron.')
