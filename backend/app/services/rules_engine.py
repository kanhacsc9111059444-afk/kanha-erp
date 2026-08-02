"""
Scoped Dynamic Rules Engine — future-proof ERP changes without rewriting the whole app.

Principle:
  Core code = stable. Behavior that changes over time lives in RULES (data).
  AI may propose; human approves; apply only inside SAFE_SCOPES.
"""
from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.models import DynamicRule, RuleProposal

# Only these scopes may be changed dynamically — never "rewrite_erp" / "schema" / "security"
SAFE_SCOPES: dict[str, str] = {
    "pricing": "Sell price / list price adjustments",
    "discount": "Invoice / POS discount % or amount",
    "reorder": "Stock reorder point / suggest qty",
    "credit": "Customer credit limit nudges",
    "reminder": "Overdue / follow-up timing",
    "pos_offer": "POS festival / seasonal offers",
    "gst_hint": "Compliance reminder thresholds (not legal filing)",
    "sla": "Service ticket SLA hours",
    "commission": "Sales commission % by period",
}

_CODE_RE = re.compile(r"^[a-z0-9][a-z0-9_\-]{1,78}$")


def assert_safe_scope(scope: str) -> str:
    s = (scope or "").strip().lower()
    if s not in SAFE_SCOPES:
        raise ValueError(f"Scope '{scope}' not allowed. Safe: {', '.join(SAFE_SCOPES)}")
    return s


def _in_window(rule: DynamicRule, when: datetime) -> bool:
    if rule.status != "active":
        return False
    if rule.effective_from and when < rule.effective_from:
        return False
    if rule.effective_to and when > rule.effective_to:
        return False
    months = rule.months or []
    if months and when.month not in [int(m) for m in months]:
        return False
    weekdays = rule.weekdays or []
    if weekdays and when.weekday() not in [int(d) for d in weekdays]:
        return False
    return True


def _match_conditions(conditions: dict, context: dict) -> bool:
    if not conditions:
        return True
    for key, expected in conditions.items():
        if key.startswith("_"):
            continue
        actual = context.get(key)
        if isinstance(expected, dict):
            if "eq" in expected and actual != expected["eq"]:
                return False
            if "gte" in expected and (actual is None or float(actual) < float(expected["gte"])):
                return False
            if "lte" in expected and (actual is None or float(actual) > float(expected["lte"])):
                return False
            if "in" in expected and actual not in expected["in"]:
                return False
            if "contains" in expected and str(expected["contains"]).lower() not in str(actual or "").lower():
                return False
        else:
            if actual != expected:
                return False
    return True


def list_rules(db: Session, company_id: int, *, scope: str | None = None, include_retired: bool = False) -> list[dict]:
    q = db.query(DynamicRule).filter(DynamicRule.company_id == company_id)
    if scope:
        q = q.filter(DynamicRule.scope == scope)
    if not include_retired:
        q = q.filter(DynamicRule.status != "retired")
    rows = q.order_by(DynamicRule.scope.asc(), DynamicRule.priority.desc(), DynamicRule.version.desc()).all()
    # Latest version per code only for active list
    seen = set()
    out = []
    for r in rows:
        if r.code in seen and not include_retired:
            continue
        seen.add(r.code)
        out.append(_rule_dict(r))
    return out


def _rule_dict(r: DynamicRule) -> dict:
    return {
        "id": r.id,
        "code": r.code,
        "name": r.name,
        "scope": r.scope,
        "description": r.description,
        "conditions": r.conditions or {},
        "actions": r.actions or {},
        "priority": r.priority,
        "version": r.version,
        "effective_from": r.effective_from.isoformat() + "Z" if r.effective_from else None,
        "effective_to": r.effective_to.isoformat() + "Z" if r.effective_to else None,
        "months": r.months or [],
        "weekdays": r.weekdays or [],
        "status": r.status,
        "source": r.source,
        "updated_at": r.updated_at.isoformat() + "Z" if r.updated_at else None,
    }


def evaluate(db: Session, company_id: int, scope: str, context: dict | None = None, when: datetime | None = None) -> dict[str, Any]:
    """Return matched rules + merged actions for a scope (does not mutate ERP)."""
    scope = assert_safe_scope(scope)
    when = when or datetime.utcnow()
    context = context or {}
    rows = (
        db.query(DynamicRule)
        .filter(DynamicRule.company_id == company_id, DynamicRule.scope == scope, DynamicRule.status == "active")
        .order_by(DynamicRule.priority.desc(), DynamicRule.version.desc())
        .all()
    )
    # latest version per code
    latest: dict[str, DynamicRule] = {}
    for r in rows:
        if r.code not in latest:
            latest[r.code] = r
    matched = []
    merged: dict[str, Any] = {}
    for r in sorted(latest.values(), key=lambda x: -x.priority):
        if not _in_window(r, when):
            continue
        if not _match_conditions(r.conditions or {}, context):
            continue
        matched.append(_rule_dict(r))
        for k, v in (r.actions or {}).items():
            if k not in merged:
                merged[k] = v
    return {
        "ok": True,
        "scope": scope,
        "when": when.isoformat() + "Z",
        "matched": matched,
        "actions": merged,
        "count": len(matched),
    }


def create_or_version_rule(
    db: Session,
    *,
    company_id: int,
    code: str,
    scope: str,
    name: str,
    conditions: dict,
    actions: dict,
    user_id: int | None = None,
    description: str = "",
    priority: int = 100,
    effective_from: datetime | None = None,
    effective_to: datetime | None = None,
    months: list | None = None,
    weekdays: list | None = None,
    source: str = "manual",
) -> DynamicRule:
    scope = assert_safe_scope(scope)
    code = (code or "").strip().lower()
    if not _CODE_RE.match(code):
        raise ValueError("code must be lowercase letters/numbers/_/- (2-80 chars)")
    prev = (
        db.query(DynamicRule)
        .filter(DynamicRule.company_id == company_id, DynamicRule.code == code)
        .order_by(DynamicRule.version.desc())
        .first()
    )
    version = (prev.version + 1) if prev else 1
    if prev and prev.status == "active":
        prev.status = "retired"  # soft supersede — history kept
    row = DynamicRule(
        company_id=company_id,
        code=code,
        name=name or code,
        scope=scope,
        description=description,
        conditions=conditions or {},
        actions=actions or {},
        priority=int(priority),
        version=version,
        effective_from=effective_from,
        effective_to=effective_to,
        months=months or [],
        weekdays=weekdays or [],
        status="active",
        source=source,
        created_by=user_id,
    )
    db.add(row)
    db.flush()
    return row


def pause_rule(db: Session, company_id: int, rule_id: int) -> dict:
    row = db.get(DynamicRule, rule_id)
    if not row or row.company_id != company_id:
        return {"ok": False, "error": "not found"}
    row.status = "paused"
    db.flush()
    return {"ok": True, "id": row.id, "status": "paused"}


def retire_rule(db: Session, company_id: int, rule_id: int) -> dict:
    row = db.get(DynamicRule, rule_id)
    if not row or row.company_id != company_id:
        return {"ok": False, "error": "not found"}
    row.status = "retired"
    db.flush()
    return {"ok": True, "id": row.id, "status": "retired", "message": "Soft-deleted — history kept"}


def seasonal_proposals(company_id: int, user_id: int | None = None) -> list[dict]:
    """Built-in time-based ideas the Rules Agent can learn / suggest (no LLM required)."""
    year = datetime.utcnow().year
    return [
        {
            "scope": "pos_offer",
            "title": "Diwali POS festive discount",
            "rationale": "Seasonal sales lift — Oct/Nov only; scoped to POS offers, not whole ERP.",
            "proposed": {
                "code": f"pos_diwali_{year}",
                "name": "Diwali festive 5% POS",
                "scope": "pos_offer",
                "months": [10, 11],
                "priority": 80,
                "conditions": {},
                "actions": {"discount_pct": 5, "label": "Diwali Offer"},
                "effective_from": f"{year}-10-01T00:00:00",
                "effective_to": f"{year}-11-15T23:59:59",
            },
        },
        {
            "scope": "reminder",
            "title": "Year-end collection push",
            "rationale": "March — tighter overdue reminders for cash flow.",
            "proposed": {
                "code": f"reminder_ye_{year}",
                "name": "Year-end overdue cadence",
                "scope": "reminder",
                "months": [3],
                "priority": 90,
                "conditions": {"days_overdue": {"gte": 7}},
                "actions": {"remind_every_days": 2, "channel": "whatsapp"},
            },
        },
        {
            "scope": "reorder",
            "title": "Monsoon stock buffer",
            "rationale": "Jun–Sep logistics delay — raise reorder buffer only in inventory scope.",
            "proposed": {
                "code": f"reorder_monsoon_{year}",
                "name": "Monsoon reorder +20%",
                "scope": "reorder",
                "months": [6, 7, 8, 9],
                "priority": 70,
                "conditions": {},
                "actions": {"reorder_factor": 1.2, "extra_days_cover": 7},
            },
        },
        {
            "scope": "discount",
            "title": "Dealer volume discount Q4",
            "rationale": "Oct–Dec channel push — dealers only.",
            "proposed": {
                "code": f"discount_dealer_q4_{year}",
                "name": "Dealer Q4 volume 3%",
                "scope": "discount",
                "months": [10, 11, 12],
                "priority": 60,
                "conditions": {"party_type": "dealer", "order_total": {"gte": 50000}},
                "actions": {"discount_pct": 3},
            },
        },
    ]


def create_proposal(db: Session, company_id: int, item: dict, user_id: int | None = None) -> RuleProposal:
    scope = assert_safe_scope(item.get("scope") or (item.get("proposed") or {}).get("scope") or "")
    row = RuleProposal(
        company_id=company_id,
        scope=scope,
        title=item.get("title") or "Rule proposal",
        rationale=item.get("rationale") or "",
        proposed=item.get("proposed") or {},
        status="pending",
        created_by=user_id,
    )
    db.add(row)
    db.flush()
    return row


def approve_proposal(db: Session, company_id: int, proposal_id: int, user_id: int) -> dict:
    prop = db.get(RuleProposal, proposal_id)
    if not prop or prop.company_id != company_id:
        return {"ok": False, "error": "not found"}
    if prop.status != "pending":
        return {"ok": False, "error": f"status is {prop.status}"}
    p = dict(prop.proposed or {})
    # parse dates
    ef = et = None
    if p.get("effective_from"):
        ef = datetime.fromisoformat(str(p["effective_from"]).replace("Z", ""))
    if p.get("effective_to"):
        et = datetime.fromisoformat(str(p["effective_to"]).replace("Z", ""))
    rule = create_or_version_rule(
        db,
        company_id=company_id,
        code=p.get("code") or f"ai_{proposal_id}",
        scope=p.get("scope") or prop.scope,
        name=p.get("name") or prop.title,
        conditions=p.get("conditions") or {},
        actions=p.get("actions") or {},
        user_id=user_id,
        description=prop.rationale,
        priority=int(p.get("priority") or 100),
        effective_from=ef,
        effective_to=et,
        months=p.get("months") or [],
        weekdays=p.get("weekdays") or [],
        source="ai_proposal",
    )
    prop.status = "approved"
    prop.reviewed_by = user_id
    prop.rule_id = rule.id
    db.flush()
    return {"ok": True, "proposal_id": prop.id, "rule": _rule_dict(rule)}


def reject_proposal(db: Session, company_id: int, proposal_id: int, user_id: int) -> dict:
    prop = db.get(RuleProposal, proposal_id)
    if not prop or prop.company_id != company_id:
        return {"ok": False, "error": "not found"}
    prop.status = "rejected"
    prop.reviewed_by = user_id
    db.flush()
    return {"ok": True, "id": prop.id, "status": "rejected"}


def seed_demo_rules(db: Session, company_id: int) -> int:
    """Ensure a full set of demo rules so Automation never shows empty Rules Studio."""
    specs = [
        {
            "code": "discount_default_small",
            "scope": "discount",
            "name": "Small order courtesy 1%",
            "conditions": {"order_total": {"lte": 5000}},
            "actions": {"discount_pct": 1, "label": "Courtesy"},
            "priority": 10,
            "description": "Demo scoped rule — discount on small orders",
        },
        {
            "code": "reorder_factor_summer",
            "scope": "reorder",
            "name": "Summer reorder buffer +20%",
            "conditions": {"season": "summer"},
            "actions": {"reorder_factor": 1.2, "label": "Summer buffer"},
            "priority": 20,
            "description": "Raises purchase suggest qty in peak season",
        },
        {
            "code": "wa_chase_overdue",
            "scope": "reminder",
            "name": "Auto overdue WhatsApp chase",
            "conditions": {"days_overdue": {"gte": 3}},
            "actions": {"template": "invoice_overdue", "channel": "whatsapp"},
            "priority": 30,
            "description": "Triggers overdue chase template from Automation",
        },
        {
            "code": "credit_hold_soft",
            "scope": "credit",
            "name": "Soft credit hold above limit",
            "conditions": {"outstanding_over_limit": True},
            "actions": {"hold": "soft", "require_approval": True},
            "priority": 40,
            "description": "Dealer/customer over credit → soft hold",
        },
        {
            "code": "pos_weekend_offer",
            "scope": "pos_offer",
            "name": "Weekend POS 2% offer",
            "conditions": {"weekday_in": ["sat", "sun"]},
            "actions": {"discount_pct": 2, "label": "Weekend"},
            "priority": 15,
            "description": "Scan billing weekend courtesy offer",
        },
        {
            "code": "sla_service_48h",
            "scope": "sla",
            "name": "Service ticket 48h SLA",
            "conditions": {"ticket_age_hours": {"gte": 48}},
            "actions": {"escalate": True, "notify": "service_manager"},
            "priority": 25,
            "description": "Escalate open service tickets past 48h",
        },
    ]
    created = 0
    for s in specs:
        codes = {
            r.code
            for r in db.query(DynamicRule)
            .filter(DynamicRule.company_id == company_id, DynamicRule.code == s["code"])
            .all()
        }
        if s["code"] in codes:
            continue
        try:
            create_or_version_rule(
                db,
                company_id=company_id,
                code=s["code"],
                scope=s["scope"],
                name=s["name"],
                conditions=s["conditions"],
                actions=s["actions"],
                priority=s["priority"],
                source="seed",
                description=s["description"],
            )
            created += 1
        except Exception:
            continue
    return created
