"""
Third-party app hooks — generic connector layer.

Marg / Busy / Vyapar / any running app → same hook model.
No per-ERP spaghetti: presets only set labels + default events.
Transport = webhook out / webhook in / file pack (manageable).
"""
from __future__ import annotations

import hashlib
import secrets
import time
from datetime import datetime
from typing import Any

import httpx
from sqlalchemy.orm import Session

from app.models import Company

# Presets = catalog only. Runtime always uses one Hook schema.
HOOK_PRESETS: list[dict[str, Any]] = [
    {
        "id": "marg",
        "label": "Marg ERP",
        "hint": "Customer pe Marg already chal raha ho — webhook / CSV / API URL se link.",
        "default_events": ["invoice.created", "payment.recorded", "party.upsert", "stock.adjust"],
    },
    {
        "id": "busy",
        "label": "Busy Accounting",
        "hint": "Busy books primary rahe — Kanha ops events push / daybook pull.",
        "default_events": ["invoice.created", "payment.recorded", "journal.posted"],
    },
    {
        "id": "vyapar",
        "label": "Vyapar / billing app",
        "hint": "Shop billing app se party + invoice sync via webhook.",
        "default_events": ["invoice.created", "party.upsert"],
    },
    {
        "id": "custom",
        "label": "Custom / any app",
        "hint": "Koi bhi third-party — outbound URL + inbound token. Same contract.",
        "default_events": ["invoice.created", "payment.recorded", "party.upsert", "stock.adjust", "generic"],
    },
    {
        "id": "tally",
        "label": "Tally (hook)",
        "hint": "Tally pe webhook/CSV listener — data pack APIs alag se bhi hain (#/bridges ERP packs).",
        "default_events": ["invoice.created", "payment.recorded", "party.upsert", "journal.posted"],
    },
]

ALLOWED_EVENTS = {
    "invoice.created",
    "payment.recorded",
    "party.upsert",
    "stock.adjust",
    "journal.posted",
    "generic",
}


def _sj(db: Session, company_id: int) -> tuple[Company, dict]:
    co = db.get(Company, company_id)
    if not co:
        raise ValueError("Company not found")
    return co, dict(co.settings_json or {})


def _save(db: Session, co: Company, sj: dict) -> None:
    co.settings_json = sj
    db.add(co)
    db.commit()
    db.refresh(co)


def list_presets() -> list[dict[str, Any]]:
    return list(HOOK_PRESETS)


def list_hooks(db: Session, company_id: int) -> list[dict[str, Any]]:
    _, sj = _sj(db, company_id)
    return list(sj.get("third_party_hooks") or [])


def get_hook(db: Session, company_id: int, hook_id: str) -> dict[str, Any] | None:
    for h in list_hooks(db, company_id):
        if h.get("id") == hook_id:
            return h
    return None


def create_hook(
    db: Session,
    company_id: int,
    *,
    preset: str = "custom",
    name: str = "",
    direction: str = "both",
    outbound_url: str = "",
    events: list[str] | None = None,
    created_by: str = "",
) -> dict[str, Any]:
    preset = (preset or "custom").lower()
    meta = next((p for p in HOOK_PRESETS if p["id"] == preset), None)
    if not meta:
        raise ValueError(f"Unknown preset {preset}. Use: {[p['id'] for p in HOOK_PRESETS]}")
    if direction not in ("in", "out", "both"):
        raise ValueError("direction must be in|out|both")

    ev = [e for e in (events or meta["default_events"]) if e in ALLOWED_EVENTS]
    if not ev:
        ev = list(meta["default_events"])

    hook_id = f"hook_{preset}_{int(time.time())}_{secrets.token_hex(3)}"
    inbound_token = secrets.token_urlsafe(24)
    hook = {
        "id": hook_id,
        "preset": preset,
        "label": meta["label"],
        "name": (name or f"{meta['label']} link").strip()[:80],
        "direction": direction,
        "status": "active",
        "outbound_url": (outbound_url or "").strip(),
        "inbound_token": inbound_token,
        "events": ev,
        "stats": {"pushed": 0, "received": 0, "failed": 0},
        "last_push_at": None,
        "last_receive_at": None,
        "last_error": None,
        "created_at": datetime.utcnow().isoformat() + "Z",
        "created_by": created_by,
        "note": meta["hint"],
    }
    co, sj = _sj(db, company_id)
    rows = list(sj.get("third_party_hooks") or [])
    rows.append(hook)
    sj["third_party_hooks"] = rows[-40:]  # hard cap — manageability
    _save(db, co, sj)
    return hook


def update_hook(db: Session, company_id: int, hook_id: str, patch: dict[str, Any]) -> dict[str, Any]:
    co, sj = _sj(db, company_id)
    rows = list(sj.get("third_party_hooks") or [])
    found = None
    for i, h in enumerate(rows):
        if h.get("id") != hook_id:
            continue
        h = dict(h)
        if "name" in patch and patch["name"] is not None:
            h["name"] = str(patch["name"])[:80]
        if "status" in patch and patch["status"] in ("active", "paused", "off"):
            h["status"] = patch["status"]
        if "direction" in patch and patch["direction"] in ("in", "out", "both"):
            h["direction"] = patch["direction"]
        if "outbound_url" in patch:
            h["outbound_url"] = str(patch["outbound_url"] or "").strip()
        if "events" in patch and isinstance(patch["events"], list):
            h["events"] = [e for e in patch["events"] if e in ALLOWED_EVENTS] or h.get("events") or ["generic"]
        if patch.get("rotate_token"):
            h["inbound_token"] = secrets.token_urlsafe(24)
        h["updated_at"] = datetime.utcnow().isoformat() + "Z"
        rows[i] = h
        found = h
        break
    if not found:
        raise ValueError("Hook not found")
    sj["third_party_hooks"] = rows
    _save(db, co, sj)
    return found


def delete_hook(db: Session, company_id: int, hook_id: str) -> bool:
    co, sj = _sj(db, company_id)
    rows = list(sj.get("third_party_hooks") or [])
    new = [h for h in rows if h.get("id") != hook_id]
    if len(new) == len(rows):
        return False
    sj["third_party_hooks"] = new
    # also trim related inbox for this hook
    inbox = [x for x in list(sj.get("third_party_inbox") or []) if x.get("hook_id") != hook_id]
    sj["third_party_inbox"] = inbox[-100:]
    _save(db, co, sj)
    return True


def _append_log(sj: dict, entry: dict) -> None:
    log = list(sj.get("third_party_log") or [])
    log.append(entry)
    sj["third_party_log"] = log[-150:]


def push_event(
    db: Session,
    company_id: int,
    *,
    event: str,
    payload: dict[str, Any],
    hook_id: str | None = None,
) -> dict[str, Any]:
    """Fan-out to all matching active outbound hooks (or one hook)."""
    if event not in ALLOWED_EVENTS:
        event = "generic"
    co, sj = _sj(db, company_id)
    hooks = list(sj.get("third_party_hooks") or [])
    results = []
    now = datetime.utcnow().isoformat() + "Z"
    body = {
        "source": "kanhaerp",
        "event": event,
        "company_id": company_id,
        "sent_at": now,
        "payload": payload,
    }

    for i, h in enumerate(hooks):
        if hook_id and h.get("id") != hook_id:
            continue
        if h.get("status") != "active":
            continue
        if h.get("direction") not in ("out", "both"):
            continue
        if event not in (h.get("events") or []) and "generic" not in (h.get("events") or []):
            continue
        url = (h.get("outbound_url") or "").strip()
        h = dict(h)
        stats = dict(h.get("stats") or {})
        if not url:
            # Demo-live: queue as delivered_local when no URL (still manageable)
            stats["pushed"] = int(stats.get("pushed") or 0) + 1
            h["stats"] = stats
            h["last_push_at"] = now
            h["last_error"] = None
            hooks[i] = h
            results.append({"hook_id": h["id"], "status": "queued_local", "note": "No outbound URL — logged for mapper/CSV"})
            _append_log(
                sj,
                {"at": now, "hook_id": h["id"], "dir": "out", "event": event, "status": "queued_local", "payload": payload},
            )
            continue
        try:
            with httpx.Client(timeout=12) as client:
                res = client.post(
                    url,
                    json=body,
                    headers={
                        "Content-Type": "application/json",
                        "X-Kanha-Event": event,
                        "X-Kanha-Hook": h["id"],
                        "X-Kanha-Token": h.get("inbound_token") or "",
                    },
                )
            ok = res.status_code < 400
            if ok:
                stats["pushed"] = int(stats.get("pushed") or 0) + 1
                h["last_error"] = None
                status = "sent"
            else:
                stats["failed"] = int(stats.get("failed") or 0) + 1
                h["last_error"] = f"HTTP {res.status_code}"[:120]
                status = "failed"
            h["stats"] = stats
            h["last_push_at"] = now
            hooks[i] = h
            results.append({"hook_id": h["id"], "status": status, "http": res.status_code})
            _append_log(
                sj,
                {"at": now, "hook_id": h["id"], "dir": "out", "event": event, "status": status, "http": res.status_code},
            )
        except Exception as exc:  # noqa: BLE001
            stats["failed"] = int(stats.get("failed") or 0) + 1
            h["stats"] = stats
            h["last_push_at"] = now
            h["last_error"] = str(exc)[:160]
            hooks[i] = h
            results.append({"hook_id": h["id"], "status": "failed", "error": str(exc)[:160]})
            _append_log(
                sj,
                {"at": now, "hook_id": h["id"], "dir": "out", "event": event, "status": "failed", "error": str(exc)[:120]},
            )

    sj["third_party_hooks"] = hooks
    _save(db, co, sj)
    # Echo learn: outbound payload also trains native parity (micro phases)
    learn = None
    if results and payload:
        try:
            from app.services.bridge_intelligence import learn_from_inbound

            learn = learn_from_inbound(db, company_id, payload, source=f"outbound:{event}")
        except Exception:
            learn = None
    return {"ok": True, "event": event, "results": results, "count": len(results), "learn": learn}


def receive_inbound(
    db: Session,
    *,
    hook_id: str,
    token: str,
    event: str,
    payload: dict[str, Any],
    headers: dict | None = None,
) -> dict[str, Any]:
    """Validate token + store inbox (demo-live process). Optional light apply later."""
    # Find company by scanning hooks — portable single-tenant friendly; multi via token match
    from app.models import Company as Co

    companies = db.query(Co).all()
    matched_co = None
    matched_hook = None
    for co in companies:
        sj = dict(co.settings_json or {})
        for h in sj.get("third_party_hooks") or []:
            if h.get("id") == hook_id and h.get("inbound_token") == token:
                matched_co = co
                matched_hook = h
                break
        if matched_co:
            break
    if not matched_co or not matched_hook:
        raise PermissionError("Invalid hook or token")
    if matched_hook.get("status") != "active":
        raise PermissionError("Hook paused/off")
    if matched_hook.get("direction") not in ("in", "both"):
        raise PermissionError("Hook not accepting inbound")

    now = datetime.utcnow().isoformat() + "Z"
    event = event if event in ALLOWED_EVENTS else "generic"
    entry = {
        "id": f"in_{int(time.time() * 1000)}_{secrets.token_hex(2)}",
        "hook_id": hook_id,
        "preset": matched_hook.get("preset"),
        "event": event,
        "payload": payload or {},
        "received_at": now,
        "status": "accepted",
        "headers": {
            k: str(v)[:80]
            for k, v in list((headers or {}).items())[:12]
            if str(k).lower().startswith("x-")
        },
    }
    sj = dict(matched_co.settings_json or {})
    inbox = list(sj.get("third_party_inbox") or [])
    inbox.append(entry)
    sj["third_party_inbox"] = inbox[-100:]
    hooks = list(sj.get("third_party_hooks") or [])
    for i, h in enumerate(hooks):
        if h.get("id") == hook_id:
            h = dict(h)
            st = dict(h.get("stats") or {})
            st["received"] = int(st.get("received") or 0) + 1
            h["stats"] = st
            h["last_receive_at"] = now
            hooks[i] = h
            break
    sj["third_party_hooks"] = hooks
    _append_log(sj, {"at": now, "hook_id": hook_id, "dir": "in", "event": event, "status": "accepted"})
    _save(db, matched_co, sj)
    learn = None
    try:
        from app.services.bridge_intelligence import learn_from_inbound

        learn = learn_from_inbound(db, matched_co.id, payload or {}, source=f"hook:{matched_hook.get('preset')}")
    except Exception:
        learn = None
    return {
        "ok": True,
        "inbox_id": entry["id"],
        "company_id": matched_co.id,
        "learn": learn,
        "message": "Inbound accepted · stored for process / mapper"
        + (f" · learn accuracy {learn.get('accuracy')}" if learn else ""),
    }


def inbox(db: Session, company_id: int) -> list[dict[str, Any]]:
    _, sj = _sj(db, company_id)
    return list(reversed(sj.get("third_party_inbox") or []))[:50]


def activity_log(db: Session, company_id: int) -> list[dict[str, Any]]:
    _, sj = _sj(db, company_id)
    return list(reversed(sj.get("third_party_log") or []))[:60]


def public_inbound_path(hook_id: str) -> str:
    return f"/api/bridges/hooks/inbound/{hook_id}"


def fingerprint_token(token: str) -> str:
    return hashlib.sha256((token or "").encode()).hexdigest()[:10]
