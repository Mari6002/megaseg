# MEGASEG

Aplicación Flask para mostrar y administrar el catálogo de productos y servicios
de seguridad, gestionar cuentas con aprobación administrativa y registrar
actividad. La base de datos de la instalación local es PostgreSQL.

## Requisitos

- Windows 10/11, PowerShell y Python 3.10 o superior.
- PostgreSQL local instalado y en ejecución.

## Instalación y migración local

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

Ejecuta la migración:

```powershell
python scripts/inicializar_postgres.py
```

El script crea `backups/megaseg-pre-postgres-<fecha>.db`, conserva intacto
`megaseg.db`, copia a PostgreSQL las cuentas, roles vigentes, catálogo, auditoría
y registros históricos, actualiza las secuencias y activa `USE_POSTGRES=true`
en `.env`. No sobrescribe una base PostgreSQL que ya tenga datos; configura un
destino local vacío si el script indica que ya hay registros. Si no existe
`megaseg.db`, crea una instalación nueva y el administrador inicial desde las
credenciales del entorno.

Las tablas `facturas` y `detalles_factura` se conservan únicamente como archivo
histórico durante la migración; ya no hay pantallas ni operaciones de facturación
en la aplicación. Las cuentas antiguas con el rol retirado
`Facturador / Operador` quedan desactivadas para que un Administrador les asigne
un rol vigente y las admita de nuevo.

## Ejecutar

```powershell
python app.py
```

Abre <http://127.0.0.1:5000>. La aplicación usa PostgreSQL cuando
`USE_POSTGRES=true`; no cambia silenciosamente a SQLite si falla la conexión.
Para una prueba temporal basada en SQLite, activa explícitamente
`USE_SQLITE=true`.

## Registro y aprobación

- `Cliente` queda activo inmediatamente.
- `Gestor de Catálogo` y `Administrador` quedan pendientes y no pueden iniciar
  sesión hasta que cualquier cuenta con rol `Administrador` la admita en
  `/admin/usuarios`.
- La primera cuenta administrativa se crea únicamente durante la inicialización
  con `ADMIN_USERNAME` y `ADMIN_PASSWORD`; no se concede el primer rol de
  Administrador a través del registro público.

Roles vigentes: Administrador, Gestor de Catálogo, Supervisor, Auditor y Cliente.

## Estructura principal

| Ruta | Responsabilidad |
| --- | --- |
| `app.py` | Rutas Flask, autenticación y políticas de acceso |
| `models.py` | Modelo de usuario y verificación de contraseña |
| `conexion/` | Conexión y datos iniciales |
| `repositories/` | Consultas y persistencia |
| `forms/` | Validación de formularios |
| `templates/` | Vistas HTML |
| `sql/esquema.sql` | Esquema SQLite legado |
| `sql/esquema_postgres.sql` | Esquema PostgreSQL local |
| `scripts/inicializar_postgres.py` | Inicialización o migración con respaldo |

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
