# 📖 Manual de Usuario Administrador
## Grupo de Seguridad MEGASEG Cía. Ltda.
> Guía paso a paso para la gestión y publicación de servicios y productos en el portal web

---

### 📌 Índice de Contenidos
1. [Cómo Iniciar el Servidor de la Página Web](#1-cómo-iniciar-el-servidor-de-la-página-web)
2. [Cómo Iniciar Sesión como Administrador](#2-cómo-iniciar-sesión-como-administrador)
3. [Cómo Publicar un Nuevo Servicio o Producto](#3-cómo-publicar-un-nuevo-servicio-o-producto)
4. [Cómo Editar un Servicio o Producto Existente](#4-cómo-editar-un-servicio-o-producto-existente)
5. [Cómo Eliminar una Publicación del Catálogo](#5-cómo-eliminar-una-publicación-del-catálogo)
6. [Manejo de Fotografías e Imágenes](#6-manejo-de-fotografías-e-imágenes)
7. [Cómo Cambiar la Contraseña de Administrador](#7-cómo-cambiar-la-contraseña-de-administrador)
8. [Cerrar Sesión de Seguridad](#8-cerrar-sesión-de-seguridad)

---

### 1. Cómo Iniciar el Servidor de la Página Web

1. Abre la consola o terminal de tu computadora (PowerShell o Símbolo del Sistema).
2. Dirígete a la carpeta del proyecto:
   ```powershell
   cd "c:\Users\quiar\Documents\PAGINA MEGASEG"
   ```
3. Ejecuta el comando de inicio:
   ```powershell
   python app.py
   ```
   La aplicación requiere `SECRET_KEY`, `ADMIN_USERNAME` y `ADMIN_PASSWORD` configurados en `.env`. Mantén ese archivo privado; `.env.example` solo sirve como guía.
4. Verás un mensaje en pantalla indicando:
   ```
   ======================================================================
     GRUPO DE SEGURIDAD MEGASEG CÍA. LTDA. — SISTEMA WEB ACTIVO
     Servidor ejecutándose en: http://127.0.0.1:5000
   ======================================================================
   ```
5. Abre tu navegador web favorito (Chrome, Edge, Firefox, Safari) e ingresa a:
   👉 **http://127.0.0.1:5000**

---

### 2. Cómo Iniciar Sesión como Administrador

1. En la parte superior de la página web (o en el pie de página), haz clic en el botón **`Acceso Admin`** o dirígete a:
   👉 **http://127.0.0.1:5000/login**
2. Ingresa el usuario y la contraseña entregados de forma privada por el responsable del sistema. Las credenciales no se incluyen en este manual.
3. Haz clic en **`Ingresar al Sistema`**.
4. El sistema te mostrará un mensaje verde de bienvenida y serás redirigido al catálogo con las herramientas administrativas activadas:
   * En el menú superior verás el menú **`Gestión Catálogo`**.
   * Encima del listado aparecerá el botón **`Nuevo Ítem`**.
   * Cada tarjeta mostrará el botón amarillo de **`Editar`** (`✏️`) y el botón rojo de **`Eliminar`** (`🗑️`).
   * El catálogo cuenta con **paginación automática de 12 ítems por hoja**, por lo que podrás navegar entre páginas en la barra inferior.

---

### 3. Cómo Publicar un Nuevo Servicio o Producto

1. Con la sesión iniciada, haz clic en **`Subir Servicio o Producto`** o en el botón **`Nuevo Ítem`** (ruta: `/servicios/nuevo`).
2. Llena los campos del formulario:
   * **Tipo de Publicación:** Elige si es un *Servicio de Seguridad* o un *Producto / Equipo Físico*.
   * **Categoría de Seguridad:** Selecciona la categoría apropiada (Cámaras CCTV, Alarmas y Cercos, Guardianía Física, GPS, Automatización, etc.).
   * **Nombre del Servicio o Producto:** Escribe el nombre atractivo (ej. *Kit 8 Cámaras ColorVu 4K Hikvision*).
   * **Precio Referencial ($ USD):** Ingresa la tarifa (ej. `240.00`). Si dejas `0.00`, en la tarjeta aparecerá como `A Cotizar`.
   * **Imagen del catálogo:** Elige una sola alternativa: selecciona un archivo JPG, PNG o WebP de hasta 5 MB desde tu dispositivo, o pega el enlace público directo `http://` o `https://` de una imagen. No escribas rutas de carpetas. El sistema guarda las cargas en `static/imagenes/catalogo/` y muestra una vista previa.
   * **Descripción y Características:** Explica detalladamente los beneficios técnicos y qué incluye la opción. Recuerda que el sistema cuenta con el botón interactivo **"Ver más detalles" / "Ver menos"**, por lo que puedes escribir descripciones completas con garantías, especificaciones de resolución, turnos de guardianía, etc., sabiendo que el cliente podrá expandirlas con un clic.
   * **Disponible para contratación / venta:** Déjalo marcado para que los clientes puedan cotizarlo de inmediato.
   * **Mostrar en portada de inicio:** Si lo marcas, aparecerá en los 6 servicios destacados de la página principal.
3. Haz clic en **`Guardar en el Catálogo`**.
4. ¡Listo! El nuevo elemento quedará guardado en la base de datos y visible para todos los visitantes con su ficha técnica desplegable.

---

### 4. Cómo Editar un Servicio o Producto Existente

1. En el catálogo (`/servicios`), ubica la tarjeta que deseas modificar.
2. Haz clic en el botón amarillo con el icono de lápiz (**`✏️`**).
3. Se abrirá el formulario con toda la información actual del producto o servicio.
4. Modifica lo que necesites (precio, descripción, foto, disponibilidad).
5. Haz clic en **`Guardar en el Catálogo`**.
6. Los cambios se guardarán de inmediato en la base de datos.

---

### 5. Cómo Eliminar una Publicación del Catálogo

1. Ubica el servicio o producto que deseas dar de baja en el catálogo.
2. Haz clic en el botón rojo con el icono de papelera (**`🗑️`**).
3. Tu navegador mostrará una ventana de confirmación: *¿Seguro que deseas eliminar este servicio/producto del catálogo?*
4. Haz clic en **Aceptar**.
5. El elemento se eliminará permanentemente de la base de datos.

---

### 6. Manejo de Fotografías e Imágenes

* **Opción recomendada:** carga el archivo directamente desde el formulario. La aplicación lo guarda en `static/imagenes/catalogo/` con un nombre seguro; no tienes que abrir ni escribir una ruta del servidor.
* **Alternativa:** pega un enlace público directo a la imagen. Se aceptan enlaces `http://` o `https://`, no enlaces a páginas web ni rutas locales.
* Puedes previsualizar la imagen antes de guardar. Al editar, si no eliges otra imagen ni pegas un enlace, se conserva la imagen actual.
* Se aceptan archivos JPG, PNG y WebP de hasta 5 MB. Si dejas vacías ambas opciones al crear una publicación, se usa la imagen corporativa predeterminada.

---

### 7. Cómo Cambiar la Contraseña de Administrador

Para cambiar la contraseña de acceso sin escribirla en el comando ni mostrarla en pantalla:
1. Abre una terminal en la carpeta del proyecto.
2. Ejecuta el asistente interactivo:
   ```powershell
   python scripts/reset_admin_password.py
   ```
3. Escribe una contraseña de al menos 14 caracteres y confírmala. El sistema la guarda como hash en la base de datos y actualiza el valor privado en `.env` para futuros despliegues de una base vacía.

---

### 8. Cerrar Sesión de Seguridad

Al terminar de gestionar tus publicaciones:
1. Haz clic en el menú **`Gestión Catálogo`** y selecciona **`Cerrar Sesión Admin`**, o haz clic en **`Salir`** en la barra superior roja.
2. La página regresará a la portada pública. Los botones de edición y eliminación desaparecerán, permitiendo que cualquier persona navegue y cotice por WhatsApp de forma limpia y profesional.
