# ==============================================================================
# PROYECTO: MEGASEG SEGURIDAD INTEGRAL - CONTROLADOR PRINCIPAL FLASK (BACKEND)
# Arquitectura y Funcionamiento Inspirado en NexoDigital
# ==============================================================================
# Este archivo contiene la configuración central del servidor y los controladores
# (rutas y vistas) que gestionan la lógica de negocio para:
# 1. Página de inicio y presentación de Grupo Megaseg Cía. Ltda.
# 2. Catálogo público y gestión de Servicios & Productos (CRUD para Administrador)
# 3. Autenticación y control de acceso con Flask-Login y Flask-WTF (CSRF)
# 4. Cotizador interactivo con integración a WhatsApp
# 5. Soporte dual de Base de Datos: SQLite (local automático) y PostgreSQL (nube)
# ==============================================================================

import os
from pathlib import Path
from urllib.parse import urlsplit
from uuid import uuid4
from functools import wraps
from flask import Flask, render_template, redirect, url_for, flash, request
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_wtf.csrf import CSRFProtect
from werkzeug.exceptions import RequestEntityTooLarge
from werkzeug.utils import secure_filename

# Módulos del Sistema
from conexion.conexion import get_db_connection, close_db_connection
from models import User
from forms.login_form import LoginForm
from forms.servicio_form import ServicioForm
from repositories import servicio_repository

# ------------------------------------------------------------------------------
# INICIALIZACIÓN DE LA APLICACIÓN FLASK
# ------------------------------------------------------------------------------
app = Flask(__name__)

# Clave secreta para sesiones y formularios Flask-WTF con CSRF
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
if not app.config['SECRET_KEY']:
    raise RuntimeError('Configura SECRET_KEY en el entorno antes de iniciar la aplicación.')

app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_SECURE'] = os.getenv('SESSION_COOKIE_SECURE', '').lower() in ('1', 'true', 'yes')
app.config['MAX_CONTENT_LENGTH'] = 6 * 1024 * 1024
csrf = CSRFProtect(app)


def guardar_imagen_subida(archivo):
    """Guarda una imagen validada en una carpeta pública con nombre único."""
    nombre_seguro = secure_filename(archivo.filename)
    extension = Path(nombre_seguro).suffix.lower()
    nombre_archivo = f'{uuid4().hex}{extension}'
    carpeta_imagenes = Path(app.static_folder) / 'imagenes' / 'catalogo'
    carpeta_imagenes.mkdir(parents=True, exist_ok=True)
    archivo.save(carpeta_imagenes / nombre_archivo)
    return url_for('static', filename=f'imagenes/catalogo/{nombre_archivo}')


def url_imagen_actual(imagen):
    """Convierte una ruta histórica del campo imagen a una URL para el preview."""
    if not imagen:
        return ''

    enlace = urlsplit(imagen)
    if enlace.scheme in ('http', 'https') and enlace.netloc:
        return imagen
    if imagen.startswith('/static/'):
        return imagen
    ruta_static = imagen[7:] if imagen.startswith('static/') else imagen
    if not ruta_static.startswith('/'):
        return url_for('static', filename=ruta_static)
    return ''


def es_destino_interno(destino):
    """Solo permite redirecciones a rutas locales de este sitio."""
    if not destino:
        return False

    try:
        partes = urlsplit(destino)
    except ValueError:
        return False

    return (
        not partes.scheme
        and not partes.netloc
        and destino.startswith('/')
        and not destino.startswith('//')
        and '\\' not in destino
        and '\r' not in destino
        and '\n' not in destino
    )

# ------------------------------------------------------------------------------
# CONFIGURACIÓN DE FLASK-LOGIN
# ------------------------------------------------------------------------------
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Inicia sesión para gestionar el catálogo de servicios y productos.'
login_manager.login_message_category = 'warning'


@app.errorhandler(RequestEntityTooLarge)
def imagen_supera_limite(error):
    """Devuelve al formulario si la petición excede el límite de carga."""
    flash('El archivo supera el límite permitido. La imagen debe pesar hasta 5 MB.', 'danger')
    if request.endpoint in ('nuevo_servicio', 'editar_servicio'):
        return redirect(url_for(request.endpoint, **(request.view_args or {})))
    return error, 413


@login_manager.user_loader
def load_user(user_id):
    """Carga la instancia de usuario activa para Flask-Login."""
    try:
        return User.get_by_id(int(user_id))
    except Exception:
        return None


# ------------------------------------------------------------------------------
# GESTIÓN DEL CICLO DE VIDA DE LA CONEXIÓN A BASE DE DATOS
# ------------------------------------------------------------------------------
@app.teardown_appcontext
def teardown_db(exception):
    """Garantiza el cierre automático de la conexión al terminar cada petición."""
    close_db_connection(exception)


# ------------------------------------------------------------------------------
# CONTEXT PROCESSOR (DATOS INSTITUCIONALES GLOBALES)
# ------------------------------------------------------------------------------
@app.context_processor
def inject_empresa_info():
    """Inyecta los datos de contacto, institucionales y razón social a todas las plantillas Jinja2."""
    return {
        'empresa': {
            'nombre': 'Grupo de Seguridad Megaseg Cía. Ltda.',
            'siglas': 'MEGASEG LTDA.',
            'ubicacion': 'Calle Jorge Añazco 117 y Vía Colombia, Lago Agrio, Sucumbíos',
            'telefono': '+593 98 290 0705',
            'telefono_fijo': '(06) 283-0000',
            'whatsapp': '593982900705',
            'email': 'contacto@megaseg.ec',
            'facebook': 'https://www.facebook.com/megaseg.ec/',
            'mision': 'Proveer servicios de seguridad física y tecnológica con los más altos estándares de calidad, garantizando la custodia eficaz de personas, bienes e instalaciones en Sucumbíos con personal acreditado y tecnología de vanguardia.',
            'vision': 'Ser la empresa referente de seguridad privada e innovación electrónica en la región oriental del Ecuador, reconocida por la excelencia operativa, rapidez de respuesta y confiabilidad inquebrantable de nuestras soluciones.',
            'anio': 2026
        }
    }


def admin_required(f):
    """Decorador para proteger rutas exclusivas de administración."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin():
            flash('Acceso restringido. Solo los administradores pueden gestionar el catálogo.', 'danger')
            return redirect(url_for('inicio'))
        return f(*args, **kwargs)
    return decorated_function


# ==============================================================================
# RUTAS PÚBLICAS Y DE PORTADA
# ==============================================================================

@app.route('/')
def inicio():
    """
    Ruta de la portada principal (Landing Page).
    Muestra presentación corporativa, misión/visión, servicios destacados y cotizador.
    """
    servicios_destacados = servicio_repository.obtener_destacados()
    return render_template('index.html', servicios_destacados=servicios_destacados)


# ==============================================================================
# RUTAS DEL CATÁLOGO DE SERVICIOS Y PRODUCTOS (CRUD)
# ==============================================================================

@app.route('/servicios')
@app.route('/productos')
@app.route('/catalogo')
def servicios():
    """
    Ruta del catálogo completo de servicios y productos con paginación de 12 ítems por hoja.
    Pública para consulta, búsqueda multicriterio y cotización directa por WhatsApp.
    Muestra controles de Editar/Eliminar exclusivamente para el Administrador autenticado.
    """
    import math

    q = request.args.get('q', '').strip()
    tipo = request.args.get('tipo', '').strip()
    disp = request.args.get('disp', '').strip()
    orden = request.args.get('orden', '').strip()
    
    try:
        page = int(request.args.get('page', 1))
        if page < 1:
            page = 1
    except (ValueError, TypeError):
        page = 1

    por_pagina = 12

    tipos_servicio = servicio_repository.obtener_tipos()
    total_items = servicio_repository.contar_servicios(q, tipo, disp)

    # 2. Paginación
    total_paginas = max(1, math.ceil(total_items / por_pagina)) if total_items > 0 else 1
    if page > total_paginas:
        page = total_paginas

    offset = (page - 1) * por_pagina

    lista_servicios = servicio_repository.listar_servicios(
        busqueda=q,
        tipo=tipo,
        disponibilidad=disp,
        orden=orden,
        limite=por_pagina,
        desplazamiento=offset
    )

    # Rangos de ítems mostrados
    items_desde = offset + 1 if total_items > 0 else 0
    items_hasta = min(offset + por_pagina, total_items)

    # Rango de botones numéricos (hasta 5 páginas centradas)
    start_page = max(1, page - 2)
    end_page = min(total_paginas, page + 2)
    rango_paginas = list(range(start_page, end_page + 1))

    return render_template(
        'servicios.html',
        servicios=lista_servicios,
        tipos_servicio=tipos_servicio,
        query_busqueda=q,
        tipo_seleccionado=tipo,
        disp_seleccionado=disp,
        orden_seleccionado=orden,
        pagina_actual=page,
        total_paginas=total_paginas,
        total_items=total_items,
        por_pagina=por_pagina,
        items_desde=items_desde,
        items_hasta=items_hasta,
        rango_paginas=rango_paginas,
        tiene_anterior=(page > 1),
        tiene_siguiente=(page < total_paginas),
        pagina_anterior=(page - 1),
        pagina_siguiente=(page + 1)
    )


@app.route('/servicios/nuevo', methods=['GET', 'POST'])
@app.route('/productos/nuevo', methods=['GET', 'POST'])
@login_required
@admin_required
def nuevo_servicio():
    """
    Permite al Administrador registrar un nuevo servicio o producto en el catálogo.
    """
    tipos = servicio_repository.obtener_tipos()

    form = ServicioForm()
    form.tipo_servicio_id.choices = [(t['id'], t['nombre']) for t in tipos]

    if form.validate_on_submit():
        archivo = form.imagen_archivo.data
        if archivo and archivo.filename:
            imagen_val = guardar_imagen_subida(archivo)
        else:
            imagen_val = (form.imagen.data or '').strip()
        if not imagen_val:
            imagen_val = url_for('static', filename='imagenes/guardia-megaseg.jpg')

        servicio_repository.crear_servicio({
            'tipo_servicio_id': form.tipo_servicio_id.data,
            'nombre': form.nombre.data.strip(),
            'precio_base': float(form.precio.data or 0.0),
            'imagen': imagen_val,
            'descripcion': form.descripcion.data.strip(),
            'disponible': 1 if form.disponible.data else 0,
            'es_producto': int(form.es_producto.data),
            'destacado': 1 if form.destacado.data else 0
        })

        flash(f'¡"{form.nombre.data.strip()}" ha sido publicado con éxito en el catálogo!', 'success')
        return redirect(url_for('servicios'))

    return render_template(
        'formulario_servicio.html',
        form=form,
        editando=False,
        imagen_actual='',
        imagen_previa=url_imagen_actual(form.imagen.data)
    )


@app.route('/servicios/editar/<int:id>', methods=['GET', 'POST'])
@app.route('/productos/editar/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def editar_servicio(id):
    """
    Permite al Administrador modificar la información o precio de un servicio/producto.
    """
    servicio = servicio_repository.obtener_servicio(id)

    if not servicio:
        flash('El elemento solicitado no existe en el catálogo.', 'warning')
        return redirect(url_for('servicios'))

    tipos = servicio_repository.obtener_tipos()

    form = ServicioForm()
    form.tipo_servicio_id.choices = [(t['id'], t['nombre']) for t in tipos]

    if form.validate_on_submit():
        archivo = form.imagen_archivo.data
        if archivo and archivo.filename:
            imagen_val = guardar_imagen_subida(archivo)
        else:
            imagen_val = (form.imagen.data or '').strip()
        if not imagen_val:
            imagen_val = servicio['imagen'] or url_for(
                'static',
                filename='imagenes/guardia-megaseg.jpg'
            )

        servicio_repository.actualizar_servicio(id, {
            'tipo_servicio_id': form.tipo_servicio_id.data,
            'nombre': form.nombre.data.strip(),
            'precio_base': float(form.precio.data or 0.0),
            'imagen': imagen_val,
            'descripcion': form.descripcion.data.strip(),
            'disponible': 1 if form.disponible.data else 0,
            'es_producto': int(form.es_producto.data),
            'destacado': 1 if form.destacado.data else 0
        })

        flash(f'¡"{form.nombre.data.strip()}" se actualizó correctamente!', 'success')
        return redirect(url_for('servicios'))

    # Cargar valores existentes en la petición GET
    if request.method == 'GET':
        form.tipo_servicio_id.data = servicio['tipo_servicio_id']
        form.es_producto.data = servicio.get('es_producto', 0)
        form.nombre.data = servicio['nombre']
        form.precio.data = servicio['precio_base']
        form.imagen.data = ''
        form.descripcion.data = servicio['descripcion']
        form.disponible.data = bool(servicio['disponible'])
        form.destacado.data = bool(servicio.get('destacado', 0))

    return render_template(
        'formulario_servicio.html',
        form=form,
        editando=True,
        imagen_actual=url_imagen_actual(servicio['imagen']),
        imagen_previa=(
            url_imagen_actual(form.imagen.data)
            if form.imagen.data
            else url_imagen_actual(servicio['imagen'])
        )
    )


@app.route('/servicios/eliminar/<int:id>', methods=['POST'])
@app.route('/productos/eliminar/<int:id>', methods=['POST'])
@login_required
@admin_required
def eliminar_servicio(id):
    """
    Permite al Administrador dar de baja una publicación del catálogo.
    """
    servicio = servicio_repository.obtener_servicio(id)

    if servicio:
        servicio_repository.eliminar_servicio(id)
        flash(f'El servicio o producto "{servicio["nombre"]}" fue eliminado del catálogo.', 'info')
    else:
        flash('No se encontró el elemento a eliminar.', 'warning')

    return redirect(url_for('servicios'))


# ==============================================================================
# AUTENTICACIÓN (LOGIN & LOGOUT)
# ==============================================================================

@app.route('/login', methods=['GET', 'POST'])
def login():
    """
    Página de inicio de sesión de Administrador con validación y Flask-Login.
    """
    if current_user.is_authenticated:
        flash('Ya tienes una sesión activa como Administrador.', 'info')
        return redirect(url_for('servicios'))

    form = LoginForm()

    if form.validate_on_submit():
        usuario_ingresado = form.usuario.data.strip()
        user = User.get_by_usuario(usuario_ingresado)

        if user and user.verificar_password(form.password.data):
            login_user(user, remember=form.recordarme.data)
            flash(f'¡Bienvenido {user.nombre}! Modo administrador activado.', 'success')
            next_page = request.args.get('next', '')
            destino = next_page if es_destino_interno(next_page) else url_for('servicios')
            return redirect(destino)
        else:
            flash('Usuario o contraseña incorrectos. Verifica tus credenciales.', 'danger')

    return render_template('login.html', form=form)


@app.route('/logout', methods=['POST'])
@login_required
def logout():
    """Cierra la sesión del administrador y regresa a la portada."""
    logout_user()
    flash('Has cerrado sesión exitosamente. La web ahora está en modo cliente.', 'info')
    return redirect(url_for('inicio'))


# ------------------------------------------------------------------------------
# EJECUCIÓN DIRECTA DEL SERVIDOR
# ------------------------------------------------------------------------------
if __name__ == '__main__':
    puerto = int(os.getenv('PORT', 5000))
    debug_mode = os.getenv('FLASK_ENV', 'development').lower() == 'development'
    print(f"\n" + "="*70)
    print(f"  GRUPO DE SEGURIDAD MEGASEG CÍA. LTDA. — SISTEMA WEB ACTIVO")
    print(f"  Servidor ejecutándose en: http://127.0.0.1:{puerto}")
    print(f"="*70 + "\n")
    app.run(host='0.0.0.0', port=puerto, debug=debug_mode)
