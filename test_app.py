from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
import atexit
import os
import gc

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

test_database = TemporaryDirectory(prefix='megaseg-test-')
database.DB_PATH = Path(test_database.name) / 'megaseg-test.db'


def cleanup_test_database():
    connection = globals().get('conn')
    if connection:
        try:
            connection.close()
        except Exception:
            pass
    try:
        with app.app.app_context():
            app.close_db_connection(None)
    except Exception:
        pass
    gc.collect()
    test_database.cleanup()


atexit.register(cleanup_test_database)

import app

app.app.config['TESTING'] = True
app.app.config['WTF_CSRF_ENABLED'] = False

client = app.app.test_client()

# 1. Test Home
res = client.get('/')
assert res.status_code == 200, f'Home failed: {res.status_code}'
assert b'MEGASEG' in res.data, 'Megaseg not in home'
print('1. Home page OK')

# 2. Test Catalog
res = client.get('/servicios')
assert res.status_code == 200, f'Catalog failed: {res.status_code}'
print('2. Catalog page OK')

# 3. Test Login
admin_username = os.getenv('ADMIN_USERNAME')
admin_password = os.getenv('ADMIN_PASSWORD')
res = client.post(
    '/login',
    data={'usuario': admin_username, 'password': admin_password},
    follow_redirects=True
)
assert res.status_code == 200, f'Login failed: {res.status_code}'
assert 'Modo administrador activado'.encode('utf-8') in res.data or 'Bienvenido'.encode('utf-8') in res.data
print('3. Login authentication OK')

# 4. Test New Service Creation with a local image upload
static_folder_original = app.app.static_folder
with TemporaryDirectory() as carpeta_temporal:
    app.app.static_folder = carpeta_temporal
    try:
        res_new = client.post('/servicios/nuevo', data={
            'tipo_servicio_id': 1,
            'es_producto': 0,
            'nombre': 'Servicio Test Automatizado',
            'precio': 99.99,
            'imagen': '',
            'imagen_archivo': (BytesIO(b'\x89PNG\r\n\x1a\n' + b'\x00' * 16), 'camara.png'),
            'descripcion': 'Descripcion de prueba automatizada para verificar el CRUD.',
            'disponible': 'y',
            'destacado': 'y'
        }, follow_redirects=True)
    finally:
        app.app.static_folder = static_folder_original
    archivos_subidos = list((Path(carpeta_temporal) / 'imagenes' / 'catalogo').glob('*.png'))
    assert len(archivos_subidos) == 1, 'Uploaded image was not saved to the catalog folder'

assert res_new.status_code == 200, f'Create service failed: {res_new.status_code}'
assert b'Servicio Test Automatizado' in res_new.data, 'New service not found in catalog'
res_bad_image = client.post('/servicios/nuevo', data={
    'tipo_servicio_id': 1,
    'es_producto': 0,
    'nombre': 'Servicio con ruta inválida',
    'precio': 99.99,
    'imagen': '/static/imagenes/camaras-cctv.svg',
    'descripcion': 'Descripcion de prueba para validar enlaces de imagen.',
    'disponible': 'y'
})
assert res_bad_image.status_code == 200
assert 'El enlace debe comenzar'.encode('utf-8') in res_bad_image.data
res_search = client.get('/servicios?q=Servicio+Test+Automatizado')
assert res_search.status_code == 200
assert b'Servicio Test Automatizado' in res_search.data, 'Catalog search failed'
print('4. Service creation OK')

# 5. Verify in DB and get ID
conn = database.get_db_connection()
c = conn.cursor()
c.execute("SELECT id, imagen FROM servicios WHERE nombre = %s", ('Servicio Test Automatizado',))
row = c.fetchone()
assert row is not None, 'Service not found in DB'
test_id = row['id']
imagen_guardada = row['imagen']
assert imagen_guardada.startswith('/static/imagenes/catalogo/'), 'Uploaded image URL is incorrect'
print(f'5. Image upload and database persistence OK (ID: {test_id})')

# 6. Test Edit
res_edit = client.post(f'/servicios/editar/{test_id}', data={
    'tipo_servicio_id': 1,
    'es_producto': 0,
    'nombre': 'Servicio Test Editado',
    'precio': 150.00,
    'imagen': '',
    'descripcion': 'Descripcion actualizada y verificada.',
    'disponible': 'y'
}, follow_redirects=True)
assert res_edit.status_code == 200
assert b'Servicio Test Editado' in res_edit.data
c.execute("SELECT imagen FROM servicios WHERE id = %s", (test_id,))
assert c.fetchone()['imagen'] == imagen_guardada, 'Editing without a replacement must preserve the image'
print('6. Service edit OK')

# Replacing the image with a web URL updates the existing record.
res_url_edit = client.post(f'/servicios/editar/{test_id}', data={
    'tipo_servicio_id': 1,
    'es_producto': 0,
    'nombre': 'Servicio Test Editado',
    'precio': 150.00,
    'imagen': 'https://example.com/camara.jpg',
    'descripcion': 'Descripcion actualizada y verificada.',
    'disponible': 'y'
}, follow_redirects=True)
assert res_url_edit.status_code == 200
c.execute("SELECT imagen FROM servicios WHERE id = %s", (test_id,))
assert c.fetchone()['imagen'] == 'https://example.com/camara.jpg'
print('6a. Image replacement by URL OK')

# 7. Test Delete
res_del = client.post(f'/servicios/eliminar/{test_id}', follow_redirects=True)
assert res_del.status_code == 200
assert 'fue eliminado'.encode('utf-8') in res_del.data

# Verify in DB that it is gone
c.execute("SELECT id FROM servicios WHERE id = %s", (test_id,))
assert c.fetchone() is None, 'Service still exists in DB!'
print('7. Service deletion and DB cleanup OK')

# 8. Test Logout
res_logout = client.post('/logout', follow_redirects=True)
assert res_logout.status_code == 200
print('8. Logout OK')

# 9. Test Pagination (12 items per page)
for index in range(4):
    app.servicio_repository.crear_servicio({
        'tipo_servicio_id': 1,
        'nombre': f'Servicio de paginación {index}',
        'precio_base': 10.00,
        'imagen': '',
        'descripcion': 'Registro temporal de prueba de paginación.',
        'disponible': True,
        'es_producto': 0,
        'destacado': False
    })

res_page1 = client.get('/servicios?page=1')
assert res_page1.status_code == 200
assert 'badgeTotalServicios">12</span>'.encode('utf-8') in res_page1.data
assert '12 por'.encode('utf-8') in res_page1.data

res_page2 = client.get('/servicios?page=2')
assert res_page2.status_code == 200
assert 'badgeTotalServicios">1</span>'.encode('utf-8') in res_page2.data
assert 'de <strong class="text-white">2</strong>'.encode('utf-8') in res_page2.data
print('9. Pagination of 12 items per page OK')

c.close()
conn.close()
print('\n>>> ALL FULL-STACK END-TO-END TESTS PASSED! <<<')
