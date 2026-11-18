from pathlib import Path
import re

text = Path(r"..\NEXODIGITAL\app.py").read_text(encoding="utf-8", errors="ignore")
match = re.search(r"@app\.route\(['\"]/registro['\"].*?(?=\n@app\.route|\Z)", text, re.DOTALL)
if match:
    print(match.group(0)[:2000])
else:
    print("No /registro route found")
