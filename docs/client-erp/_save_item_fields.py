import json
from pathlib import Path

p = Path(r"C:\Users\HP\.cursor\browser-logs\cdp-response-Runtime.evaluate-2026-08-02T14-14-04-555Z.json")
d = json.loads(p.read_text(encoding="utf-8"))
v = d.get("result", d)
if isinstance(v, dict) and "result" in v:
    v = v["result"]
if isinstance(v, dict) and "value" in v:
    v = v["value"]

fields = v.get("fields") or []
# keep meaningful labels
clean = []
seen = set()
for f in fields:
    lab = (f.get("label") or "").strip()
    sid = f.get("shortId") or ""
    typ = (f.get("type") or "").lower()
    if not lab and not sid:
        continue
    # skip date fragment noise
    if lab in {"dd", "mm", "yyyy"}:
        continue
    key = sid or lab
    if key in seen:
        continue
    seen.add(key)
    clean.append(f)

md = []
md.append("# Form: Item Master (Add Item)\n")
md.append(f"**Source:** {v.get('url')}\n")
md.append(f"**Tabs:** {', '.join(v.get('tabs') or []) or 'Add Item | View Item'}\n")
md.append(f"**Headings:** {', '.join(v.get('headings') or [])}\n")
md.append("\n## Fields\n\n| Field | Type | Required | Options / notes |\n|-------|------|----------|------------------|\n")
for f in clean:
    lab = (f.get("label") or f.get("shortId") or "").replace("|", "/")
    typ = f.get("type") or ""
    req = "yes" if f.get("required") else ""
    opts = f.get("options") or []
    note = ""
    if opts:
        note = ", ".join(opts[:8])
        if len(opts) > 8:
            note += ", …"
    elif f.get("placeholder"):
        note = f.get("placeholder")
    elif f.get("value") not in ("", False, True, None) and typ not in ("text", "textarea"):
        note = f"default={f.get('value')}"
    md.append(f"| {lab} | {typ} | {req} | {note} |\n")

md.append("\n## Kanha mapping\n- Entity: `Item`\n- Fresh entry only\n- Relations: Branch, Brand, Category/Group, Unit, Godown, tax/MRP as present\n")

out_md = Path(r"E:\KanhaOS-AI\docs\client-erp\forms\item-master.md")
out_json = Path(r"E:\KanhaOS-AI\docs\client-erp\forms\item-master.json")
out_md.write_text("".join(md), encoding="utf-8")
out_json.write_text(json.dumps({"url": v.get("url"), "tabs": v.get("tabs"), "fields": clean}, indent=2, ensure_ascii=False), encoding="utf-8")
print(f"item fields={len(clean)}")
for f in clean[:50]:
    print("-", f.get("label"), f"[{f.get('type')}]")
