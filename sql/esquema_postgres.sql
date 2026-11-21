-- ==============================================================================
-- PROYECTO: MEGASEG SEGURIDAD INTEGRAL - ESQUEMA DE BASE DE DATOS (PostgreSQL)
-- ==============================================================================
-- Instrucciones de Ejecución:
-- 1. En pgAdmin: Crear la base de datos 'megaseg' (o tu BD en Render/Supabase/Neon).
-- 2. Abrir Query Tool (Herramienta de Consultas) sobre la base 'megaseg'.
-- 3. Pegar este archivo completo y presionar F5 (Ejecutar).
-- 4. O vía terminal: psql -U postgres -d megaseg -f sql/esquema_postgres.sql
-- ==============================================================================

-- ==============================================================================
-- 1. TABLA DE ROLES DEL SISTEMA (RBAC)
-- ==============================================================================
CREATE TABLE IF NOT EXISTS roles (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(50) NOT NULL UNIQUE,
    descripcion TEXT
);

-- ==============================================================================
-- 2. TABLA DE USUARIOS Y CONTROL DE ACCESO
-- ==============================================================================
CREATE TABLE IF NOT EXISTS usuarios (
    id SERIAL PRIMARY KEY,
    usuario VARCHAR(50) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL,
    rol_id INTEGER NOT NULL REFERENCES roles(id),
    nombre VARCHAR(100) NOT NULL,
    email VARCHAR(120),
    telefono VARCHAR(50),
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    creado_en TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- ==============================================================================
-- 3. CATEGORÍAS DEL CATÁLOGO
-- ==============================================================================
CREATE TABLE IF NOT EXISTS tipos_servicio (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL UNIQUE,
    descripcion TEXT
);

-- ==============================================================================
-- 4. CATÁLOGO DE SERVICIOS Y PRODUCTOS (PLANTILLA DINÁMICA CONECTADA A BD)
-- ==============================================================================
CREATE TABLE IF NOT EXISTS servicios (
    id SERIAL PRIMARY KEY,
    tipo_servicio_id INT NOT NULL REFERENCES tipos_servicio(id) ON UPDATE CASCADE ON DELETE RESTRICT,
    nombre VARCHAR(150) NOT NULL,
    precio_base NUMERIC(12,2) NOT NULL DEFAULT 0.00 CHECK (precio_base >= 0),
    imagen TEXT,
    descripcion TEXT NOT NULL,
    disponible BOOLEAN NOT NULL DEFAULT TRUE,
    es_producto INT NOT NULL DEFAULT 0, -- 0: Servicio Operativo, 1: Producto / Equipo Físico
    destacado BOOLEAN NOT NULL DEFAULT FALSE,
    
    -- Campos dinámicos de la ficha técnica y plantilla comercial
    tipo_producto VARCHAR(100) DEFAULT 'Servicio Operativo',
    garantia TEXT,
    zona_cobertura TEXT,
    disponibilidad_atencion TEXT,
    modalidad_pago TEXT,
    ficha_tecnica TEXT,
    whatsapp_msg TEXT,
    campos_extra JSONB NOT NULL DEFAULT '[]'::jsonb,
    
    creado_en TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- ==============================================================================
-- 5. AUDITORÍA Y LOGS DEL SISTEMA (Historial de Cambios, Acciones y Roles)
-- ==============================================================================
CREATE TABLE IF NOT EXISTS logs_actividad (
    id SERIAL PRIMARY KEY,
    usuario_id INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE SET NULL,
    accion VARCHAR(100) NOT NULL,
    entidad VARCHAR(50) NOT NULL,
    entidad_id INTEGER,
    detalles TEXT,
    ip VARCHAR(45),
    fecha TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Estas tablas se conservan únicamente para archivar los datos históricos existentes.
CREATE TABLE IF NOT EXISTS facturas (
    id SERIAL PRIMARY KEY,
    numero_factura VARCHAR(50) NOT NULL UNIQUE, -- Ej: 001-001-000000001
    cliente_nombre VARCHAR(150) NOT NULL,
    cliente_identificacion VARCHAR(20) NOT NULL, -- RUC / Cédula
    cliente_email VARCHAR(120),
    cliente_telefono VARCHAR(50),
    cliente_direccion VARCHAR(255),
    tipo_documento VARCHAR(20) NOT NULL DEFAULT 'Factura',
    subtotal NUMERIC(12,2) NOT NULL DEFAULT 0.00,
    iva NUMERIC(12,2) NOT NULL DEFAULT 0.00,
    total NUMERIC(12,2) NOT NULL DEFAULT 0.00,
    forma_pago VARCHAR(100) DEFAULT 'Transferencia bancaria',
    estado VARCHAR(20) NOT NULL DEFAULT 'Emitida', -- 'Emitida', 'Pagada', 'Anulada'
    estado_sri VARCHAR(30) NOT NULL DEFAULT 'PENDIENTE', -- 'PENDIENTE', 'TRANSMITIDO', 'AUTORIZADO', 'NO AUTORIZADO'
    clave_acceso VARCHAR(49),
    numero_autorizacion VARCHAR(49),
    fecha_emision TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    fecha_autorizacion TIMESTAMPTZ,
    observaciones TEXT,
    creado_por INT REFERENCES usuarios(id) ON DELETE SET NULL
);

-- ==============================================================================
-- 7. DETALLE DE ÍTEMS DE FACTURACIÓN
-- ==============================================================================
CREATE TABLE IF NOT EXISTS detalles_factura (
    id SERIAL PRIMARY KEY,
    factura_id INT NOT NULL REFERENCES facturas(id) ON DELETE CASCADE,
    servicio_id INT REFERENCES servicios(id) ON DELETE SET NULL,
    descripcion TEXT NOT NULL,
    cantidad INT NOT NULL DEFAULT 1 CHECK (cantidad > 0),
    precio_unitario NUMERIC(12,2) NOT NULL DEFAULT 0.00,
    subtotal NUMERIC(12,2) NOT NULL DEFAULT 0.00
);

-- ==============================================================================
-- ÍNDICES DE RENDIMIENTO (OPTIMIZACIÓN PARA BÚSQUEDA Y PAGINACIÓN)
-- ==============================================================================
CREATE INDEX IF NOT EXISTS idx_servicios_tipo ON servicios (tipo_servicio_id);
CREATE INDEX IF NOT EXISTS idx_servicios_disponible ON servicios (disponible);
CREATE INDEX IF NOT EXISTS idx_servicios_destacado ON servicios (destacado);
CREATE INDEX IF NOT EXISTS idx_servicios_nombre ON servicios (LOWER(nombre));
CREATE INDEX IF NOT EXISTS idx_usuarios_login ON usuarios (LOWER(usuario));
CREATE INDEX IF NOT EXISTS idx_logs_fecha ON logs_actividad (fecha DESC);
CREATE INDEX IF NOT EXISTS idx_logs_usuario ON logs_actividad (usuario_id);
CREATE INDEX IF NOT EXISTS idx_facturas_numero ON facturas (numero_factura);
CREATE INDEX IF NOT EXISTS idx_facturas_sri ON facturas (estado_sri);
CREATE INDEX IF NOT EXISTS idx_facturas_cliente ON facturas (cliente_identificacion);

CREATE TABLE IF NOT EXISTS consultas_servicios (
    id SERIAL PRIMARY KEY,
    servicio_id INTEGER REFERENCES servicios(id),
    termino_busqueda VARCHAR(255),
    ip VARCHAR(45),
    fecha TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_consultas_ip ON consultas_servicios(ip);

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
    comentario TEXT NOT NULL CHECK (char_length(comentario) BETWEEN 10 AND 1000),
    calificacion SMALLINT NOT NULL CHECK (calificacion BETWEEN 1 AND 5),
    aprobada BOOLEAN NOT NULL DEFAULT FALSE,
    creada_en TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

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

CREATE INDEX IF NOT EXISTS idx_servicios_campos_extra
ON servicios USING gin (campos_extra);

-- ==============================================================================
-- DATOS INICIALES (SEEDS PARA PRODUCCIÓN / DESARROLLO)
-- ==============================================================================

-- 1. Roles del Sistema (RBAC)
INSERT INTO roles (nombre, descripcion) VALUES
('Administrador', 'Control total del sistema: catálogo, auditoría y gestión de usuarios'),
('Gestor de Catálogo', 'Encargado de publicar, actualizar y editar servicios, productos, imágenes y fichas técnicas'),
('Supervisor', 'Supervisión operativa, edición de catálogo y consulta de auditoría'),
('Cliente', 'Consulta del catálogo y solicitud de cotizaciones'),
('Auditor', 'Visualización exclusiva de registros de auditoría y reportes del sistema')
ON CONFLICT (nombre) DO UPDATE SET descripcion = EXCLUDED.descripcion;

-- 3. Categorías de Servicios y Productos
INSERT INTO tipos_servicio (nombre, descripcion) VALUES
('Cámaras CCTV & Monitoreo', 'Videovigilancia en tiempo real y circuitos cerrados'),
('Alarmas & Cercos Eléctricos', 'Sistemas de disuasión perimetral y sensores de intrusión'),
('Guardianía Privada', 'Seguridad física uniformada y armada con personal acreditado'),
('Rastreo Satelital GPS', 'Control y localización de vehículos y flotas'),
('Automatización & Domótica', 'Portones automáticos, cerraduras inteligentes y control de acceso'),
('Audio Disuasión 24/7', 'Central de perifoneo preventivo en vivo')
ON CONFLICT (nombre) DO NOTHING;

-- 4. Catálogo Inicial con Plantilla Dinámica y Datos Completos
INSERT INTO servicios (
    tipo_servicio_id, nombre, precio_base, imagen, descripcion, disponible, es_producto, destacado,
    tipo_producto, garantia, zona_cobertura, disponibilidad_atencion, modalidad_pago, ficha_tecnica, whatsapp_msg
)
SELECT 
    t.id,
    'Guardianía Privada & Seguridad Física',
    0.00,
    '/static/imagenes/guardia-megaseg.jpg',
    'Oficiales de seguridad física uniformados y acreditados por las autoridades ecuatorianas para residencias, plantas y empresas.',
    TRUE,
    0,
    TRUE,
    'Servicio Operativo',
    'Soporte técnico directo en Lago Agrio y garantía certificada por Megaseg.',
    'Nueva Loja (Lago Agrio), Shushufindi, Cascales, Cuyabeno y toda la provincia de Sucumbíos.',
    'Central de monitoreo y respuesta operativa activa 24 horas, los 365 días del año.',
    'Emisión de factura autorizada por SRI, transferencias bancarias y planes empresariales.',
    'Incluye: Personal uniformado acreditado, control de accesos, rondas perimetrales y bitácora de novedades.',
    'Hola Megaseg, deseo cotizar el servicio de Guardianía Privada & Seguridad Física'
FROM tipos_servicio t
WHERE t.nombre = 'Guardianía Privada'
  AND NOT EXISTS (SELECT 1 FROM servicios WHERE nombre = 'Guardianía Privada & Seguridad Física')
LIMIT 1;

INSERT INTO servicios (
    tipo_servicio_id, nombre, precio_base, imagen, descripcion, disponible, es_producto, destacado,
    tipo_producto, garantia, zona_cobertura, disponibilidad_atencion, modalidad_pago, ficha_tecnica, whatsapp_msg
)
SELECT 
    t.id,
    'Alarmas y Cercos Eléctricos Perimetrales',
    180.00,
    'https://images.unsplash.com/photo-1508873696983-2df5293cb395?w=800&auto=format&fit=crop&q=80',
    'Disuasión perimetral homologada con energizadores de 10.000V, sirenas de gran potencia y respaldo de batería ante apagones.',
    TRUE,
    0,
    TRUE,
    'Servicio Operativo',
    'Soporte técnico directo en Lago Agrio y garantía certificada por Megaseg.',
    'Nueva Loja (Lago Agrio), Shushufindi, Cascales, Cuyabeno y toda la provincia de Sucumbíos.',
    'Central de monitoreo y respuesta operativa activa 24 horas, los 365 días del año.',
    'Emisión de factura autorizada por SRI, transferencias bancarias y planes empresariales.',
    'Incluye: Energizador homologado de 10.000V, postes templadores, alambre galvanizado y sirena 30W con batería.',
    'Hola Megaseg, deseo cotizar el servicio de Alarmas y Cercos Eléctricos Perimetrales'
FROM tipos_servicio t
WHERE t.nombre = 'Alarmas & Cercos Eléctricos'
  AND NOT EXISTS (SELECT 1 FROM servicios WHERE nombre = 'Alarmas y Cercos Eléctricos Perimetrales')
LIMIT 1;

INSERT INTO servicios (
    tipo_servicio_id, nombre, precio_base, imagen, descripcion, disponible, es_producto, destacado,
    tipo_producto, garantia, zona_cobertura, disponibilidad_atencion, modalidad_pago, ficha_tecnica, whatsapp_msg
)
SELECT 
    t.id,
    'Cámaras de Seguridad CCTV & IP en Vivo',
    120.00,
    'https://images.unsplash.com/photo-1557597774-9d273605dfa9?w=800&auto=format&fit=crop&q=80',
    'Instalación, mantenimiento y configuración de videovigilancia de alta definición con acceso 24/7 desde tu smartphone.',
    TRUE,
    0,
    TRUE,
    'Servicio Operativo',
    'Soporte técnico directo en Lago Agrio y garantía certificada por Megaseg.',
    'Nueva Loja (Lago Agrio), Shushufindi, Cascales, Cuyabeno y toda la provincia de Sucumbíos.',
    'Central de monitoreo y respuesta operativa activa 24 horas, los 365 días del año.',
    'Emisión de factura autorizada por SRI, transferencias bancarias y planes empresariales.',
    'Incluye: Configuración en app móvil, cableado estructurado, pruebas de visión nocturna y respaldo de energía.',
    'Hola Megaseg, deseo cotizar el servicio de Cámaras de Seguridad CCTV & IP en Vivo'
FROM tipos_servicio t
WHERE t.nombre = 'Cámaras CCTV & Monitoreo'
  AND NOT EXISTS (SELECT 1 FROM servicios WHERE nombre = 'Cámaras de Seguridad CCTV & IP en Vivo')
LIMIT 1;

INSERT INTO servicios (
    tipo_servicio_id, nombre, precio_base, imagen, descripcion, disponible, es_producto, destacado,
    tipo_producto, garantia, zona_cobertura, disponibilidad_atencion, modalidad_pago, ficha_tecnica, whatsapp_msg
)
SELECT 
    t.id,
    'Kit 4 Cámaras ColorVu Hikvision + DVR + Disco 1TB',
    240.00,
    'https://images.unsplash.com/photo-1557597774-9d273605dfa9?w=800&auto=format&fit=crop&q=80',
    'Kit completo de videovigilancia con visión nocturna a todo color las 24 horas, DVR grabador y disco de 1TB incluido.',
    TRUE,
    1,
    TRUE,
    'Equipo Físico',
    '1 año de garantía oficial de fábrica con soporte técnico en Lago Agrio.',
    'Envíos e instalación en toda la provincia de Sucumbíos y Orellana.',
    'Atención y soporte técnico de lunes a sábado de 08:00 a 18:00.',
    'Emisión de factura autorizada por SRI, pagos con tarjeta, transferencia y efectivo.',
    'Incluye: 4 Cámaras Hikvision ColorVu Full HD, 1 DVR 4 canales pentahíbrido, 1 Disco Duro 1TB Western Digital Purple especial para vigilancia, 4 fuentes de poder y baluns.',
    'Hola Megaseg, deseo cotizar el Kit 4 Cámaras ColorVu Hikvision + DVR + Disco 1TB'
FROM tipos_servicio t
WHERE t.nombre = 'Cámaras CCTV & Monitoreo'
  AND NOT EXISTS (SELECT 1 FROM servicios WHERE nombre = 'Kit 4 Cámaras ColorVu Hikvision + DVR + Disco 1TB')
LIMIT 1;
