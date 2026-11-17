# 🛡️ Grupo de Seguridad MEGASEG Cía. Ltda.
### Plataforma Web Corporativa, Catálogo Dinámico & Panel de Administración
> **Arquitectura de Software Profesional basada en el ecosistema NEXODIGITAL (Flask + WTForms + Base de Datos + Bootstrap 5)**

Bienvenido a la plataforma web oficial de **Grupo de Seguridad Megaseg Cía. Ltda.** (Lago Agrio, Sucumbíos, Ecuador). Este proyecto implementa la misma arquitectura, patrones de diseño y robustez técnica de **NEXODIGITAL**, adaptado a las necesidades específicas de Megaseg: una presencia pública de alto impacto y un panel de administración enfocado exclusivamente en **publicar, editar y dar de baja servicios y productos de seguridad**.

---

## 🏗️ 1. Arquitectura del Proyecto (Estructura de Bloques)

Siguiendo el estándar de **NEXODIGITAL**, el proyecto está organizado en módulos claros con separación estricta de responsabilidades (MVC - Modelo, Vista, Controlador):

```
PAGINA MEGASEG/
│
├── app.py                             # Configuración Flask y rutas/controladores
├── models.py                          # [Modelos] Clase User (Flask-Login) y verificación de contraseñas
├── repositories/
│   └── servicio_repository.py         # Consultas y operaciones CRUD del catálogo
├── sql/
│   └── esquema.sql                    # DDL SQLite, tablas, claves foráneas e índices
├── requirements.txt                   # [Dependencias] Flask, Flask-Login, Flask-WTF, WTForms, etc.
├── Procfile                           # [Despliegue] Archivo de despliegue en la nube (Gunicorn para Render/Railway)
├── .env.example                       # [Variables de Entorno] Plantilla para configuración de producción
├── .env                               # [Configuración Local] Clave secreta y parámetros activos
├── .gitignore                         # [Git] Exclusión de base de datos local, temporales y __pycache__
├── README.md                          # [Documentación Técnica] Arquitectura, seguridad y despliegue
├── MANUAL_ADMINISTRADOR.md            # [Manual de Usuario] Guía práctica paso a paso para el administrador
│
├── conexion/
│   ├── __init__.py
│   ├── conexion.py                    # Abre y cierra conexiones SQLite / PostgreSQL
│   └── inicializacion.py              # Aplica el DDL y carga datos iniciales
│
├── forms/
│   ├── __init__.py
│   ├── login_form.py                  # Formulario de autenticación con Flask-WTF y protección CSRF
│   ├── servicio_form.py               # Formulario de creación/edición de servicios con validaciones
│   └── producto_form.py               # Formulario específico para productos y kits físicos
│
├── templates/
│   ├── base.html                      # Plantilla maestra (Bootstrap 5.3.3, Icons, Flashes y tipografías)
│   ├── index.html                     # Portada de inicio: Hero cinematográfico, Nosotros, Misión, Cotizador
│   ├── servicios.html                 # Catálogo interactivo con paginación (12 ítems/hoja), buscador, filtros y CRUD
│   ├── formulario_servicio.html       # Formulario visual para registrar y editar publicaciones
│   ├── login.html                     # Pantalla de inicio de sesión administrativo con toggle de contraseña
│   └── components/
│       ├── navbar.html                # Barra de navegación modular con estado de sesión dinámico
│       └── footer.html                # Pie de página modular con información institucional
│
└── static/
    ├── css/
    │   └── estilo.css                 # Diseño visual Megaseg + NexoDigital Tokens (Dark, High Contrast)
    ├── js/
    │   └── script.js                  # Lógica del frontend (buscador en vivo, filtros por chips y WhatsApp)
    └── imagenes/
        ├── logo-megaseg.png           # Logotipo corporativo oficial
        ├── guardia-megaseg.jpg        # Fotografía real integrada en el Hero Banner
        ├── nosotros.jpg               # Fotografía corporativa en la sección ¿Quiénes Somos?
        └── catalogo/                  # Imágenes cargadas desde el formulario
```

---

## ⚡ 2. Cómo Ejecutar el Proyecto en Local

### Requisitos:
* Python 3.10 o superior (verificado con Python 3.14).

### Paso a paso:
1. Abre una terminal (PowerShell o CMD) en la carpeta del proyecto:
   ```powershell
   cd "c:\Users\quiar\Documents\PAGINA MEGASEG"
   ```
2. Instala las dependencias (si no las tienes instaladas):
   ```powershell
   python -m pip install -r requirements.txt
   ```
3. Inicia el servidor de desarrollo:
   ```powershell
   python app.py
   ```
4. Abre tu navegador en:
   👉 **http://127.0.0.1:5000**

> **Nota:** La base SQLite (`megaseg.db`) se crea en la raíz al ejecutar la aplicación. Las tablas se inicializan sin borrar registros existentes; si están vacías, se agregan los datos de inicio.

---

## 🗄️ 3. Conexión a Base de Datos (Dual SQLite / PostgreSQL)

Al igual que en **NEXODIGITAL**, la capa de persistencia (`conexion/conexion.py`) está desacoplada y soporta:

1. **Modo local (SQLite):**
   * Genera el archivo `megaseg.db` en la raíz.
   * No requiere instalar PostgreSQL localmente para probar el sistema.
   * Activa las claves foráneas y utiliza un cursor que permite acceder a los campos como diccionarios (`row['nombre']`).
   * `conexion/conexion.py` lee `sql/esquema.sql` al inicializar y llama al DDL con `CREATE TABLE IF NOT EXISTS`.
   * La base de datos está excluida de Git mediante `.gitignore`; cada desarrollador conserva su archivo local.

2. **Modo Producción en la Nube (PostgreSQL):**
   * Si en el archivo `.env` o en las variables del servidor defines `DATABASE_URL`:
     ```ini
     DATABASE_URL=postgresql://usuario:password@host:5432/nombre_db
     ```
   * El sistema se conecta a PostgreSQL vía `psycopg2`. El servidor PostgreSQL debe tener previamente las tablas creadas; el DDL de `sql/esquema.sql` está destinado a SQLite local.
   * Si PostgreSQL falla, la aplicación detiene la operación y reporta el error; no cambia a SQLite ni guarda datos en otra base por accidente.

### DDL y relación de datos

El DDL (Data Definition Language) define la estructura de la base de datos y se mantiene en `sql/esquema.sql`, no dentro de las rutas Flask:

1. `usuarios` guarda las cuentas de administración.
2. `tipos_servicio` guarda las categorías del catálogo.
3. `servicios` guarda tanto los servicios como los productos. `tipo_servicio_id` es una clave foránea hacia `tipos_servicio.id`; la relación impide borrar una categoría que todavía tenga publicaciones.
4. Los índices ayudan a consultar por categoría, disponibilidad, destacados y nombre.

El esquema es idempotente: se puede ejecutar más de una vez sin borrar tablas ni sus datos. La conexión lo carga mediante `inicializar_base_datos()` en `conexion/conexion.py`. Los registros iniciales solo se insertan cuando las tablas correspondientes están vacías.

### Dónde va cada responsabilidad

| Carpeta o archivo | Responsabilidad |
| --- | --- |
| `forms/` | Campos, validaciones y protección CSRF de formularios |
| `app.py` | Rutas, control de acceso, mensajes y selección de plantillas |
| `repositories/servicio_repository.py` | Consultas parametrizadas y CRUD del catálogo |
| `conexion/conexion.py` | Apertura y cierre de la conexión |
| `conexion/inicializacion.py` | Aplicación del DDL y carga inicial no destructiva |
| `sql/esquema.sql` | DDL: tablas, restricciones e índices |
| `templates/` | Interfaz HTML/Jinja2 |
| `static/` | CSS, JavaScript e imágenes |

El flujo para guardar una publicación es **formulario WTForms → validación con `validate_on_submit()` → función del repositorio → INSERT parametrizado → `commit()` → redirección al catálogo**. La lista se obtiene con `SELECT` desde el repositorio y se presenta en las plantillas. El SQL no se escribe dentro del HTML ni se concatena con datos del formulario. La carga inicial vive en `conexion/inicializacion.py`, separada tanto de las rutas como del módulo que abre conexiones.

---

## 🔒 4. Seguridad Implementada

Siguiendo los estándares de seguridad web de **NEXODIGITAL**:
* **Protección contra CSRF (Cross-Site Request Forgery):** Todos los formularios POST utilizan `{{ form.hidden_tag() }}` gestionado por **Flask-WTF** con firmas criptográficas de `SECRET_KEY`.
* **Cifrado de Contraseñas:** Las contraseñas de los administradores se guardan mediante hashes criptográficos (`scrypt` / `pbkdf2` / `bcrypt`), nunca en texto plano.
* **Control de Acceso Basado en Sesión (RBAC):** Rutas administrativas (`/servicios/nuevo`, `/servicios/editar/<id>`, `/servicios/eliminar/<id>`) protegidas con los decoradores `@login_required` y `@admin_required`.
* **Prevención de Inyección SQL:** El repositorio utiliza consultas parametrizadas (`%s`); el adaptador las convierte a `?` para SQLite. Los filtros y datos del formulario no se concatenan en los valores SQL.
* **Cierre Automático de Conexiones:** Decorador `@app.teardown_appcontext` que asegura que no queden conexiones de base de datos huérfanas en el pool.

---

## 👥 5. Flujos de Usuario vs. Administrador

### A. Para Clientes y Visitantes:
* Portada comercial completa con presentación de Grupo Megaseg, misión, visión y ventajas.
* **Catálogo de Servicios y Productos:**
  * Búsqueda en vivo mientras escribes.
  * Píldoras de filtrado rápido por categoría (`Todos`, `CCTV`, `Alarmas & Cercos`, `Guardianía`, `GPS`, etc.).
  * Ordenamiento por precio o nombre.
  * Botón de **Cotización Directa a WhatsApp** (`https://wa.me/593982900705`) preconfigurado con el nombre del servicio.
* **Cotizador Interactivo Online:** Formulario de 3 pasos que compila un mensaje estructurado para WhatsApp.

### B. Para el Administrador:
* Ingreso a través de `/login` con las credenciales configuradas de forma privada para el administrador. No se publican credenciales por defecto en el código ni en este manual.
* Acceso exclusivo a:
  * Botón **`➕ Subir Servicio o Producto`** (`/servicios/nuevo`).
  * Botón **`✏️ Editar`** en cada tarjeta del catálogo (`/servicios/editar/<id>`).
  * Botón **`🗑️ Eliminar`** con confirmación previa (`/servicios/eliminar/<id>`).
  * Conmutador de disponibilidad (Disponible vs. Próximamente) y destacado en portada.
* **Sin sobrecarga innecesaria:** No incluye módulos pesados de facturación contable ni proveedores, manteniendo el panel ágil, directo y fácil de operar.

---

## 🚀 6. Despliegue en Servidores en la Nube (Render, Railway, etc.)

El repositorio está listo para subir a GitHub y desplegar con un solo clic:
* `Procfile`: Configurado para arrancar con `gunicorn app:app`.
* Variables de entorno requeridas en el panel del hosting:
  * `FLASK_ENV=production`
  * `SECRET_KEY=tu_clave_secreta_super_segura`
  * `DATABASE_URL=tu_cadena_de_conexion_postgresql` (opcional si usas PostgreSQL de Render o Supabase).
