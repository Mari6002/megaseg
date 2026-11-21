# ==============================================================================
# PROYECTO: MEGASEG - FORMULARIO DE INICIO DE SESIÓN
# ==============================================================================
# Permite autenticar administradores mediante usuario o correo y contraseña.
# ==============================================================================

from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Length


class LoginForm(FlaskForm):
    """Formulario de acceso seguro al panel de administración de Megaseg."""
    usuario = StringField(
        'Usuario o Correo Electrónico',
        validators=[
            DataRequired(message='Ingresa tu usuario o correo.'),
            Length(min=3, max=100, message='Debe tener entre 3 y 100 caracteres.')
        ]
    )

    password = PasswordField(
        'Contraseña',
        validators=[
            DataRequired(message='Ingresa tu contraseña de acceso.')
        ]
    )

    recordarme = BooleanField('Mantener sesión iniciada')

    submit = SubmitField('Ingresar al Sistema')


class RecuperarPasswordForm(FlaskForm):
    """Solicita el envío de un enlace temporal de recuperación."""

    usuario_o_email = StringField(
        'Usuario o correo electrónico',
        validators=[
            DataRequired(message='Ingresa tu usuario o correo.'),
            Length(min=3, max=120, message='Ingresa un dato válido.')
        ]
    )
    submit = SubmitField('Enviar enlace de recuperación')


class NuevaPasswordForm(FlaskForm):
    """Define una contraseña nueva desde un enlace válido."""

    password = PasswordField(
        'Nueva contraseña',
        validators=[
            DataRequired(message='Ingresa la nueva contraseña.'),
            Length(min=14, max=128, message='La contraseña debe tener al menos 14 caracteres.')
        ]
    )
    confirm_password = PasswordField(
        'Confirmar nueva contraseña',
        validators=[
            DataRequired(message='Confirma la nueva contraseña.'),
        ]
    )
    submit = SubmitField('Guardar nueva contraseña')
