# Recuperación de contraseña en Megaseg

Este manual explica cómo funciona la recuperación de contraseña por correo,
cómo configurarla, qué se guarda en PostgreSQL y cómo probarla sin utilizar
IA. SQLite no es la base principal ni una fuente para producción.

## 1. Objetivo

Un usuario que olvidó su contraseña debe poder:

1. Escribir su usuario o correo en **Iniciar sesión**.
2. Recibir un correo con un enlace temporal.
3. Abrir el enlace dentro de 30 minutos.
4. Crear una contraseña nueva de al menos 14 caracteres.
5. Iniciar sesión con la contraseña nueva.

El enlace:

- No se guarda completo en la base.
- Solo se guarda su huella SHA-256.
- Expira después de 30 minutos.
- Solo puede utilizarse una vez.
- No revela si un usuario existe.
- Solo funciona para cuentas activas.

## 2. Archivos principales

| Archivo | Responsabilidad |
| --- | --- |
| `app.py` | Rutas de solicitud y restablecimiento |
| `forms/login_form.py` | Formularios de recuperación |
| `templates/login.html` | Enlace visible desde el inicio de sesión |
| `templates/recuperar_password.html` | Solicitud de recuperación |
| `templates/restablecer_password.html` | Nueva contraseña |
| `repositories/usuario_repository.py` | Buscar cuentas y cambiar contraseñas |
| `security/passwords.py` | Crear hashes scrypt seguros |
| `sql/mejoras_postgres.sql` | Actualización incremental de PostgreSQL |

## 3. Variables de entorno

Agrega estas variables en el entorno local `.env` o en las Environment Variables
de Render:

```env
PASSWORD_RESET_SECRET=
SMTP_HOST=
SMTP_PORT=587
SMTP_USERNAME=
SMTP_PASSWORD=
SMTP_USE_TLS=true
MAIL_FROM=
```

Explicación:

- `PASSWORD_RESET_SECRET`: secreto privado usado para firmar enlaces.
  Debe ser diferente de `SECRET_KEY`.
- `SMTP_HOST`: servidor SMTP del proveedor.
- `SMTP_PORT`: puerto SMTP, normalmente `587`.
- `SMTP_USERNAME`: usuario autorizado del servidor de correo.
- `SMTP_PASSWORD`: contraseña SMTP o contraseña de aplicación.
- `SMTP_USE_TLS`: `true` para STARTTLS.
- `MAIL_FROM`: dirección visible como remitente.

Ejemplos comunes:

```text
Gmail:
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=tu-cuenta@gmail.com
SMTP_PASSWORD=contraseña-de-aplicación
MAIL_FROM=tu-cuenta@gmail.com

Microsoft 365:
SMTP_HOST=smtp.office365.com
SMTP_PORT=587
SMTP_USERNAME=correo@tu-dominio.com
SMTP_PASSWORD=contraseña-o-secreto-autorizado
MAIL_FROM=correo@tu-dominio.com
```

Si el proveedor usa autenticación en dos pasos, no uses la contraseña normal:
crea una contraseña de aplicación en ese proveedor.

No subas `.env`, secretos SMTP ni claves privadas a GitHub.

## 4. SQL necesario en PostgreSQL

Ejecuta este bloque en pgAdmin, Query Tool o psql sobre la base `megaseg`.
No elimina usuarios, servicios ni datos existentes.

```sql
CREATE TABLE IF NOT EXISTS password_reset_tokens (
    id SERIAL PRIMARY KEY,
    usuario_id INTEGER NOT NULL
        REFERENCES usuarios(id)
        ON DELETE CASCADE,
    token_hash VARCHAR(64) NOT NULL UNIQUE,
    creado_en TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expira_en TIMESTAMPTZ NOT NULL,
    usado_en TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_password_reset_usuario
ON password_reset_tokens(usuario_id);
```

Esta tabla contiene únicamente el control del enlace:

- `usuario_id`: cuenta que solicitó recuperar la contraseña.
- `token_hash`: huella SHA-256 del enlace; no es el token completo.
- `creado_en`: momento de creación.
- `expira_en`: vencimiento, establecido 30 minutos después.
- `usado_en`: fecha de uso. Mientras sea `NULL`, todavía puede utilizarse.

Verifica la tabla:

```sql
SELECT
    id,
    usuario_id,
    creado_en,
    expira_en,
    usado_en
FROM password_reset_tokens
ORDER BY creado_en DESC;
```

## 5. Flujo lógico completo

### Paso A: Usuario solicita recuperación

1. El usuario abre `/login`.
2. Pulsa **¿Olvidaste tu contraseña?**.
3. La página solicita `/recuperar-password`.
4. El servidor busca el usuario o correo.
5. Si existe y está activo:
   - Crea un token firmado.
   - Calcula su SHA-256.
   - Marca enlaces anteriores de ese usuario como utilizados.
   - Guarda el nuevo `token_hash` y 30 minutos de vigencia.
   - Envía el enlace completo por correo.
6. Si no existe o está inactivo:
   - No informa que la cuenta existe.
   - Se muestra el mismo mensaje general por seguridad.

La URL tiene esta forma conceptual:

```text
https://tu-dominio/restablecer-password/EL-TOKEN-FIRMADO
```

### Paso B: Usuario abre el enlace

1. El servidor verifica la firma del token.
2. Comprueba que no tenga más de 30 minutos.
3. Calcula nuevamente el SHA-256 del token recibido.
4. Busca ese hash en PostgreSQL.
5. Exige que:
   - pertenezca al usuario indicado;
   - no esté marcado como usado;
   - no haya expirado.

Si todo es válido, muestra el formulario de nueva contraseña.

### Paso C: Usuario crea la nueva contraseña

1. La página exige mínimo 14 caracteres.
2. Compara contraseña y confirmación.
3. El servidor crea un hash scrypt.
4. Actualiza `usuarios.password`.
5. Coloca `usado_en` en el token.
6. Registra el evento en `logs_actividad`.

Los cambios se realizan juntos en PostgreSQL:

```text
Actualizar contraseña
        +
Marcar token como usado
        =
Una operación válida
```

Si el usuario intenta abrir el mismo enlace otra vez, encuentra `usado_en`
relleno y no puede cambiar nuevamente la contraseña.

## 6. Generación del secreto

Para generar un secreto local puedes ejecutar PowerShell:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Copia el resultado en `PASSWORD_RESET_SECRET`. En producción se debe crear
otro secreto distinto para Render.

No uses contraseñas conocidas ni reutilices `SECRET_KEY`.

## 7. Cómo probar sin correo real

Primero configura un proveedor SMTP válido o una bandeja de pruebas.

### Prueba correcta

1. Ejecuta la aplicación.
2. Abre `/login`.
3. Pulsa **¿Olvidaste tu contraseña?**.
4. Ingresa el correo real de una cuenta activa.
5. Revisa correo, SPAM y carpeta promocional.
6. Abre el enlace recibido.
7. Ingresa una contraseña nueva de al menos 14 caracteres.
8. Confirma la contraseña.
9. Regresa a `/login`.
10. Inicia sesión con la contraseña nueva.

### Prueba de cuenta inexistente

1. Ingresa un correo que no esté registrado.
2. Debe aparecer el mismo mensaje general.
3. No debe indicar que la cuenta no existe.

### Prueba de vencimiento

1. Solicita un enlace.
2. Modifica manualmente `expira_en` a una fecha anterior.
3. Abre el enlace.
4. Debe mostrarse como inválido o expirado.

Ejemplo SQL de prueba:

```sql
UPDATE password_reset_tokens
SET expira_en = CURRENT_TIMESTAMP - INTERVAL '1 minute'
WHERE id = (
    SELECT id
    FROM password_reset_tokens
    ORDER BY creado_en DESC
    LIMIT 1
);
```

### Prueba de un solo uso

1. Solicita un enlace.
2. Úsalo y cambia la contraseña.
3. Recarga o abre otra vez el mismo enlace.
4. Debe rechazarse porque `usado_en` ya tiene fecha.

Consulta el estado:

```sql
SELECT
    usuario_id,
    creado_en,
    expira_en,
    usado_en
FROM password_reset_tokens
ORDER BY creado_en DESC
LIMIT 20;
```

## 8. Limpieza periódica

Los enlaces vencidos o usados pueden eliminarse periódicamente:

```sql
DELETE FROM password_reset_tokens
WHERE usado_en IS NOT NULL
   OR expira_en < CURRENT_TIMESTAMP - INTERVAL '7 days';
```

No se necesita ejecutar diariamente si el volumen es pequeño, pero conviene
agregar una tarea programada o SQL periódico en producción.

## 9. Seguridad

- Nunca guardar el token completo en base de datos.
- Nunca enviar la contraseña en el correo.
- Nunca incluir el hash scrypt en el mensaje.
- Nunca devolver si un usuario existe.
- Nunca aceptar enlaces vencidos.
- Nunca reutilizar enlaces usados.
- Nunca escribir `SMTP_PASSWORD` en el código o Git.
- Usar HTTPS en producción.
- Mantener `PASSWORD_RESET_SECRET` estable. Si cambia, todos los enlaces
  existentes dejan de ser válidos.

## 10. Rutas implementadas

```text
GET  /login
POST /login
GET  /recuperar-password
POST /recuperar-password
GET  /restablecer-password/<token>
POST /restablecer-password/<token>
```

El sistema de correo es SMTP. No depende de SQLite. PostgreSQL conserva
únicamente el registro técnico del token y su estado.
