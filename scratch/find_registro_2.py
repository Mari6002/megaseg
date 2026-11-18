from pathlib import Path
import re

text = Path(r"..\NEXODIGITAL\app.py").read_text(encoding="utf-8", errors="ignore")
match = re.search(r"@app\.route\(['\"]/registro['\"].*?(?=\n@app\.route|\Z)", text, re.DOTALL)
if match:
    lines = match.group(0).splitlines()
    print("\n".join(lines[35:100]))
