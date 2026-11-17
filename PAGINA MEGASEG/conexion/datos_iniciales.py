"""Contenido de ejemplo que se carga solo cuando las tablas están vacías."""

# Categorías disponibles al crear una base local nueva.
CATEGORIAS_INICIALES = [
    ('Cámaras CCTV & Monitoreo', 'Videovigilancia en tiempo real y circuitos cerrados'),
    ('Alarmas & Cercos Eléctricos', 'Sistemas de disuasión perimetral y sensores de intrusión'),
    ('Guardianía Privada', 'Seguridad física uniformada y armada con personal acreditado'),
    ('Rastreo Satelital GPS', 'Control y localización de vehículos y flotas'),
    ('Automatización & Domótica', 'Portones automáticos, cerraduras inteligentes y control de acceso'),
    ('Audio Disuasión 24/7', 'Central de perifoneo preventivo en vivo'),
]

# Catálogo ilustrativo; la categoría se resuelve por nombre, nunca por ID supuesto.
SERVICIOS_INICIALES = [
    (
        'Cámaras CCTV & Monitoreo', 'Cámaras de Seguridad CCTV & IP en Vivo', 120.00,
        'https://images.unsplash.com/photo-1557597774-9d273605dfa9?w=800&auto=format&fit=crop&q=80',
        'Instalación, mantenimiento y configuración de videovigilancia de alta definición con acceso 24/7 desde tu smartphone.',
        1, 0, 1,
    ),
    (
        'Alarmas & Cercos Eléctricos', 'Alarmas y Cercos Eléctricos Perimetrales', 180.00,
        'https://images.unsplash.com/photo-1508873696983-2df5293cb395?w=800&auto=format&fit=crop&q=80',
        'Disuasión perimetral homologada con energizadores de 10.000V, sirenas de gran potencia y respaldo de batería ante apagones.',
        1, 0, 1,
    ),
    (
        'Guardianía Privada', 'Guardianía Privada & Seguridad Física', 0.00,
        '/static/imagenes/guardia-megaseg.jpg',
        'Oficiales de seguridad física uniformados y acreditados por las autoridades ecuatorianas para residencias, plantas y empresas.',
        1, 0, 1,
    ),
    (
        'Rastreo Satelital GPS', 'Rastreo Satelital GPS para Flotas', 25.00,
        'https://images.unsplash.com/photo-1519641471654-76ce0107ad1b?w=800&auto=format&fit=crop&q=80',
        'Plataforma satelital en tiempo real con apagado de motor remoto ante robo, alertas de velocidad e historial de rutas.',
        1, 0, 0,
    ),
    (
        'Automatización & Domótica', 'Automatización de Portones & Control de Acceso', 250.00,
        'https://images.unsplash.com/photo-1558002038-1055907df827?w=800&auto=format&fit=crop&q=80',
        'Motores de alto tráfico para puertas corredizas y batientes, video porteros IP y cerraduras biométricas inteligentes.',
        1, 0, 0,
    ),
    (
        'Audio Disuasión 24/7', 'Audio Disuasión & Central de Monitoreo 24/7', 45.00,
        'https://images.unsplash.com/photo-1551836022-d5d88e9218df?w=800&auto=format&fit=crop&q=80',
        'Operadores alertas las 24 horas en Lago Agrio. Ante cualquier intruso sospechoso se activa perifoneo disuasivo en vivo.',
        1, 0, 1,
    ),
    (
        'Cámaras CCTV & Monitoreo', 'Kit 4 Cámaras ColorVu Hikvision + DVR + Disco 1TB', 240.00,
        'https://images.unsplash.com/photo-1557597774-9d273605dfa9?w=800&auto=format&fit=crop&q=80',
        'Kit completo de videovigilancia con visión nocturna a todo color las 24 horas, DVR grabador y disco de 1TB incluido.',
        1, 1, 1,
    ),
    (
        'Alarmas & Cercos Eléctricos', 'Energizador Cerco Eléctrico 10.000V Hagroy', 165.00,
        'https://images.unsplash.com/photo-1508873696983-2df5293cb395?w=800&auto=format&fit=crop&q=80',
        'Energizador de alta descarga disuasiva para hasta 1.500 metros lineales con batería de respaldo y sirena de 30W.',
        1, 1, 0,
    ),
    (
        'Automatización & Domótica', 'Cerradura Biométrica Digital Inteligente con Huella', 135.00,
        'https://images.unsplash.com/photo-1558002038-1055907df827?w=800&auto=format&fit=crop&q=80',
        'Apertura por huella dactilar ultra rápida, clave táctil, tarjetas RFID y llave física de emergencia con app móvil.',
        1, 1, 1,
    ),
]
