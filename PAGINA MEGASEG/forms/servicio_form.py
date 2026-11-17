# ==============================================================================
# PROYECTO: MEGASEG - FORMULARIO DE SERVICIOS Y PRODUCTOS
# ==============================================================================
# Define la estructura de datos requerida para dar de alta o modificar
# servicios y productos en el catálogo comercial de Grupo Megaseg.
# ==============================================================================

from flask_wtf import FlaskForm
from urllib.parse import urlsplit

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

    # Categoría a la que pertenece (clave foránea hacia tipos_servicio)
    tipo_servicio_id = SelectField(
        'Categoría de Seguridad',
        coerce=int,
        validators=[DataRequired(message='Selecciona una categoría.')]
    )

    # Identificador si es un servicio o producto
    es_producto = SelectField(
        'Tipo de Publicación',
        choices=[(0, 'Servicio de Seguridad'), (1, 'Producto / Equipo Físico')],
        coerce=int,
        default=0
    )

    # Nombre comercial
    nombre = StringField(
        'Nombre del Servicio o Producto',
        validators=[
            DataRequired(message='El nombre es obligatorio.'),
            Length(min=3, max=150, message='Debe tener entre 3 y 150 caracteres.')
        ]
    )

    # Precio referencial o tarifa base
    precio = FloatField(
        'Precio Referencial ($ USD)',
        default=0.0,
        validators=[
            NumberRange(min=0.0, message='El precio debe ser un valor numérico mayor o igual a 0.')
        ]
    )

    # Enlace público directo; no se aceptan rutas locales del servidor.
    imagen = StringField(
        'Enlace directo a una imagen',
        validators=[
            Optional(),
            Length(max=500, message='El enlace no puede exceder 500 caracteres.')
        ]
    )

    imagen_archivo = FileField('Imagen desde este dispositivo')

    # Descripción comercial completa
    descripcion = TextAreaField(
        'Descripción y Características',
        validators=[
            DataRequired(message='La descripción es obligatoria.'),
            Length(min=10, max=1000, message='Debe tener entre 10 y 1000 caracteres.')
        ]
    )

    # Disponibilidad comercial
    disponible = BooleanField('Disponible para contratación / venta inmediata', default=True)

    # Destacado en la portada
    destacado = BooleanField('Destacar en la página de inicio (Portada)', default=False)

    # Botón de envío
    submit = SubmitField('Guardar en el Catálogo')

    def validate_imagen(self, field):
        """Acepta enlaces web HTTP(S), no rutas de carpetas locales."""
        if not field.data:
            return

        try:
            enlace = urlsplit(field.data.strip())
        except ValueError as error:
            raise ValidationError('Ingresa un enlace de imagen válido.') from error

        if enlace.scheme not in ('http', 'https') or not enlace.netloc:
            raise ValidationError('El enlace debe comenzar con http:// o https://.')

    def validate_imagen_archivo(self, field):
        """Valida formato, firma y tamaño antes de guardar una imagen subida."""
        archivo = field.data
        if not archivo or not archivo.filename:
            return

        extension = archivo.filename.rsplit('.', 1)[-1].lower()
        firmas = {
            'jpg': lambda contenido: contenido.startswith(b'\xff\xd8\xff'),
            'jpeg': lambda contenido: contenido.startswith(b'\xff\xd8\xff'),
            'png': lambda contenido: contenido.startswith(b'\x89PNG\r\n\x1a\n'),
            'webp': lambda contenido: (
                contenido[:4] == b'RIFF' and contenido[8:12] == b'WEBP'
            )
        }
        validar_firma = firmas.get(extension)
        if validar_firma is None:
            raise ValidationError('Usa una imagen JPG, PNG o WebP.')

        flujo = archivo.stream
        posicion = flujo.tell()
        flujo.seek(0, 2)
        tamano = flujo.tell()
        flujo.seek(0)
        firma = flujo.read(12)
        flujo.seek(posicion)

        if tamano > 5 * 1024 * 1024:
            raise ValidationError('La imagen no puede superar los 5 MB.')
        if not validar_firma(firma):
            raise ValidationError('El archivo no coincide con el formato de imagen seleccionado.')

    def validate(self, extra_validators=None):
        """Impide enviar un archivo y un enlace al mismo tiempo."""
        valido = super().validate(extra_validators=extra_validators)
        archivo = self.imagen_archivo.data
        tiene_archivo = archivo is not None and bool(archivo.filename)
        tiene_enlace = bool((self.imagen.data or '').strip())

        if tiene_archivo and tiene_enlace:
            self.imagen_archivo.errors.append(
                'Elige una sola opción: sube un archivo o pega un enlace.'
            )
            valido = False

        return valido
