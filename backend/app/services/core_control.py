"""
Owner-only Core Control — ultra support agent.

SAFETY RULES (hard):
- NEVER delete business rows, purge DB, drop tables, or wipe invoices/stock/users.
- Prefer repair / unlock / mark-healed / enable modules (additive only).
- Default Autofix = SAFE fixes only.
- Risky fixes need explicit confirm + show drawbacks first.
- After each fix: re-scan; if health drops, attempt rollback of that fix.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.modules import ALL_MODULES, DEFAULT_PERMISSIONS, default_modules_enabled
from app.models import (
    ApprovalRequest,
    Company,
    Customer,
    Employee,
    FailedEntry,
    Invoice,
    JournalEntry,
    Lead,
    Product,
    PurchaseOrder,
    Role,
    SalesOrder,
    ServiceTicket,
    StockBalance,
    SyncState,
    User,
)

# Hard allowlist — nothing outside this can run
FIX_CATALOG: dict[str, dict[str, Any]] = {
    "heal_failed_entries": {
        "safety": "safe",
        "deletes": False,
        "drawbacks": [
            "Queue status becomes healed — failed write payload stays stored (not deleted).",
            "Does NOT auto-replay money/stock posts (avoids double-entry).",
        ],
        "side_effects": ["FailedEntry.heal_status updated only"],
    },
    "sync_modules": {
        "safety": "safe",
        "deletes": False,
        "drawbacks": ["Only ADDS missing module keys as enabled — never turns modules off."],
        "side_effects": ["company.modules_enabled keys added"],
    },
    "sync_admin_permissions": {
        "safety": "safe",
        "deletes": False,
        "drawbacks": [
            "Merges DEFAULT_PERMISSIONS into admin role only — never removes existing grants.",
        ],
        "side_effects": ["Role(admin).permissions additive merge"],
    },
    "ensure_owner_level": {
        "safety": "safe",
        "deletes": False,
        "drawbacks": [
            "Sets the current owner user to approval hierarchy level 5 (highest).",
            "Does not change other users' levels.",
        ],
        "side_effects": ["approval.hierarchy user level → 5"],
    },
    "refresh_salary_policy_defaults": {
        "safety": "safe",
        "deletes": False,
        "drawbacks": [
            "Adds missing salary policy keys from defaults only — never overwrites existing values.",
        ],
        "side_effects": ["hrms.salary_policy missing keys filled"],
    },
    "repair_negative_balances": {
        "safety": "safe",
        "deletes": False,
        "drawbacks": [
            "Clamps invoice.paid down to invoice.total when paid > total (data anomaly fix).",
            "Does not delete invoices or payments.",
        ],
        "side_effects": ["Invoice.paid clamped to total"],
    },
    "clear_blackout": {
        "safety": "confirm",
        "deletes": False,
        "drawbacks": [
            "Writes unlock immediately — if you wanted freeze for disaster, this ends it.",
            "Portable pack history is kept (not deleted).",
        ],
        "side_effects": ["blackout.active=false"],
    },
    "unlock_period": {
        "safety": "confirm",
        "deletes": False,
        "drawbacks": [
            "Closed months reopen for posts — books hygiene weaker until you re-lock.",
            "Does not delete journals or invoices.",
        ],
        "side_effects": ["period lock cleared"],
    },
    "approve_pending_so": {
        "safety": "confirm",
        "deletes": False,
        "drawbacks": [
            "Bypasses manager review on pending SOs — can invoice high-value orders.",
            "Does not delete/cancel orders; only sets approval_status=approved.",
        ],
        "side_effects": ["SalesOrder.approval_status=approved"],
    },
    "ensure_demo_density": {
        "safety": "confirm",
        "deletes": False,
        "drawbacks": [
            "May ADD demo rows (stock/tickets) — never deletes existing live data.",
            "Avoid on real production data unless you want seed density.",
        ],
        "side_effects": ["may insert demo completeness rows"],
    },
    "list_only": {
        "safety": "safe",
        "deletes": False,
        "drawbacks": ["No change."],
        "side_effects": [],
    },
}

FORBIDDEN_ACTIONS = (
    "delete",
    "purge",
    "drop",
    "truncate",
    "wipe",
    "remove_all",
    "demo_purge",
)

HISTORY_KEY_PREFIX = "core.control.history"
HISTORY_MAX = 30

CATEGORY_KEYS = ("ops", "data", "security", "integrations", "books")


def _owner_emails() -> set[str]:
    emails = {
        (settings.admin_email or "").strip().lower(),
        (getattr(settings, "core_owner_email", None) or "").strip().lower(),
        "admin@kanhaerp.com",
    }
    emails.discard("")
    return emails


def assert_core_owner(user: User) -> None:
    ok = bool(getattr(user, "is_superadmin", False)) or (
        (user.email or "").strip().lower() in _owner_emails()
    )
    if not ok:
        raise HTTPException(403, "Core Control is owner-only. Not available on this account.")


def resolve_core_owner_user(db: Session) -> User:
    """Pick the owner account used for Core Control recovery sessions."""
    for email in _owner_emails():
        row = db.query(User).filter(User.email == email).first()
        if row and getattr(row, "is_active", True):
            return row
    row = db.query(User).filter(User.is_superadmin.is_(True), User.is_active.is_(True)).first()
    if row:
        return row
    raise HTTPException(500, "No Core Control owner user found. Seed admin first.")


def configured_core_master_pass() -> str:
    """Master passphrase for login-page Ultra Support. Demo has a known fallback."""
    master = (getattr(settings, "core_control_pass", None) or "").strip()
    if master:
        return master
    if settings.demo_mode:
        return "KanhaCoreUltra1"
    return ""


def verify_core_unlock_passphrase(db: Session, passphrase: str) -> User:
    """
    Unlock Core Control without normal login.
    Accepts: CORE_CONTROL_PASS (or demo fallback), OR the owner account password.
    """
    import secrets

    from app.core.security import verify_password

    pw = (passphrase or "").strip()
    if not pw:
        raise HTTPException(401, "Core Control passphrase required")

    owner = resolve_core_owner_user(db)
    master = configured_core_master_pass()
    if master and len(pw) == len(master) and secrets.compare_digest(pw, master):
        return owner
    if verify_password(pw, owner.password_hash):
        return owner
    raise HTTPException(401, "Invalid Core Control passphrase")


def reset_user_password_by_owner(
    db: Session,
    company_id: int,
    owner: User,
    *,
    email: str,
    new_password: str,
) -> dict[str, Any]:
    """Owner recovery: set a user's password. Never deletes the user."""
    from app.core.rate_limit import validate_password_strength
    from app.core.security import hash_password

    assert_core_owner(owner)
    target_email = (email or "").strip().lower()
    if not target_email:
        raise HTTPException(400, "email required")
    validate_password_strength(new_password)
    row = (
        db.query(User)
        .filter(User.company_id == company_id, User.email == target_email)
        .first()
    )
    if not row:
        raise HTTPException(404, f"User not found: {target_email}")
    before = diagnose(db, company_id, user=owner)
    row.password_hash = hash_password(new_password)
    # bump session so old tokens die if column exists
    if hasattr(row, "session_epoch"):
        row.session_epoch = int(getattr(row, "session_epoch", 0) or 0) + 1
    db.flush()
    after = diagnose(db, company_id, user=owner)
    log_action(
        db,
        company_id,
        action="reset_user_password",
        score_before=before.get("health_score"),
        score_after=after.get("health_score"),
        user_email=owner.email or "",
        detail={"target_email": target_email, "never_delete": True},
    )
    return {
        "ok": True,
        "message": f"Password reset for {target_email}. Old sessions invalidated if supported.",
        "email": target_email,
        "never_delete": True,
    }


def _policy_banner() -> dict[str, Any]:
    return {
        "never_delete": True,
        "never_purge": True,
        "default_autofix": "safe_only",
        "confirm_required_for": [k for k, v in FIX_CATALOG.items() if v["safety"] == "confirm"],
        "message": (
            "Core Control only repairs. It never deletes invoices, stock, users, or runs purge. "
            "Safe autofix first; risky unlocks need Confirm after you read drawbacks."
        ),
    }


def _history_key(company_id: int) -> str:
    return f"{HISTORY_KEY_PREFIX}.{company_id}"


def log_action(
    db: Session,
    company_id: int,
    *,
    action: str,
    score_before: int | None = None,
    score_after: int | None = None,
    user_email: str = "",
    detail: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Append one Core Control action (last 30 kept). Never deletes business data."""
    key = _history_key(company_id)
    row = db.query(SyncState).filter(SyncState.key == key).first()
    if not row:
        row = SyncState(key=key, value={"items": []})
        db.add(row)
        db.flush()
    val = dict(row.value or {})
    items = list(val.get("items") or [])
    entry = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "action": action,
        "score_before": score_before,
        "score_after": score_after,
        "user_email": user_email or "",
    }
    if detail:
        entry["detail"] = detail
    items.append(entry)
    val["items"] = items[-HISTORY_MAX:]
    row.value = val
    db.flush()
    return entry


def get_history(db: Session, company_id: int) -> list[dict[str, Any]]:
    key = _history_key(company_id)
    row = db.query(SyncState).filter(SyncState.key == key).first()
    if not row:
        return []
    return list((row.value or {}).get("items") or [])


def _module_pulse(db: Session, company_id: int) -> dict[str, int]:
    return {
        "leads": db.query(Lead).filter(Lead.company_id == company_id).count(),
        "customers": db.query(Customer).filter(Customer.company_id == company_id).count(),
        "sales_orders": db.query(SalesOrder).filter(SalesOrder.company_id == company_id).count(),
        "invoices": db.query(Invoice).filter(Invoice.company_id == company_id).count(),
        "purchase_orders": db.query(PurchaseOrder).filter(PurchaseOrder.company_id == company_id).count(),
        "products": db.query(Product).filter(Product.company_id == company_id).count(),
        "employees": db.query(Employee).filter(Employee.company_id == company_id).count(),
        "tickets": db.query(ServiceTicket).filter(ServiceTicket.company_id == company_id).count(),
        "journals": db.query(JournalEntry).filter(JournalEntry.company_id == company_id).count(),
    }


def _integrity_summary(db: Session, company_id: int) -> dict[str, Any]:
    paid_gt = (
        db.query(Invoice)
        .filter(Invoice.company_id == company_id, Invoice.paid > Invoice.total)
        .count()
    )
    cutoff = datetime.utcnow() - timedelta(days=7)
    so_stale = (
        db.query(SalesOrder)
        .filter(
            SalesOrder.company_id == company_id,
            SalesOrder.approval_status == "pending",
            SalesOrder.created_at != None,  # noqa: E711
            SalesOrder.created_at < cutoff,
        )
        .count()
    )
    age_cut = datetime.utcnow() - timedelta(days=3)
    failed_aging = (
        db.query(FailedEntry)
        .filter(
            FailedEntry.heal_status == "pending",
            FailedEntry.created_at != None,  # noqa: E711
            FailedEntry.created_at < age_cut,
        )
        .filter(
            (FailedEntry.company_id == company_id) | (FailedEntry.company_id == None)  # noqa: E711
        )
        .count()
    )
    samples = [
        {"id": inv.id, "number": inv.number, "paid": inv.paid, "total": inv.total}
        for inv in (
            db.query(Invoice)
            .filter(Invoice.company_id == company_id, Invoice.paid > Invoice.total)
            .limit(5)
            .all()
        )
    ]
    return {
        "invoices_paid_gt_total": paid_gt,
        "sales_orders_pending_over_7d": so_stale,
        "failed_entries_aging_3d": failed_aging,
        "samples_paid_gt_total": samples,
    }


def _confidence_label(score: int, pulse: dict[str, int], integrity: dict[str, Any]) -> str:
    filled = sum(1 for v in pulse.values() if v and v > 0)
    anomalies = int(integrity.get("invoices_paid_gt_total") or 0) + int(
        integrity.get("failed_entries_aging_3d") or 0
    )
    if filled >= 6 and anomalies == 0 and score >= 80:
        return "high"
    if filled >= 3 and score >= 50:
        return "medium"
    return "low"


def _empty_categories() -> dict[str, list]:
    return {k: [] for k in CATEGORY_KEYS}


def diagnose(db: Session, company_id: int, user: User | None = None) -> dict[str, Any]:
    from app.services.blackout import blackout_status
    from app.services.ha_cluster import cluster_status
    from app.services.ha_heal import list_failed_entries
    from app.services.period_lock import period_status
    from app.services.hierarchy_approvals import get_module_controls, get_user_level
    from app.services.legal_compliance import DEFAULT_SALARY_POLICY, legal_board, get_salary_policy

    issues: list[dict[str, Any]] = []
    healthy: list[str] = []
    categories = _empty_categories()

    def add_issue(cat: str, issue: dict[str, Any]) -> None:
        issue["category"] = cat
        issues.append(issue)
        if cat in categories:
            categories[cat].append(issue)

    pulse = _module_pulse(db, company_id)
    integrity = _integrity_summary(db, company_id)

    # --- ops: blackout / cluster / failed entries ---
    bo = blackout_status(db)
    if bo.get("active"):
        meta = FIX_CATALOG["clear_blackout"]
        add_issue(
            "ops",
            {
                "id": "blackout",
                "severity": "critical",
                "where": "Resilience / HA",
                "why": "Blackout freeze is ON — writes blocked (503).",
                "fix": "clear_blackout",
                "auto": False,
                "safety": meta["safety"],
                "drawbacks": meta["drawbacks"],
            },
        )
    else:
        healthy.append("Blackout clear — writes open")

    try:
        cl = cluster_status(db)
        if cl.get("enabled"):
            healthy.append(f"Cluster enabled · role={cl.get('role')} · node={cl.get('node_id')}")
        else:
            healthy.append("Cluster disabled (single-node OK)")
    except Exception:
        healthy.append("Cluster status unavailable (non-blocking)")

    failed = list_failed_entries(db, status="pending", limit=50)
    if failed:
        meta = FIX_CATALOG["heal_failed_entries"]
        add_issue(
            "ops",
            {
                "id": "failed_entries",
                "severity": "high",
                "where": "Failed entry queue",
                "why": f"{len(failed)} crashed writes pending heal (payload kept, not deleted).",
                "fix": "heal_failed_entries",
                "auto": True,
                "safety": meta["safety"],
                "drawbacks": meta["drawbacks"],
                "count": len(failed),
                "sample": [
                    {"id": f["id"], "path": f["path"], "error": (f["error"] or "")[:120]}
                    for f in failed[:5]
                ],
            },
        )
    else:
        healthy.append("No pending failed entries")

    if integrity.get("failed_entries_aging_3d"):
        add_issue(
            "ops",
            {
                "id": "failed_entries_aging",
                "severity": "medium",
                "where": "Failed entry queue",
                "why": (
                    f"{integrity['failed_entries_aging_3d']} pending failed entries older than 3 days."
                ),
                "fix": "heal_failed_entries",
                "auto": True,
                "safety": "safe",
                "drawbacks": FIX_CATALOG["heal_failed_entries"]["drawbacks"],
            },
        )

    # --- books: period lock / salary / legal ---
    pl = period_status(db, company_id)
    if pl.get("closed_through"):
        meta = FIX_CATALOG["unlock_period"]
        add_issue(
            "books",
            {
                "id": "period_lock",
                "severity": "medium",
                "where": "Accounting",
                "why": f"Books closed through {pl['closed_through']}.",
                "fix": "unlock_period",
                "auto": False,
                "safety": meta["safety"],
                "drawbacks": meta["drawbacks"],
            },
        )
    else:
        healthy.append("Accounting periods open")

    # --- data: SO / modules / density / integrity ---
    pending_so = (
        db.query(SalesOrder)
        .filter(SalesOrder.company_id == company_id, SalesOrder.approval_status == "pending")
        .count()
    )
    if pending_so:
        meta = FIX_CATALOG["approve_pending_so"]
        add_issue(
            "data",
            {
                "id": "pending_so",
                "severity": "medium",
                "where": "Sales",
                "why": f"{pending_so} sales orders pending approval.",
                "fix": "approve_pending_so",
                "auto": False,
                "safety": meta["safety"],
                "drawbacks": meta["drawbacks"],
            },
        )
    else:
        healthy.append("No pending SO approvals")

    if integrity.get("sales_orders_pending_over_7d"):
        add_issue(
            "data",
            {
                "id": "so_pending_aging",
                "severity": "medium",
                "where": "Sales",
                "why": (
                    f"{integrity['sales_orders_pending_over_7d']} sales orders pending >7 days."
                ),
                "fix": "approve_pending_so",
                "auto": False,
                "safety": "confirm",
                "drawbacks": FIX_CATALOG["approve_pending_so"]["drawbacks"],
            },
        )

    if integrity.get("invoices_paid_gt_total"):
        meta = FIX_CATALOG["repair_negative_balances"]
        add_issue(
            "data",
            {
                "id": "paid_gt_total",
                "severity": "high",
                "where": "Invoices",
                "why": (
                    f"{integrity['invoices_paid_gt_total']} invoices with paid > total "
                    "(anomaly — clamp paid, never delete)."
                ),
                "fix": "repair_negative_balances",
                "auto": True,
                "safety": meta["safety"],
                "drawbacks": meta["drawbacks"],
            },
        )
    else:
        healthy.append("No invoices with paid > total")

    pending_appr = (
        db.query(ApprovalRequest)
        .filter(ApprovalRequest.company_id == company_id, ApprovalRequest.status == "pending")
        .count()
    )
    if pending_appr:
        add_issue(
            "security",
            {
                "id": "pending_approvals",
                "severity": "low",
                "where": "Approvals inbox",
                "why": (
                    f"{pending_appr} hierarchy approvals waiting "
                    "(manual decide — Core Control will not auto-approve inbox)."
                ),
                "fix": "list_only",
                "auto": False,
                "safety": "safe",
                "drawbacks": ["No automatic change — preserves approval discipline."],
            },
        )

    co = db.get(Company, company_id)
    mods = dict((co.modules_enabled if co else None) or default_modules_enabled())
    missing_mods = [k for k in ALL_MODULES if k not in mods]
    if missing_mods:
        meta = FIX_CATALOG["sync_modules"]
        add_issue(
            "data",
            {
                "id": "modules_sync",
                "severity": "low",
                "where": "Company modules",
                "why": f"Missing module keys: {', '.join(missing_mods[:8])}",
                "fix": "sync_modules",
                "auto": True,
                "safety": meta["safety"],
                "drawbacks": meta["drawbacks"],
            },
        )
    else:
        healthy.append(f"All {len(ALL_MODULES)} modules registered")

    # Admin permissions additive check
    admin_role = db.query(Role).filter(Role.company_id == company_id, Role.code == "admin").first()
    if admin_role:
        perms = set(admin_role.permissions or [])
        missing_perms = [p for p in DEFAULT_PERMISSIONS if p not in perms]
        if missing_perms:
            meta = FIX_CATALOG["sync_admin_permissions"]
            add_issue(
                "security",
                {
                    "id": "admin_permissions",
                    "severity": "medium",
                    "where": "Admin role",
                    "why": f"Admin role missing {len(missing_perms)} default permissions (additive merge available).",
                    "fix": "sync_admin_permissions",
                    "auto": True,
                    "safety": meta["safety"],
                    "drawbacks": meta["drawbacks"],
                },
            )
        else:
            healthy.append("Admin role has default permissions")
    else:
        healthy.append("No admin role row (skipped permission sync)")

    # Owner hierarchy level
    if user is not None:
        lvl = get_user_level(db, company_id, user)
        if lvl < 5:
            meta = FIX_CATALOG["ensure_owner_level"]
            add_issue(
                "security",
                {
                    "id": "owner_level",
                    "severity": "low",
                    "where": "Approval hierarchy",
                    "why": f"Owner user level is {lvl}; recommended 5 for Core Control authority.",
                    "fix": "ensure_owner_level",
                    "auto": True,
                    "safety": meta["safety"],
                    "drawbacks": meta["drawbacks"],
                },
            )
        else:
            healthy.append("Owner approval level = 5")

    # Salary policy missing keys (stored vs defaults)
    from app.services.legal_compliance import SALARY_POLICY_KEY

    sp_row = db.query(SyncState).filter(SyncState.key == f"{SALARY_POLICY_KEY}.{company_id}").first()
    stored_sp = dict((sp_row.value if sp_row else None) or {})
    missing_sp_keys = [k for k in DEFAULT_SALARY_POLICY if k not in stored_sp]
    if missing_sp_keys:
        meta = FIX_CATALOG["refresh_salary_policy_defaults"]
        add_issue(
            "books",
            {
                "id": "salary_policy_keys",
                "severity": "low",
                "where": "HRMS salary policy",
                "why": f"Missing salary policy keys: {', '.join(missing_sp_keys[:6])}",
                "fix": "refresh_salary_policy_defaults",
                "auto": True,
                "safety": meta["safety"],
                "drawbacks": meta["drawbacks"],
            },
        )
    else:
        healthy.append("Salary policy keys complete")

    stock_rows = db.query(StockBalance).filter(StockBalance.company_id == company_id).count()
    inv_count = pulse["invoices"]
    if stock_rows == 0 or inv_count == 0:
        meta = FIX_CATALOG["ensure_demo_density"]
        add_issue(
            "data",
            {
                "id": "sparse_demo",
                "severity": "medium" if settings.demo_mode else "info",
                "where": "Inventory / Sales",
                "why": (
                    f"Sparse data (stock_rows={stock_rows}, invoices={inv_count}). "
                    "Demo density can ADD seed rows — never deletes."
                ),
                "fix": "ensure_demo_density",
                "auto": False,
                "safety": meta["safety"],
                "drawbacks": meta["drawbacks"],
            },
        )
    else:
        healthy.append(f"Stock rows {stock_rows} · invoices {inv_count}")

    legal = legal_board(db, company_id)
    blocked = int((legal.get("counts") or {}).get("blocked_gates") or 0)
    if blocked:
        add_issue(
            "books",
            {
                "id": "legal_gates",
                "severity": "info",
                "where": "Legal & Risk",
                "why": f"{blocked} legal gates blocked (intentional — Core Control will not auto-approve legal gates).",
                "fix": "list_only",
                "auto": False,
                "safety": "safe",
                "drawbacks": ["Preserves compliance consciousness."],
            },
        )

    sp = get_salary_policy(db, company_id)
    healthy.append(f"Salary policy mode={sp.get('mode')}")
    ctrls = get_module_controls(db, company_id)
    healthy.append(f"Approval controls ({len(ctrls)} modules)")
    healthy.append(
        "Module pulse: "
        + ", ".join(f"{k}={v}" for k, v in pulse.items())
    )

    # --- integrations readiness (info only, never auto) ---
    integ_flags = [
        ("whatsapp", bool(getattr(settings, "whatsapp_live", False)), "WhatsApp Meta token"),
        ("llm", bool(getattr(settings, "llm_live", False)), "LLM API"),
        ("gsp", bool(getattr(settings, "gsp_live", False)), "GSP e-Invoice/e-Way"),
        ("razorpay", bool(getattr(settings, "razorpay_live", False)), "Razorpay keys"),
    ]
    for iid, live, label in integ_flags:
        if not live:
            add_issue(
                "integrations",
                {
                    "id": f"integ_{iid}",
                    "severity": "info",
                    "where": "Integrations",
                    "why": f"{label} not live (settings flags) — configure when ready.",
                    "fix": "list_only",
                    "auto": False,
                    "safety": "safe",
                    "drawbacks": ["Info only — Core Control does not auto-wire credentials."],
                },
            )
        else:
            healthy.append(f"{label} live")

    score = max(
        0,
        100
        - sum(
            {"critical": 35, "high": 15, "medium": 8, "low": 3, "info": 0}.get(i["severity"], 5)
            for i in issues
        ),
    )
    confidence = _confidence_label(score, pulse, integrity)
    safe_ids = [
        i["fix"]
        for i in issues
        if i.get("auto") and FIX_CATALOG.get(i.get("fix"), {}).get("safety") == "safe"
    ]
    # unique preserve order
    seen: set[str] = set()
    safe_unique = []
    for fid in safe_ids:
        if fid not in seen:
            seen.add(fid)
            safe_unique.append(fid)
    confirm_ids = []
    seen_c: set[str] = set()
    for i in issues:
        fid = i.get("fix")
        if FIX_CATALOG.get(fid, {}).get("safety") == "confirm" and fid not in seen_c:
            seen_c.add(fid)
            confirm_ids.append(fid)

    return {
        "ok": len([i for i in issues if i["severity"] in ("critical", "high")]) == 0,
        "health_score": score,
        "confidence": confidence,
        "scanned_at": datetime.utcnow().isoformat() + "Z",
        "issues": issues,
        "categories": categories,
        "healthy": healthy,
        "module_pulse": pulse,
        "integrity": integrity,
        "auto_fixable": safe_unique,
        "needs_confirm": confirm_ids,
        "policy": _policy_banner(),
        "owner_only": True,
        "summary": (
            f"Core Control scan: score {score}/100 · confidence {confidence} · "
            f"{len(issues)} findings · {len(safe_unique)} safe auto · "
            f"{len(confirm_ids)} need confirm. Never deletes data."
        ),
    }


def preview_fixes(db: Session, company_id: int, *, include_confirm: bool = False, user: User | None = None) -> dict[str, Any]:
    """Dry-run: show what would change + drawbacks. No writes."""
    report = diagnose(db, company_id, user=user)
    plan = []
    for issue in report["issues"]:
        fid = issue.get("fix")
        if not fid or fid == "list_only":
            continue
        meta = FIX_CATALOG.get(fid) or {}
        if meta.get("safety") == "confirm" and not include_confirm:
            plan.append(
                {
                    "fix": fid,
                    "issue": issue["id"],
                    "would_run_in_default_autofix": False,
                    "reason": "Needs explicit Confirm — shows drawbacks first",
                    "drawbacks": meta.get("drawbacks") or [],
                    "deletes": False,
                }
            )
            continue
        if meta.get("safety") != "safe" and not include_confirm:
            continue
        plan.append(
            {
                "fix": fid,
                "issue": issue["id"],
                "would_run_in_default_autofix": meta.get("safety") == "safe",
                "drawbacks": meta.get("drawbacks") or [],
                "side_effects": meta.get("side_effects") or [],
                "deletes": False,
            }
        )
    # de-dupe plan by fix id keeping first
    seen: set[str] = set()
    uniq = []
    for p in plan:
        if p["fix"] in seen:
            continue
        seen.add(p["fix"])
        uniq.append(p)
    return {
        "dry_run": True,
        "policy": _policy_banner(),
        "health_score": report["health_score"],
        "confidence": report.get("confidence"),
        "plan": uniq,
        "message": "Preview only — no data changed. Default Autofix runs SAFE items only.",
    }


def _snapshot_for_rollback(db: Session, company_id: int, fix_id: str, user: User | None = None) -> dict[str, Any]:
    """Minimal state to undo a single fix if score drops."""
    if fix_id == "clear_blackout":
        from app.services.blackout import blackout_status

        return {"blackout": blackout_status(db)}
    if fix_id == "unlock_period":
        from app.services.period_lock import period_status

        return {"period": period_status(db, company_id)}
    if fix_id == "approve_pending_so":
        ids = [
            so.id
            for so in db.query(SalesOrder)
            .filter(SalesOrder.company_id == company_id, SalesOrder.approval_status == "pending")
            .all()
        ]
        return {"pending_so_ids": ids}
    if fix_id == "heal_failed_entries":
        ids = [r.id for r in db.query(FailedEntry).filter(FailedEntry.heal_status == "pending").all()]
        return {"pending_failed_ids": ids}
    if fix_id == "sync_modules":
        co = db.get(Company, company_id)
        return {"modules_enabled": dict((co.modules_enabled if co else {}) or {})}
    if fix_id == "sync_admin_permissions":
        role = db.query(Role).filter(Role.company_id == company_id, Role.code == "admin").first()
        return {"permissions": list((role.permissions if role else None) or [])}
    if fix_id == "ensure_owner_level" and user is not None:
        from app.services.hierarchy_approvals import get_user_level

        return {"user_id": user.id, "level": get_user_level(db, company_id, user)}
    if fix_id == "refresh_salary_policy_defaults":
        from app.services.legal_compliance import SALARY_POLICY_KEY

        row = db.query(SyncState).filter(SyncState.key == f"{SALARY_POLICY_KEY}.{company_id}").first()
        return {"salary_policy": dict((row.value if row else None) or {})}
    if fix_id == "repair_negative_balances":
        rows = (
            db.query(Invoice)
            .filter(Invoice.company_id == company_id, Invoice.paid > Invoice.total)
            .all()
        )
        return {"paid_map": {str(r.id): r.paid for r in rows}}
    return {}


def _rollback_fix(db: Session, company_id: int, fix_id: str, snap: dict[str, Any], user: User) -> dict[str, Any]:
    if fix_id == "clear_blackout" and snap.get("blackout", {}).get("active"):
        row = db.query(SyncState).filter(SyncState.key == "ops.blackout").first()
        if row:
            val = dict(row.value or {})
            val["active"] = True
            val["reason"] = "Re-engaged by Core Control rollback (health drop)"
            row.value = val
            db.flush()
        return {"rolled_back": True, "fix": fix_id}

    if fix_id == "unlock_period":
        prev = (snap.get("period") or {}).get("closed_through")
        if prev:
            from app.services.period_lock import set_period_lock

            set_period_lock(
                db,
                company_id,
                closed_through=prev,
                note="Restored by Core Control rollback",
                updated_by=user.email or "",
            )
            return {"rolled_back": True, "fix": fix_id, "closed_through": prev}

    if fix_id == "approve_pending_so":
        for sid in snap.get("pending_so_ids") or []:
            so = db.get(SalesOrder, sid)
            if so and so.company_id == company_id:
                so.approval_status = "pending"
        db.flush()
        return {"rolled_back": True, "fix": fix_id, "count": len(snap.get("pending_so_ids") or [])}

    if fix_id == "heal_failed_entries":
        for eid in snap.get("pending_failed_ids") or []:
            row = db.get(FailedEntry, eid)
            if row:
                row.heal_status = "pending"
                row.healed_at = None
                row.heal_note = "Reverted by Core Control rollback"
        db.flush()
        return {"rolled_back": True, "fix": fix_id}

    if fix_id == "sync_modules":
        co = db.get(Company, company_id)
        if co and "modules_enabled" in snap:
            co.modules_enabled = snap["modules_enabled"]
            db.flush()
            return {"rolled_back": True, "fix": fix_id}

    if fix_id == "sync_admin_permissions" and "permissions" in snap:
        role = db.query(Role).filter(Role.company_id == company_id, Role.code == "admin").first()
        if role:
            role.permissions = snap["permissions"]
            db.flush()
            return {"rolled_back": True, "fix": fix_id}

    if fix_id == "ensure_owner_level" and snap.get("user_id"):
        from app.services.hierarchy_approvals import set_user_level

        set_user_level(
            db,
            company_id,
            user_id=int(snap["user_id"]),
            level=int(snap.get("level") or 1),
            title="restored by Core Control rollback",
        )
        return {"rolled_back": True, "fix": fix_id}

    if fix_id == "refresh_salary_policy_defaults" and "salary_policy" in snap:
        from app.services.legal_compliance import SALARY_POLICY_KEY

        row = db.query(SyncState).filter(SyncState.key == f"{SALARY_POLICY_KEY}.{company_id}").first()
        if row:
            row.value = snap["salary_policy"]
            db.flush()
            return {"rolled_back": True, "fix": fix_id}

    if fix_id == "repair_negative_balances":
        for sid, paid in (snap.get("paid_map") or {}).items():
            inv = db.get(Invoice, int(sid))
            if inv and inv.company_id == company_id:
                inv.paid = paid
        db.flush()
        return {"rolled_back": True, "fix": fix_id, "count": len(snap.get("paid_map") or {})}

    return {"rolled_back": False, "fix": fix_id, "note": "No destructive change; rollback N/A or already safe"}


def apply_fix(
    db: Session,
    company_id: int,
    user: User,
    fix_id: str,
    *,
    confirm: bool = False,
) -> dict[str, Any]:
    """Apply one named fix. Never deletes. Confirm required for risky fixes."""
    for bad in FORBIDDEN_ACTIONS:
        if bad in (fix_id or "").lower():
            raise HTTPException(400, f"Forbidden action '{fix_id}' — Core Control never deletes/purges.")

    meta = FIX_CATALOG.get(fix_id)
    if not meta:
        raise HTTPException(400, f"Unknown or disallowed fix '{fix_id}'")
    if meta.get("deletes"):
        raise HTTPException(400, "This fix is marked deletes=True — blocked by policy")
    if meta.get("safety") == "confirm" and not confirm:
        raise HTTPException(
            400,
            f"Fix '{fix_id}' needs confirm=true after you review drawbacks: {meta.get('drawbacks')}",
        )

    snap = _snapshot_for_rollback(db, company_id, fix_id, user=user)
    before = diagnose(db, company_id, user=user)["health_score"]

    if fix_id == "clear_blackout":
        from app.services.blackout import unlock_blackout

        st = unlock_blackout(db, unlocked_by=user.email or "core_control")
        out = {"fix": fix_id, "ok": True, "result": st, "message": "Blackout cleared — writes restored (no data deleted)"}
    elif fix_id == "heal_failed_entries":
        rows = db.query(FailedEntry).filter(FailedEntry.heal_status == "pending").all()
        n = 0
        for r in rows:
            r.heal_status = "healed"
            r.heal_note = f"Core Control safe-heal by {user.email} (payload retained)"
            r.healed_at = datetime.utcnow()
            n += 1
        db.flush()
        out = {
            "fix": fix_id,
            "ok": True,
            "healed": n,
            "message": f"Marked {n} failed entries healed — payloads kept, nothing deleted, no auto money replay",
        }
    elif fix_id == "unlock_period":
        from app.services.period_lock import set_period_lock

        st = set_period_lock(
            db, company_id, closed_through=None, note="Unlocked by Core Control (confirmed)", updated_by=user.email or ""
        )
        out = {"fix": fix_id, "ok": True, "result": st, "message": "Period unlocked (journals not deleted)"}
    elif fix_id == "approve_pending_so":
        rows = (
            db.query(SalesOrder)
            .filter(SalesOrder.company_id == company_id, SalesOrder.approval_status == "pending")
            .all()
        )
        for so in rows:
            so.approval_status = "approved"
        db.flush()
        out = {"fix": fix_id, "ok": True, "approved": len(rows), "message": f"Approved {len(rows)} SOs (not deleted)"}
    elif fix_id == "sync_modules":
        co = db.get(Company, company_id)
        if not co:
            return {"fix": fix_id, "ok": False, "message": "Company missing"}
        mods = dict(co.modules_enabled or {})
        for k in ALL_MODULES:
            mods.setdefault(k, True)  # additive only
        co.modules_enabled = mods
        db.flush()
        out = {"fix": fix_id, "ok": True, "modules": len(mods), "message": "Modules synced (added keys only)"}
    elif fix_id == "sync_admin_permissions":
        role = db.query(Role).filter(Role.company_id == company_id, Role.code == "admin").first()
        if not role:
            out = {"fix": fix_id, "ok": False, "message": "Admin role not found"}
        else:
            perms = list(role.permissions or [])
            added = [p for p in DEFAULT_PERMISSIONS if p not in perms]
            if added:
                role.permissions = perms + added
                db.flush()
            out = {
                "fix": fix_id,
                "ok": True,
                "added": len(added),
                "message": f"Admin permissions merged (+{len(added)} keys, none removed)",
            }
    elif fix_id == "ensure_owner_level":
        from app.services.hierarchy_approvals import set_user_level

        entry = set_user_level(
            db,
            company_id,
            user_id=user.id,
            level=5,
            dept="ops",
            title="owner",
        )
        out = {
            "fix": fix_id,
            "ok": True,
            "level": entry,
            "message": f"Owner {user.email} set to approval level 5",
        }
    elif fix_id == "refresh_salary_policy_defaults":
        from app.services.legal_compliance import DEFAULT_SALARY_POLICY, SALARY_POLICY_KEY

        key = f"{SALARY_POLICY_KEY}.{company_id}"
        row = db.query(SyncState).filter(SyncState.key == key).first()
        if not row:
            row = SyncState(key=key, value={})
            db.add(row)
            db.flush()
        stored = dict(row.value or {})
        added_keys = []
        for k, v in DEFAULT_SALARY_POLICY.items():
            if k not in stored:
                stored[k] = v
                added_keys.append(k)
        row.value = stored
        db.flush()
        out = {
            "fix": fix_id,
            "ok": True,
            "added_keys": added_keys,
            "message": f"Salary policy defaults merged (+{len(added_keys)} keys, existing kept)",
        }
    elif fix_id == "repair_negative_balances":
        rows = (
            db.query(Invoice)
            .filter(Invoice.company_id == company_id, Invoice.paid > Invoice.total)
            .all()
        )
        n = 0
        for inv in rows:
            inv.paid = float(inv.total or 0)
            n += 1
        db.flush()
        out = {
            "fix": fix_id,
            "ok": True,
            "clamped": n,
            "message": f"Clamped paid→total on {n} invoices (no deletes)",
        }
    elif fix_id == "ensure_demo_density":
        from app.services.demo_completeness import ensure_demo_density

        ensure_demo_density(db, company_id)
        db.flush()
        out = {"fix": fix_id, "ok": True, "message": "Demo density applied (additive seed only — no deletes)"}
    elif fix_id == "list_only":
        out = {"fix": fix_id, "ok": True, "message": "No change"}
    else:
        raise HTTPException(400, f"Unhandled fix '{fix_id}'")

    db.flush()
    after_score = diagnose(db, company_id, user=user)["health_score"]
    out["before_score"] = before
    out["after_score"] = after_score
    out["drawbacks"] = meta.get("drawbacks") or []
    out["deletes"] = False

    if after_score < before - 5:
        rb = _rollback_fix(db, company_id, fix_id, snap, user)
        out["ok"] = False
        out["rolled_back"] = rb.get("rolled_back")
        out["message"] = (
            f"Health dropped {before}→{after_score} after {fix_id}. "
            f"Rollback attempted={rb.get('rolled_back')}. Change undone where possible."
        )
    try:
        log_action(
            db,
            company_id,
            action=f"fix:{fix_id}",
            score_before=before,
            score_after=out.get("after_score"),
            user_email=user.email or "",
            detail={"ok": out.get("ok"), "rolled_back": out.get("rolled_back")},
        )
    except Exception:
        pass
    return out


def autofix_all(
    db: Session,
    company_id: int,
    user: User,
    *,
    confirm_risky: bool = False,
) -> dict[str, Any]:
    """
    Default: SAFE fixes only (never delete).
    confirm_risky=True also runs confirm-level fixes after drawbacks were shown.
    When confirm_risky: backup_sqlite first; refuse if sqlite backup fails.
    """
    backup_result: dict[str, Any] | None = None
    if confirm_risky:
        from app.services.backup import backup_sqlite

        backup_result = backup_sqlite()
        url = (settings.database_url or "").lower()
        if "sqlite" in url and not backup_result.get("ok"):
            return {
                "ok": False,
                "refused": True,
                "backup": backup_result,
                "before_score": None,
                "after_score": None,
                "applied": [],
                "skipped_needs_confirm": [],
                "policy": _policy_banner(),
                "message": (
                    "Risky autofix refused — SQLite backup failed. "
                    "Fix backup path first; Core Control never deletes but will not unlock without a backup."
                ),
                "owner_only": True,
            }

    preview = preview_fixes(db, company_id, include_confirm=confirm_risky, user=user)
    report = diagnose(db, company_id, user=user)
    applied = []
    skipped = []
    ran: set[str] = set()

    for issue in report["issues"]:
        fid = issue.get("fix")
        if not fid or fid == "list_only" or fid in ran:
            continue
        meta = FIX_CATALOG.get(fid) or {}
        if meta.get("safety") == "safe":
            ran.add(fid)
            try:
                applied.append(apply_fix(db, company_id, user, fid, confirm=False))
            except Exception as e:
                applied.append({"fix": fid, "ok": False, "message": str(e)})
        elif meta.get("safety") == "confirm":
            if confirm_risky:
                ran.add(fid)
                try:
                    applied.append(apply_fix(db, company_id, user, fid, confirm=True))
                except Exception as e:
                    applied.append({"fix": fid, "ok": False, "message": str(e)})
            else:
                skipped.append(
                    {
                        "fix": fid,
                        "issue": issue["id"],
                        "reason": "Needs Confirm — read drawbacks first",
                        "drawbacks": meta.get("drawbacks") or [],
                    }
                )

    after = diagnose(db, company_id, user=user)
    try:
        log_action(
            db,
            company_id,
            action="autofix_risky" if confirm_risky else "autofix_safe",
            score_before=report["health_score"],
            score_after=after["health_score"],
            user_email=user.email or "",
            detail={
                "applied": len(applied),
                "skipped": len(skipped),
                "backup_ok": (backup_result or {}).get("ok") if backup_result else None,
            },
        )
    except Exception:
        pass

    db.commit()
    result: dict[str, Any] = {
        "ok": True,
        "before_score": report["health_score"],
        "after_score": after["health_score"],
        "confidence": after.get("confidence"),
        "applied": applied,
        "skipped_needs_confirm": skipped,
        "preview": preview,
        "remaining_issues": after["issues"],
        "categories": after.get("categories"),
        "healthy": after["healthy"],
        "policy": _policy_banner(),
        "message": (
            f"{'Risky+safe' if confirm_risky else 'Safe'} autofix done · "
            f"score {report['health_score']} → {after['health_score']}. "
            f"{len(applied)} repairs · {len(skipped)} skipped (need confirm). Never deleted data."
        ),
        "owner_only": True,
    }
    if backup_result is not None:
        result["backup"] = backup_result
        if not backup_result.get("ok") and "sqlite" not in (settings.database_url or "").lower():
            result["backup_warning"] = (
                "Non-SQLite DB — backup_sqlite skipped/warned; risky fixes still ran. "
                "Use managed backups (pg_dump)."
            )
    return result


def full_strength_scan(db: Session, company_id: int, user: User | None = None) -> dict[str, Any]:
    """One-shot: diagnose + preview + recent history + policy + pulse + integrity."""
    diag = diagnose(db, company_id, user=user)
    prev = preview_fixes(db, company_id, include_confirm=True, user=user)
    hist = get_history(db, company_id)
    return {
        "ok": diag.get("ok"),
        "health_score": diag["health_score"],
        "confidence": diag.get("confidence"),
        "diagnose": diag,
        "preview": prev,
        "history": hist[-5:],
        "policy": _policy_banner(),
        "module_pulse": diag.get("module_pulse"),
        "integrity": diag.get("integrity"),
        "categories": diag.get("categories"),
        "summary": diag.get("summary"),
        "owner_only": True,
        "never_delete": True,
    }


def core_control_reply(db: Session, company_id: int, user: User, message: str) -> dict[str, Any]:
    raw = (message or "").strip()
    msg = raw.lower()

    # reset password user@x NewPass123
    if any(k in msg for k in ("reset password", "password reset", "bhool", "forgot password")):
        import re

        m = re.search(
            r"(?:reset\s+password|password\s+reset)\s+(\S+)\s+(\S+)",
            raw,
            flags=re.I,
        )
        if m:
            try:
                out = reset_user_password_by_owner(
                    db, company_id, user, email=m.group(1), new_password=m.group(2)
                )
                return {
                    "reply": f"{out['message']}\nNever deletes users — sirf password sudhaar.",
                    "mode": "core_control",
                    "owner_only": True,
                    "password_reset": out,
                    "suggestions": ["Scan ERP health", "Enter workspace"],
                }
            except HTTPException as e:
                return {
                    "reply": str(e.detail),
                    "mode": "core_control",
                    "owner_only": True,
                    "suggestions": ["reset password email@x NewPass9x"],
                }
        return {
            "reply": (
                "Password reset (owner recovery):\n"
                "Type: reset password email@company.com NewPass9x\n"
                "User delete nahi hota — sirf naya password set."
            ),
            "mode": "core_control",
            "owner_only": True,
            "suggestions": ["reset password admin@kanhaerp.com Welcome9x"],
        }

    if any(k in msg for k in ("full scan", "full strength", "deep scan")):
        full = full_strength_scan(db, company_id, user=user)
        pulse = full.get("module_pulse") or {}
        pulse_txt = ", ".join(f"{k}={v}" for k, v in list(pulse.items())[:6])
        return {
            "reply": (
                f"Full strength scan\n{full.get('summary')}\n"
                f"Pulse: {pulse_txt}\n"
                f"Integrity paid>total={(full.get('integrity') or {}).get('invoices_paid_gt_total', 0)}\n"
                f"{_policy_banner()['message']}"
            ),
            "mode": "core_control",
            "owner_only": True,
            "full": full,
            "suggestions": ["Preview plan", "Safe autofix", "History"],
        }

    if any(k in msg for k in ("history", "log", "actions")):
        hist = get_history(db, company_id)
        lines = [
            f"• {h.get('timestamp')} · {h.get('action')} · "
            f"{h.get('score_before')}→{h.get('score_after')} · {h.get('user_email')}"
            for h in hist[-10:]
        ]
        return {
            "reply": "Core Control history (last 10):\n" + ("\n".join(lines) or "• Empty"),
            "mode": "core_control",
            "owner_only": True,
            "history": hist,
            "suggestions": ["Full scan", "Scan again"],
        }

    if any(k in msg for k in ("preview", "drawback", "dry", "pehle dekho", "plan")):
        prev = preview_fixes(db, company_id, include_confirm=True, user=user)
        lines = []
        for p in prev["plan"][:12]:
            lines.append(
                f"• {p['fix']} — default_run={p.get('would_run_in_default_autofix')} · "
                f"drawbacks: {'; '.join(p.get('drawbacks') or [])[:160]}"
            )
        return {
            "reply": f"Preview (no changes):\n{prev['message']}\n" + ("\n".join(lines) or "• Nothing pending"),
            "mode": "core_control",
            "owner_only": True,
            "preview": prev,
            "suggestions": ["Safe autofix", "Scan again", "Confirm risky fixes"],
        }

    if any(k in msg for k in ("confirm risky", "confirm all", "risky fix", "unlock confirm")):
        result = autofix_all(db, company_id, user, confirm_risky=True)
        return {
            "reply": (
                f"Confirmed risky+safe fixes.\n{result['message']}\n"
                + "\n".join(f"• {a.get('message')}" for a in (result.get("applied") or [])[:8])
            ),
            "mode": "core_control",
            "owner_only": True,
            "result": result,
            "suggestions": ["Scan again", "Preview plan"],
        }

    if any(k in msg for k in ("fixix", "repair", "sudhar", "heal", "rectify", "autofix", "auto fix", "ready", "safe")):
        result = autofix_all(db, company_id, user, confirm_risky=False)
        skip = result.get("skipped_needs_confirm") or []
        skip_txt = ""
        if skip:
            skip_txt = "\n\nSkipped (confirm needed):\n" + "\n".join(
                f"• {s['fix']}: {s['reason']}" for s in skip[:6]
            )
        return {
            "reply": (
                f"Safe autofix complete (no deletes).\n"
                f"Score {result['before_score']} → {result['after_score']}.\n"
                f"{result['message']}\n"
                + "\n".join(f"• {a.get('message')}" for a in (result.get("applied") or [])[:8])
                + skip_txt
            ),
            "mode": "core_control",
            "owner_only": True,
            "result": result,
            "suggestions": ["Preview plan", "Confirm risky fixes", "Scan again"],
        }

    report = diagnose(db, company_id, user=user)
    if any(k in msg for k in ("scan", "diagnose", "status", "health", "problem", "issue", "check")):
        lines = []
        for i in report["issues"][:10]:
            lines.append(
                f"• [{i['severity']}/{i.get('safety','')}/{i.get('category','')}] {i['where']}: {i['why']}"
            )
        return {
            "reply": (
                f"Core Control diagnose\n{report['summary']}\n"
                + ("\n".join(lines) or "• No issues")
                + f"\n\n{_policy_banner()['message']}"
            ),
            "mode": "core_control",
            "owner_only": True,
            "diagnose": report,
            "suggestions": ["Preview plan", "Safe autofix", "Confirm risky fixes", "Full scan"],
        }

    return {
        "reply": (
            "Core Control (owner) — repair only, never delete.\n"
            "1) Scan / Full scan  2) Preview drawbacks  3) Safe autofix  "
            "4) Confirm risky (blackout/period/SO)  5) History  "
            "6) reset password email@x NewPass\n"
            "Agar health drop ho to rollback try hota hai."
        ),
        "mode": "core_control",
        "owner_only": True,
        "policy": _policy_banner(),
        "suggestions": ["Scan ERP health", "Full scan", "Preview plan", "Safe autofix", "reset password …"],
    }
