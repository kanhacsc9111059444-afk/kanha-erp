"""KanhaERP smoke test — login + core APIs."""
from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request

BASE = "http://127.0.0.1:8080"
results: list[tuple[str, bool, str]] = []


def req(method: str, path: str, body: dict | None = None, token: str | None = None) -> tuple[int, dict | str]:
    data = None
    headers = {"Accept": "application/json"}
    if body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    r = urllib.request.Request(BASE + path, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(r, timeout=30) as resp:
            raw = resp.read().decode()
            try:
                return resp.status, json.loads(raw)
            except Exception:
                return resp.status, raw[:200]
    except urllib.error.HTTPError as e:
        raw = e.read().decode(errors="ignore")
        try:
            return e.code, json.loads(raw)
        except Exception:
            return e.code, raw[:200]


def check(name: str, ok: bool, detail: str = "") -> None:
    results.append((name, ok, detail))
    mark = "PASS" if ok else "FAIL"
    print(f"[{mark}] {name}" + (f" — {detail}" if detail else ""))


# 1 health
code, health = req("GET", "/api/health")
check("GET /api/health", code == 200 and isinstance(health, dict) and health.get("ok") is True, f"app={health.get('app') if isinstance(health, dict) else health}")

# 2 index
code, _ = req("GET", "/")
check("GET / (SPA)", code == 200)

# 3 login
code, login = req("POST", "/api/auth/login", {"email": "admin@kanhaerp.com", "password": "admin123"})
token = login.get("access_token") if isinstance(login, dict) else None
if not token and isinstance(login, dict):
    token = (login.get("token") or login.get("access") or "")
check("POST /api/auth/login", code == 200 and bool(token), f"code={code}")

if not token:
    print("\nABORT: no token")
    sys.exit(1)

# Authenticated suite
suite = [
    ("GET", "/api/brand/public", None),
    ("GET", "/api/books/summary", None),
    ("GET", "/api/books/coa", None),
    ("GET", "/api/hrms/employees", None),
    ("GET", "/api/bridges", None),
    ("GET", "/api/bridges/tally/sync", None),
    ("GET", "/api/extras/whatsapp-login", None),
    ("GET", "/api/extras/store-slots", None),
    ("GET", "/api/mis/sales-summary", None),
    ("GET", "/api/advanced/chase/overdue", None),
    ("GET", "/api/outstanding/summary", None),
]

for method, path, body in suite:
    c, data = req(method, path, body, token=token)
    ok = 200 <= c < 300
    detail = f"HTTP {c}"
    if isinstance(data, dict) and data.get("detail"):
        detail += f" detail={data.get('detail')}"
    check(f"{method} {path}", ok, detail)

# OCR parse
c, data = req(
    "POST",
    "/api/extras/ocr/parse",
    {
        "text": "Invoice No: INV-SMOKE-1\nBill To: Smoke Test Co\nGSTIN: 22AAAAA0000A1Z5\nGrand Total: 11800\nDate: 02/08/2026",
        "doc_kind": "invoice",
    },
    token=token,
)
fields = (data or {}).get("fields") if isinstance(data, dict) else {}
check(
    "POST /api/extras/ocr/parse",
    c == 200 and bool(fields.get("invoice_no")),
    f"inv={fields.get('invoice_no')} amt={fields.get('amount')}",
)

# Create ledger
c, data = req(
    "POST",
    "/api/books/ledgers",
    {"code": "SMOK9", "name": "Smoke Ledger", "account_type": "expense", "is_group": False, "opening_balance": 0},
    token=token,
)
check("POST /api/books/ledgers", c == 200 and (isinstance(data, dict) and data.get("code") == "SMOK9"), str(data.get("message") if isinstance(data, dict) else data)[:80])

# Payment voucher small
c, data = req(
    "POST",
    "/api/books/vouchers",
    {"voucher_type": "payment", "amount": 10, "party_name": "Smoke Vendor", "narration": "smoke", "from_account": "1200", "to_account": "2100"},
    token=token,
)
check("POST /api/books/vouchers payment", c == 200 and isinstance(data, dict) and data.get("ok") is True, f"num={data.get('number') if isinstance(data, dict) else data}")

# Hire employee
c, data = req(
    "POST",
    "/api/hrms/employees",
    {"full_name": "Smoke Emp", "department": "QA", "designation": "Tester", "basic_salary": 20000, "work_type": "office"},
    token=token,
)
emp_ok = c == 200 and isinstance(data, dict) and bool(data.get("code"))
check("POST /api/hrms/employees", emp_ok, f"code={data.get('code') if isinstance(data, dict) else data}")

# Meta webhook verify
c, data = req("GET", "/api/meta/whatsapp/webhook?hub.mode=subscribe&hub.verify_token=kanha_meta_verify&hub.challenge=SMOKE123")
# Plain text challenge
check("GET Meta webhook verify", c == 200 and ("SMOKE123" in str(data) or data == "SMOKE123"), f"resp={str(data)[:40]}")

failed = [r for r in results if not r[1]]
print("\n==========")
print(f"TOTAL {len(results)}  PASS {len(results)-len(failed)}  FAIL {len(failed)}")
if failed:
    print("FAILED:")
    for n, _, d in failed:
        print(f"  - {n}: {d}")
    sys.exit(1)
print("SMOKE OK")
sys.exit(0)
