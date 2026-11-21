# MEGASEG

Aplicación Flask para mostrar y administrar el catálogo de productos y servicios
de seguridad, gestionar cuentas con aprobación administrativa y registrar
actividad. La base de datos de la instalación local es PostgreSQL.

## Requisitos

- Windows 10/11, PowerShell y Python 3.10 o superior.
- PostgreSQL local instalado y en ejecución.

## Instalación local en PostgreSQL

Desde PowerShell, en la carpeta del proyecto:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
notepad .env
```

Configura en `.env` una `SECRET_KEY` aleatoria, `DB_PASSWORD` con la contraseña
real de tu PostgreSQL local y credenciales seguras para `ADMIN_USERNAME` y
`ADMIN_PASSWORD`. La contraseña inicial del administrador debe tener al menos
14 caracteres. No compartas ni subas `.env`.

Inicializa PostgreSQL:

```powershell
python scripts/inicializar_postgres.py
```

El script crea la base PostgreSQL si no existe, aplica el esquema y carga los
datos de catálogo definidos para una instalación nueva. No lee, copia ni
modifica `megaseg.db`, y no vacía los datos que ya existan en PostgreSQL. Si la
tabla de usuarios está vacía, crea el primer administrador usando las
credenciales configuradas. La configuración de `.env` se conserva sin cambios.

Las tablas `facturas` y `detalles_factura` se mantienen como archivo histórico;
ya no hay pantallas ni operaciones de facturación en la aplicación. La base
SQLite existente se conserva aparte y no se transfiere automáticamente. Si más
adelante se decide importar datos, debe hacerse como una migración explícita,
planificada y validada, no como parte de la inicialización.

## Ejecutar

```powershell
python app.py
```

Abre <http://127.0.0.1:5000>. La aplicación usa PostgreSQL cuando
`USE_POSTGRES=true`; no cambia silenciosamente a SQLite si falla la conexión.
Para una prueba temporal basada en SQLite, activa explícitamente
`USE_SQLITE=true`. Si no se configura ningún motor, la aplicación falla con un
mensaje explícito en vez de conectarse a SQLite por defecto.

## Registro y aprobación

- `Cliente` queda activo inmediatamente.
- `Gestor de Catálogo` y `Administrador` quedan pendientes y no pueden iniciar
  sesión hasta que cualquier cuenta con rol `Administrador` la admita en
  `/admin/usuarios`.
- La primera cuenta administrativa se crea únicamente durante la inicialización
  con `ADMIN_USERNAME` y `ADMIN_PASSWORD`; no se concede el primer rol de
  Administrador a través del registro público.

Roles vigentes: Administrador, Gestor de Catálogo, Supervisor, Auditor y Cliente.

## Cómo interpretar la auditoría

- **Usuario responsable:** cuenta que realizó la acción.
- **Rol activo:** rol vigente al momento del evento.
- **Acción:** operación registrada, por ejemplo inicio de sesión, creación,
  modificación, eliminación o cambio de rol.
- **Entidad:** objeto afectado. `auth` es una sesión de usuario, `servicio`
  pertenece al catálogo, `usuario` corresponde a cuentas y roles, y `resena`
  representa una opinión pendiente o aprobada.
- **Identificador:** número del registro afectado. Por ejemplo, `#10` identifica
  el servicio con ese ID.
- **Detalles:** resultado concreto explicado en lenguaje administrativo.
- **Dirección IP:** origen desde el que se realizó la operación.

## Contraseñas y usuarios

Las contraseñas nuevas se reciben en texto plano desde el formulario y se
convierten una sola vez a un hash scrypt antes de guardarse en PostgreSQL.
El hash es irreversible; no es cifrado que se pueda descifrar. El inicio de
sesión compara la contraseña ingresada con el hash y nunca necesita recuperar
la contraseña original.

Para revisar cuentas antiguas sin modificar la base:

```powershell
python scripts/migrar_hashes_password.py
```

Si el informe muestra contraseñas heredadas sin hash, conviértelas de forma
transaccional conservando la contraseña que usa cada cuenta:

```powershell
python scripts/migrar_hashes_password.py --apply
```

El asistente no muestra las contraseñas ni modifica la base si encuentra un
formato hash heredado que no puede verificar. El `ADMIN_PASSWORD` de `.env` se
usa únicamente para inicializar el primer Administrador; retíralo manualmente
después de crear esa cuenta. Para cambiar la contraseña del Administrador usa
`python scripts/reset_admin_password.py`; la contraseña nueva no se guarda en
`.env`.

## Estructura principal

| Ruta | Responsabilidad |
| --- | --- |
| `app.py` | Rutas Flask, autenticación y políticas de acceso |
| `models.py` | Modelo de usuario y verificación de contraseña |
| `conexion/` | Conexión y datos iniciales |
| `repositories/` | Consultas y persistencia |
| `forms/` | Validación de formularios |
| `templates/index1.html` | Composición Jinja de la portada principal |
| `templates/components/inicio/` | Secciones independientes de la portada |
| `templates/components/` | Navegación y pie de página compartidos |
| `templates/index.html` | Alias compatible de la portada |
| `static/css/estilo.css` | Estilos de la aplicación |
| `static/js/script.js` | Interacciones del catálogo y cotizador |
| `sql/esquema.sql` | Esquema SQLite legado |
| `sql/esquema_postgres.sql` | Esquema PostgreSQL local |
| `scripts/inicializar_postgres.py` | Inicialización de PostgreSQL sin importar SQLite |
| `scripts/migrar_hashes_password.py` | Conversión segura de contraseñas heredadas en PostgreSQL |
| `scripts/migrar_rol_postgres.py` | Adaptación del esquema `rol_id` al esquema de Megaseg |
| `MANUAL_RECUPERACION_PASSWORD.md` | Guía completa de recuperación de contraseñas por correo |

Las imágenes del catálogo se guardan en `static/imagenes/catalogo/`. Se aceptan
JPG, PNG y WebP de hasta 5 MB.

## Pruebas

Con el entorno configurado, ejecuta:

```powershell
python test_app.py
python test_nuevas_funciones.py
```

## Despliegue

`Procfile` inicia Gunicorn. En el entorno de despliegue configura
`SECRET_KEY`, `FLASK_ENV=production`, `SESSION_COOKIE_SECURE=true` y
`DATABASE_URL` si corresponde. No reutilices el `.env` local en producción.

### Publicar el código en GitHub

1. Verifica que `.env`, `megaseg.db` y archivos `.dump` estén ignorados:

```powershell
git status --short
git check-ignore .env megaseg.db
```

2. Revisa los archivos cambiados, confirma la versión y envía `main`:

```powershell
git add .
git diff --cached --stat
git diff --cached --check
git commit -m "Preparar Megaseg para producción"
git push origin main
```

Si GitHub solicita autenticación, usa el navegador o un Personal Access
Token con permisos de `Contents: Read and write`; nunca uses ni subas la
contraseña de PostgreSQL ni `SECRET_KEY` en el repositorio.

### Render: aplicación y PostgreSQL

1. Crea un nuevo proyecto en Render y selecciona **Blueprint**.
2. Conecta el repositorio `Mari6002/megaseg` y usa `render.yaml`.
3. Crea o verifica la base PostgreSQL administrada por el Blueprint.
4. En **Environment**, configura los secretos de producción:
   - `SECRET_KEY`: cadena larga y aleatoria, distinta de la local.
   - `ADMIN_USERNAME`: usuario inicial del Administrador.
   - `ADMIN_PASSWORD`: contraseña nueva de al menos 14 caracteres.
5. Cambia la contraseña de PostgreSQL en Render y no reutilices la contraseña
   local. Render proporciona `DATABASE_URL` automáticamente.
5. Configura también el correo de recuperación: `SMTP_HOST`, `SMTP_PORT`,
   `SMTP_USERNAME`, `SMTP_PASSWORD`, `MAIL_FROM`, `SMTP_USE_TLS=true` y
   `PASSWORD_RESET_SECRET` con una cadena distinta y aleatoria.
6. Ejecuta un despliegue. El comando `preDeployCommand` aplica
   `sql/esquema_postgres.sql` y crea el Administrador solo si la tabla está
   vacía. No importa ni copia `megaseg.db`.
7. Después del primer inicio, elimina `ADMIN_PASSWORD` de las variables de
   Render y cambia la contraseña por un procedimiento seguro si fuera necesario.

GitHub Pages no debe usarse para esta aplicación Flask: Pages solo sirve
archivos estáticos y no puede ejecutar Gunicorn ni PostgreSQL. Usa Render para
la aplicación dinámica y GitHub únicamente para el código y las versiones.

### Dominio propio

1. En Render abre el servicio web y selecciona **Settings → Custom Domains**.
2. Agrega el dominio o subdominio contratado, por ejemplo
   `megaseg.com.ec` o `www.megaseg.com.ec`.
3. Render mostrará registros DNS específicos. En el proveedor de dominio crea:
   - `CNAME www` apuntando al dominio `*.onrender.com` indicado por Render.
   - `A` o `ALIAS/APEX` para el dominio raíz, según lo indique el proveedor.
4. Espera la validación DNS y activa la redirección HTTPS/certificado que
   proporciona Render.
5. En el dominio propio, verifica inicio, login, catálogo, administración y
   renovación de sesión con `https://`.

## Recuperación de contraseña por correo

En **Login** aparece **¿Olvidaste tu contraseña?**. El usuario escribe su usuario
o correo y recibe, si la cuenta existe y está activa, un enlace válido por 30
minutos. El enlace solo puede utilizarse una vez.

Configura estas variables en Render o en `.env` local:

| Variable | Uso |
| --- | --- |
| `SMTP_HOST` | Servidor SMTP del proveedor |
| `SMTP_PORT` | Puerto SMTP, normalmente `587` |
| `SMTP_USERNAME` | Usuario o dirección remitente autorizada |
| `SMTP_PASSWORD` | Contraseña SMTP o contraseña de aplicación |
| `SMTP_USE_TLS` | Usa `true` para STARTTLS |
| `MAIL_FROM` | Dirección que aparecerá como remitente |
| `PASSWORD_RESET_SECRET` | Secreto largo y diferente de `SECRET_KEY` |

Ejemplo para Gmail: `smtp.gmail.com`, puerto `587`, usuario con el correo
completo y contraseña de aplicación de Google. Ejemplo para Microsoft 365:
`smtp.office365.com`, puerto `587`, usuario y contraseña autorizados por el
administrador del correo corporativo.

No uses la contraseña normal del correo si el proveedor exige autenticación en
dos pasos. Genera una contraseña de aplicación. Nunca subas `SMTP_PASSWORD`,
`PASSWORD_RESET_SECRET` ni `SECRET_KEY` a GitHub.
