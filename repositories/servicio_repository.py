"""Consultas y operaciones de persistencia del catálogo de servicios y productos."""

from conexion.conexion import get_db_connection


def obtener_destacados(limite=6):
    """Devuelve servicios destacados o, si no hay, los primeros disponibles."""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        '''
        SELECT s.*, t.nombre AS tipo_nombre
        FROM servicios s
        JOIN tipos_servicio t ON s.tipo_servicio_id = t.id
        WHERE s.destacado = %s AND s.disponible = %s
        ORDER BY s.id ASC
        LIMIT %s
        ''',
        (True, True, limite)
    )
    servicios = cursor.fetchall()

    if not servicios:
        cursor.execute(
            '''
            SELECT s.*, t.nombre AS tipo_nombre
            FROM servicios s
            JOIN tipos_servicio t ON s.tipo_servicio_id = t.id
                WHERE s.disponible = %s
            ORDER BY s.id ASC
            LIMIT %s
            ''',
                (True, limite)
        )
        servicios = cursor.fetchall()

    cursor.close()
    return servicios


def obtener_tipos():
    """Devuelve las categorías ordenadas para los filtros y formularios."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM tipos_servicio ORDER BY nombre ASC')
    tipos = cursor.fetchall()
    cursor.close()
    return tipos


def _construir_filtros(busqueda='', tipo='', disponibilidad=''):
    """Construye filtros parametrizados para las consultas del catálogo."""
    condiciones = []
    parametros = []

    if busqueda:
        condiciones.append(
            '(s.nombre LIKE %s OR s.descripcion LIKE %s OR t.nombre LIKE %s OR s.ficha_tecnica LIKE %s)'
        )
        valor = f'%{busqueda}%'
        parametros.extend([valor, valor, valor, valor])

    if tipo:
        condiciones.append('t.nombre = %s')
        parametros.append(tipo)

    if disponibilidad in ('1', '0'):
        condiciones.append('s.disponible = %s')
        parametros.append(disponibilidad == '1')

    where_sql = (' WHERE ' + ' AND '.join(condiciones)) if condiciones else ''
    return where_sql, parametros


def contar_servicios(busqueda='', tipo='', disponibilidad=''):
    """Cuenta los registros que coinciden con los filtros del catálogo."""
    where_sql, parametros = _construir_filtros(busqueda, tipo, disponibilidad)
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        f'''
        SELECT COUNT(*) AS total
        FROM servicios s
        JOIN tipos_servicio t ON s.tipo_servicio_id = t.id
        {where_sql}
        ''',
        parametros
    )
    fila = cursor.fetchone()
    cursor.close()
    return fila['total'] if fila else 0


def listar_servicios(busqueda='', tipo='', disponibilidad='', orden='',
                     limite=12, desplazamiento=0):
    """Recupera una página del catálogo con orden seguro y filtros parametrizados."""
    where_sql, parametros = _construir_filtros(busqueda, tipo, disponibilidad)
    ordenes = {
        'precio-asc': 'ORDER BY s.precio_base ASC, s.id DESC',
        'precio-desc': 'ORDER BY s.precio_base DESC, s.id DESC',
        'nombre-asc': 'ORDER BY s.nombre ASC'
    }
    order_sql = ordenes.get(orden, 'ORDER BY s.destacado DESC, s.id DESC')

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        f'''
        SELECT s.*, t.nombre AS tipo_nombre
        FROM servicios s
        JOIN tipos_servicio t ON s.tipo_servicio_id = t.id
        {where_sql}
        {order_sql}
        LIMIT %s OFFSET %s
        ''',
        parametros + [limite, desplazamiento]
    )
    servicios = cursor.fetchall()
    cursor.close()
    return servicios


def obtener_servicio(servicio_id):
    """Busca un servicio por su identificador con el nombre de su categoría."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        '''
        SELECT s.*, t.nombre AS tipo_nombre
        FROM servicios s
        JOIN tipos_servicio t ON s.tipo_servicio_id = t.id
        WHERE s.id = %s
        ''',
        (servicio_id,)
    )
    servicio = cursor.fetchone()
    cursor.close()
    return servicio


def crear_servicio(datos):
    """Inserta un servicio validado con todos los campos de la plantilla dinámica."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        '''
        INSERT INTO servicios (
            tipo_servicio_id, nombre, precio_base, imagen, descripcion,
            disponible, es_producto, destacado, tipo_producto, garantia,
            zona_cobertura, disponibilidad_atencion, modalidad_pago, ficha_tecnica, whatsapp_msg
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id
        ''',
        (
            datos['tipo_servicio_id'],
            datos['nombre'],
            datos['precio_base'],
            datos['imagen'],
            datos['descripcion'],
            bool(datos['disponible']),
            datos['es_producto'],
            bool(datos['destacado']),
            datos.get('tipo_producto') or ('Equipo Físico' if datos['es_producto'] else 'Servicio Operativo'),
            datos.get('garantia', ''),
            datos.get('zona_cobertura', ''),
            datos.get('disponibilidad_atencion', ''),
            datos.get('modalidad_pago', ''),
            datos.get('ficha_tecnica', ''),
            datos.get('whatsapp_msg', '')
        )
    )
    servicio_id = cursor.fetchone()['id']
    conn.commit()
    cursor.close()
    return servicio_id


def actualizar_servicio(servicio_id, datos):
    """Actualiza todos los datos y especificaciones de un servicio o producto existente."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        '''
        UPDATE servicios
        SET tipo_servicio_id = %s,
            nombre = %s,
            precio_base = %s,
            imagen = %s,
            descripcion = %s,
            disponible = %s,
            es_producto = %s,
            destacado = %s,
            tipo_producto = %s,
            garantia = %s,
            zona_cobertura = %s,
            disponibilidad_atencion = %s,
            modalidad_pago = %s,
            ficha_tecnica = %s,
            whatsapp_msg = %s
        WHERE id = %s
        ''',
        (
            datos['tipo_servicio_id'],
            datos['nombre'],
            datos['precio_base'],
            datos['imagen'],
            datos['descripcion'],
            bool(datos['disponible']),
            datos['es_producto'],
            bool(datos['destacado']),
            datos.get('tipo_producto') or ('Equipo Físico' if datos['es_producto'] else 'Servicio Operativo'),
            datos.get('garantia', ''),
            datos.get('zona_cobertura', ''),
            datos.get('disponibilidad_atencion', ''),
            datos.get('modalidad_pago', ''),
            datos.get('ficha_tecnica', ''),
            datos.get('whatsapp_msg', ''),
            servicio_id
        )
    )
    conn.commit()
    cursor.close()


def eliminar_servicio(servicio_id):
    """Elimina un registro del catálogo y devuelve cuántas filas afectó."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM servicios WHERE id = %s', (servicio_id,))
    filas_afectadas = cursor.rowcount
    conn.commit()
    cursor.close()
    return filas_afectadas
