from pathlib import Path

p = Path(r"..\NEXODIGITAL\.env")
if p.exists():
    print(p.read_text(encoding="utf-8", errors="ignore"))
else:
    print(".env not in NEXODIGITAL, checking .env.example:")
    p_ex = Path(r"..\NEXODIGITAL\.env.example")
    if p_ex.exists():
        print(p_ex.read_text(encoding="utf-8", errors="ignore"))
