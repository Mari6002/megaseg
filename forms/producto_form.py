# ==============================================================================
# PROYECTO: MEGASEG - FORMULARIO DE PRODUCTO
# ==============================================================================
# Hereda de ServicioForm permitiendo manejar productos y kits de seguridad.
# ==============================================================================

from .servicio_form import ServicioForm


class ProductoForm(ServicioForm):
    """Formulario específico para equipos, repuestos y kits físicos de seguridad."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.es_producto.data = 1
