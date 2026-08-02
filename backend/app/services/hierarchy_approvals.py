"""
Hierarchy + emergency approval engine.

Every department/module can require approval before data becomes final.
Emergency path: escalate directly to admin / highest authorised level (bypass chain).
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models import ApprovalRequest, Notification, SyncState, User

HIER_KEY = "approval.hierarchy"
CTRL_KEY = "approval.module_controls"

# Higher number = more authority
DEFAULT_CONTROLS: dict[str, dict[str, Any]] = {
    "sales": {"enabled": True, "label": "Sales orders / high value", "threshold": 500000, "min_level": 2, "dept": "sales"},
    "purchase": {"enabled": True, "label": "Purchase / vendor pay", "threshold": 100000, "min_level": 2, "dept": "purchase"},
    "credit_note": {"enabled": True, "label": "Sales credit notes", "threshold": 10000, "min_level": 2, "dept": "sales"},
    "inventory": {"enabled": True, "label": "Stock adjust / transfer", "threshold": 0, "min_level": 2, "dept": "inventory"},
    "hrms_expense": {"enabled": True, "label": "Expense claims", "threshold": 5000, "min_level": 2, "dept": "hrms"},
    "hrms_leave": {"enabled": True, "label": "Leave requests", "threshold": 0, "min_level": 2, "dept": "hrms"},
    "payroll": {"enabled": True, "label": "Payroll run / disburse", "threshold": 0, "min_level": 3, "dept": "hrms"},
    "accounting": {"enabled": True, "label": "Journals / period lock", "threshold": 0, "min_level": 3, "dept": "accounts"},
    "crm": {"enabled": False, "label": "CRM lead/quote (optional)", "threshold": 0, "min_level": 2, "dept": "sales"},
    "logistics": {"enabled": True, "label": "Dispatch / e-way", "threshold": 0, "min_level": 2, "dept": "logistics"},
    "pricing": {"enabled": True, "label": "Dealer pricing changes", "threshold": 0, "min_level": 3, "dept": "sales"},
    "automation": {"enabled": True, "label": "WA bulk / rules", "threshold": 0, "min_level": 3, "dept": "ops"},
}


def _row(db: Session, key: str, company_id: int) -> SyncState:
    full = f"{key}.{company_id}"
    row = db.query(SyncState).filter(SyncState.key == full).first()
    if not row:
        row = SyncState(key=full, value={})
        db.add(row)
        db.flush()
    return row


def get_module_controls(db: Session, company_id: int) -> dict[str, Any]:
    row = _row(db, CTRL_KEY, company_id)
    merged = {k: {**v} for k, v in DEFAULT_CONTROLS.items()}
    for k, v in (row.value or {}).items():
        if k in merged and isinstance(v, dict):
            merged[k].update(v)
        elif isinstance(v, dict):
            merged[k] = v
    return merged


def set_module_controls(db: Session, company_id: int, controls: dict[str, Any]) -> dict[str, Any]:
    row = _row(db, CTRL_KEY, company_id)
    cur = dict(row.value or {})
    for k, v in (controls or {}).items():
        if not isinstance(v, dict):
            continue
        cur[k] = {**(cur.get(k) or {}), **v}
    row.value = cur
    db.flush()
    return get_module_controls(db, company_id)


def get_user_level(db: Session, company_id: int, user: User) -> int:
    if getattr(user, "is_superadmin", False):
        return 5
    row = _row(db, HIER_KEY, company_id)
    levels = dict((row.value or {}).get("users") or {})
    entry = levels.get(str(user.id)) or {}
    if entry.get("level") is not None:
        return int(entry["level"])
    # role-based fallback
    return 3 if user.role_id else 1


def set_user_level(
    db: Session,
    company_id: int,
    *,
    user_id: int,
    level: int,
    dept: str = "",
    title: str = "",
) -> dict[str, Any]:
    if level < 1 or level > 5:
        raise HTTPException(400, "approval level must be 1–5 (5 = admin/highest)")
    row = _row(db, HIER_KEY, company_id)
    val = dict(row.value or {})
    users = dict(val.get("users") or {})
    users[str(user_id)] = {
        "level": level,
        "dept": dept or "",
        "title": title or "",
        "updated_at": datetime.utcnow().isoformat() + "Z",
    }
    val["users"] = users
    row.value = val
    db.flush()
    return users[str(user_id)]


def hierarchy_snapshot(db: Session, company_id: int) -> dict[str, Any]:
    row = _row(db, HIER_KEY, company_id)
    users_cfg = dict((row.value or {}).get("users") or {})
    users = db.query(User).filter(User.company_id == company_id, User.is_active == True).all()  # noqa: E712
    out = []
    for u in users:
        cfg = users_cfg.get(str(u.id)) or {}
        lvl = 5 if u.is_superadmin else int(cfg.get("level") or (3 if u.role_id else 1))
        out.append(
            {
                "user_id": u.id,
                "email": u.email,
                "full_name": u.full_name,
                "level": lvl,
                "dept": cfg.get("dept") or "",
                "title": cfg.get("title") or ("Superadmin" if u.is_superadmin else ""),
                "is_superadmin": bool(u.is_superadmin),
            }
        )
    out.sort(key=lambda x: (-x["level"], x["full_name"]))
    return {
        "levels": [
            {"level": 1, "name": "Executive / Entry"},
            {"level": 2, "name": "Team Lead / Manager"},
            {"level": 3, "name": "Dept Head"},
            {"level": 4, "name": "Director / CXO"},
            {"level": 5, "name": "Admin / Highest authority"},
        ],
        "users": out,
        "module_controls": get_module_controls(db, company_id),
        "note": (
            "Lower levels submit → pending until approver ≥ required level. "
            "Emergency: escalate straight to level 5 / admin — bypass intermediate, work na ruke."
        ),
    }


def needs_approval(db: Session, company_id: int, module: str, amount: float = 0) -> tuple[bool, int]:
    ctrl = get_module_controls(db, company_id).get(module) or {}
    if not ctrl.get("enabled"):
        return False, 0
    thr = float(ctrl.get("threshold") or 0)
    min_lvl = int(ctrl.get("min_level") or 2)
    if amount >= thr or thr <= 0:
        return True, min_lvl
    return False, 0


def submit_approval(
    db: Session,
    *,
    company_id: int,
    requester: User,
    module: str,
    entity_type: str,
    entity_id: str,
    title: str,
    amount: float = 0,
    payload: dict | None = None,
    emergency: bool = False,
    emergency_reason: str = "",
) -> ApprovalRequest:
    ctrl = get_module_controls(db, company_id).get(module) or DEFAULT_CONTROLS.get(module) or {}
    need, min_lvl = needs_approval(db, company_id, module, amount)
    if emergency:
        need = True
        min_lvl = 5
    elif not need:
        # still allow voluntary submit
        min_lvl = int(ctrl.get("min_level") or 2)

    req_level = get_user_level(db, company_id, requester)
    # If requester already high enough and not emergency, auto-approve
    if not emergency and req_level >= min_lvl and need:
        row = ApprovalRequest(
            company_id=company_id,
            module=module,
            entity_type=entity_type,
            entity_id=str(entity_id),
            title=title[:200],
            amount=float(amount or 0),
            payload=payload or {},
            status="approved",
            requested_by=requester.id,
            required_level=min_lvl,
            current_level=req_level,
            emergency=False,
            decided_by=requester.id,
            decided_at=datetime.utcnow().isoformat() + "Z",
            decision_note="Auto-approved — requester level ≥ required",
        )
        db.add(row)
        db.flush()
        return row

    row = ApprovalRequest(
        company_id=company_id,
        module=module,
        entity_type=entity_type,
        entity_id=str(entity_id),
        title=title[:200],
        amount=float(amount or 0),
        payload=payload or {},
        status="pending",
        requested_by=requester.id,
        required_level=5 if emergency else min_lvl,
        current_level=req_level,
        emergency=bool(emergency),
        emergency_reason=(emergency_reason or "")[:400],
        decision_note="",
    )
    db.add(row)
    db.flush()

    # Notify eligible approvers
    snap = hierarchy_snapshot(db, company_id)
    target = 5 if emergency else min_lvl
    for u in snap["users"]:
        if u["level"] >= target and u["user_id"] != requester.id:
            db.add(
                Notification(
                    company_id=company_id,
                    user_id=u["user_id"],
                    title="🚨 Emergency approval" if emergency else "Approval needed",
                    body=f"{title} · {module} · ₹{amount:,.0f}"[:240],
                )
            )
    return row


def decide_approval(
    db: Session,
    *,
    company_id: int,
    request_id: int,
    decider: User,
    approve: bool,
    note: str = "",
) -> ApprovalRequest:
    row = (
        db.query(ApprovalRequest)
        .filter(ApprovalRequest.id == request_id, ApprovalRequest.company_id == company_id)
        .first()
    )
    if not row:
        raise HTTPException(404, "Approval request not found")
    if row.status not in ("pending",):
        raise HTTPException(400, f"Already {row.status}")
    lvl = get_user_level(db, company_id, decider)
    need = 5 if row.emergency else int(row.required_level or 2)
    if lvl < need and not getattr(decider, "is_superadmin", False):
        raise HTTPException(403, f"Need approval level ≥ {need} (yours is {lvl})")
    row.status = "emergency_approved" if (approve and row.emergency) else ("approved" if approve else "rejected")
    row.decided_by = decider.id
    row.decided_at = datetime.utcnow().isoformat() + "Z"
    row.decision_note = (note or "")[:400]
    row.current_level = lvl
    db.flush()
    if row.requested_by:
        db.add(
            Notification(
                company_id=company_id,
                user_id=row.requested_by,
                title=f"Approval {row.status}",
                body=f"{row.title} → {row.status}",
            )
        )
    return row


def list_approvals(
    db: Session,
    company_id: int,
    *,
    status: str | None = None,
    mine_user_id: int | None = None,
    inbox_for: User | None = None,
) -> list[ApprovalRequest]:
    q = db.query(ApprovalRequest).filter(ApprovalRequest.company_id == company_id)
    if status:
        q = q.filter(ApprovalRequest.status == status)
    if mine_user_id:
        q = q.filter(ApprovalRequest.requested_by == mine_user_id)
    rows = q.order_by(ApprovalRequest.id.desc()).limit(200).all()
    if inbox_for is not None:
        lvl = get_user_level(db, company_id, inbox_for)
        filtered = []
        for r in rows:
            if r.status != "pending":
                continue
            need = 5 if r.emergency else int(r.required_level or 2)
            if lvl >= need or getattr(inbox_for, "is_superadmin", False):
                filtered.append(r)
        return filtered
    return rows


def pending_blocks_entity(db: Session, company_id: int, entity_type: str, entity_id: str) -> ApprovalRequest | None:
    return (
        db.query(ApprovalRequest)
        .filter(
            ApprovalRequest.company_id == company_id,
            ApprovalRequest.entity_type == entity_type,
            ApprovalRequest.entity_id == str(entity_id),
            ApprovalRequest.status == "pending",
        )
        .order_by(ApprovalRequest.id.desc())
        .first()
    )
