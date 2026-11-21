# Publicar Megaseg en GitHub Pages

GitHub Pages sirve únicamente archivos estáticos. La portada dentro de `docs/`
funciona sin VS Code, sin Python y sin servidor propio. El sistema dinámico
del catálogo, login y PostgreSQL se despliega por separado en Render.

## Qué contiene

- `docs/index.html`: página pública independiente.
- `docs/css/estilo.css`: estilos oficiales.
- `docs/images/`: imágenes y logotipo.
- `docs/robots.txt`: reglas de rastreo.
- `docs/sitemap.xml`: mapa para buscadores.
- `docs/404.html`: página de error.
- `docs/.nojekyll`: evita procesamiento Jekyll.

## Activar GitHub Pages

1. Guarda el proyecto en GitHub en la rama `main`.
2. Abre `Settings > Pages`.
3. En **Build and deployment**, selecciona:
   - Source: `Deploy from a branch`.
   - Branch: `main`.
   - Folder: `/docs`.
4. Guarda y espera a que termine el despliegue.

La dirección inicial será:

```text
https://Mari6002.github.io/megaseg/
```

Sustituye `Mari6002` únicamente si cambia el propietario real del repositorio.

## Configurar dominio propio

Cuando tengas el dominio contratado:

1. Agrega el dominio en `Settings > Pages > Custom domain`.
2. Crea el registro DNS indicado por GitHub.
3. Conserva HTTPS activado.
4. Sustituye en `docs/index.html` la URL:

```html
<link rel="canonical" href="https://TU-DOMINIO/">
```

Sustituye también:

- `https://mari6002.github.io/megaseg/` en `robots.txt`.
- `https://mari6002.github.io/megaseg/` en `sitemap.xml`.
- El `@id` y URL del JSON-LD si corresponde.

No publiques enlaces a `localhost`, `127.0.0.1` ni URLs privadas.

## Google Search Console

1. Abre Google Search Console.
2. Agrega la propiedad por dominio o URL.
3. Verifica la propiedad mediante DNS o el método que indique Google.
4. Envía `https://TU-DOMINIO/sitemap.xml`.
5. Solicita indexación de la portada.
6. Conecta Google Maps y Google Business Profile si aún no están vinculados.

Google no garantiza primera posición. La indexación mejora con:

- Dominio propio y HTTPS.
- Nombre, dirección y teléfono consistentes.
- Perfil oficial de Google Business.
- Contenido original y actual.
- Enlaces externos confiables.
- Velocidad y compatibilidad móvil.
- Sitemap y versiones no duplicadas de la página.

## Actualizar la portada

Edita `docs/index.html`, luego ejecuta:

```powershell
git add docs
git diff --cached --stat
git diff --cached --check
git commit -m "Actualizar portada pública Megaseg"
git push origin main
```

GitHub Pages actualizará automáticamente el sitio estático.

## Aplicación dinámica

La portada estática puede mostrar información pública. Para funciones reales:

- Login.
- Administración.
- PostgreSQL.
- Carga de imágenes.
- Reseñas moderadas.
- Recuperación de contraseña.

Debe usar Render u otro servidor Python. GitHub Pages no ejecuta Flask ni
PostgreSQL y no puede reemplazar el despliegue dinámico.
