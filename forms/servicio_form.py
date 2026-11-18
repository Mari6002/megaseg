# ==============================================================================
# PROYECTO: MEGASEG - FORMULARIO DE SERVICIOS Y PRODUCTOS (PLANTILLA DINÁMICA)
# ==============================================================================
# Define la estructura de datos requerida para dar de alta o modificar
# servicios y productos en el catálogo comercial de Grupo Megaseg, conectada
# a la base de datos con soporte para fichas técnicas, garantías y cobertura.
# ==============================================================================

from urllib.parse import urlsplit
from flask_wtf import FlaskForm
from wtforms import (
    StringField,
    TextAreaField,
    FloatField,
    BooleanField,
    SubmitField,
    SelectField,
    FileField
)
from wtforms.validators import DataRequired, Length, NumberRange, Optional, ValidationError


class ServicioForm(FlaskForm):
    """Formulario para la administración de servicios y productos de seguridad."""

    # 1. Categoría (clave foránea hacia tipos_servicio)
    tipo_servicio_id = SelectField(
        'Categoría de Seguridad',
        coerce=int,
        validators=[DataRequired(message='Selecciona una categoría.')]
    )

    # 2. Identificador si es un servicio o producto
    es_producto = SelectField(
        'Tipo de Publicación',
        choices=[(0, 'Servicio de Seguridad'), (1, 'Producto / Equipo Físico')],
        coerce=int,
        default=0
    )

    # 3. Etiqueta para la Ficha Técnica (ej: Equipo Físico, Servicio Operativo, Kit Tecnológico)
    tipo_producto = StringField(
        'Etiqueta de Ficha Técnica',
        default='Servicio Operativo',
        validators=[
            Optional(),
            Length(max=100, message='La etiqueta no puede superar 100 caracteres.')
        ]
    )

    # 4. Nombre comercial / Título
    nombre = StringField(
        'Nombre del Servicio o Producto',
        validators=[
            DataRequired(message='El nombre es obligatorio.'),
            Length(min=3, max=150, message='Debe tener entre 3 y 150 caracteres.')
        ]
    )

    # 5. Precio referencial o tarifa base
    precio = FloatField(
        'Precio Referencial ($ USD)',
        default=0.0,
        validators=[
            NumberRange(min=0.0, message='El precio debe ser un valor numérico mayor o igual a 0.')
        ]
    )

    # 6. Imagen: archivo local o enlace directo
    imagen = StringField(
        'Enlace directo a una imagen (Opcional)',
        validators=[
            Optional(),
            Length(max=500, message='El enlace no puede exceder 500 caracteres.')
        ]
    )

    imagen_archivo = FileField('Subir imagen desde este dispositivo')

    # 7. Descripción corta / comercial
    descripcion = TextAreaField(
        'Descripción Resumida',
        validators=[
            DataRequired(message='La descripción es obligatoria.'),
            Length(min=10, max=1000, message='Debe tener entre 10 y 1000 caracteres.')
        ]
    )

    # 8. Campos dinámicos de la ficha técnica desplegable
    garantia = StringField(
        'Garantía y Respaldo',
        default='Soporte técnico directo en Lago Agrio y garantía certificada por Megaseg.',
        validators=[
            Optional(),
            Length(max=255, message='No puede superar los 255 caracteres.')
        ]
    )

    zona_cobertura = StringField(
        'Zona de Cobertura',
        default='Nueva Loja (Lago Agrio), Shushufindi, Cascales, Cuyabeno y toda la provincia de Sucumbíos.',
        validators=[
            Optional(),
            Length(max=255, message='No puede superar los 255 caracteres.')
        ]
    )

    disponibilidad_atencion = StringField(
        'Disponibilidad de Atención',
        default='Central de monitoreo y respuesta operativa activa 24 horas, los 365 días del año.',
        validators=[
            Optional(),
            Length(max=255, message='No puede superar los 255 caracteres.')
        ]
    )

    modalidad_pago = StringField(
        'Modalidad de Pago / Facturación',
        default='Emisión de factura autorizada por SRI, transferencias bancarias y planes empresariales.',
        validators=[
            Optional(),
            Length(max=255, message='No puede superar los 255 caracteres.')
        ]
    )

    ficha_tecnica = TextAreaField(
        'Detalles Específicos / Ficha Técnica (Lo que incluye)',
        validators=[
            Optional(),
            Length(max=2000, message='No puede superar los 2000 caracteres.')
        ]
    )

    whatsapp_msg = StringField(
        'Mensaje Predeterminado para WhatsApp',
        validators=[
            Optional(),
            Length(max=255, message='No puede superar los 255 caracteres.')
        ]
    )

    # 9. Disponibilidad y destacado
    disponible = BooleanField('Disponible para contratación / venta inmediata', default=True)
    destacado = BooleanField('Destacar en la página de inicio (Portada)', default=False)

    # Botón de envío
    submit = SubmitField('Guardar en el Catálogo')

    def validate_imagen(self, field):
        """Acepta enlaces web HTTP(S)."""
        if not field.data or not field.data.strip():
            return

        try:
            enlace = urlsplit(field.data.strip())
        except ValueError as error:
            raise ValidationError('Ingresa un enlace de imagen válido.') from error

        if enlace.scheme not in ('http', 'https') or not enlace.netloc:
            raise ValidationError('El enlace debe comenzar con http:// o https://.')

    def validate_imagen_archivo(self, field):
        """Valida formato y tamaño antes de guardar una imagen subida."""
        archivo = field.data
        if not archivo or not getattr(archivo, 'filename', None):
            return

        extension = archivo.filename.rsplit('.', 1)[-1].lower()
        if extension not in ('jpg', 'jpeg', 'png', 'webp'):
            raise ValidationError('Formato no permitido. Usa una imagen JPG, PNG o WebP.')

        flujo = archivo.stream
        try:
            posicion = flujo.tell()
            flujo.seek(0, 2)
            tamano = flujo.tell()
            flujo.seek(posicion)

            if tamano > 5 * 1024 * 1024:
                raise ValidationError('La imagen no puede superar los 5 MB.')
        except Exception:
            pass

    def validate(self, extra_validators=None):
        """Valida sin conflictos mutuos si un campo está vacío."""
        valido = super().validate(extra_validators=extra_validators)
        archivo = self.imagen_archivo.data
        tiene_archivo = archivo is not None and bool(getattr(archivo, 'filename', None))
        tiene_enlace = bool((self.imagen.data or '').strip())

        if tiene_archivo and tiene_enlace:
            self.imagen_archivo.errors.append(
                'Elige una sola opción: sube un archivo desde tu dispositivo o pega un enlace web.'
            )
            valido = False

        return valido
