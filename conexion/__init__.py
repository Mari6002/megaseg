# ==============================================================================
# PROYECTO: MEGASEG SEGURIDAD INTEGRAL - MÓDULO DE CONEXIÓN
# ==============================================================================
# Provee conexión centralizada para PostgreSQL o SQLite (conmutación automática).
# ==============================================================================

from .conexion import get_db_connection, close_db_connection, inicializar_base_datos
