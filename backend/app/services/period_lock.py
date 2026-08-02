"""Accounting period soft-lock — protects books integrity (top-ERP hygiene)."""
from __future__ import annotations

from datetime import date, datetime
from typing import Any

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models import SyncState

PERIOD_KEY = "accounting.period_lock"


def _row(db: Session, company_id: int) -> SyncState:
    key = f"{PERIOD_KEY}.{company_id}"
    row = db.query(SyncState).filter(SyncState.key == key).first()
    if not row:
        row = SyncState(key=key, value={"closed_through": None, "note": ""})
        db.add(row)
        db.flush()
    return row


def period_status(db: Session, company_id: int) -> dict[str, Any]:
    row = _row(db, company_id)
    val = dict(row.value or {})
    return {
        "closed_through": val.get("closed_through"),  # YYYY-MM
        "note": val.get("note") or "",
        "updated_at": val.get("updated_at"),
        "updated_by": val.get("updated_by") or "",
        "message": (
            f"Books closed through {val['closed_through']} — no new posts in closed months."
            if val.get("closed_through")
            else "No period lock — all months open."
        ),
    }


def set_period_lock(
    db: Session,
    company_id: int,
    *,
    closed_through: str | None,
    note: str = "",
    updated_by: str = "",
) -> dict[str, Any]:
    """closed_through = YYYY-MM (inclusive). None clears lock."""
    if closed_through:
        try:
            datetime.strptime(closed_through + "-01", "%Y-%m-%d")
        except ValueError as e:
            raise HTTPException(400, "closed_through must be YYYY-MM") from e
    row = _row(db, company_id)
    row.value = {
        "closed_through": closed_through or None,
        "note": (note or "")[:300],
        "updated_at": datetime.utcnow().isoformat() + "Z",
        "updated_by": updated_by or "",
    }
    db.flush()
    return period_status(db, company_id)


def assert_period_open(db: Session, company_id: int, doc_date: date | None = None) -> None:
    """Raise 423 if document date falls in a closed period."""
    st = period_status(db, company_id)
    closed = st.get("closed_through")
    if not closed:
        return
    d = doc_date or date.today()
    doc_ym = f"{d.year:04d}-{d.month:02d}"
    if doc_ym <= closed:
        raise HTTPException(
            423,
            f"Accounting period locked through {closed}. "
            f"Document date {doc_ym} is closed — Unlock in Accounting or use a later date.",
        )
