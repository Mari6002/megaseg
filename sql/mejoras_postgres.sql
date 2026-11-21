-- MEGASEG - Actualización incremental de PostgreSQL
-- Ejecutar sobre la base 'megaseg'. No elimina usuarios, servicios ni datos existentes.

ALTER TABLE logs_actividad
    ADD COLUMN IF NOT EXISTS usuario_nombre VARCHAR(100),
    ADD COLUMN IF NOT EXISTS rol VARCHAR(50);

ALTER TABLE servicios
    ADD COLUMN IF NOT EXISTS campos_extra JSONB NOT NULL DEFAULT '[]'::jsonb;

CREATE INDEX IF NOT EXISTS idx_servicios_campos_extra
    ON servicios USING gin (campos_extra);

CREATE TABLE IF NOT EXISTS consultas_servicios (
    id SERIAL PRIMARY KEY,
    servicio_id INTEGER REFERENCES servicios(id),
    termino_busqueda VARCHAR(255),
    ip VARCHAR(45),
    fecha TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_consultas_ip
    ON consultas_servicios(ip);

CREATE TABLE IF NOT EXISTS solicitudes_cotizacion (
    id SERIAL PRIMARY KEY,
    servicio_id INTEGER REFERENCES servicios(id),
    nombre_cliente VARCHAR(150),
    telefono VARCHAR(50),
    email VARCHAR(120),
    mensaje TEXT,
    estado VARCHAR(20) DEFAULT 'Pendiente',
    fecha TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS sesiones (
    id SERIAL PRIMARY KEY,
    usuario_id INTEGER NOT NULL REFERENCES usuarios(id),
    fecha_inicio TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    fecha_fin TIMESTAMPTZ,
    ip VARCHAR(45),
    user_agent TEXT
);

CREATE TABLE IF NOT EXISTS resenas (
    id SERIAL PRIMARY KEY,
    servicio_id INTEGER REFERENCES servicios(id) ON DELETE SET NULL,
    nombre VARCHAR(100) NOT NULL,
    comentario TEXT NOT NULL
        CHECK (char_length(comentario) BETWEEN 10 AND 1000),
    calificacion SMALLINT NOT NULL
        CHECK (calificacion BETWEEN 1 AND 5),
    aprobada BOOLEAN NOT NULL DEFAULT FALSE,
    creada_en TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

ALTER TABLE resenas
    ADD COLUMN IF NOT EXISTS servicio_id INTEGER REFERENCES servicios(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_resenas_aprobada_fecha
    ON resenas(aprobada, creada_en DESC);

CREATE TABLE IF NOT EXISTS password_reset_tokens (
    id SERIAL PRIMARY KEY,
    usuario_id INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    token_hash VARCHAR(64) NOT NULL UNIQUE,
    creado_en TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expira_en TIMESTAMPTZ NOT NULL,
    usado_en TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_password_reset_usuario
    ON password_reset_tokens(usuario_id);
