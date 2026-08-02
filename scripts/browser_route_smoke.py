"""Load SPA in headless Chrome and collect console errors across routes."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

BASE = "http://127.0.0.1:8080"
CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
PORT = 9333
PROF = Path(r"c:\Users\HP\Projects\kanha-erp\data\recheck_browser\smoke_profile")
PROF.mkdir(parents=True, exist_ok=True)

ROUTES = [
    "dashboard",
    "ops-board",
    "crm",
    "sales",
    "purchase",
    "books",
    "inventory",
    "manufacturing",
    "accounting",
    "hrms",
    "mis",
    "rfq",
    "documents",
    "compliance",
    "settings",
    "whatsapp",
    "agents",
    "ha",
    "payments-ops",
    "pos",
]


def http_json(url, method="GET", body=None, headers=None):
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(url, data=data, method=method, headers=headers or {})
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read().decode())


def ws_send(ws_url, method, params=None, _id=1):
    # minimal websocket via PowerShell is hard; use CDP HTTP /json/new and evaluate via
    # chrome-remote-interface alternative: use selenium-less raw with websocket-client if present
    import websocket  # type: ignore

    ws = websocket.create_connection(ws_url, timeout=10)
    msg = {"id": _id, "method": method, "params": params or {}}
    ws.send(json.dumps(msg))
    # read until matching id
    deadline = time.time() + 15
    result = None
    while time.time() < deadline:
        raw = ws.recv()
        data = json.loads(raw)
        if data.get("id") == _id:
            result = data
            break
    ws.close()
    return result


def main():
    # kill old chrome on port
    try:
        urllib.request.urlopen(f"http://127.0.0.1:{PORT}/json/version", timeout=1)
        print("CDP already up")
    except Exception:
        subprocess.Popen(
            [
                CHROME,
                f"--remote-debugging-port={PORT}",
                f"--user-data-dir={PROF}",
                "--headless=new",
                "--disable-gpu",
                "--no-first-run",
                "--no-default-browser-check",
                f"{BASE}/#/login",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        time.sleep(2.5)

    try:
        import websocket  # noqa: F401
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "websocket-client", "-q"])
        import websocket  # noqa: F401

    tabs = http_json(f"http://127.0.0.1:{PORT}/json")
    page = next((t for t in tabs if t.get("type") == "page" and "webSocketDebuggerUrl" in t), None)
    if not page:
        print("NO_TAB", tabs[:2])
        sys.exit(2)
    ws_url = page["webSocketDebuggerUrl"]

    # Enable Runtime + Console + Network
    import websocket

    ws = websocket.create_connection(ws_url, timeout=20)
    rid = 0

    def call(method, params=None, wait=True):
        nonlocal rid
        rid += 1
        ws.send(json.dumps({"id": rid, "method": method, "params": params or {}}))
        if not wait:
            return None
        deadline = time.time() + 20
        while time.time() < deadline:
            data = json.loads(ws.recv())
            if data.get("id") == rid:
                return data
        return None

    call("Runtime.enable")
    call("Console.enable")
    call("Page.enable")
    call("Network.enable")

    # Login via evaluate
    login = http_json(
        f"{BASE}/api/auth/login",
        method="POST",
        body={"email": "admin@kanhaerp.com", "password": "admin123"},
        headers={"Content-Type": "application/json"},
    )
    token = login["access_token"]
    user = login.get("user") or {}

    expr = f"""
    (() => {{
      localStorage.setItem('kanha_token', {json.dumps(token)});
      localStorage.setItem('kanha_user', {json.dumps(json.dumps(user))});
      location.hash = '#/dashboard';
      location.reload();
      return 'ok';
    }})()
    """
    call("Runtime.evaluate", {"expression": expr, "awaitPromise": False})
    time.sleep(2.5)

    errors = []
    page_results = []

    # drain events helper
    def drain(seconds=1.2):
        end = time.time() + seconds
        while time.time() < end:
            ws.settimeout(0.3)
            try:
                raw = ws.recv()
            except Exception:
                continue
            data = json.loads(raw)
            method = data.get("method")
            if method == "Runtime.exceptionThrown":
                desc = data["params"]["exceptionDetails"].get("text") or str(data["params"]["exceptionDetails"])[:200]
                errors.append(("exception", desc))
            elif method == "Runtime.consoleAPICalled" and data["params"].get("type") in ("error", "warning"):
                args = data["params"].get("args") or []
                msg = " ".join(str(a.get("value") or a.get("description") or "") for a in args)[:200]
                errors.append((data["params"]["type"], msg))
            elif method == "Console.messageAdded":
                m = data["params"]["message"]
                if m.get("level") in ("error", "warning"):
                    errors.append((m.get("level"), m.get("text", "")[:200]))

    drain(1.5)

    for route in ROUTES:
        before = len(errors)
        call(
            "Runtime.evaluate",
            {"expression": f"location.hash = '#/{route}'; 'go'", "returnByValue": True},
        )
        time.sleep(1.4)
        drain(1.0)
        # check page body text
        body = call(
            "Runtime.evaluate",
            {
                "expression": """(() => {
                  const b = document.querySelector('#page-body');
                  const t = (b && b.innerText) || document.body.innerText || '';
                  const err = document.querySelector('#page-body .error');
                  return {
                    len: t.length,
                    hasLoading: t.includes('Loading'),
                    error: err ? err.innerText : '',
                    title: (document.querySelector('.topbar h1, .shell-title, h1') || {}).innerText || '',
                    hash: location.hash
                  };
                })()""",
                "returnByValue": True,
            },
        )
        val = ((body or {}).get("result") or {}).get("result") or {}
        value = val.get("value") if isinstance(val, dict) else None
        if not isinstance(value, dict):
            # nested
            value = val if isinstance(val, dict) and "len" in val else {"raw": str(val)[:120]}
        new_errs = errors[before:]
        status = "OK"
        if value.get("error"):
            status = "PAGE_ERROR"
        elif value.get("hasLoading") and (value.get("len") or 0) < 40:
            status = "STUCK_LOADING"
        elif (value.get("len") or 0) < 20:
            status = "EMPTY"
        if new_errs:
            status = status + "+JS" if status != "OK" else "JS_ERR"
        page_results.append((route, status, value, new_errs[:3]))
        print(f"{route}: {status} len={value.get('len')} err={value.get('error')!r} js={len(new_errs)}")

    ws.close()
    bad = [r for r in page_results if not r[1].startswith("OK")]
    print("\nSUMMARY bad=", len(bad), "of", len(page_results), "js_total=", len(errors))
    for e in errors[:15]:
        print(" ERR", e)
    if bad:
        for b in bad:
            print(" BAD", b[0], b[1], b[2], b[3])
        sys.exit(1)
    print("ALL_ROUTES_RENDER_OK")
    sys.exit(0)


if __name__ == "__main__":
    main()
