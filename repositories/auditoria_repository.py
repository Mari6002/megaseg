"""Repositorio de persistencia y consultas para la Auditoría y Logs del Sistema."""

from conexion.conexion import get_db_connection


def registrar_log(usuario_id=None, usuario_nombre='Sistema', rol='Invitado',
                  accion='', entidad='', entidad_id='', detalles='', ip='127.0.0.1'):
    """Registra un evento en la bitácora de auditoría."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                '''
                INSERT INTO logs_actividad (
                    usuario_id, usuario_nombre, rol, accion, entidad, entidad_id, detalles, ip
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ''',
                (
                    usuario_id,
                    usuario_nombre or 'Sistema',
                    rol or 'Invitado',
                    accion,
                    entidad,
                    int(entidad_id) if str(entidad_id).isdigit() else None,
                    detalles,
                    ip or '127.0.0.1'
                )
            )
        except Exception:
            conn.rollback()
            cursor.execute(
                '''
                INSERT INTO logs_actividad (
                    usuario_id, accion, entidad, entidad_id, detalles, ip
                )
                VALUES (%s, %s, %s, %s, %s, %s)
                ''',
                (
                    usuario_id,
                    accion,
                    entidad,
                    int(entidad_id) if str(entidad_id).isdigit() else None,
                    detalles,
                    ip or '127.0.0.1'
                )
            )
        conn.commit()
        cursor.close()
    except Exception as e:
        # Los logs no deben interrumpir el flujo principal de la aplicación
        print(f"[AUDITORIA ERROR] No se pudo guardar el log: {e}")


def obtener_logs(limite=100, desplazamiento=0, busqueda='', accion='', entidad=''):
    """Devuelve los registros cronológicos de auditoría con filtros opcionales."""
    condiciones = []
    parametros = []

    if busqueda:
        condiciones.append(
            '(COALESCE(l.usuario_nombre, u.nombre) LIKE %s OR COALESCE(l.rol, r.nombre) LIKE %s OR u.usuario LIKE %s OR l.accion LIKE %s OR l.entidad LIKE %s OR l.detalles LIKE %s OR l.ip LIKE %s)'
        )
        val = f'%{busqueda}%'
        parametros.extend([val, val, val, val, val, val, val])

    if accion:
        condiciones.append('accion = %s')
        parametros.append(accion)

    if entidad:
        condiciones.append('entidad = %s')
        parametros.append(entidad)

    where_sql = (' WHERE ' + ' AND '.join(condiciones)) if condiciones else ''

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            f'''
            SELECT l.*,
                   COALESCE(l.usuario_nombre, u.nombre) AS usuario_nombre,
                   COALESCE(l.rol, r.nombre) AS rol
            FROM logs_actividad l
            LEFT JOIN usuarios u ON u.id = l.usuario_id
            LEFT JOIN roles r ON r.id = u.rol_id
            {where_sql}
            ORDER BY l.fecha DESC, l.id DESC
            LIMIT %s OFFSET %s
            ''',
            parametros + [limite, desplazamiento]
        )
    except Exception:
        cursor.execute(
            f'''
            SELECT * FROM logs_actividad
            {where_sql}
            ORDER BY fecha DESC, id DESC
            LIMIT %s OFFSET %s
            ''',
            parametros + [limite, desplazamiento]
        )
    logs = cursor.fetchall()
    cursor.close()
    return logs


def contar_logs(busqueda='', accion='', entidad=''):
    """Devuelve el total de eventos registrados según los filtros."""
    condiciones = []
    parametros = []

    if busqueda:
        condiciones.append(
            '(COALESCE(l.usuario_nombre, u.nombre) LIKE %s OR COALESCE(l.rol, r.nombre) LIKE %s OR u.usuario LIKE %s OR l.accion LIKE %s OR l.entidad LIKE %s OR l.detalles LIKE %s OR l.ip LIKE %s)'
        )
        val = f'%{busqueda}%'
        parametros.extend([val, val, val, val, val, val, val])

    if accion:
        condiciones.append('accion = %s')
        parametros.append(accion)

    if entidad:
        condiciones.append('entidad = %s')
        parametros.append(entidad)

    where_sql = (' WHERE ' + ' AND '.join(condiciones)) if condiciones else ''

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            f'''
            SELECT COUNT(*) AS total
            FROM logs_actividad l
            LEFT JOIN usuarios u ON u.id = l.usuario_id
            LEFT JOIN roles r ON r.id = u.rol_id
            {where_sql}
            ''',
            parametros
        )
    except Exception:
        cursor.execute(
            f'''
            SELECT COUNT(*) AS total FROM logs_actividad
            {where_sql}
            ''',
            parametros
        )
    fila = cursor.fetchone()
    cursor.close()
    return fila['total'] if fila else 0
