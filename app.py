# ==============================================================================
# PROYECTO: MEGASEG SEGURIDAD INTEGRAL - CONTROLADOR PRINCIPAL FLASK (BACKEND)
# ==============================================================================
# Este archivo contiene la configuración central del servidor y los controladores
# (rutas y vistas) que gestionan la lógica de negocio para:
# 1. Página de inicio y presentación de Grupo Megaseg Cía. Ltda.
# 2. Catálogo público y gestión de Servicios & Productos (Plantilla Dinámica)
# 3. Autenticación, control de acceso RBAC y Auditoría del Sistema (Logs)
# 4. Gestión de Roles y Permisos de Usuarios
# 5. Cotizador interactivo con integración a WhatsApp
# 6. Conexión a PostgreSQL local y SQLite para pruebas
# ==============================================================================

import os
import json
import unicodedata
import hashlib
from datetime import datetime, timedelta, timezone
from pathlib import Path
from dotenv import load_dotenv

# Carga variables de entorno (.env)
load_dotenv(Path(__file__).resolve().parent / '.env')
from urllib.parse import urlsplit
from uuid import uuid4
from functools import wraps
from flask import Flask, render_template, redirect, url_for, flash, request, send_from_directory
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from werkzeug.exceptions import RequestEntityTooLarge
from werkzeug.utils import secure_filename
from werkzeug.middleware.proxy_fix import ProxyFix
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
import smtplib
from email.message import EmailMessage

# Módulos del Sistema
from conexion.conexion import close_db_connection, get_db_connection
from models import User
from forms.login_form import LoginForm, RecuperarPasswordForm, NuevaPasswordForm
from forms.servicio_form import ServicioForm
from forms.registro_form import RegistroForm
from repositories import (
    servicio_repository,
    auditoria_repository,
    usuario_repository,
    resenas_repository,
)

# ------------------------------------------------------------------------------
# INICIALIZACIÓN DE LA APLICACIÓN FLASK
# ------------------------------------------------------------------------------
app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

# Clave secreta para sesiones y formularios Flask-WTF con CSRF
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
if not app.config['SECRET_KEY']:
    raise RuntimeError('Configura SECRET_KEY en el entorno antes de iniciar la aplicación.')

app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_SECURE'] = os.getenv('SESSION_COOKIE_SECURE', '').lower() in ('1', 'true', 'yes')
app.config['MAX_CONTENT_LENGTH'] = 6 * 1024 * 1024
csrf = CSRFProtect(app)

limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    storage_uri=os.getenv('RATELIMIT_STORAGE_URL', 'memory://'),
    default_limits=[],
)

UPLOAD_DIR = Path(os.getenv('UPLOAD_DIR')).resolve() if os.getenv('UPLOAD_DIR') else None
if UPLOAD_DIR:
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def guardar_imagen_subida(archivo):
    """Guarda una imagen validada en una carpeta pública con nombre único."""
    nombre_seguro = secure_filename(archivo.filename)
    extension = Path(nombre_seguro).suffix.lower()
    nombre_archivo = f'{uuid4().hex}{extension}'
    if os.getenv('UPLOAD_DIR'):
        archivo.save(UPLOAD_DIR / nombre_archivo)
        return f'/media/catalogo/{nombre_archivo}'
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


def limpiar_texto_usuario(texto, longitud_maxima):
    """Normaliza Unicode, conserva saltos y elimina controles incompatibles."""
    if texto is None:
        return ''
    texto = unicodedata.normalize('NFC', str(texto))
    texto = texto.replace('\r\n', '\n').replace('\r', '\n')
    texto = ''.join(
        caracter
        for caracter in texto
        if caracter in '\t\n' or unicodedata.category(caracter) != 'Cc'
    )
    lineas = [linea.strip(' \t') for linea in texto.strip().split('\n')]
    texto_limpio = '\n'.join(lineas)
    return texto_limpio[:longitud_maxima]


def obtener_serializador_recuperacion():
    clave = os.getenv('PASSWORD_RESET_SECRET') or app.config['SECRET_KEY']
    return URLSafeTimedSerializer(clave, salt='megaseg-recuperacion-password')


def enviar_correo_recuperacion(destino, enlace):
    """Envía el enlace por SMTP; devuelve False si el correo no está configurado."""
    host = (os.getenv('SMTP_HOST') or '').strip()
    remitente = (os.getenv('MAIL_FROM') or '').strip()
    if not host or not remitente:
        return False

    mensaje = EmailMessage()
    mensaje['Subject'] = 'Recuperación de contraseña - Grupo Megaseg'
    mensaje['From'] = remitente
    mensaje['To'] = destino
    mensaje.set_content(
        'Hola,\n\n'
        'Recibimos una solicitud para restablecer tu contraseña de Megaseg.\n'
        f'Abre este enlace en los próximos 30 minutos:\n{enlace}\n\n'
        'Si no solicitaste este cambio, puedes ignorar este correo.\n'
    )

    puerto = int(os.getenv('SMTP_PORT', '587'))
    usuario = os.getenv('SMTP_USERNAME') or ''
    clave = os.getenv('SMTP_PASSWORD') or ''
    uso_tls = os.getenv('SMTP_USE_TLS', 'true').lower() in ('1', 'true', 'yes')

    with smtplib.SMTP(host, puerto, timeout=15) as smtp:
        smtp.ehlo()
        if uso_tls:
            smtp.starttls()
            smtp.ehlo()
        if usuario:
            smtp.login(usuario, clave)
        smtp.send_message(mensaje)
    return True


@app.route('/media/catalogo/<path:nombre_archivo>')
def media_catalogo(nombre_archivo):
    """Sirve imágenes locales o desde el disco persistente configurado."""
    carpeta = UPLOAD_DIR or (Path(app.static_folder) / 'imagenes' / 'catalogo')
    return send_from_directory(carpeta, nombre_archivo)


@app.route('/healthz')
def healthz():
    """Chequeo simple de disponibilidad de aplicación y PostgreSQL."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT 1')
        cursor.fetchone()
        cursor.close()
        return {'status': 'ok'}, 200
    except Exception:
        return {'status': 'error'}, 503


def campos_extra_desde_peticion():
    """Convierte pares título/detalle del formulario en una lista segura para JSONB."""
    titulos = request.form.getlist('campo_extra_titulo')
    detalles = request.form.getlist('campo_extra_detalle')
    campos = []
    for titulo, detalle in zip(titulos, detalles):
        titulo = limpiar_texto_usuario(titulo, 100)
        detalle = limpiar_texto_usuario(detalle, 2000)
        if titulo and detalle:
            campos.append({'titulo': titulo, 'detalle': detalle})
    return json.dumps(campos, ensure_ascii=False)

# ------------------------------------------------------------------------------
# CONFIGURACIÓN DE FLASK-LOGIN
# ------------------------------------------------------------------------------
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Inicia sesión para acceder a las funciones del sistema.'
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
        user = User.get_by_id(int(user_id))
        return user if user and user.is_active else None
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
            'ruc': '2191726354001',
            'ubicacion': 'Calle José María Urbina y Tungurahua, Ref: A 3 cuadras del Hospital del IESS, Barrio: Las Garzas., Lago Agrio, Provincia de Sucumbíos, Ecuador',
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
            flash('Acceso restringido. Solo los administradores pueden gestionar esta sección.', 'danger')
            return redirect(url_for('inicio'))
        return f(*args, **kwargs)
    return decorated_function


def catalog_manager_required(f):
    """Decorador para permitir la gestión del catálogo a Administradores y Gestores de Catálogo."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.can_manage_catalog():
            flash('Acceso restringido. Solo administradores o gestores de catálogo pueden gestionar productos y servicios.', 'danger')
            return redirect(url_for('servicios'))
        return f(*args, **kwargs)
    return decorated_function


def role_required(*roles):
    """Decorador genérico para control de acceso RBAC por roles."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated or not current_user.has_role(*roles):
                flash('Acceso restringido. Tu rol actual no cuenta con los permisos necesarios.', 'danger')
                return redirect(url_for('inicio'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator


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
    resenas = resenas_repository.obtener_aprobadas(limite=6)
    resumen_resenas = resenas_repository.obtener_resumen()
    servicios_resenas = servicio_repository.listar_servicios(limite=100)
    return render_template(
        'index1.html',
        servicios_destacados=servicios_destacados,
        resenas=resenas,
        resumen_resenas=resumen_resenas,
        servicios_resenas=servicios_resenas,
    )


# ==============================================================================
# RUTAS DEL CATÁLOGO DE SERVICIOS Y PRODUCTOS (PLANTILLA DINÁMICA & CRUD)
# ==============================================================================

@app.route('/servicios')
@app.route('/productos')
@app.route('/catalogo')
def servicios():
    """
    Ruta del catálogo completo de servicios y productos con paginación de 12 ítems por hoja.
    Plantilla técnica con acordeón y campos dinámicos condicionales.
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

    # Paginación
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

    items_desde = offset + 1 if total_items > 0 else 0
    items_hasta = min(offset + por_pagina, total_items)

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
@catalog_manager_required
def nuevo_servicio():
    """
    Permite al Administrador registrar un nuevo servicio o producto en la base de datos
    con soporte completo para su plantilla técnica, garantías y cobertura.
    """
    tipos = servicio_repository.obtener_tipos()

    form = ServicioForm()
    form.tipo_servicio_id.choices = [(t['id'], t['nombre']) for t in tipos]

    if form.validate_on_submit():
        archivo = form.imagen_archivo.data
        if archivo and hasattr(archivo, 'filename') and archivo.filename:
            imagen_val = guardar_imagen_subida(archivo)
        else:
            imagen_val = (form.imagen.data or '').strip()
        if not imagen_val:
            imagen_val = url_for('static', filename='imagenes/guardia-megaseg.jpg')

        nuevo_id = servicio_repository.crear_servicio({
            'tipo_servicio_id': form.tipo_servicio_id.data,
            'nombre': limpiar_texto_usuario(form.nombre.data, 150),
            'precio_base': float(form.precio.data or 0.0),
            'imagen': imagen_val,
            'descripcion': limpiar_texto_usuario(form.descripcion.data, 1000),
            'disponible': 1 if form.disponible.data else 0,
            'es_producto': int(form.es_producto.data),
            'destacado': 1 if form.destacado.data else 0,
            'tipo_producto': limpiar_texto_usuario(form.tipo_producto.data, 100),
            'garantia': limpiar_texto_usuario(form.garantia.data, 255),
            'zona_cobertura': limpiar_texto_usuario(form.zona_cobertura.data, 255),
            'disponibilidad_atencion': limpiar_texto_usuario(form.disponibilidad_atencion.data, 255),
            'modalidad_pago': limpiar_texto_usuario(form.modalidad_pago.data, 255),
            'ficha_tecnica': limpiar_texto_usuario(form.ficha_tecnica.data, 2000),
            'whatsapp_msg': limpiar_texto_usuario(form.whatsapp_msg.data, 255),
            'campos_extra': campos_extra_desde_peticion()
        })

        # Auditoría del sistema
        auditoria_repository.registrar_log(
            usuario_id=current_user.id,
            usuario_nombre=current_user.nombre,
            rol=current_user.rol,
            accion='CREAR',
            entidad='servicio',
            entidad_id=nuevo_id,
            detalles=f'Publicó el servicio o producto: "{form.nombre.data.strip()}"',
            ip=request.remote_addr
        )

        flash(f'¡"{form.nombre.data.strip()}" ha sido publicado con éxito en la base de datos!', 'success')
        return redirect(url_for('servicios'))

    return render_template(
        'formulario_servicio.html',
        form=form,
        editando=False,
        imagen_actual='',
        campos_extra=[],
        imagen_previa=url_imagen_actual(form.imagen.data)
    )


@app.route('/servicios/editar/<int:id>', methods=['GET', 'POST'])
@app.route('/productos/editar/<int:id>', methods=['GET', 'POST'])
@login_required
@catalog_manager_required
def editar_servicio(id):
    """
    Permite al Administrador modificar la información técnica, precios o garantías
    de un servicio o producto, preservando la imagen existente si no se sube una nueva.
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
        if archivo and hasattr(archivo, 'filename') and archivo.filename:
            imagen_val = guardar_imagen_subida(archivo)
        else:
            imagen_val = (form.imagen.data or '').strip()

        # Si no se seleccionó ninguna imagen nueva, se preserva la actual
        if not imagen_val:
            imagen_val = servicio.get('imagen') or url_for('static', filename='imagenes/guardia-megaseg.jpg')

        servicio_repository.actualizar_servicio(id, {
            'tipo_servicio_id': form.tipo_servicio_id.data,
            'nombre': limpiar_texto_usuario(form.nombre.data, 150),
            'precio_base': float(form.precio.data or 0.0),
            'imagen': imagen_val,
            'descripcion': limpiar_texto_usuario(form.descripcion.data, 1000),
            'disponible': 1 if form.disponible.data else 0,
            'es_producto': int(form.es_producto.data),
            'destacado': 1 if form.destacado.data else 0,
            'tipo_producto': limpiar_texto_usuario(form.tipo_producto.data, 100),
            'garantia': limpiar_texto_usuario(form.garantia.data, 255),
            'zona_cobertura': limpiar_texto_usuario(form.zona_cobertura.data, 255),
            'disponibilidad_atencion': limpiar_texto_usuario(form.disponibilidad_atencion.data, 255),
            'modalidad_pago': limpiar_texto_usuario(form.modalidad_pago.data, 255),
            'ficha_tecnica': limpiar_texto_usuario(form.ficha_tecnica.data, 2000),
            'whatsapp_msg': limpiar_texto_usuario(form.whatsapp_msg.data, 255),
            'campos_extra': campos_extra_desde_peticion()
        })

        # Auditoría del sistema
        auditoria_repository.registrar_log(
            usuario_id=current_user.id,
            usuario_nombre=current_user.nombre,
            rol=current_user.rol,
            accion='EDITAR',
            entidad='servicio',
            entidad_id=id,
            detalles=f'Actualizó especificaciones de: "{form.nombre.data.strip()}"',
            ip=request.remote_addr
        )

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
        form.tipo_producto.data = servicio.get('tipo_producto', '')
        form.garantia.data = servicio.get('garantia', '')
        form.zona_cobertura.data = servicio.get('zona_cobertura', '')
        form.disponibilidad_atencion.data = servicio.get('disponibilidad_atencion', '')
        form.modalidad_pago.data = servicio.get('modalidad_pago', '')
        form.ficha_tecnica.data = servicio.get('ficha_tecnica', '')
        form.whatsapp_msg.data = servicio.get('whatsapp_msg', '')

    return render_template(
        'formulario_servicio.html',
        form=form,
        editando=True,
        imagen_actual=url_imagen_actual(servicio.get('imagen')),
        campos_extra=servicio.get('campos_extra') or [],
        imagen_previa=(
            url_imagen_actual(form.imagen.data)
            if form.imagen.data
            else url_imagen_actual(servicio.get('imagen'))
        )
    )


@app.route('/servicios/eliminar/<int:id>', methods=['POST'])
@app.route('/productos/eliminar/<int:id>', methods=['POST'])
@login_required
@catalog_manager_required
def eliminar_servicio(id):
    """
    Permite al Administrador dar de baja una publicación del catálogo.
    """
    servicio = servicio_repository.obtener_servicio(id)

    if servicio:
        servicio_repository.eliminar_servicio(id)

        # Auditoría del sistema
        auditoria_repository.registrar_log(
            usuario_id=current_user.id,
            usuario_nombre=current_user.nombre,
            rol=current_user.rol,
            accion='ELIMINAR',
            entidad='servicio',
            entidad_id=id,
            detalles=f'Eliminó del catálogo: "{servicio["nombre"]}"',
            ip=request.remote_addr
        )

        flash(f'El servicio o producto "{servicio["nombre"]}" fue eliminado del catálogo.', 'info')
    else:
        flash('No se encontró el elemento a eliminar.', 'warning')

    return redirect(url_for('servicios'))


# ==============================================================================
# AUDITORÍA DEL SISTEMA (LOGS & HISTORIAL DE ACTIVIDAD)
# ==============================================================================

@app.route('/admin/logs')
@login_required
@role_required('Administrador', 'Auditor', 'Supervisor')
def admin_logs():
    """
    Módulo del Auditor: muestra qué se ha ido cambiando, cuándo, quién y los roles
    activos al momento de la operación.
    """
    q = request.args.get('q', '').strip()
    accion = request.args.get('accion', '').strip()

    logs = auditoria_repository.obtener_logs(limite=200, busqueda=q, accion=accion)

    return render_template(
        'admin_logs.html',
        logs=logs,
        busqueda=q,
        accion_sel=accion
    )


@app.route('/resenas/nueva', methods=['POST'])
@limiter.limit('5 per hour')
def nueva_resena():
    nombre = limpiar_texto_usuario(request.form.get('nombre'), 100)
    comentario = limpiar_texto_usuario(request.form.get('comentario'), 1000)
    servicio_id_raw = (request.form.get('servicio_id') or '').strip()
    servicio_id = int(servicio_id_raw) if servicio_id_raw.isdigit() else None
    try:
        calificacion = int(request.form.get('calificacion', 0))
    except (TypeError, ValueError):
        calificacion = 0

    if len(nombre) < 2 or len(nombre) > 100:
        flash('Ingresa tu nombre con entre 2 y 100 caracteres.', 'danger')
        return redirect(url_for('inicio') + '#resenas')
    if len(comentario) < 10 or len(comentario) > 1000:
        flash('La reseña debe tener entre 10 y 1000 caracteres.', 'danger')
        return redirect(url_for('inicio') + '#resenas')
    if calificacion not in range(1, 6):
        flash('Selecciona una calificación de 1 a 5 estrellas.', 'danger')
        return redirect(url_for('inicio') + '#resenas')

    if servicio_id is not None:
        servicio = servicio_repository.obtener_servicio(servicio_id)
        if not servicio:
            flash('El servicio seleccionado no existe.', 'danger')
            return redirect(url_for('inicio') + '#resenas')

    resenas_repository.crear(nombre, comentario, calificacion, servicio_id)
    flash('Tu reseña fue enviada y permanecerá pendiente hasta ser aprobada por Megaseg.', 'success')
    return redirect(url_for('inicio') + '#resenas')


@app.route('/admin/resenas')
@login_required
@admin_required
def admin_resenas():
    return render_template(
        'admin_resenas.html',
        resenas=resenas_repository.obtener_todas(),
    )


@app.route('/admin/resenas/<int:id>/aprobar', methods=['POST'])
@login_required
@admin_required
def aprobar_resena(id):
    resenas_repository.cambiar_aprobacion(id, True)
    flash('La reseña fue aprobada y ya puede mostrarse públicamente.', 'success')
    return redirect(url_for('admin_resenas'))


@app.route('/admin/resenas/<int:id>/ocultar', methods=['POST'])
@login_required
@admin_required
def ocultar_resena(id):
    resenas_repository.cambiar_aprobacion(id, False)
    flash('La reseña fue ocultada.', 'info')
    return redirect(url_for('admin_resenas'))


@app.route('/admin/resenas/<int:id>/eliminar', methods=['POST'])
@login_required
@admin_required
def eliminar_resena(id):
    resenas_repository.eliminar(id)
    flash('La reseña fue eliminada.', 'warning')
    return redirect(url_for('admin_resenas'))


# ==============================================================================
# GESTIÓN DE USUARIOS Y ROLES (RBAC)
# ==============================================================================

@app.route('/admin/usuarios')
@login_required
@admin_required
def admin_usuarios():
    """
    Muestra los usuarios registrados, la lista de roles del sistema y permite
    reasignar roles administrativos u operativos.
    """
    usuarios = usuario_repository.listar_usuarios()
    roles = usuario_repository.obtener_roles()

    return render_template(
        'admin_usuarios.html',
        usuarios=usuarios,
        roles=roles
    )


@app.route('/admin/cambiar-rol/<int:id>', methods=['POST'])
@login_required
@admin_required
def admin_cambiar_rol(id):
    """Actualiza el rol asignado a un usuario y lo asienta en la auditoría."""
    nuevo_rol = request.form.get('nuevo_rol', '').strip()
    usuario_dest = usuario_repository.obtener_usuario_por_id(id)

    if not usuario_dest:
        flash('Usuario no encontrado.', 'warning')
        return redirect(url_for('admin_usuarios'))

    roles_permitidos = {rol['nombre'] for rol in usuario_repository.obtener_roles()}
    if nuevo_rol not in roles_permitidos:
        flash('El rol seleccionado no es válido.', 'warning')
        return redirect(url_for('admin_usuarios'))

    if nuevo_rol != usuario_dest['rol']:
        usuario_repository.actualizar_rol(id, nuevo_rol)

        auditoria_repository.registrar_log(
            usuario_id=current_user.id,
            usuario_nombre=current_user.nombre,
            rol=current_user.rol,
            accion='CAMBIO_ROL',
            entidad='usuario',
            entidad_id=id,
            detalles=f'Cambió el rol de {usuario_dest["usuario"]} a "{nuevo_rol}"',
            ip=request.remote_addr
        )

        flash(f'Se actualizó el rol de {usuario_dest["usuario"]} a "{nuevo_rol}".', 'success')

    return redirect(url_for('admin_usuarios'))


@app.route('/admin/cambiar-estado/<int:id>', methods=['POST'])
@login_required
@admin_required
def admin_cambiar_estado(id):
    """
    Permite a cualquier Administrador admitir/activar a usuarios que se registraron
    con roles operativos (Gestor de Catálogo, Administrador, etc.) o suspender su acceso.
    """
    usuario_dest = usuario_repository.obtener_usuario_por_id(id)

    if not usuario_dest:
        flash('Usuario no encontrado.', 'warning')
        return redirect(url_for('admin_usuarios'))

    if usuario_dest['id'] == current_user.id:
        flash('No puedes suspender o cambiar el estado de tu propia cuenta administradora.', 'warning')
        return redirect(url_for('admin_usuarios'))

    nuevo_estado = 0 if usuario_dest['activo'] else 1
    usuario_repository.cambiar_estado(id, nuevo_estado)

    accion_txt = 'ADMITIDO / ACTIVADO' if nuevo_estado else 'DESACTIVADO'
    auditoria_repository.registrar_log(
        usuario_id=current_user.id,
        usuario_nombre=current_user.nombre,
        rol=current_user.rol,
        accion='CAMBIO_ESTADO',
        entidad='usuario',
        entidad_id=id,
        detalles=f'El administrador {current_user.nombre} marcó al usuario "{usuario_dest["usuario"]}" ({usuario_dest["rol"]}) como {accion_txt}',
        ip=request.remote_addr
    )

    if nuevo_estado:
        flash(f'¡El usuario "{usuario_dest["usuario"]}" ha sido ADMITIDO exitosamente como {usuario_dest["rol"]}!', 'success')
    else:
        flash(f'El usuario "{usuario_dest["usuario"]}" ha sido suspendido/inactivado.', 'info')

    return redirect(url_for('admin_usuarios'))


# ==============================================================================
# AUTENTICACIÓN Y REGISTRO (LOGIN, REGISTRO & LOGOUT)
# ==============================================================================

@app.route('/registro', methods=['GET', 'POST'])
def registro():
    """
    Permite crear cuentas de Cliente o solicitar un rol que requiere admisión.
    """
    if current_user.is_authenticated:
        flash('Ya tienes una sesión activa en el sistema.', 'info')
        return redirect(url_for('servicios'))

    form = RegistroForm()

    if form.validate_on_submit():
        usuario_limpio = limpiar_texto_usuario(form.usuario.data, 40)
        email_limpio = limpiar_texto_usuario(form.email.data, 120)

        if usuario_repository.existe_usuario(usuario_limpio):
            flash('El nombre de usuario ya se encuentra registrado. Elige otro.', 'danger')
            return render_template('registro.html', form=form)

        if usuario_repository.existe_email(email_limpio):
            flash('El correo electrónico ya está registrado con otra cuenta.', 'danger')
            return render_template('registro.html', form=form)

        rol_solicitado = form.rol.data
        requiere_admision = rol_solicitado != 'Cliente'
        activo = not requiere_admision

        nuevo_id = usuario_repository.crear_usuario({
            'usuario': usuario_limpio,
            'nombre': limpiar_texto_usuario(form.nombre.data, 100),
            'email': email_limpio,
            'telefono': (form.telefono.data or '').strip(),
            'password': form.password.data,
            'rol': rol_solicitado,
            'activo': activo
        })

        auditoria_repository.registrar_log(
            usuario_id=nuevo_id,
            usuario_nombre=form.nombre.data.strip(),
            rol=rol_solicitado,
            accion='REGISTRO',
            entidad='usuario',
            entidad_id=nuevo_id,
            detalles=f'Registro de usuario con rol "{rol_solicitado}" (activo: {activo})',
            ip=request.remote_addr
        )

        if requiere_admision:
            flash(
                f'¡Cuenta creada exitosamente! Por política de seguridad, el rol "{rol_solicitado}" '
                'requiere ser admitido por cualquier Administrador antes de poder iniciar sesión.',
                'warning'
            )
            return redirect(url_for('login'))
        else:
            nuevo_user = User.get_by_id(nuevo_id)
            if nuevo_user and nuevo_user.is_active:
                login_user(nuevo_user)
                flash(f'¡Bienvenido a Megaseg, {nuevo_user.nombre}! Tu cuenta como "{nuevo_user.rol}" está activa.', 'success')
                return redirect(url_for('servicios'))
            flash('Tu cuenta ha sido creada exitosamente. Ya puedes iniciar sesión.', 'success')
            return redirect(url_for('login'))

    return render_template('registro.html', form=form)


@app.route('/recuperar-password', methods=['GET', 'POST'])
@limiter.limit('3 per hour')
def recuperar_password():
    """Solicita un enlace temporal sin revelar si la cuenta existe."""
    form = RecuperarPasswordForm()

    if form.validate_on_submit():
        dato = limpiar_texto_usuario(form.usuario_o_email.data, 120)
        valor = dato.lower()
        usuario = usuario_repository.obtener_usuario_por_usuario_o_email(valor)

        if usuario and usuario.get('email') and usuario.get('activo'):
            serializador = obtener_serializador_recuperacion()
            token = serializador.dumps({'usuario_id': usuario['id']})
            token_hash = hashlib.sha256(token.encode('utf-8')).hexdigest()
            expira_en = datetime.now(timezone.utc) + timedelta(minutes=30)
            try:
                conn_reset = get_db_connection()
                cursor_reset = conn_reset.cursor()
                cursor_reset.execute(
                    'UPDATE password_reset_tokens SET usado_en = %s WHERE usuario_id = %s AND usado_en IS NULL',
                    (datetime.now(timezone.utc), usuario['id'])
                )
                cursor_reset.execute(
                    '''
                    INSERT INTO password_reset_tokens (usuario_id, token_hash, expira_en)
                    VALUES (%s, %s, %s)
                    ''',
                    (usuario['id'], token_hash, expira_en)
                )
                conn_reset.commit()
                cursor_reset.close()
            except Exception as error:
                app.logger.error('No se pudo registrar el token de recuperación: %s', type(error).__name__)
            enlace = url_for(
                'restablecer_password',
                token=token,
                _external=True,
                _scheme='https' if os.getenv('SESSION_COOKIE_SECURE', '').lower() in ('1', 'true', 'yes') else 'http'
            )
            try:
                enviar_correo_recuperacion(usuario['email'], enlace)
            except Exception as error:
                app.logger.error('No se pudo enviar el correo de recuperación: %s', type(error).__name__)

        flash(
            'Si existe una cuenta activa asociada a ese dato, recibirás un enlace válido por 30 minutos.',
            'info'
        )
        return redirect(url_for('login'))

    return render_template('recuperar_password.html', form=form)


@app.route('/restablecer-password/<token>', methods=['GET', 'POST'])
@limiter.limit('5 per hour')
def restablecer_password(token):
    """Valida un token de un solo uso y permite cambiar la contraseña."""
    try:
        datos = obtener_serializador_recuperacion().loads(token, max_age=1800)
        usuario_id = int(datos['usuario_id'])
    except (BadSignature, SignatureExpired, KeyError, TypeError, ValueError):
        flash('El enlace es inválido o expiró. Solicita uno nuevo.', 'danger')
        return redirect(url_for('recuperar_password'))

    token_hash = hashlib.sha256(token.encode('utf-8')).hexdigest()
    try:
        conn_reset = get_db_connection()
        cursor_reset = conn_reset.cursor()
        cursor_reset.execute(
            '''
            SELECT id FROM password_reset_tokens
            WHERE usuario_id = %s
              AND token_hash = %s
              AND usado_en IS NULL
              AND expira_en > %s
            ''',
            (usuario_id, token_hash, datetime.now(timezone.utc))
        )
        token_registrado = cursor_reset.fetchone()
        if not token_registrado:
            cursor_reset.close()
            flash('El enlace ya fue utilizado o expiró. Solicita uno nuevo.', 'danger')
            return redirect(url_for('recuperar_password'))
    except Exception:
        cursor_reset.close()
        flash('No se pudo validar el enlace de recuperación.', 'danger')
        return redirect(url_for('recuperar_password'))

    usuario = usuario_repository.obtener_usuario_por_id(usuario_id)
    if not usuario or not usuario['activo']:
        flash('La cuenta no está disponible para recuperar su contraseña.', 'danger')
        return redirect(url_for('login'))

    form = NuevaPasswordForm()
    if form.validate_on_submit():
        if form.password.data != form.confirm_password.data:
            flash('Las contraseñas no coinciden.', 'danger')
            return render_template('restablecer_password.html', form=form)

        if len(form.password.data) < 14:
            flash('La contraseña debe tener al menos 14 caracteres.', 'danger')
            return render_template('restablecer_password.html', form=form)

        from security.passwords import hash_password
        cursor_reset.execute(
            'UPDATE usuarios SET password = %s WHERE id = %s',
            (hash_password(form.password.data), usuario_id)
        )
        cursor_reset.execute(
            '''
            UPDATE password_reset_tokens
            SET usado_en = %s
            WHERE id = %s AND usado_en IS NULL
            ''',
            (datetime.now(timezone.utc), token_registrado['id'])
        )
        conn_reset.commit()
        cursor_reset.close()
        auditoria_repository.registrar_log(
            usuario_id=usuario_id,
            usuario_nombre=usuario['nombre'],
            rol=usuario['rol'],
            accion='RECUPERAR_PASSWORD',
            entidad='auth',
            entidad_id=usuario_id,
            detalles='Restableció su contraseña mediante un enlace válido enviado por correo.',
            ip=request.remote_addr
        )
        flash('Tu contraseña fue cambiada correctamente. Ya puedes iniciar sesión.', 'success')
        return redirect(url_for('login'))

    return render_template('restablecer_password.html', form=form)


@app.route('/login', methods=['GET', 'POST'])
@limiter.limit('10 per minute')
def login():
    """
    Página de inicio de sesión con validación, Flask-Login y registro de auditoría.
    """
    if current_user.is_authenticated:
        flash('Ya tienes una sesión activa en el sistema.', 'info')
        return redirect(url_for('servicios'))

    form = LoginForm()

    if form.validate_on_submit():
        usuario_ingresado = form.usuario.data.strip()
        user = User.get_by_usuario(usuario_ingresado)

        if user and user.verificar_password(form.password.data):
            if not user.is_active:
                flash('Tu cuenta se encuentra inactiva. Contacta al administrador.', 'danger')
                return render_template('login.html', form=form)

            login_user(user, remember=form.recordarme.data)

            # Auditoría
            auditoria_repository.registrar_log(
                usuario_id=user.id,
                usuario_nombre=user.nombre,
                rol=user.rol,
                accion='LOGIN',
                entidad='auth',
                entidad_id=user.id,
                detalles=f'Inicio de sesión exitoso como {user.rol}',
                ip=request.remote_addr
            )

            flash(f'¡Bienvenido {user.nombre}! Acceso con rol: {user.rol}.', 'success')
            next_page = request.args.get('next', '')
            destino = next_page if es_destino_interno(next_page) else url_for('servicios')
            return redirect(destino)
        else:
            flash('Usuario o contraseña incorrectos. Verifica tus credenciales.', 'danger')

    return render_template('login.html', form=form)


@app.route('/logout', methods=['POST'])
@login_required
def logout():
    """Cierra la sesión y asienta el evento en la auditoría."""
    auditoria_repository.registrar_log(
        usuario_id=current_user.id,
        usuario_nombre=current_user.nombre,
        rol=current_user.rol,
        accion='LOGOUT',
        entidad='auth',
        entidad_id=current_user.id,
        detalles='Cierre de sesión seguro',
        ip=request.remote_addr
    )
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
