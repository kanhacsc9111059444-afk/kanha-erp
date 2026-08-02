"""
Emergency blackout / disaster lockdown.
When engaged: no business entries; data frozen into portable ERP packs.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.models import SyncState


BLACKOUT_KEY = "ops.blackout"
CONFIRM_ENGAGE = "BLACKOUT NOW"
CONFIRM_UNLOCK = "RESUME LIVE"


def _get_row(db: Session) -> SyncState:
    row = db.query(SyncState).filter(SyncState.key == BLACKOUT_KEY).first()
    if not row:
        row = SyncState(key=BLACKOUT_KEY, value={"active": False})
        db.add(row)
        db.flush()
    return row


def blackout_status(db: Session) -> dict[str, Any]:
    row = _get_row(db)
    val = dict(row.value or {})
    return {
        "active": bool(val.get("active")),
        "reason": val.get("reason") or "",
        "engaged_at": val.get("engaged_at"),
        "engaged_by": val.get("engaged_by") or "",
        "portable": val.get("portable") or {},
        "confirm_engage": CONFIRM_ENGAGE,
        "confirm_unlock": CONFIRM_UNLOCK,
        "message": (
            "BLACKOUT ON — all entries blocked. Download portable pack / wait for connectivity."
            if val.get("active")
            else "Live — entries allowed."
        ),
    }


def is_blackout(db: Session | None = None) -> bool:
    """Fast check — opens its own session if none provided (middleware)."""
    own = False
    if db is None:
        from app.core.database import SessionLocal

        db = SessionLocal()
        own = True
    try:
        row = db.query(SyncState).filter(SyncState.key == BLACKOUT_KEY).first()
        if not row:
            return False
        return bool((row.value or {}).get("active"))
    except Exception:
        return False
    finally:
        if own:
            db.close()


def engage_blackout(
    db: Session,
    *,
    reason: str = "disaster / blackout",
    engaged_by: str = "",
    mirror: bool = True,
) -> dict[str, Any]:
    """Lock writes + freeze portable ERP packs on all mirrors."""
    from app.services.ha_cluster import current_seq
    from app.services.ha_portable import build_portable_pack, mirror_portable_to_all_sites
    from app.core.config import BACKUP

    seq = current_seq(db) + 1
    portable: dict[str, Any] = {}
    if mirror:
        try:
            portable = mirror_portable_to_all_sites(seq)
        except Exception as e:
            # Still freeze local pack even if mirrors fail
            portable = {"ok": False, "error": str(e), "fallback": build_portable_pack(BACKUP, seq=seq, role_hint="blackout")}
    else:
        portable = build_portable_pack(BACKUP, seq=seq, role_hint="blackout")

    row = _get_row(db)
    row.value = {
        "active": True,
        "reason": (reason or "disaster / blackout")[:500],
        "engaged_at": datetime.utcnow().isoformat() + "Z",
        "engaged_by": engaged_by or "",
        "portable": {
            "seq": seq,
            "checksum": portable.get("checksum"),
            "latest_zip": portable.get("archive", {}).get("latest_zip")
            or portable.get("latest_zip")
            or (portable.get("fallback") or {}).get("latest_zip"),
            "mirrors": len(portable.get("mirrors") or []),
            "message": portable.get("message") or "Portable pack frozen",
        },
    }
    db.flush()
    return {
        "ok": True,
        "blackout": blackout_status(db),
        "portable": portable,
        "message": "BLACKOUT engaged — entries blocked; portable ERP packs saved.",
    }


def unlock_blackout(db: Session, *, unlocked_by: str = "") -> dict[str, Any]:
    row = _get_row(db)
    prev = dict(row.value or {})
    row.value = {
        "active": False,
        "reason": "",
        "engaged_at": prev.get("engaged_at"),
        "unlocked_at": datetime.utcnow().isoformat() + "Z",
        "unlocked_by": unlocked_by or "",
        "portable": prev.get("portable") or {},
    }
    db.flush()
    return {
        "ok": True,
        "blackout": blackout_status(db),
        "message": "BLACKOUT cleared — ERP live for entries again.",
    }
