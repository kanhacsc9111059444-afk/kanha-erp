import re
from pathlib import Path

p = Path(r"C:\Users\HP\.cursor\browser-logs\snapshot-2026-08-02T14-04-29-183Z-hzkwwz.log")
t = p.read_text(encoding="utf-8", errors="ignore")

out = Path(r"E:\KanhaOS-AI\docs\client-erp\_home_extract.txt")
lines = []

m = re.search(r'options: "([^"]+)"', t)
lines.append("=== MENUS ===")
if m:
    lines.append(m.group(1))

names = re.findall(r"- role: checkbox\n\s+name: (.+)", t)
lines.append(f"\n=== FEATURES ({len(names)}) ===")
lines.extend(names)

btns = re.findall(r"- role: button\n\s+name: (.+)", t)
lines.append("\n=== BUTTONS ===")
lines.extend(btns)

heads = re.findall(r"- role: heading\n\s+name: (.+)", t)
lines.append("\n=== HEADINGS ===")
lines.extend(heads)

out.write_text("\n".join(lines), encoding="utf-8")
print(f"wrote {out} features={len(names)}")
