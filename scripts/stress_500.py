"""
KanhaERP final operational stress — ~500+ entry flows across modules.
Run: PYTHONPATH=backend python scripts/stress_500.py
"""
from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.request
from typing import Any

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8080"


def req(method: str, path: str, token: str | None = None, body: dict | None = None) -> tuple[int, Any]:
    data = None
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if body is not None:
        data = json.dumps(body).encode("utf-8")
    r = urllib.request.Request(BASE + path, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(r, timeout=60) as res:
            raw = res.read().decode("utf-8")
            return res.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="replace")
        try:
            payload = json.loads(raw)
        except Exception:
            payload = {"detail": raw[:500]}
        return e.code, payload


def main() -> int:
    t0 = time.time()
    ok = 0
    fail = 0
    errors: list[str] = []
    modules_ok: dict[str, int] = {}

    def track(mod: str, code: int, label: str):
        nonlocal ok, fail
        if 200 <= code < 300:
            ok += 1
            modules_ok[mod] = modules_ok.get(mod, 0) + 1
        else:
            fail += 1
            errors.append(f"{mod} {label}: HTTP {code}")

    code, login = req("POST", "/api/auth/login", body={"email": "admin@kanhaerp.com", "password": "admin123"})
    if code != 200:
        print("LOGIN_FAIL", login)
        return 1
    token = login["access_token"]
    track("auth", code, "login")

    # Health + legal + hierarchy
    for path, mod in [
        ("/api/health", "health"),
        ("/api/legal/board", "legal"),
        ("/api/approvals/hierarchy", "approvals"),
        ("/api/approvals?inbox=true", "approvals"),
        ("/api/hrms/salary-policy", "hrms"),
        ("/api/hrms/consent/clause", "hrms"),
        ("/api/accounting/period-lock", "accounting"),
        ("/api/ai/chat", "ai"),
    ]:
        if path == "/api/ai/chat":
            c, _ = req("POST", path, token, {"message": "ERP modules guide"})
        else:
            c, _ = req("GET", path, token)
        track(mod, c, path)

    # Seed references
    c, products = req("GET", "/api/inventory/products", token)
    track("inventory", c, "products")
    c, customers = req("GET", "/api/crm/customers", token)
    track("crm", c, "customers")
    c, vendors = req("GET", "/api/purchase/vendors", token)
    track("purchase", c, "vendors")
    c, warehouses = req("GET", "/api/inventory/warehouses", token)
    track("inventory", c, "warehouses")
    pid = (products[0]["id"] if products else None)
    cid = (customers[0]["id"] if customers else None)
    vid = (vendors[0]["id"] if vendors else None)
    wh = (warehouses[0]["id"] if warehouses else None)

    # ── 200 CRM leads ──
    for i in range(200):
        c, _ = req(
            "POST",
            "/api/crm/leads",
            token,
            {"name": f"Stress Lead {i}", "phone": f"+9198{i:08d}"[:13], "source": "stress", "stage": "new"},
        )
        track("crm", c, f"lead-{i}")

    # ── 50 quotations + convert some ──
    quote_ids = []
    for i in range(50):
        if not cid or not pid:
            break
        c, q = req(
            "POST",
            "/api/crm/quotations",
            token,
            {
                "customer_id": cid,
                "lines": [{"product_id": pid, "qty": 1 + (i % 5), "rate": 1000 + i * 10, "gst_rate": 18}],
            },
        )
        track("crm", c, f"quote-{i}")
        if c < 300 and isinstance(q, dict) and q.get("id"):
            quote_ids.append(q["id"])

    so_ids = []
    for qid in quote_ids[:30]:
        c, so = req("POST", f"/api/sales/flow/quote-to-order/{qid}", token)
        track("sales", c, f"q2o-{qid}")
        if c < 300 and isinstance(so, dict) and so.get("id"):
            so_ids.append(so["id"])

    for soid in so_ids[:15]:
        # approve if pending
        req("POST", f"/api/sales/orders/{soid}/approve", token, {"note": "stress"})
        c, _ = req("POST", f"/api/sales/flow/order-to-invoice/{soid}", token)
        track("sales", c, f"o2i-{soid}")

    # ── 50 inventory adjusts ──
    for i in range(50):
        if not pid or not wh:
            break
        c, _ = req(
            "POST",
            "/api/inventory/adjust",
            token,
            {"product_id": pid, "warehouse_id": wh, "qty": 1, "notes": f"stress-{i}"},
        )
        track("inventory", c, f"adj-{i}")

    # ── 40 attendance + 20 expenses ──
    c, emps = req("GET", "/api/hrms/employees", token)
    track("hrms", c, "emps")
    emp_ids = [e["id"] for e in (emps or [])][:5] or []
    for i in range(40):
        if not emp_ids:
            break
        eid = emp_ids[i % len(emp_ids)]
        c, _ = req(
            "POST",
            "/api/hrms/attendance",
            token,
            {"employee_id": eid, "status": "present", "source": "stress"},
        )
        track("hrms", c, f"att-{i}")

    for i in range(20):
        if not emp_ids:
            break
        c, _ = req(
            "POST",
            "/api/hrms/expenses",
            token,
            {"employee_id": emp_ids[0], "amount": 500 + i * 10, "category": "travel", "description": f"stress-{i}"},
        )
        track("hrms", c, f"exp-{i}")

    # ── 30 journals ──
    for i in range(30):
        c, _ = req("POST", "/api/accounting/journals", token, {"narration": f"Stress JV {i}"})
        track("accounting", c, f"jv-{i}")

    # ── 20 service tickets ──
    for i in range(20):
        c, _ = req(
            "POST",
            "/api/service/tickets",
            token,
            {"subject": f"Stress ticket {i}", "ticket_type": "complaint", "notes": "stress"},
        )
        track("service", c, f"tkt-{i}")

    # ── 20 AI chats ──
    for i in range(20):
        msg = ["outstanding", "GST summary", "low stock", "ERP modules guide", "pending approvals"][i % 5]
        c, _ = req("POST", "/api/ai/chat", token, {"message": msg})
        track("ai", c, f"chat-{i}")

    # ── Approvals: normal + emergency ──
    c, sub = req(
        "POST",
        "/api/approvals/submit",
        token,
        {
            "module": "purchase",
            "entity_type": "stress",
            "entity_id": "PO-STRESS-1",
            "title": "Stress purchase approval",
            "amount": 250000,
        },
    )
    track("approvals", c, "submit")
    c, emg = req(
        "POST",
        "/api/approvals/submit",
        token,
        {
            "module": "logistics",
            "entity_type": "stress",
            "entity_id": "URGENT-1",
            "title": "Emergency dispatch",
            "amount": 1,
            "emergency": True,
            "emergency_reason": "Customer truck waiting — bypass chain",
        },
    )
    track("approvals", c, "emergency")
    if isinstance(emg, dict) and emg.get("id"):
        c, _ = req("POST", f"/api/approvals/{emg['id']}/decide", token, {"approve": True, "note": "Admin emergency OK"})
        track("approvals", c, "emergency-decide")

    # Agents + WA + compliance
    for path, mod in [
        ("/api/agents/cash/run", "agents"),
        ("/api/agents/stock/run", "agents"),
        ("/api/compliance/scan", "compliance"),
        ("/api/accounting/reports/gst", "accounting"),
        ("/api/hrms/payroll/run", "hrms"),
        ("/api/whatsapp/os", "whatsapp"),
    ]:
        method = "POST" if path.endswith("/run") or path.endswith("/payroll/run") else "GET"
        c, _ = req(method, path, token, {} if method == "POST" else None)
        track(mod, c, path)

    elapsed = round(time.time() - t0, 2)
    total = ok + fail
    report = {
        "base": BASE,
        "total_ops": total,
        "ok": ok,
        "fail": fail,
        "success_rate_pct": round(100 * ok / total, 2) if total else 0,
        "elapsed_sec": elapsed,
        "per_module": modules_ok,
        "errors_sample": errors[:25],
        "error_count": len(errors),
        "verdict": "PASS" if fail == 0 and ok >= 500 else ("PASS_WITH_GAPS" if fail < 20 and ok >= 400 else "NEEDS_FIX"),
    }
    out = json.dumps(report, indent=2)
    print(out)
    path = "c:/Users/HP/Projects/kanha-erp/data/stress_500_report.json"
    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write(out)
    except Exception:
        pass
    return 0 if report["verdict"] != "NEEDS_FIX" else 2


if __name__ == "__main__":
    raise SystemExit(main())
