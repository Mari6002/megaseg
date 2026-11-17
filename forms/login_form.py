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
