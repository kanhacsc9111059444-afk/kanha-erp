"""Dynamic Rules Studio API — scoped, time-based, AI-propose / human-apply."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.core.deps import CurrentUser, DbDep, assert_perm, audit
from app.models import RuleProposal
from app.services.rules_engine import (
    SAFE_SCOPES,
    approve_proposal,
    create_or_version_rule,
    create_proposal,
    evaluate,
    list_rules,
    pause_rule,
    reject_proposal,
    retire_rule,
    seasonal_proposals,
    seed_demo_rules,
)

router = APIRouter(prefix="/api/rules", tags=["rules"])


@router.get("/scopes")
def rules_scopes(user: CurrentUser, db: DbDep) -> dict:
    assert_perm(user, db, "automation.*", "settings.*", "agents.*")
    return {
        "ok": True,
        "scopes": [{"id": k, "label": v} for k, v in SAFE_SCOPES.items()],
        "principle": "AI proposes inside scope only — never rewrites whole ERP core.",
    }


@router.get("")
def rules_list(user: CurrentUser, db: DbDep, scope: str | None = None) -> dict:
    assert_perm(user, db, "automation.*", "settings.*", "agents.*")
    seed_demo_rules(db, user.company_id)
    db.commit()
    return {"ok": True, "rules": list_rules(db, user.company_id, scope=scope)}


class RuleIn(BaseModel):
    code: str
    name: str = ""
    scope: str
    description: str = ""
    conditions: dict[str, Any] = Field(default_factory=dict)
    actions: dict[str, Any] = Field(default_factory=dict)
    priority: int = 100
    effective_from: str | None = None
    effective_to: str | None = None
    months: list[int] = Field(default_factory=list)
    weekdays: list[int] = Field(default_factory=list)


@router.post("")
def rules_create(body: RuleIn, user: CurrentUser, db: DbDep) -> dict:
    assert_perm(user, db, "automation.*", "settings.*")
    try:
        ef = datetime.fromisoformat(body.effective_from.replace("Z", "")) if body.effective_from else None
        et = datetime.fromisoformat(body.effective_to.replace("Z", "")) if body.effective_to else None
        row = create_or_version_rule(
            db,
            company_id=user.company_id,
            code=body.code,
            scope=body.scope,
            name=body.name,
            conditions=body.conditions,
            actions=body.actions,
            user_id=user.id,
            description=body.description,
            priority=body.priority,
            effective_from=ef,
            effective_to=et,
            months=body.months,
            weekdays=body.weekdays,
            source="manual",
        )
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    audit(db, company_id=user.company_id, user_id=user.id, action="rule_upsert", entity="dynamic_rule", entity_id=row.code)
    db.commit()
    return {"ok": True, "id": row.id, "code": row.code, "version": row.version, "message": f"Rule {row.code} v{row.version} active (scoped: {row.scope})"}


class EvalIn(BaseModel):
    scope: str
    context: dict[str, Any] = Field(default_factory=dict)


@router.post("/evaluate")
def rules_evaluate(body: EvalIn, user: CurrentUser, db: DbDep) -> dict:
    assert_perm(user, db, "automation.*", "settings.*", "sales.*", "agents.*")
    try:
        return evaluate(db, user.company_id, body.scope, body.context)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e


@router.post("/{rule_id}/pause")
def rules_pause(rule_id: int, user: CurrentUser, db: DbDep) -> dict:
    assert_perm(user, db, "automation.*", "settings.*")
    r = pause_rule(db, user.company_id, rule_id)
    if not r.get("ok"):
        raise HTTPException(404, r.get("error"))
    db.commit()
    return r


@router.post("/{rule_id}/retire")
def rules_retire(rule_id: int, user: CurrentUser, db: DbDep) -> dict:
    assert_perm(user, db, "automation.*", "settings.*")
    r = retire_rule(db, user.company_id, rule_id)
    if not r.get("ok"):
        raise HTTPException(404, r.get("error"))
    audit(db, company_id=user.company_id, user_id=user.id, action="rule_retire", entity="dynamic_rule", entity_id=str(rule_id))
    db.commit()
    return r


@router.get("/proposals")
def proposals_list(user: CurrentUser, db: DbDep, status: str = "pending") -> dict:
    assert_perm(user, db, "automation.*", "settings.*", "agents.*")
    q = db.query(RuleProposal).filter(RuleProposal.company_id == user.company_id)
    if status != "all":
        q = q.filter(RuleProposal.status == status)
    rows = q.order_by(RuleProposal.id.desc()).limit(50).all()
    return {
        "ok": True,
        "proposals": [
            {
                "id": p.id,
                "scope": p.scope,
                "title": p.title,
                "rationale": p.rationale,
                "proposed": p.proposed,
                "status": p.status,
                "rule_id": p.rule_id,
            }
            for p in rows
        ],
    }


@router.post("/agent/learn")
def rules_agent_learn(user: CurrentUser, db: DbDep) -> dict:
    """
    Rules Agent: learn seasonal / time-based improvements → proposals only.
    Does NOT auto-apply (safe future-proof).
    """
    assert_perm(user, db, "automation.*", "settings.*", "agents.*")
    ideas = seasonal_proposals(user.company_id, user.id)
    # Optional LLM enrichment later — base set always works
    created = []
    for idea in ideas:
        # skip if same code already pending
        code = (idea.get("proposed") or {}).get("code")
        exists = False
        if code:
            for p in db.query(RuleProposal).filter(RuleProposal.company_id == user.company_id, RuleProposal.status == "pending").all():
                if (p.proposed or {}).get("code") == code:
                    exists = True
                    break
        if exists:
            continue
        row = create_proposal(db, user.company_id, idea, user.id)
        created.append({"id": row.id, "title": row.title, "scope": row.scope})
    audit(db, company_id=user.company_id, user_id=user.id, action="rules_learn", entity="rule_proposal", detail={"count": len(created)})
    db.commit()
    return {
        "ok": True,
        "created": created,
        "count": len(created),
        "message": f"Rules Agent proposed {len(created)} scoped improvements — review & Approve (no auto whole-ERP change)",
    }


@router.post("/proposals/{proposal_id}/approve")
def proposals_approve(proposal_id: int, user: CurrentUser, db: DbDep) -> dict:
    assert_perm(user, db, "automation.*", "settings.*")
    try:
        r = approve_proposal(db, user.company_id, proposal_id, user.id)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    if not r.get("ok"):
        raise HTTPException(400, r.get("error") or "failed")
    audit(db, company_id=user.company_id, user_id=user.id, action="rule_approve", entity="rule_proposal", entity_id=str(proposal_id))
    db.commit()
    return r


@router.post("/proposals/{proposal_id}/reject")
def proposals_reject(proposal_id: int, user: CurrentUser, db: DbDep) -> dict:
    assert_perm(user, db, "automation.*", "settings.*")
    r = reject_proposal(db, user.company_id, proposal_id, user.id)
    if not r.get("ok"):
        raise HTTPException(404, r.get("error"))
    db.commit()
    return r
