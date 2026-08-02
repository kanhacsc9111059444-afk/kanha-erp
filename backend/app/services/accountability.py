"""Accountability signals — not spyware. Find waste / abuse from ERP audit trail."""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from app.models import AuditLog, User, WorkDraft


def scan_anomalies(db: Session, company_id: int, *, hours: int = 48) -> dict[str, Any]:
    since = datetime.utcnow() - timedelta(hours=hours)
    rows = (
        db.query(AuditLog)
        .filter(AuditLog.company_id == company_id, AuditLog.created_at >= since)
        .order_by(AuditLog.id.desc())
        .limit(2000)
        .all()
    )
    by_user: dict[int, list] = defaultdict(list)
    for r in rows:
        if r.user_id:
            by_user[r.user_id].append(r)

    users = {u.id: u for u in db.query(User).filter(User.company_id == company_id).all()}
    flags: list[dict] = []

    sensitive = {"backup", "export", "delete", "einvoice", "change_password", "update"}
    for uid, acts in by_user.items():
        u = users.get(uid)
        name = u.full_name if u else f"user#{uid}"
        email = u.email if u else ""

        # After-hours burst (IST-ish: UTC+5:30 → rough UTC hour 16-01 = evening/night India)
        night = [a for a in acts if a.created_at and (a.created_at.hour >= 16 or a.created_at.hour < 2)]
        if len(night) >= 25:
            flags.append(
                {
                    "severity": "medium",
                    "code": "after_hours_burst",
                    "user_id": uid,
                    "user": name,
                    "email": email,
                    "count": len(night),
                    "message": f"{name}: {len(night)} actions in late hours — review if expected shift",
                }
            )

        backups = [a for a in acts if a.action in ("backup", "export") or a.entity == "database"]
        if len(backups) >= 3:
            flags.append(
                {
                    "severity": "high",
                    "code": "data_exfil_pattern",
                    "user_id": uid,
                    "user": name,
                    "email": email,
                    "count": len(backups),
                    "message": f"{name}: {len(backups)} backup/export events — possible data siphon",
                }
            )

        deletes = [a for a in acts if "delete" in (a.action or "").lower()]
        if len(deletes) >= 10:
            flags.append(
                {
                    "severity": "high",
                    "code": "mass_delete",
                    "user_id": uid,
                    "user": name,
                    "email": email,
                    "count": len(deletes),
                    "message": f"{name}: {len(deletes)} deletes — check accidental or malicious wipe",
                }
            )

        logins = [a for a in acts if a.action == "login"]
        if len(logins) >= 20:
            flags.append(
                {
                    "severity": "medium",
                    "code": "login_churn",
                    "user_id": uid,
                    "user": name,
                    "email": email,
                    "count": len(logins),
                    "message": f"{name}: {len(logins)} logins — shared password or unstable session?",
                }
            )

        sens = [a for a in acts if a.action in sensitive]
        if len(sens) >= 40:
            flags.append(
                {
                    "severity": "medium",
                    "code": "high_volume_sensitive",
                    "user_id": uid,
                    "user": name,
                    "email": email,
                    "count": len(sens),
                    "message": f"{name}: unusually high sensitive volume ({len(sens)})",
                }
            )

    # Stale open drafts = unfinished work / abandoned entries (time waste signal, soft)
    open_drafts = (
        db.query(WorkDraft)
        .filter(WorkDraft.company_id == company_id, WorkDraft.status == "open")
        .all()
    )
    stale_cut = datetime.utcnow() - timedelta(hours=24)
    for d in open_drafts:
        if d.updated_at and d.updated_at < stale_cut:
            u = users.get(d.user_id)
            flags.append(
                {
                    "severity": "low",
                    "code": "stale_draft",
                    "user_id": d.user_id,
                    "user": u.full_name if u else f"user#{d.user_id}",
                    "email": u.email if u else "",
                    "draft_key": d.draft_key,
                    "message": f"Open draft '{d.title or d.draft_key}' untouched >24h — recover or discard",
                }
            )

    sev = {"high": 0, "medium": 0, "low": 0}
    for f in flags:
        sev[f["severity"]] = sev.get(f["severity"], 0) + 1

    return {
        "ok": True,
        "hours": hours,
        "audit_rows_scanned": len(rows),
        "open_drafts": len(open_drafts),
        "flags": sorted(flags, key=lambda x: {"high": 0, "medium": 1, "low": 2}[x["severity"]]),
        "summary": sev,
        "message": (
            "No unusual patterns in window"
            if not flags
            else f"{len(flags)} signals — review high severity first"
        ),
        "note": "These are accountability signals from ERP audit — not phone spyware.",
    }
