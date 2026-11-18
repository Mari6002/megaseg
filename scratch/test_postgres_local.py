import os
import psycopg2
from dotenv import load_dotenv

load_dotenv('.env')

host = os.getenv('DB_HOST', 'localhost')
port = os.getenv('DB_PORT', '5432')
user = os.getenv('DB_USER', 'postgres')
password = os.getenv('DB_PASSWORD', '123456')

print(f"Probando conexion a PostgreSQL en {host}:{port} con usuario {user}...")

try:
    conn = psycopg2.connect(
        host=host,
        port=port,
        user=user,
        password=password,
        dbname='postgres',
        connect_timeout=3
    )
    print("✓ Conexión exitosa a PostgreSQL!")
    conn.close()
except Exception as e:
    import traceback
    print("Error tipo:", type(e))
    # intentar obtener mensaje en bytes
    try:
        msg = str(e)
    except Exception:
        msg = repr(e)
    print("Mensaje:", msg)
