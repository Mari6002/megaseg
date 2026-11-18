import psycopg2

passwords_to_try = ['123456', 'postgres', 'admin', 'root', '1234', '12345', '']

for pwd in passwords_to_try:
    try:
        conn = psycopg2.connect(
            host='localhost',
            port=5432,
            user='postgres',
            password=pwd,
            dbname='postgres',
            connect_timeout=2
        )
        print(f"✓ ÉXITO: Conexión lograda con password: '{pwd}'")
        conn.close()
        break
    except psycopg2.OperationalError as e:
        raw_msg = e.args[0] if hasattr(e, 'args') and e.args else str(e)
        if isinstance(raw_msg, bytes):
            decoded = raw_msg.decode('latin1', errors='ignore')
        else:
            decoded = str(raw_msg)
        print(f"Password '{pwd}' falló: {decoded.strip()}")
    except Exception as e:
        print(f"Password '{pwd}' error: {e}")
