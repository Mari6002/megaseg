# Manual del administrador de MEGASEG

## 1. Instalación y PostgreSQL local

1. Inicia el servicio de PostgreSQL en Windows.
2. Instala dependencias y crea la configuración local:

   ```powershell
   python -m pip install -r requirements.txt
   Copy-Item .env.example .env
   notepad .env
   ```

3. Configura `SECRET_KEY`, `DB_PASSWORD`, `ADMIN_USERNAME` y
   `ADMIN_PASSWORD`. La contraseña del administrador inicial debe tener al menos
   14 caracteres. No compartas el archivo `.env`.
4. Migra la base local:

   ```powershell
   python scripts/inicializar_postgres.py
   ```

   Si existe `megaseg.db`, el script crea primero un respaldo fechado en
   `backups/`, copia sus datos a una base PostgreSQL vacía y conserva el archivo
   SQLite original. Si no existe, inicializa el esquema, el catálogo inicial y
   el administrador desde `.env`. El script no sobrescribe bases PostgreSQL con
   datos.
5. Inicia la web:

   ```powershell
   python app.py
   ```

   Abre <http://127.0.0.1:5000>. Si no se puede conectar a PostgreSQL, revisa
   que el servicio esté en ejecución y que `DB_HOST`, `DB_PORT`, `DB_NAME`,
   `DB_USER` y `DB_PASSWORD` sean correctos.

## 2. Cuentas y admisión

En `/registro`, cualquier persona puede solicitar una cuenta:

- **Cliente:** se activa al registrarse.
- **Gestor de Catálogo:** queda pendiente hasta que un Administrador lo admita.
- **Administrador:** también queda pendiente; no se puede obtener el primer
  Administrador por registro público.

El primer Administrador se crea en una instalación vacía usando las variables
`ADMIN_USERNAME` y `ADMIN_PASSWORD`. Un Administrador activo entra en
`/admin/usuarios` y usa **Admitir** para activar cualquier cuenta pendiente. La
admisión queda anotada en la auditoría. Los Administradores no pueden
desactivarse a sí mismos.

Desde esa misma pantalla, un Administrador puede cambiar el rol de una cuenta
entre los roles vigentes: Administrador, Gestor de Catálogo, Supervisor, Auditor
y Cliente. Los roles inválidos o retirados no se aceptan.

## 3. Catálogo

El catálogo público está en `/servicios`. Un Administrador o Gestor de Catálogo
admitido puede crear, editar y eliminar productos y servicios. El formulario
permite guardar precio, disponibilidad, categoría, imagen y detalles técnicos.
Las imágenes locales admitidas son JPG, PNG y WebP de hasta 5 MB. Al editar, si
no se carga otra imagen, se conserva la existente.

## 4. Auditoría

Los roles Administrador, Auditor y Supervisor pueden consultar `/admin/logs`.
La bitácora registra acciones de acceso, catálogo y cambios de rol. Los eventos
históricos se conservan; las vistas actuales ya no incluyen operaciones de
facturación.

## 5. Retiro de facturación y conservación de datos

Se retiraron el rol `Facturador / Operador`, las rutas y las pantallas del módulo
de facturación. Las tablas `facturas` y `detalles_factura` se mantienen en el
esquema únicamente para conservar los registros históricos al migrar; no se
crean facturas de demostración ni se exponen en la web. Las cuentas antiguas
con el rol retirado se desactivan y deben recibir un rol vigente y una admisión
administrativa.

## 6. Archivos y respaldo

- `megaseg.db`: base SQLite original; no se borra al migrar.
- `backups/`: respaldos SQLite fechados previos a la migración.
- `.env`: credenciales y configuración local; no se versiona.
- `sql/esquema_postgres.sql`: esquema de PostgreSQL.

No uses el asistente de reinicio SQLite para borrar datos PostgreSQL. Antes de
cambiar o eliminar una base PostgreSQL, crea un respaldo con las herramientas
de PostgreSQL.
