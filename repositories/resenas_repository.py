"""Persistencia y moderación de reseñas públicas."""

from conexion.conexion import get_db_connection


def obtener_aprobadas(limite=6):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        '''
        SELECT r.id, r.nombre, r.comentario, r.calificacion, r.creada_en,
               r.servicio_id, s.nombre AS servicio_nombre
        FROM resenas r
        LEFT JOIN servicios s ON s.id = r.servicio_id
        WHERE r.aprobada = %s
        ORDER BY r.creada_en DESC, r.id DESC
        LIMIT %s
        ''',
        (True, limite)
    )
    filas = cursor.fetchall()
    cursor.close()
    return filas


def obtener_resumen():
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            '''
            SELECT COUNT(*) AS total,
                   COALESCE(ROUND(AVG(calificacion)::numeric, 1), 0) AS promedio
            FROM resenas
            WHERE aprobada = %s
            ''',
            (True,)
        )
        fila = cursor.fetchone()
    except Exception:
        conn.rollback()
        cursor.execute(
            '''
            SELECT COUNT(*) AS total,
                   COALESCE(ROUND(AVG(calificacion), 1), 0) AS promedio
            FROM resenas
            WHERE aprobada = %s
            ''',
            (True,)
        )
        fila = cursor.fetchone()
    cursor.close()
    return fila or {'total': 0, 'promedio': 0}


def obtener_todas(limite=200):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        '''
        SELECT r.id, r.nombre, r.comentario, r.calificacion, r.aprobada,
               r.creada_en, r.servicio_id, s.nombre AS servicio_nombre
        FROM resenas r
        LEFT JOIN servicios s ON s.id = r.servicio_id
        ORDER BY r.creada_en DESC, r.id DESC
        LIMIT %s
        ''',
        (limite,)
    )
    filas = cursor.fetchall()
    cursor.close()
    return filas


def crear(nombre, comentario, calificacion, servicio_id=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        '''
        INSERT INTO resenas (nombre, comentario, calificacion, servicio_id, aprobada)
        VALUES (%s, %s, %s, %s, FALSE)
        RETURNING id
        ''',
        (nombre, comentario, calificacion, servicio_id)
    )
    resena_id = cursor.fetchone()['id']
    conn.commit()
    cursor.close()
    return resena_id


def cambiar_aprobacion(resena_id, aprobada):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        'UPDATE resenas SET aprobada = %s WHERE id = %s',
        (bool(aprobada), resena_id)
    )
    filas = cursor.rowcount
    conn.commit()
    cursor.close()
    return filas


def eliminar(resena_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM resenas WHERE id = %s', (resena_id,))
    filas = cursor.rowcount
    conn.commit()
    cursor.close()
    return filas
