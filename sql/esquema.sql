-- ==============================================================================
-- PROYECTO: MEGASEG SEGURIDAD INTEGRAL - ESQUEMA LOCAL (SQLite)
-- Basado en la arquitectura profesional de NEXODIGITAL
-- ==============================================================================

-- 1. TABLA DE ROLES DEL SISTEMA (RBAC)
CREATE TABLE IF NOT EXISTS roles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre VARCHAR(50) NOT NULL UNIQUE,
    descripcion TEXT
);

-- 2. TABLA DE USUARIOS Y CONTROL DE ACCESO
CREATE TABLE IF NOT EXISTS usuarios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario VARCHAR(50) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL,
    rol VARCHAR(50) NOT NULL DEFAULT 'Cliente',
    nombre VARCHAR(100) NOT NULL,
    email VARCHAR(120),
    telefono VARCHAR(50),
    activo INTEGER NOT NULL DEFAULT 1,
    creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3. CATEGORÍAS DEL CATÁLOGO
CREATE TABLE IF NOT EXISTS tipos_servicio (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre VARCHAR(100) NOT NULL UNIQUE,
    descripcion TEXT
);

-- 4. CATÁLOGO DE SERVICIOS Y PRODUCTOS (PLANTILLA DINÁMICA CONECTADA A BD)
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
    
    -- Campos dinámicos para la plantilla técnica y comercial
    tipo_producto VARCHAR(100) DEFAULT 'Servicio Operativo',
    garantia TEXT,
    zona_cobertura TEXT,
    disponibilidad_atencion TEXT,
    modalidad_pago TEXT,
    ficha_tecnica TEXT,
    whatsapp_msg TEXT,
    
    creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (tipo_servicio_id)
        REFERENCES tipos_servicio (id)
        ON UPDATE CASCADE
        ON DELETE RESTRICT
);

-- 5. AUDITORÍA Y LOGS DEL SISTEMA (Historial de cambios, fechas, usuarios y roles)
CREATE TABLE IF NOT EXISTS logs_actividad (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id INTEGER,
    usuario_nombre VARCHAR(100),
    rol VARCHAR(50),
    accion VARCHAR(100) NOT NULL,
    entidad VARCHAR(50) NOT NULL,
    entidad_id VARCHAR(50),
    detalles TEXT,
    ip VARCHAR(45),
    fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (usuario_id) REFERENCES usuarios (id) ON DELETE SET NULL
);

-- 6. FACTURACIÓN ELECTRÓNICA & INTEGRACIÓN CON SRI
CREATE TABLE IF NOT EXISTS facturas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    numero_factura VARCHAR(50) NOT NULL UNIQUE,
    cliente_nombre VARCHAR(150) NOT NULL,
    cliente_identificacion VARCHAR(20) NOT NULL,
    cliente_email VARCHAR(120),
    cliente_telefono VARCHAR(50),
    cliente_direccion VARCHAR(255),
    tipo_documento VARCHAR(20) NOT NULL DEFAULT 'Factura',
    subtotal REAL NOT NULL DEFAULT 0.0,
    iva REAL NOT NULL DEFAULT 0.0,
    total REAL NOT NULL DEFAULT 0.0,
    forma_pago VARCHAR(100) DEFAULT 'Transferencia bancaria',
    estado VARCHAR(20) NOT NULL DEFAULT 'Emitida',
    estado_sri VARCHAR(30) NOT NULL DEFAULT 'PENDIENTE',
    clave_acceso VARCHAR(49),
    numero_autorizacion VARCHAR(49),
    fecha_emision TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    fecha_autorizacion TIMESTAMP,
    observaciones TEXT,
    creado_por INTEGER,
    FOREIGN KEY (creado_por) REFERENCES usuarios (id) ON DELETE SET NULL
);

-- 7. DETALLE DE ÍTEMS DE FACTURACIÓN
CREATE TABLE IF NOT EXISTS detalles_factura (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    factura_id INTEGER NOT NULL,
    servicio_id INTEGER,
    descripcion TEXT NOT NULL,
    cantidad INTEGER NOT NULL DEFAULT 1 CHECK (cantidad > 0),
    precio_unitario REAL NOT NULL DEFAULT 0.0,
    subtotal REAL NOT NULL DEFAULT 0.0,
    FOREIGN KEY (factura_id) REFERENCES facturas (id) ON DELETE CASCADE,
    FOREIGN KEY (servicio_id) REFERENCES servicios (id) ON DELETE SET NULL
);

-- ÍNDICES DE RENDIMIENTO
CREATE INDEX IF NOT EXISTS idx_servicios_tipo ON servicios (tipo_servicio_id);
CREATE INDEX IF NOT EXISTS idx_servicios_disponible ON servicios (disponible);
CREATE INDEX IF NOT EXISTS idx_servicios_destacado ON servicios (destacado);
CREATE INDEX IF NOT EXISTS idx_servicios_nombre ON servicios (nombre COLLATE NOCASE);
CREATE INDEX IF NOT EXISTS idx_usuarios_login ON usuarios (usuario COLLATE NOCASE);
CREATE INDEX IF NOT EXISTS idx_logs_fecha ON logs_actividad (fecha DESC);
CREATE INDEX IF NOT EXISTS idx_logs_usuario ON logs_actividad (usuario_id);
CREATE INDEX IF NOT EXISTS idx_facturas_numero ON facturas (numero_factura);
CREATE INDEX IF NOT EXISTS idx_facturas_sri ON facturas (estado_sri);
