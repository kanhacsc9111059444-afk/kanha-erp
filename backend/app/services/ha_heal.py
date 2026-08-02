"""Entry crash auto-heal — rollback bad writes, keep payload for re-entry."""
from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.models import FailedEntry

log = logging.getLogger("kanha.heal")

_SKIP_PREFIXES = (
    "/api/ha/",
    "/api/auth/login",
    "/api/health",
    "/api/ops/backup",
)


def module_from_path(path: str) -> str:
    parts = [p for p in (path or "").split("/") if p]
    if len(parts) >= 2 and parts[0] == "api":
        return parts[1]
    return "unknown"


def should_capture(path: str, method: str) -> bool:
    if method.upper() not in {"POST", "PUT", "PATCH", "DELETE"}:
        return False
    if not path.startswith("/api/"):
        return False
    return not any(path.startswith(p) for p in _SKIP_PREFIXES)


def record_failed_entry(
    db: Session,
    *,
    path: str,
    method: str,
    status_code: int,
    error_message: str,
    payload: dict[str, Any] | list | None = None,
    user_email: str = "",
    company_id: int | None = None,
) -> FailedEntry | None:
    if not should_capture(path, method):
        return None
    # Don't spam identical pending rows within same path+user+error
    existing = (
        db.query(FailedEntry)
        .filter(
            FailedEntry.heal_status == "pending",
            FailedEntry.path == path,
            FailedEntry.user_email == (user_email or ""),
            FailedEntry.error_message == (error_message or "")[:2000],
        )
        .order_by(FailedEntry.id.desc())
        .first()
    )
    body: dict[str, Any]
    if isinstance(payload, dict):
        body = payload
    elif payload is None:
        body = {}
    else:
        body = {"_raw": payload}

    if existing:
        existing.status_code = status_code
        existing.payload = body
        existing.updated_at = datetime.utcnow()
        db.flush()
        return existing

    row = FailedEntry(
        company_id=company_id,
        user_email=user_email or "",
        method=method.upper(),
        path=path,
        module_hint=module_from_path(path),
        error_message=(error_message or "")[:4000],
        status_code=int(status_code or 500),
        payload=body,
        heal_status="pending",
        heal_note="Auto-captured: write rolled back. Re-enter when ready.",
    )
    db.add(row)
    db.flush()
    return row


def list_failed_entries(db: Session, *, status: str | None = "pending", limit: int = 50) -> list[dict]:
    q = db.query(FailedEntry).order_by(FailedEntry.id.desc())
    if status:
        q = q.filter(FailedEntry.heal_status == status)
    rows = q.limit(limit).all()
    return [
        {
            "id": r.id,
            "module": r.module_hint,
            "method": r.method,
            "path": r.path,
            "error": r.error_message,
            "status_code": r.status_code,
            "user_email": r.user_email,
            "heal_status": r.heal_status,
            "heal_note": r.heal_note,
            "payload": r.payload,
            "created_at": r.created_at.isoformat() + "Z" if r.created_at else None,
            "healed_at": r.healed_at.isoformat() + "Z" if r.healed_at else None,
            "reentry": {
                "method": r.method,
                "path": r.path,
                "body": r.payload,
            },
        }
        for r in rows
    ]


def mark_healed(db: Session, entry_id: int, *, note: str = "", status: str = "healed") -> dict:
    row = db.get(FailedEntry, entry_id)
    if not row:
        return {"ok": False, "error": "not found"}
    row.heal_status = status
    row.heal_note = note or row.heal_note
    row.healed_at = datetime.utcnow()
    db.commit()
    return {"ok": True, "id": row.id, "heal_status": row.heal_status}


def parse_body_bytes(raw: bytes) -> dict[str, Any] | list | None:
    if not raw:
        return {}
    try:
        return json.loads(raw.decode("utf-8"))
    except Exception:
        return {"_raw_text": raw.decode("utf-8", errors="replace")[:8000]}
