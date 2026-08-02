"""Headless Chrome CDP: capture console errors + #app content for KanhaERP login."""
from __future__ import annotations

import asyncio
import json
import subprocess
import time
import urllib.request
from pathlib import Path

import websockets

CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
PROF = Path(r"c:\Users\HP\Projects\kanha-erp\data\recheck_browser\cdp_profile")
URL = "http://127.0.0.1:8080/#/login"


async def run(ws_url: str) -> None:
    logs: list[dict] = []
    async with websockets.connect(ws_url, max_size=8_000_000) as ws:
        req_id = 0

        async def send(method: str, params: dict | None = None) -> dict:
            nonlocal req_id
            req_id += 1
            mid = req_id
            await ws.send(json.dumps({"id": mid, "method": method, "params": params or {}}))
            while True:
                data = json.loads(await asyncio.wait_for(ws.recv(), timeout=15))
                if data.get("id") == mid:
                    return data
                if data.get("method"):
                    logs.append(data)

        await send("Runtime.enable")
        await send("Console.enable")
        await send("Page.enable")
        await send("Network.enable")
        await send("Page.navigate", {"url": URL})

        end = time.time() + 8
        while time.time() < end:
            try:
                data = json.loads(await asyncio.wait_for(ws.recv(), timeout=0.8))
                if data.get("method"):
                    logs.append(data)
            except asyncio.TimeoutError:
                pass

        expr = """({
          appLen: (document.getElementById('app')||{}).innerHTML.length || 0,
          hasLogin: !!document.querySelector('.login-shell'),
          hasRecover: !!document.getElementById('kanha-recover'),
          sample: ((document.getElementById('app')||{}).innerHTML || '').slice(0, 300),
          scripts: [...document.scripts].map(s => s.src || 'inline')
        })"""
        res = await send("Runtime.evaluate", {"expression": expr, "returnByValue": True})
        print("EVAL", json.dumps(res.get("result", {}), ensure_ascii=False)[:2500])

        interesting = {
            "Runtime.exceptionThrown",
            "Console.messageAdded",
            "Runtime.consoleAPICalled",
            "Log.entryAdded",
        }
        for d in logs:
            m = d.get("method", "")
            if m in interesting:
                print("EVT", m, json.dumps(d.get("params", {}), ensure_ascii=False)[:2000])


def main() -> None:
    if PROF.exists():
        import shutil

        shutil.rmtree(PROF, ignore_errors=True)
    PROF.mkdir(parents=True, exist_ok=True)

    proc = subprocess.Popen(
        [
            CHROME,
            "--headless=new",
            "--disable-gpu",
            "--remote-debugging-port=9222",
            f"--user-data-dir={PROF}",
            "--no-first-run",
            "--disable-extensions",
            "about:blank",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        time.sleep(2)
        tabs = json.load(urllib.request.urlopen("http://127.0.0.1:9222/json", timeout=5))
        page = next((t for t in tabs if t.get("type") == "page" and t.get("webSocketDebuggerUrl")), tabs[0])
        print("TAB0", page.get("url"))
        asyncio.run(run(page["webSocketDebuggerUrl"]))
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


if __name__ == "__main__":
    main()
