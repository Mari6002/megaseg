from pathlib import Path

p = Path(r"..\NEXODIGITAL\conexion\conexion.py")
if p.exists():
    print(p.read_text(encoding="utf-8", errors="ignore")[:2500])
