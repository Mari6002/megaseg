# ==============================================================================
# PROYECTO: MEGASEG - FORMULARIO DE REGISTRO DE USUARIOS Y ASIGNACIÓN DE ROLES
# ==============================================================================

from flask_wtf import FlaskForm
from wtforms import (
    StringField,
    PasswordField,
    SelectField,
    SubmitField
)
from wtforms.validators import (
    DataRequired,
    Length,
    Email,
    EqualTo,
    ValidationError
)


class RegistroForm(FlaskForm):
    """Formulario para la creación de nuevas cuentas en el sistema."""

    usuario = StringField(
        'Nombre de Usuario (Login)',
        validators=[
            DataRequired(message='El nombre de usuario es obligatorio.'),
            Length(min=3, max=40, message='Debe tener entre 3 y 40 caracteres.')
        ]
    )

    nombre = StringField(
        'Nombre Completo o Razón Social',
        validators=[
            DataRequired(message='Tu nombre es obligatorio.'),
            Length(min=3, max=100, message='Debe tener entre 3 y 100 caracteres.')
        ]
    )

    email = StringField(
        'Correo Electrónico',
        validators=[
            DataRequired(message='El correo electrónico es obligatorio.'),
            Email(message='Ingresa un correo electrónico válido.')
        ]
    )

    telefono = StringField(
        'Teléfono / Celular (WhatsApp)',
        validators=[
            DataRequired(message='El número de teléfono es obligatorio.'),
            Length(min=7, max=20, message='Ingresa un número telefónico válido.')
        ]
    )

    rol = SelectField(
        'Rol de la Cuenta',
        choices=[
            ('Cliente', 'Cliente (Acceso inmediato para consultar catálogo y cotizar)'),
            ('Gestor de Catálogo', 'Gestor de Catálogo (Subir y actualizar productos/servicios - Requiere admisión de un Administrador)'),
            ('Administrador', 'Administrador (Control total del sistema - Requiere admisión de un Administrador)')
        ],
        default='Cliente'
    )

    password = PasswordField(
        'Contraseña',
        validators=[
            DataRequired(message='La contraseña es obligatoria.'),
            Length(min=8, max=60, message='La contraseña debe tener al menos 8 caracteres.')
        ]
    )

    confirm_password = PasswordField(
        'Confirmar Contraseña',
        validators=[
            DataRequired(message='Confirma tu contraseña.'),
            EqualTo('password', message='Las contraseñas no coinciden.')
        ]
    )

    submit = SubmitField('Crear Cuenta')

    def validate_usuario(self, field):
        """Valida que el usuario contenga solo caracteres alfanuméricos y guiones."""
        valor = field.data.strip()
        if not valor.replace('_', '').replace('.', '').replace('-', '').isalnum():
            raise ValidationError('El usuario solo puede contener letras, números, puntos y guiones.')
