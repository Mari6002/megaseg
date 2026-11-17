-- Esquema local de Megaseg para SQLite.
-- CREATE TABLE IF NOT EXISTS conserva los datos y permite reiniciar la app.

CREATE TABLE IF NOT EXISTS usuarios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario VARCHAR(50) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL,
    rol VARCHAR(50) NOT NULL DEFAULT 'Administrador',
    nombre VARCHAR(100),
    email VARCHAR(120),
    creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS tipos_servicio (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre VARCHAR(100) NOT NULL UNIQUE,
    descripcion TEXT
);

CREATE TABLE IF NOT EXISTS servicios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tipo_servicio_id INTEGER NOT NULL,
    nombre VARCHAR(150) NOT NULL,
    precio_base REAL NOT NULL DEFAULT 0 CHECK (precio_base >= 0),
    imagen TEXT,
    descripcion TEXT NOT NULL,
    disponible INTEGER NOT NULL DEFAULT 1,
    es_producto INTEGER NOT NULL DEFAULT 0,
    destacado INTEGER NOT NULL DEFAULT 0,
    creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (tipo_servicio_id)
        REFERENCES tipos_servicio (id)
        ON UPDATE CASCADE
        ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS idx_servicios_tipo
    ON servicios (tipo_servicio_id);
CREATE INDEX IF NOT EXISTS idx_servicios_disponible
    ON servicios (disponible);
CREATE INDEX IF NOT EXISTS idx_servicios_destacado
    ON servicios (destacado);
CREATE INDEX IF NOT EXISTS idx_servicios_nombre
    ON servicios (nombre COLLATE NOCASE);
CREATE INDEX IF NOT EXISTS idx_usuarios_login
    ON usuarios (usuario COLLATE NOCASE);
