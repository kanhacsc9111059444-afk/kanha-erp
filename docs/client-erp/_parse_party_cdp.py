import json
from pathlib import Path

src = Path(r"C:\Users\HP\.cursor\browser-logs\cdp-response-Runtime.evaluate-2026-08-02T14-11-46-300Z.json")
data = json.loads(src.read_text(encoding="utf-8"))
# structure may be {result:{value:{...}}} or nested
val = data
for k in ("result", "value"):
    if isinstance(val, dict) and k in val:
        val = val[k]
if isinstance(val, dict) and "result" in val and isinstance(val["result"], dict) and "value" in val["result"]:
    val = val["result"]["value"]

fields = val.get("fields") or []
# filter junk from global menu
skip_types = {"checkbox"}
skip_labels = set()
clean = []
for f in fields:
    t = (f.get("type") or "").lower()
    lab = (f.get("label") or "").strip()
    fid = (f.get("id") or "")
    # keep form-ish ids (asp.net ContentPlaceHolder)
    if t in skip_types and "ContentPlaceHolder" not in fid and "txt" not in fid.lower() and "ddl" not in fid.lower():
        continue
    if t == "checkbox" and lab in {
        "Create User","Create Lead Source","Day Book","MIS Report","Assign User Dashboard"
    }:
        continue
    if not lab and not fid:
        continue
    # prefer real form controls
    if any(x in fid for x in ("ContentPlaceHolder", "txt", "ddl", "btn", "chk", "rbl", "cmb")) or t in ("text","password","email","number","tel","search","textarea","select-one","select","submit","button","file","date","radio"):
        clean.append(f)

out = Path(r"E:\KanhaOS-AI\docs\client-erp\forms\party-master.raw.json")
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps({"url": val.get("url"), "title": val.get("title"), "heads": val.get("heads"), "fields": clean}, indent=2), encoding="utf-8")
print("clean", len(clean), "of", len(fields))
for f in clean[:80]:
    print(f"- [{f.get('type')}] {f.get('label') or f.get('id')} | id={str(f.get('id'))[-50:]}")
