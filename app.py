# ==============================================================================
# PROYECTO: MEGASEG SEGURIDAD INTEGRAL - CONTROLADOR PRINCIPAL FLASK (BACKEND)
# Arquitectura y Funcionamiento Inspirado en NexoDigital
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
from pathlib import Path
from dotenv import load_dotenv

# Carga variables de entorno (.env)
load_dotenv(Path(__file__).resolve().parent / '.env')
from urllib.parse import urlsplit
from uuid import uuid4
from functools import wraps
from flask import Flask, render_template, redirect, url_for, flash, request
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_wtf.csrf import CSRFProtect
from werkzeug.exceptions import RequestEntityTooLarge
from werkzeug.utils import secure_filename

# Módulos del Sistema
from conexion.conexion import close_db_connection
from models import User
from forms.login_form import LoginForm
from forms.servicio_form import ServicioForm
from forms.registro_form import RegistroForm
from repositories import servicio_repository, auditoria_repository, usuario_repository

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
            'ruc': '2191726354001',
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
    return render_template('index.html', servicios_destacados=servicios_destacados)


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
            'nombre': form.nombre.data.strip(),
            'precio_base': float(form.precio.data or 0.0),
            'imagen': imagen_val,
            'descripcion': form.descripcion.data.strip(),
            'disponible': 1 if form.disponible.data else 0,
            'es_producto': int(form.es_producto.data),
            'destacado': 1 if form.destacado.data else 0,
            'tipo_producto': (form.tipo_producto.data or '').strip(),
            'garantia': (form.garantia.data or '').strip(),
            'zona_cobertura': (form.zona_cobertura.data or '').strip(),
            'disponibilidad_atencion': (form.disponibilidad_atencion.data or '').strip(),
            'modalidad_pago': (form.modalidad_pago.data or '').strip(),
            'ficha_tecnica': (form.ficha_tecnica.data or '').strip(),
            'whatsapp_msg': (form.whatsapp_msg.data or '').strip()
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
            'nombre': form.nombre.data.strip(),
            'precio_base': float(form.precio.data or 0.0),
            'imagen': imagen_val,
            'descripcion': form.descripcion.data.strip(),
            'disponible': 1 if form.disponible.data else 0,
            'es_producto': int(form.es_producto.data),
            'destacado': 1 if form.destacado.data else 0,
            'tipo_producto': (form.tipo_producto.data or '').strip(),
            'garantia': (form.garantia.data or '').strip(),
            'zona_cobertura': (form.zona_cobertura.data or '').strip(),
            'disponibilidad_atencion': (form.disponibilidad_atencion.data or '').strip(),
            'modalidad_pago': (form.modalidad_pago.data or '').strip(),
            'ficha_tecnica': (form.ficha_tecnica.data or '').strip(),
            'whatsapp_msg': (form.whatsapp_msg.data or '').strip()
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
        usuario_limpio = form.usuario.data.strip()
        email_limpio = form.email.data.strip()

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
            'nombre': form.nombre.data.strip(),
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


@app.route('/login', methods=['GET', 'POST'])
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
