"""Complete KanhaERP page/API smoke — login + every major page dependency."""
from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8080"


def req(method: str, path: str, token: str | None = None, body: dict | None = None):
    data = None
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if body is not None:
        data = json.dumps(body).encode()
    r = urllib.request.Request(BASE + path, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(r, timeout=20) as res:
            raw = res.read().decode("utf-8", "replace")
            try:
                return res.status, json.loads(raw) if raw else None
            except Exception:
                return res.status, raw[:200]
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", "replace")
        return e.code, raw[:300]
    except Exception as e:
        return 0, str(e)


PAGES = {
    "assets": [
        ("GET", "/"),
        ("GET", "/assets/js/app.js?v=adv3"),
        ("GET", "/assets/js/api.js?v=adv3"),
        ("GET", "/assets/css/app.css?v=adv3"),
    ],
    "core": [
        ("GET", "/api/health"),
        ("GET", "/api/brand/public"),
        ("GET", "/api/modules"),
        ("GET", "/api/auth/me"),
        ("GET", "/api/dashboard"),
        ("GET", "/api/notifications"),
        ("GET", "/api/core-control/access"),
    ],
    "ops-board": [
        ("GET", "/api/ops-board/pending"),
        ("GET", "/api/ops-board/actions"),
        ("GET", "/api/advanced/smart-alerts"),
    ],
    "crm": [
        ("GET", "/api/crm/customers"),
        ("GET", "/api/crm/leads"),
        ("GET", "/api/crm/opportunities"),
        ("GET", "/api/crm/quotations"),
    ],
    "sales": [
        ("GET", "/api/sales/orders"),
        ("GET", "/api/sales/invoices"),
        ("GET", "/api/sales/payments"),
        ("GET", "/api/sales/deliveries"),
    ],
    "purchase": [
        ("GET", "/api/purchase/vendors"),
        ("GET", "/api/purchase/orders"),
        ("GET", "/api/purchase/invoices"),
        ("GET", "/api/purchase/grn"),
        ("GET", "/api/purchase/payments"),
        ("GET", "/api/inventory/products"),
    ],
    "books": [
        ("GET", "/api/books/summary"),
        ("GET", "/api/books/vouchers"),
        ("GET", "/api/books/daybook"),
        ("GET", "/api/books/reports/trial-balance"),
        ("GET", "/api/books/coa"),
        ("GET", "/api/books/cash-book"),
        ("GET", "/api/books/bank-book"),
        ("GET", "/api/books/reports/gstr3b"),
        ("GET", "/api/books/bank-recon"),
        ("GET", "/api/books/cost-centres"),
        ("GET", "/api/books/reports/pnl"),
        ("GET", "/api/books/ledger/1100"),
        ("GET", "/api/advanced/bill-wise?party_type=customer"),
        ("GET", "/api/advanced/bill-wise?party_type=vendor"),
    ],
    "inventory": [
        ("GET", "/api/inventory/products"),
        ("GET", "/api/inventory/warehouses"),
        ("GET", "/api/inventory/stock"),
        ("GET", "/api/inventory/godown-stock"),
        ("GET", "/api/advanced/godown-valuation"),
        ("GET", "/api/advanced/stock-ageing"),
    ],
    "manufacturing": [
        ("GET", "/api/manufacturing/work-orders"),
        ("GET", "/api/production/challans"),
    ],
    "advanced": [
        ("GET", "/api/advanced/ageing/receivables"),
        ("GET", "/api/advanced/ageing/payables"),
        ("GET", "/api/advanced/mis/compare"),
        ("GET", "/api/advanced/chase/overdue"),
    ],
    "misc": [
        ("GET", "/api/dealers"),
        ("GET", "/api/pricing/lists"),
        ("GET", "/api/rfq"),
        ("GET", "/api/documents"),
        ("GET", "/api/compliance/scorecard"),
        ("GET", "/api/agents"),
        ("GET", "/api/whatsapp/threads"),
    ],
}


def main():
    st, login = req("POST", "/api/auth/login", body={"email": "admin@kanhaerp.com", "password": "admin123"})
    if st != 200 or not isinstance(login, dict) or not login.get("access_token"):
        print("LOGIN_FAIL", st, login)
        sys.exit(2)
    token = login["access_token"]
    print("LOGIN_OK")

    fails = []
    for page, calls in PAGES.items():
        print(f"\n== {page} ==")
        for method, path in calls:
            code, data = req(method, path, token=token if path.startswith("/api/") and path not in ("/api/health", "/api/brand/public") else (token if path.startswith("/api/") else None))
            # health/brand need no auth; modules etc need auth
            if not path.startswith("/api/"):
                code, data = req(method, path)
            elif path in ("/api/health", "/api/brand/public"):
                code, data = req(method, path)
            else:
                code, data = req(method, path, token=token)
            ok = 200 <= int(code) < 300
            mark = "OK" if ok else "FAIL"
            extra = ""
            if not ok:
                fails.append((page, path, code, str(data)[:120]))
                extra = f" -> {str(data)[:100]}"
            elif isinstance(data, dict) and path.endswith("gstr3b"):
                extra = f" rcm={data.get('rcm', {}).get('docs')}"
            elif isinstance(data, list):
                extra = f" n={len(data)}"
            print(f"  {mark} {code} {path}{extra}")

    # party csv + party ledger
    print("\n== party ==")
    st, custs = req("GET", "/api/crm/customers", token=token)
    name = custs[0]["name"] if isinstance(custs, list) and custs else "A"
    for path in [
        f"/api/advanced/party-ledger?party={urllib.request.quote(name)}&party_type=customer",
        f"/api/advanced/party-ledger.csv?party={urllib.request.quote(name)}&party_type=customer",
    ]:
        code, data = req("GET", path, token=token)
        ok = 200 <= int(code) < 300
        if not ok:
            fails.append(("party", path, code, str(data)[:120]))
        print(f"  {'OK' if ok else 'FAIL'} {code} {path[:80]}")

    print("\n== SUMMARY ==")
    if fails:
        print(f"FAILS={len(fails)}")
        for f in fails:
            print(" ", f)
        sys.exit(1)
    print("ALL_PAGE_APIS_OK")
    sys.exit(0)


if __name__ == "__main__":
    import urllib.parse

    urllib.request.quote = urllib.parse.quote
    main()
