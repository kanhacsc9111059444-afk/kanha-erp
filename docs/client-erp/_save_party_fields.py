import json
from pathlib import Path

p = Path(r"C:\Users\\HP\.cursor\browser-logs\cdp-response-Runtime.evaluate-2026-08-02T14-12-20-206Z.json")
d = json.loads(p.read_text(encoding="utf-8"))
v = d.get("result", d)
if isinstance(v, dict) and "result" in v:
    v = v["result"]
if isinstance(v, dict) and "value" in v:
    v = v["value"]

fields = v.get("fields") or []
# de-dupe by label
seen = set()
uniq = []
for f in fields:
    lab = (f.get("label") or "").strip()
    if not lab or lab in seen:
        continue
    # skip mega menu junk
    if lab.startswith("-- Select") or len(lab) > 90:
        continue
    if lab.count("\n") or "Create User" in lab and "GST" not in lab:
        continue
    seen.add(lab)
    uniq.append(f)

out = {
    "url": v.get("url"),
    "tabs": v.get("tabs"),
    "buttons": [b for b in (v.get("buttons") or []) if "Ask" not in b and b != "\U0001f4ac Ask Dia"],
    "fields": [
        {
            "label": f.get("label"),
            "type": f.get("type"),
            "required": f.get("required"),
            "placeholder": f.get("placeholder"),
            "options": f.get("options") or [],
            "id": f.get("id"),
        }
        for f in uniq
    ],
}

dest = Path(r"E:\KanhaOS-AI\docs\client-erp\forms\party-master.json")
dest.parent.mkdir(parents=True, exist_ok=True)
dest.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
print(f"saved {len(out['fields'])} fields -> {dest}")
for f in out["fields"]:
    req = "*" if f["required"] else ""
    opts = (" opts=" + "|".join(f["options"][:8])) if f["options"] else ""
    print(f"{f['label']}{req} [{f['type']}]{opts}")
