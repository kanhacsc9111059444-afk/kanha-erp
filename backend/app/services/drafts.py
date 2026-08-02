"""Server-side work drafts — phone theft / crash pe data company ke paas rahe."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.models import WorkDraft


def upsert_draft(
    db: Session,
    *,
    company_id: int,
    user_id: int,
    draft_key: str,
    payload: dict[str, Any],
    module: str = "",
    title: str = "",
    client: str = "web",
) -> WorkDraft:
    row = (
        db.query(WorkDraft)
        .filter(
            WorkDraft.company_id == company_id,
            WorkDraft.user_id == user_id,
            WorkDraft.draft_key == draft_key,
        )
        .first()
    )
    if not row:
        row = WorkDraft(
            company_id=company_id,
            user_id=user_id,
            draft_key=draft_key,
        )
        db.add(row)
    row.module = module or row.module or draft_key.split(".")[0]
    row.title = title or row.title or draft_key
    row.payload = payload or {}
    row.client = client or "web"
    row.status = "open"
    row.updated_at = datetime.utcnow()
    db.flush()
    return row


def list_drafts(db: Session, *, company_id: int, user_id: int | None = None, status: str = "open") -> list[dict]:
    q = db.query(WorkDraft).filter(WorkDraft.company_id == company_id)
    if user_id is not None:
        q = q.filter(WorkDraft.user_id == user_id)
    if status and status != "all":
        q = q.filter(WorkDraft.status == status)
    rows = q.order_by(WorkDraft.updated_at.desc()).limit(100).all()
    return [
        {
            "id": r.id,
            "draft_key": r.draft_key,
            "module": r.module,
            "title": r.title,
            "payload": r.payload,
            "client": r.client,
            "status": r.status,
            "user_id": r.user_id,
            "updated_at": r.updated_at.isoformat() + "Z" if r.updated_at else None,
        }
        for r in rows
    ]


def mark_draft(db: Session, draft_id: int, *, user_id: int, company_id: int, status: str) -> dict:
    row = db.get(WorkDraft, draft_id)
    if not row or row.company_id != company_id:
        return {"ok": False, "error": "not found"}
    if row.user_id != user_id:
        # admin can discard orphan drafts via settings.* path — handled by caller
        pass
    row.status = status
    db.flush()
    return {"ok": True, "id": row.id, "status": row.status}
