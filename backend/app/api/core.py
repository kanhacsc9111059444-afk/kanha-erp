from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.deps import CurrentUser, DbDep, assert_perm, audit
from app.core.modules import ALL_MODULES, canonicalize_modules_enabled, default_modules_enabled
from app.core.rate_limit import check_login_rate_limit, validate_password_strength
from app.core.security import create_access_token, hash_password, verify_password
from app.models import (
    AuditLog,
    Company,
    CustomField,
    Notification,
    Role,
    User,
    Workflow,
)
from app.services.backup import backup_sqlite

router = APIRouter(prefix="/api", tags=["core"])


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict[str, Any]


@router.post("/auth/login", response_model=TokenOut)
def login(body: LoginIn, request: Request, db: DbDep) -> dict:
    check_login_rate_limit(request)
    user = db.query(User).filter(User.email == body.email.lower()).first()
    if not user or not verify_password(body.password, user.password_hash):
        # Track failed attempts so admin can see who/when tried
        suspect = user or db.query(User).filter(User.email == body.email.lower()).first()
        audit(
            db,
            company_id=suspect.company_id if suspect else None,
            user_id=None,
            action="login_failed",
            entity="user",
            entity_id=(body.email or "").lower()[:64],
            detail={"email": (body.email or "").lower(), "reason": "invalid_credentials"},
            request=request,
        )
        db.commit()
        raise HTTPException(status_code=401, detail="Invalid email or password")
    company = db.get(Company, user.company_id)
    role = db.get(Role, user.role_id) if user.role_id else None
    token = create_access_token(
        user.email,
        {
            "company_id": user.company_id,
            "uid": user.id,
            "se": int(getattr(user, "session_epoch", 0) or 0),
        },
    )
    audit(
        db,
        company_id=user.company_id,
        user_id=user.id,
        action="login",
        entity="user",
        entity_id=str(user.id),
        detail={
            "email": user.email,
            "name": user.full_name,
            "role": role.code if role else ("superadmin" if user.is_superadmin else ""),
        },
        request=request,
    )
    db.commit()
    weak = body.password in {"admin123", "sales123"} and settings.is_production
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "company_id": user.company_id,
            "company_name": company.name if company else "",
            "theme": user.theme,
            "ui_prefs": getattr(user, "ui_prefs", None) or {},
            "is_superadmin": user.is_superadmin,
            "role": {"code": role.code, "name": role.name, "permissions": role.permissions} if role else None,
            "must_change_password": weak,
        },
    }


class PasswordChangeIn(BaseModel):
    current_password: str
    new_password: str


@router.post("/auth/change-password")
def change_password(body: PasswordChangeIn, user: CurrentUser, db: DbDep) -> dict:
    row = db.get(User, user.id)
    if not row or not verify_password(body.current_password, row.password_hash):
        raise HTTPException(400, "Current password incorrect")
    validate_password_strength(body.new_password)
    row.password_hash = hash_password(body.new_password)
    audit(db, company_id=user.company_id, user_id=user.id, action="change_password", entity="user")
    db.commit()
    return {"ok": True, "message": "Password updated"}


def _brand_payload(company: Company | None = None) -> dict:
    wl = {}
    if company and isinstance(company.settings_json, dict):
        wl = (company.settings_json or {}).get("white_label") or {}
    return {
        "app_name": wl.get("app_name") or settings.app_name,
        "tagline": wl.get("tagline") or settings.brand_tagline,
        "logo_url": wl.get("logo_url") or settings.brand_logo_url,
        "primary": wl.get("primary") or settings.brand_primary,
        "accent": wl.get("accent") or settings.brand_accent,
        "support_email": wl.get("support_email") or settings.brand_support_email,
        "company_name": company.name if company else settings.company_name,
        "company_gstin": company.gstin if company else settings.company_gstin,
        "white_label_ready": True,
    }


@router.get("/brand/public")
def brand_public(db: DbDep) -> dict:
    company = db.query(Company).first()
    return _brand_payload(company)


@router.get("/brand")
def brand_get(user: CurrentUser, db: DbDep) -> dict:
    company = db.get(Company, user.company_id)
    return _brand_payload(company)


class BrandIn(BaseModel):
    app_name: str | None = None
    tagline: str | None = None
    logo_url: str | None = None
    primary: str | None = None
    accent: str | None = None
    support_email: str | None = None
    company_name: str | None = None
    company_gstin: str | None = None


@router.put("/brand")
def brand_put(body: BrandIn, user: CurrentUser, db: DbDep) -> dict:
    assert_perm(user, db, "settings.*")
    company = db.get(Company, user.company_id)
    if not company:
        raise HTTPException(404, "Company not found")
    settings_json = dict(company.settings_json or {})
    wl = dict(settings_json.get("white_label") or {})
    data = body.model_dump(exclude_none=True)
    if "company_name" in data:
        company.name = data.pop("company_name")
    if "company_gstin" in data:
        company.gstin = data.pop("company_gstin")
    wl.update(data)
    settings_json["white_label"] = wl
    company.settings_json = settings_json
    audit(db, company_id=user.company_id, user_id=user.id, action="update", entity="brand")
    db.commit()
    return _brand_payload(company)


@router.post("/ops/backup")
def ops_backup(user: CurrentUser, db: DbDep) -> dict:
    assert_perm(user, db, "settings.*")
    result = backup_sqlite()
    audit(db, company_id=user.company_id, user_id=user.id, action="backup", entity="database", detail=result)
    db.commit()
    return result


@router.get("/ops/modules-overview")
def ops_modules_overview(user: CurrentUser, db: DbDep) -> dict:
    """What each module contains (counts) â€” for complete module pages + go-live purge UI."""
    assert_perm(user, db, "settings.*", "dashboard.*", "reports.*")
    from app.services.demo_purge import module_overview

    return module_overview(db, user.company_id)


class PurgeDemoIn(BaseModel):
    confirm: str = Field(..., description='Must be exactly: DELETE DEMO SAMPLE')


@router.post("/ops/purge-demo")
def ops_purge_demo(body: PurgeDemoIn, user: CurrentUser, db: DbDep) -> dict:
    """
    One-click wipe of sample/demo transactional data.
    HARD BLOCKED when DEMO_MODE=false (live) â€” real data never mass-deleted here.
    """
    assert_perm(user, db, "settings.*")
    from app.services.demo_purge import purge_demo_data

    result = purge_demo_data(db, user.company_id, confirm=body.confirm)
    if result.get("blocked"):
        raise HTTPException(403, detail=result.get("error") or "Purge blocked")
    if not result.get("ok"):
        raise HTTPException(400, detail=result.get("error") or "Purge failed")
    audit(
        db,
        company_id=user.company_id,
        user_id=user.id,
        action="purge_demo",
        entity="database",
        detail={"total_rows": result.get("total_rows"), "deleted_keys": list((result.get("deleted") or {}).keys())},
    )
    db.commit()
    return result


@router.get("/auth/me")
def me(user: CurrentUser, db: DbDep) -> dict:
    company = db.get(Company, user.company_id)
    role = db.get(Role, user.role_id) if user.role_id else None
    return {
        "id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "company_id": user.company_id,
        "company": {
            "id": company.id if company else None,
            "name": company.name if company else None,
            "code": company.code if company else None,
            "currency": company.currency if company else "INR",
            "modules_enabled": (company.modules_enabled if company else default_modules_enabled()),
        },
        "role": {"code": role.code, "name": role.name, "permissions": role.permissions} if role else None,
        "theme": user.theme,
        "ui_prefs": getattr(user, "ui_prefs", None) or {},
        "is_superadmin": user.is_superadmin,
    }


@router.get("/modules")
def list_modules(user: CurrentUser, db: DbDep) -> dict:
    company = db.get(Company, user.company_id)
    enabled = canonicalize_modules_enabled(
        (company.modules_enabled if company else default_modules_enabled()) or {}
    )
    items = []
    seen_names: set[str] = set()
    for key, meta in ALL_MODULES.items():
        name = str(meta.get("name") or key)
        # Never list two modules with the same sidebar label
        if name.lower() in seen_names:
            continue
        seen_names.add(name.lower())
        items.append(
            {
                "key": key,
                **meta,
                "enabled": bool(enabled.get(key, True)),
            }
        )
    return {"modules": items}


class ModulesUpdate(BaseModel):
    modules: dict[str, bool]


@router.put("/modules")
def update_modules(body: ModulesUpdate, user: CurrentUser, db: DbDep) -> dict:
    assert_perm(user, db, "settings.*")
    company = db.get(Company, user.company_id)
    if not company:
        raise HTTPException(404, "Company not found")
    company.modules_enabled = canonicalize_modules_enabled({**default_modules_enabled(), **body.modules})
    audit(db, company_id=user.company_id, user_id=user.id, action="update", entity="modules")
    db.commit()
    return {"ok": True, "modules_enabled": company.modules_enabled}


@router.get("/custom-fields")
def custom_fields(user: CurrentUser, db: DbDep, entity: str | None = None) -> list:
    q = db.query(CustomField).filter(CustomField.company_id == user.company_id)
    if entity:
        q = q.filter(CustomField.entity == entity)
    rows = q.order_by(CustomField.sort_order).all()
    return [
        {
            "id": r.id,
            "entity": r.entity,
            "field_key": r.field_key,
            "label": r.label,
            "field_type": r.field_type,
            "required": r.required,
            "options": r.options,
            "sort_order": r.sort_order,
        }
        for r in rows
    ]


class CustomFieldIn(BaseModel):
    entity: str
    field_key: str
    label: str
    field_type: str = "text"
    required: bool = False
    options: list[Any] = Field(default_factory=list)
    sort_order: int = 0


@router.post("/custom-fields")
def create_custom_field(body: CustomFieldIn, user: CurrentUser, db: DbDep) -> dict:
    row = CustomField(company_id=user.company_id, **body.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return {"id": row.id, **body.model_dump()}


@router.get("/roles")
def roles(user: CurrentUser, db: DbDep) -> list:
    rows = db.query(Role).filter(Role.company_id == user.company_id).all()
    return [{"id": r.id, "code": r.code, "name": r.name, "permissions": r.permissions} for r in rows]


@router.get("/users")
def list_users(user: CurrentUser, db: DbDep) -> list:
    rows = db.query(User).filter(User.company_id == user.company_id).all()
    out = []
    for u in rows:
        role = db.get(Role, u.role_id) if u.role_id else None
        out.append(
            {
                "id": u.id,
                "email": u.email,
                "full_name": u.full_name,
                "role_id": u.role_id,
                "role_code": role.code if role else None,
                "role_name": role.name if role else None,
                "is_active": u.is_active,
                "is_superadmin": u.is_superadmin,
            }
        )
    return out


class UserIn(BaseModel):
    email: EmailStr
    full_name: str
    password: str = "Welcome@123"
    role_id: int | None = None


@router.post("/users")
def create_user(body: UserIn, user: CurrentUser, db: DbDep) -> dict:
    assert_perm(user, db, "settings.*")
    from app.core.rate_limit import validate_password_strength

    validate_password_strength(body.password)
    exists = db.query(User).filter(User.email == body.email.lower()).first()
    if exists:
        raise HTTPException(400, "Email already exists")
    row = User(
        company_id=user.company_id,
        email=body.email.lower(),
        full_name=body.full_name,
        password_hash=hash_password(body.password),
        role_id=body.role_id or user.role_id,
        is_active=True,
    )
    db.add(row)
    audit(db, company_id=user.company_id, user_id=user.id, action="create", entity="user", entity_id=body.email)
    db.commit()
    db.refresh(row)
    return {"id": row.id, "email": row.email, "full_name": row.full_name}


class UserPatch(BaseModel):
    is_active: bool | None = None
    role_id: int | None = None
    full_name: str | None = None


@router.put("/users/{user_id}")
def update_user(user_id: int, body: UserPatch, user: CurrentUser, db: DbDep) -> dict:
    assert_perm(user, db, "settings.*")
    row = db.query(User).filter(User.id == user_id, User.company_id == user.company_id).first()
    if not row:
        raise HTTPException(404, "User not found")
    if body.is_active is not None:
        row.is_active = body.is_active
    if body.role_id is not None:
        row.role_id = body.role_id
    if body.full_name is not None:
        row.full_name = body.full_name
    audit(db, company_id=user.company_id, user_id=user.id, action="update", entity="user", entity_id=str(user_id))
    db.commit()
    return {"ok": True}


@router.get("/workflows")
def workflows(user: CurrentUser, db: DbDep) -> list:
    rows = db.query(Workflow).filter(Workflow.company_id == user.company_id).all()
    return [
        {"id": r.id, "name": r.name, "entity": r.entity, "steps": r.steps, "active": r.active}
        for r in rows
    ]


# â”€â”€ Hierarchy approvals (dept control + emergency bypass) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€


@router.get("/approvals/hierarchy")
def approvals_hierarchy(user: CurrentUser, db: DbDep) -> dict:
    from app.services.hierarchy_approvals import get_user_level, hierarchy_snapshot

    snap = hierarchy_snapshot(db, user.company_id)
    snap["my_level"] = get_user_level(db, user.company_id, user)
    return snap


class UserLevelIn(BaseModel):
    user_id: int
    level: int
    dept: str = ""
    title: str = ""


@router.post("/approvals/hierarchy/user")
def approvals_set_user_level(body: UserLevelIn, user: CurrentUser, db: DbDep) -> dict:
    assert_perm(user, db, "settings.*")
    from app.services.hierarchy_approvals import set_user_level

    entry = set_user_level(
        db, user.company_id, user_id=body.user_id, level=body.level, dept=body.dept, title=body.title
    )
    audit(db, company_id=user.company_id, user_id=user.id, action="hierarchy", entity="user", entity_id=str(body.user_id), detail=entry)
    db.commit()
    return {"ok": True, "user_id": body.user_id, "level": entry}


class ModuleControlIn(BaseModel):
    controls: dict[str, Any]


@router.post("/approvals/module-controls")
def approvals_set_controls(body: ModuleControlIn, user: CurrentUser, db: DbDep) -> dict:
    assert_perm(user, db, "settings.*")
    from app.services.hierarchy_approvals import set_module_controls

    ctrls = set_module_controls(db, user.company_id, body.controls)
    db.commit()
    return {"ok": True, "module_controls": ctrls}


@router.get("/approvals")
def approvals_list(user: CurrentUser, db: DbDep, status: str | None = None, inbox: bool = False) -> dict:
    from app.services.hierarchy_approvals import get_user_level, list_approvals

    rows = list_approvals(
        db,
        user.company_id,
        status=status,
        inbox_for=user if inbox else None,
    )
    users = {u.id: u.full_name for u in db.query(User).filter(User.company_id == user.company_id).all()}
    return {
        "my_level": get_user_level(db, user.company_id, user),
        "items": [
            {
                "id": r.id,
                "module": r.module,
                "entity_type": r.entity_type,
                "entity_id": r.entity_id,
                "title": r.title,
                "amount": r.amount,
                "status": r.status,
                "required_level": r.required_level,
                "emergency": r.emergency,
                "emergency_reason": r.emergency_reason,
                "requested_by": r.requested_by,
                "requested_by_name": users.get(r.requested_by or 0, "â€”"),
                "decided_by": r.decided_by,
                "decided_by_name": users.get(r.decided_by or 0, "â€”") if r.decided_by else None,
                "decided_at": r.decided_at,
                "decision_note": r.decision_note,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ],
    }


class ApprovalSubmitIn(BaseModel):
    module: str
    entity_type: str
    entity_id: str
    title: str
    amount: float = 0
    payload: dict[str, Any] = Field(default_factory=dict)
    emergency: bool = False
    emergency_reason: str = ""


@router.post("/approvals/submit")
def approvals_submit(body: ApprovalSubmitIn, user: CurrentUser, db: DbDep) -> dict:
    from app.services.hierarchy_approvals import submit_approval

    row = submit_approval(
        db,
        company_id=user.company_id,
        requester=user,
        module=body.module,
        entity_type=body.entity_type,
        entity_id=body.entity_id,
        title=body.title,
        amount=body.amount,
        payload=body.payload,
        emergency=body.emergency,
        emergency_reason=body.emergency_reason,
    )
    db.commit()
    db.refresh(row)
    return {
        "id": row.id,
        "status": row.status,
        "emergency": row.emergency,
        "required_level": row.required_level,
        "message": (
            f"ðŸš¨ Emergency sent to admin/L{row.required_level}"
            if row.emergency and row.status == "pending"
            else f"Approval {row.status} Â· need L{row.required_level}+"
        ),
    }


class ApprovalDecideIn(BaseModel):
    approve: bool = True
    note: str = ""


@router.post("/approvals/{request_id}/decide")
def approvals_decide(request_id: int, body: ApprovalDecideIn, user: CurrentUser, db: DbDep) -> dict:
    from app.services.hierarchy_approvals import decide_approval

    row = decide_approval(
        db,
        company_id=user.company_id,
        request_id=request_id,
        decider=user,
        approve=body.approve,
        note=body.note,
    )
    # Mirror sales SO approve/reject when entity is sales_order
    if row.entity_type == "sales_order" and row.status in ("approved", "emergency_approved", "rejected"):
        from app.models import SalesOrder

        so = db.query(SalesOrder).filter(SalesOrder.id == int(row.entity_id), SalesOrder.company_id == user.company_id).first()
        if so:
            if row.status == "rejected":
                so.approval_status = "rejected"
                so.status = "cancelled"
            else:
                so.approval_status = "approved"
    audit(
        db,
        company_id=user.company_id,
        user_id=user.id,
        action="approval_decide",
        entity="approval",
        entity_id=str(row.id),
        detail={"status": row.status, "module": row.module},
    )
    db.commit()
    return {"id": row.id, "status": row.status, "message": f"Request #{row.id} â†’ {row.status}"}


@router.get("/notifications")
def notifications(user: CurrentUser, db: DbDep) -> list:
    rows = (
        db.query(Notification)
        .filter(Notification.company_id == user.company_id)
        .order_by(Notification.id.desc())
        .limit(50)
        .all()
    )
    return [
        {
            "id": n.id,
            "title": n.title,
            "body": n.body,
            "read": n.read,
            "created_at": n.created_at.isoformat() if n.created_at else None,
        }
        for n in rows
    ]


@router.post("/notifications/{notification_id}/read")
def mark_notification_read(notification_id: int, user: CurrentUser, db: DbDep) -> dict:
    row = (
        db.query(Notification)
        .filter(Notification.id == notification_id, Notification.company_id == user.company_id)
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Notification not found")
    row.read = True
    db.commit()
    return {"ok": True, "id": row.id}


@router.get("/audit")
def audit_logs(user: CurrentUser, db: DbDep, limit: int = 50) -> list:
    """Legacy compact audit list — prefer /api/activity for who/when/what."""
    rows = (
        db.query(AuditLog)
        .filter(AuditLog.company_id == user.company_id)
        .order_by(AuditLog.id.desc())
        .limit(min(limit, 200))
        .all()
    )
    users = {u.id: u for u in db.query(User).filter(User.company_id == user.company_id).all()}
    out = []
    for a in rows:
        u = users.get(a.user_id) if a.user_id else None
        detail = a.detail if isinstance(a.detail, dict) else {}
        if isinstance(a.detail, str):
            try:
                import json

                detail = json.loads(a.detail)
                if not isinstance(detail, dict):
                    detail = {}
            except Exception:
                detail = {}
        out.append(
            {
                "id": a.id,
                "action": a.action,
                "entity": a.entity,
                "entity_id": a.entity_id,
                "detail": detail,
                "user_id": a.user_id,
                "user_name": u.full_name if u else detail.get("name") or detail.get("email") or "—",
                "user_email": u.email if u else detail.get("email") or "",
                "ip": detail.get("ip") or "",
                "created_at": a.created_at.isoformat() if a.created_at else None,
            }
        )
    return out


_ACTION_LABELS = {
    "login": "Logged in",
    "login_failed": "Login failed",
    "logout": "Logged out",
    "page": "Opened screen",
    "create": "Created",
    "update": "Updated",
    "delete": "Deleted",
    "pos_checkout": "POS checkout",
    "books_voucher": "Posted voucher",
    "books_reverse": "Reversed voucher",
    "vendor_payment": "Vendor payment",
    "change_password": "Changed password",
    "revoke_sessions": "Revoked sessions",
    "backup": "Database backup",
    "whatsapp_send": "WhatsApp send",
    "einvoice": "E-Invoice",
    "dispatch": "Dispatch",
    "upload": "Uploaded document",
}


def _as_detail(raw) -> dict:
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str) and raw.strip():
        try:
            import json

            parsed = json.loads(raw)
            return parsed if isinstance(parsed, dict) else {"raw": raw}
        except Exception:
            return {"raw": raw}
    return {}


def _activity_summary(action: str, entity: str, entity_id: str | None, detail: dict | None) -> str:
    d = _as_detail(detail)
    label = _ACTION_LABELS.get(action, action.replace("_", " ").title())
    if action == "page":
        return f"Opened {d.get('title') or d.get('route') or entity_id or 'screen'}"
    if action == "login":
        return f"Login · {d.get('email') or ''}".strip(" ·")
    if action == "login_failed":
        return f"Failed login · {d.get('email') or entity_id or ''}"
    bits = [label]
    if entity and entity not in ("user", "ui"):
        bits.append(entity)
    if entity_id:
        bits.append(str(entity_id))
    return " · ".join(x for x in bits if x)


@router.get("/activity")
def activity_timeline(
    user: CurrentUser,
    db: DbDep,
    limit: int = 100,
    action: str | None = None,
    user_id: int | None = None,
    q: str | None = None,
) -> dict:
    """Who did what / when — full activity desk for issue tracing."""
    assert_perm(user, db, "settings.*", "approvals.*")
    lim = min(max(int(limit or 100), 1), 500)
    qry = db.query(AuditLog).filter(AuditLog.company_id == user.company_id)
    if action:
        qry = qry.filter(AuditLog.action == action)
    if user_id:
        qry = qry.filter(AuditLog.user_id == user_id)
    rows = qry.order_by(AuditLog.id.desc()).limit(lim).all()
    users = {u.id: u for u in db.query(User).filter(User.company_id == user.company_id).all()}
    items = []
    for a in rows:
        u = users.get(a.user_id) if a.user_id else None
        detail = _as_detail(a.detail)
        summary = _activity_summary(a.action, a.entity, a.entity_id, detail)
        if q:
            blob = f"{summary} {u.full_name if u else ''} {u.email if u else ''} {a.action} {a.entity}".lower()
            if q.lower() not in blob:
                continue
        items.append(
            {
                "id": a.id,
                "when": a.created_at.isoformat() if a.created_at else None,
                "user_id": a.user_id,
                "user_name": u.full_name if u else detail.get("name") or "Unknown / failed",
                "user_email": u.email if u else detail.get("email") or "",
                "action": a.action,
                "entity": a.entity,
                "entity_id": a.entity_id,
                "summary": summary,
                "ip": detail.get("ip") or "",
                "ua": detail.get("ua") or "",
                "detail": detail,
            }
        )
    # Login pulse today
    from datetime import datetime, timedelta

    since = datetime.utcnow() - timedelta(hours=24)
    day_rows = (
        db.query(AuditLog)
        .filter(
            AuditLog.company_id == user.company_id,
            AuditLog.action.in_(["login", "login_failed", "page"]),
            AuditLog.created_at >= since,
        )
        .all()
    )
    logins_ok = sum(1 for r in day_rows if r.action == "login")
    logins_fail = sum(1 for r in day_rows if r.action == "login_failed")
    pages = sum(1 for r in day_rows if r.action == "page")
    by_user: dict[int, dict] = {}
    for r in day_rows:
        if r.action != "login" or not r.user_id:
            continue
        u = users.get(r.user_id)
        slot = by_user.setdefault(
            r.user_id,
            {"user_id": r.user_id, "user_name": u.full_name if u else "?", "user_email": u.email if u else "", "logins": 0, "last_login": None},
        )
        slot["logins"] += 1
        ts = r.created_at.isoformat() if r.created_at else None
        if not slot["last_login"] or (ts and ts > slot["last_login"]):
            slot["last_login"] = ts
    return {
        "ok": True,
        "count": len(items),
        "items": items,
        "pulse_24h": {
            "logins": logins_ok,
            "login_failed": logins_fail,
            "page_views": pages,
            "active_users": len(by_user),
        },
        "logins_24h": sorted(by_user.values(), key=lambda x: x.get("last_login") or "", reverse=True),
        "note": "Track who logged in, which screen they opened, and what they saved — for issue tracing.",
    }


class PageActivityIn(BaseModel):
    route: str = Field(min_length=1, max_length=80)
    title: str = ""


@router.post("/activity/page")
def activity_page(body: PageActivityIn, request: Request, user: CurrentUser, db: DbDep) -> dict:
    """SPA screen open — throttled so refresh spam doesn't flood the log."""
    from datetime import datetime, timedelta

    route = (body.route or "").strip().lstrip("#/")[:80]
    if not route:
        raise HTTPException(400, "route required")
    since = datetime.utcnow() - timedelta(seconds=45)
    recent = (
        db.query(AuditLog)
        .filter(
            AuditLog.company_id == user.company_id,
            AuditLog.user_id == user.id,
            AuditLog.action == "page",
            AuditLog.entity_id == route,
            AuditLog.created_at >= since,
        )
        .first()
    )
    if recent:
        return {"ok": True, "skipped": True, "id": recent.id}
    audit(
        db,
        company_id=user.company_id,
        user_id=user.id,
        action="page",
        entity="ui",
        entity_id=route,
        detail={"route": route, "title": (body.title or route)[:120], "name": user.full_name, "email": user.email},
        request=request,
    )
    db.commit()
    return {"ok": True, "skipped": False}


@router.post("/activity/logout")
def activity_logout(request: Request, user: CurrentUser, db: DbDep) -> dict:
    audit(
        db,
        company_id=user.company_id,
        user_id=user.id,
        action="logout",
        entity="user",
        entity_id=str(user.id),
        detail={"email": user.email, "name": user.full_name},
        request=request,
    )
    db.commit()
    return {"ok": True}


class ThemeIn(BaseModel):
    theme: str = "light"
    density: str | None = None  # comfortable | compact
    radius: str | None = None  # soft | sharp


ALLOWED_THEMES = {
    "light",
    "dark",
    "ocean",
    "forest",
    "sunset",
    "violet",
    "graphite",
    "sand",
}


@router.put("/auth/theme")
def set_theme(body: ThemeIn, user: CurrentUser, db: DbDep) -> dict:
    theme = (body.theme or "light").strip().lower()
    if theme not in ALLOWED_THEMES:
        theme = "light"
    user.theme = theme
    prefs = dict(getattr(user, "ui_prefs", None) or {})
    if body.density in ("comfortable", "compact"):
        prefs["density"] = body.density
    if body.radius in ("soft", "sharp"):
        prefs["radius"] = body.radius
    try:
        user.ui_prefs = prefs
    except Exception:
        pass
    db.commit()
    return {"theme": user.theme, "ui_prefs": prefs}


# â”€â”€ Server drafts + stolen-device revoke + accountability â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€


class DraftIn(BaseModel):
    draft_key: str = Field(min_length=2, max_length=120)
    payload: dict[str, Any] = Field(default_factory=dict)
    module: str = ""
    title: str = ""
    client: str = "web"


@router.get("/drafts")
def drafts_list(user: CurrentUser, db: DbDep, mine: bool = True, status: str = "open") -> dict:
    from app.services.drafts import list_drafts

    uid = user.id if mine else None
    if not mine:
        assert_perm(user, db, "settings.*", "hrms.*")
    rows = list_drafts(db, company_id=user.company_id, user_id=uid, status=status)
    return {"ok": True, "count": len(rows), "drafts": rows}


@router.put("/drafts")
def drafts_save(body: DraftIn, user: CurrentUser, db: DbDep) -> dict:
    """Autosave â€” phone/browser crash pe bhi company server pe draft."""
    from app.services.drafts import upsert_draft

    row = upsert_draft(
        db,
        company_id=user.company_id,
        user_id=user.id,
        draft_key=body.draft_key.strip(),
        payload=body.payload,
        module=body.module,
        title=body.title,
        client=body.client,
    )
    db.commit()
    return {
        "ok": True,
        "id": row.id,
        "draft_key": row.draft_key,
        "updated_at": row.updated_at.isoformat() + "Z" if row.updated_at else None,
        "message": "Draft synced to server",
    }


@router.post("/drafts/{draft_id}/submit")
def drafts_submit(draft_id: int, user: CurrentUser, db: DbDep) -> dict:
    from app.services.drafts import mark_draft

    r = mark_draft(db, draft_id, user_id=user.id, company_id=user.company_id, status="submitted")
    if not r.get("ok"):
        raise HTTPException(404, "Draft not found")
    db.commit()
    return r


@router.post("/drafts/{draft_id}/discard")
def drafts_discard(draft_id: int, user: CurrentUser, db: DbDep) -> dict:
    from app.services.drafts import mark_draft

    r = mark_draft(db, draft_id, user_id=user.id, company_id=user.company_id, status="discarded")
    if not r.get("ok"):
        raise HTTPException(404, "Draft not found")
    db.commit()
    return r


@router.post("/auth/revoke-sessions")
def revoke_my_sessions(user: CurrentUser, db: DbDep) -> dict:
    """Stolen / lost phone: invalidate ALL tokens for this user (incl. this one)."""
    row = db.get(User, user.id)
    if not row:
        raise HTTPException(404, "User not found")
    row.session_epoch = int(getattr(row, "session_epoch", 0) or 0) + 1
    audit(
        db,
        company_id=user.company_id,
        user_id=user.id,
        action="revoke_sessions",
        entity="user",
        entity_id=str(user.id),
        detail={"session_epoch": row.session_epoch},
    )
    db.commit()
    return {
        "ok": True,
        "session_epoch": row.session_epoch,
        "message": "All devices logged out. Login again on trusted device.",
    }


class RevokeUserIn(BaseModel):
    user_id: int
    reason: str = "admin_security"


@router.post("/security/revoke-user-sessions")
def revoke_user_sessions(body: RevokeUserIn, user: CurrentUser, db: DbDep) -> dict:
    """Admin: employee phone stolen â€” kill their ERP sessions everywhere."""
    assert_perm(user, db, "settings.*", "hrms.*")
    row = db.get(User, body.user_id)
    if not row or row.company_id != user.company_id:
        raise HTTPException(404, "User not found")
    row.session_epoch = int(getattr(row, "session_epoch", 0) or 0) + 1
    audit(
        db,
        company_id=user.company_id,
        user_id=user.id,
        action="revoke_sessions",
        entity="user",
        entity_id=str(row.id),
        detail={"by": user.email, "reason": body.reason, "session_epoch": row.session_epoch},
    )
    db.commit()
    return {
        "ok": True,
        "user_id": row.id,
        "email": row.email,
        "session_epoch": row.session_epoch,
        "message": f"Sessions revoked for {row.email}. Their drafts remain on server.",
    }


@router.get("/security/anomalies")
def security_anomalies(user: CurrentUser, db: DbDep, hours: int = 48) -> dict:
    assert_perm(user, db, "settings.*", "hrms.*", "reports.*")
    from app.services.accountability import scan_anomalies

    return scan_anomalies(db, user.company_id, hours=min(max(hours, 6), 168))
# --- Owner-only Core Control (ultra support - not for customers) ---


class CoreChatIn(BaseModel):
    message: str = "scan"


class CoreUnlockIn(BaseModel):
    passphrase: str = Field(min_length=1, max_length=200)


class CoreResetPasswordIn(BaseModel):
    email: EmailStr
    new_password: str = Field(min_length=8, max_length=128)


def _token_payload_for_user(db: Session, user: User) -> dict:
    company = db.get(Company, user.company_id)
    role = db.get(Role, user.role_id) if user.role_id else None
    token = create_access_token(
        user.email,
        {
            "company_id": user.company_id,
            "uid": user.id,
            "se": int(getattr(user, "session_epoch", 0) or 0),
        },
    )
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "company_id": user.company_id,
            "company_name": company.name if company else "",
            "theme": user.theme,
            "ui_prefs": getattr(user, "ui_prefs", None) or {},
            "is_superadmin": user.is_superadmin,
            "role": {"code": role.code, "name": role.name, "permissions": role.permissions} if role else None,
            "must_change_password": False,
            "core_recovery": True,
        },
    }


@router.post("/core-control/unlock", response_model=TokenOut)
def core_control_unlock(body: CoreUnlockIn, request: Request, db: DbDep) -> dict:
    """Login-page Ultra Support gate — owner master pass (or owner account password)."""
    from app.services.core_control import verify_core_unlock_passphrase

    check_login_rate_limit(request)
    user = verify_core_unlock_passphrase(db, body.passphrase)
    audit(
        db,
        company_id=user.company_id,
        user_id=user.id,
        action="core_unlock",
        entity="core_control",
        detail={"via": "login_page"},
    )
    db.commit()
    return _token_payload_for_user(db, user)


@router.post("/core-control/reset-password")
def core_control_reset_password(body: CoreResetPasswordIn, user: CurrentUser, db: DbDep) -> dict:
    from app.services.core_control import assert_core_owner, reset_user_password_by_owner

    assert_core_owner(user)
    out = reset_user_password_by_owner(
        db, user.company_id, user, email=str(body.email), new_password=body.new_password
    )
    audit(
        db,
        company_id=user.company_id,
        user_id=user.id,
        action="core_reset_password",
        entity="user",
        detail={"email": str(body.email).lower()},
    )
    db.commit()
    return out


@router.get("/core-control/access")
def core_control_access(user: CurrentUser) -> dict:
    from app.services.core_control import assert_core_owner

    try:
        assert_core_owner(user)
        return {"ok": True, "owner": True, "label": "Core Control"}
    except Exception:
        return {"ok": False, "owner": False}


@router.get("/core-control/diagnose")
def core_control_diagnose(user: CurrentUser, db: DbDep) -> dict:
    from app.services.core_control import assert_core_owner, diagnose

    assert_core_owner(user)
    return diagnose(db, user.company_id, user=user)


@router.get("/core-control/preview")
def core_control_preview(user: CurrentUser, db: DbDep) -> dict:
    from app.services.core_control import assert_core_owner, preview_fixes

    assert_core_owner(user)
    return preview_fixes(db, user.company_id, include_confirm=True, user=user)


@router.get("/core-control/full")
def core_control_full(user: CurrentUser, db: DbDep) -> dict:
    from app.services.core_control import assert_core_owner, full_strength_scan

    assert_core_owner(user)
    return full_strength_scan(db, user.company_id, user=user)


@router.get("/core-control/history")
def core_control_history(user: CurrentUser, db: DbDep) -> dict:
    from app.services.core_control import assert_core_owner, get_history

    assert_core_owner(user)
    items = get_history(db, user.company_id)
    return {"ok": True, "count": len(items), "history": items, "owner_only": True}


class AutofixIn(BaseModel):
    confirm_risky: bool = False
    run_agents: bool = True


@router.post("/core-control/autofix")
def core_control_autofix(user: CurrentUser, db: DbDep, body: AutofixIn | None = None) -> dict:
    from app.services.core_control import assert_core_owner, autofix_all

    assert_core_owner(user)
    opts = body or AutofixIn()
    result = autofix_all(db, user.company_id, user, confirm_risky=bool(opts.confirm_risky))
    if opts.run_agents and not opts.confirm_risky:
        # Agents only on safe path as additive demo helpers; skip when user is carefully confirming unlocks
        try:
            from app.api.extended import agent_compliance_run

            comp = agent_compliance_run(user, db, auto_fix=True)
            result["compliance_agent"] = {"ok": True, "message": comp.get("message"), "fixed": comp.get("fixed")}
        except Exception as e:
            result["compliance_agent"] = {"ok": False, "message": str(e)}
        try:
            from app.api.extended import agent_stock_run

            stock = agent_stock_run(user, db)
            result["stock_agent"] = {"ok": True, "message": stock.get("message")}
        except Exception as e:
            result["stock_agent"] = {"ok": False, "message": str(e)}
    audit(
        db,
        company_id=user.company_id,
        user_id=user.id,
        action="core_autofix",
        entity="core_control",
        detail={
            "before": result.get("before_score"),
            "after": result.get("after_score"),
            "confirm_risky": opts.confirm_risky,
            "skipped": len(result.get("skipped_needs_confirm") or []),
        },
    )
    db.commit()
    return result


class FixConfirmIn(BaseModel):
    confirm: bool = False


@router.post("/core-control/fix/{fix_id}")
def core_control_one_fix(fix_id: str, user: CurrentUser, db: DbDep, body: FixConfirmIn | None = None) -> dict:
    from app.services.core_control import apply_fix, assert_core_owner

    assert_core_owner(user)
    conf = bool(body.confirm) if body else False
    out = apply_fix(db, user.company_id, user, fix_id, confirm=conf)
    db.commit()
    return out


@router.post("/core-control/chat")
def core_control_chat(body: CoreChatIn, user: CurrentUser, db: DbDep) -> dict:
    from app.services.core_control import assert_core_owner, core_control_reply

    assert_core_owner(user)
    return core_control_reply(db, user.company_id, user, body.message)