"""A-to-Z smoke check for KanhaERP — exit 0 if clean."""
from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8080"
ok: list[str] = []
fail: list[str] = []


def req(method: str, path: str, body=None, headers=None):
    url = BASE + path
    data = None if body is None else json.dumps(body).encode()
    h = {"Content-Type": "application/json"}
    if headers:
        h.update(headers)
    r = urllib.request.Request(url, data=data, headers=h, method=method)
    try:
        with urllib.request.urlopen(r, timeout=45) as res:
            raw = res.read().decode("utf-8", "replace")
            try:
                j = json.loads(raw)
            except Exception:
                j = {"_raw": raw[:400]}
            return res.status, j
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", "replace")
        try:
            j = json.loads(raw)
        except Exception:
            j = {"_raw": raw[:400]}
        return e.code, j
    except Exception as e:
        return 0, {"error": str(e)}


def check(name, method, path, body=None, headers=None, ok_fn=None):
    code, j = req(method, path, body, headers)
    good = (200 <= code < 300) if ok_fn is None else ok_fn(code, j)
    line = f"{'PASS' if good else 'FAIL'} {name} [{code}] {path}"
    if not good:
        line += f" :: {str(j)[:160]}"
        fail.append(line)
    else:
        ok.append(line)
    return code, j


def try_paths(name, method, paths, body=None, headers=None):
    last = (0, {})
    for path in paths:
        code, j = req(method, path, body, headers)
        last = (code, j)
        if 200 <= code < 300:
            ok.append(f"PASS {name} [{code}] {path}")
            return code, j, path
        if code not in (0, 404):
            # real error on existing route
            fail.append(f"FAIL {name} [{code}] {path} :: {str(j)[:140]}")
            return code, j, path
    fail.append(f"FAIL {name} [404] tried={paths} :: {str(last[1])[:120]}")
    return last[0], last[1], paths[0]


def main() -> int:
    check("health", "GET", "/api/health", ok_fn=lambda c, j: c == 200 and j.get("ok"))
    code, html = req("GET", "/")
    raw = str(html.get("_raw") if isinstance(html, dict) else html)
    # also fetch full page text for cache bump (json helper truncates)
    try:
        with urllib.request.urlopen(BASE + "/", timeout=20) as res:
            full_html = res.read().decode("utf-8", "replace")
    except Exception:
        full_html = raw
    if code == 200 and "form9" in full_html:
        ok.append("PASS frontend cache form9")
    else:
        fail.append(f"FAIL frontend form9 [{code}] snippet={full_html[-120:]}")

    code, login = check(
        "login",
        "POST",
        "/api/auth/login",
        {"email": "admin@kanhaerp.com", "password": "admin123"},
        ok_fn=lambda c, j: c == 200 and bool(j.get("access_token")),
    )
    token = (login or {}).get("access_token")
    if not token:
        print("==== A-TO-Z RESULT ====")
        print("FATAL: login failed")
        for x in fail + ok:
            print(x)
        return 2
    H = {"Authorization": f"Bearer {token}"}

    modules = [
        ("customers", ["GET"], ["/api/crm/customers", "/api/customers"]),
        ("products", ["GET"], ["/api/inventory/products", "/api/products", "/api/trading/products"]),
        ("invoices", ["GET"], ["/api/sales/invoices", "/api/trading/invoices", "/api/invoices"]),
        ("orders", ["GET"], ["/api/sales/orders", "/api/trading/orders", "/api/orders"]),
        ("vendors", ["GET"], ["/api/purchase/vendors", "/api/vendors", "/api/crm/vendors"]),
        ("pi", ["GET"], ["/api/purchase/invoices", "/api/trading/purchase-invoices"]),
        ("stock", ["GET"], ["/api/inventory/stock", "/api/inventory/balances", "/api/inventory/godown-stock"]),
        ("warehouses", ["GET"], ["/api/inventory/warehouses", "/api/warehouses"]),
        ("employees", ["GET"], ["/api/hr/employees", "/api/employees"]),
        ("vouchers", ["GET"], ["/api/books/vouchers"]),
        ("cash-book", ["GET"], ["/api/books/cash-book"]),
        ("gstr3b", ["GET"], ["/api/books/reports/gstr3b"]),
        ("smart-alerts", ["GET"], ["/api/advanced/smart-alerts"]),
        ("ageing-ar", ["GET"], ["/api/advanced/ageing/receivables"]),
        ("mis-compare", ["GET"], ["/api/advanced/mis/compare"]),
        ("ops-board", ["GET"], ["/api/ops-board/pending"]),
        ("tally-pack", ["GET"], ["/api/tally/export-pack"]),
    ]
    for name, methods, paths in modules:
        try_paths(name, methods[0], paths, headers=H)

    try_paths(
        "ai-bridge",
        "POST",
        ["/api/ai/chat", "/api/core-control/chat", "/api/ai/ask"],
        {"message": "bridge intelligence curriculum"},
        H,
    )

    # Bridges + intelligence
    code, hub = check(
        "bridges-hub",
        "GET",
        "/api/bridges",
        headers=H,
        ok_fn=lambda c, j: c == 200 and ("channels" in j or "intelligence" in j),
    )
    intel = (hub or {}).get("intelligence") or {}
    ok.append(
        f"INFO hub trust={intel.get('trust_score')} "
        f"phases={intel.get('phases_complete')}/{intel.get('phases_total')} "
        f"curr={intel.get('curriculum_pct')}"
    )

    check("intel-state", "GET", "/api/bridges/intelligence", headers=H, ok_fn=lambda c, j: c == 200 and "trust_score" in j)

    code, learn = check(
        "learn-cycle",
        "POST",
        "/api/bridges/intelligence/learn",
        {},
        H,
        ok_fn=lambda c, j: c == 200 and j.get("ok"),
    )
    if code == 200:
        phases = set(((learn or {}).get("run") or {}).get("phases_done") or [])
        # without auto_fix, safe_fix may be unmarked
        core = {"ingest", "normalize", "compare", "score", "taxonomy", "rules", "advance", "retain"}
        if core.issubset(phases):
            ok.append(f"PASS learn core phases {len(phases)}/9 present={sorted(phases)}")
        else:
            fail.append(f"FAIL learn missing {core - phases} got={sorted(phases)}")

    code, full = check(
        "learn-full",
        "POST",
        "/api/bridges/intelligence/learn-full",
        {},
        H,
        ok_fn=lambda c, j: c == 200 and j.get("ok"),
    )
    if code == 200:
        need = {"ingest", "normalize", "compare", "score", "taxonomy", "safe_fix", "rules", "advance", "retain"}
        got = set(((full or {}).get("run") or {}).get("phases_done") or [])
        if got == need:
            ok.append(
                f"PASS curriculum 9/9 trust={full.get('trust_score')} acc={full.get('accuracy')} "
                f"curr={((full.get('run') or {}).get('curriculum_pct'))}"
            )
        else:
            fail.append(f"FAIL curriculum missing={need - got} extra={got - need}")

    check("safe-improve", "POST", "/api/bridges/intelligence/improve", {}, H, ok_fn=lambda c, j: c == 200)
    check("hook-presets", "GET", "/api/bridges/hooks/presets", headers=H, ok_fn=lambda c, j: c == 200 and isinstance(j.get("presets"), list))
    check("hooks-list", "GET", "/api/bridges/hooks", headers=H)
    check("tally-export", "POST", "/api/bridges/tally/export", {}, H)
    check("outbox", "GET", "/api/bridges/outbox", headers=H)

    # money safety sanity on improve message
    _, imp = req("POST", "/api/bridges/intelligence/improve", {}, H)
    msg = str((imp or {}).get("message") or "").lower()
    if "money" in msg or "overwrite" in msg or "never" in msg:
        ok.append("PASS safe-improve money-guard wording")
    else:
        ok.append("INFO safe-improve message: " + str((imp or {}).get("message") or "")[:80])

    print("==== A-TO-Z RESULT ====")
    print(f"PASS {len(ok)}  FAIL {len(fail)}")
    for x in ok:
        print(x)
    print("--- FAIL ---")
    for x in fail:
        print(x)
    return 1 if fail else 0


if __name__ == "__main__":
    raise SystemExit(main())
