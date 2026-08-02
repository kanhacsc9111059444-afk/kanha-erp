"""Connected Apps / Bridges API — Native vs Bridge vs Hybrid + third-party hooks."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from app.core.deps import CurrentUser, DbDep, assert_perm, audit
from app.services import bridges as br
from app.services import connectors as cx

router = APIRouter(prefix="/api/bridges", tags=["bridges"])


@router.get("")
def bridges_hub(user: CurrentUser, db: DbDep) -> dict:
    assert_perm(user, db, "settings.*", "bridges.*", "books.*", "accounting.*", "dashboard.*")
    return br.catalog_with_status(db, user.company_id)


@router.get("/channels")
def list_channels(user: CurrentUser, db: DbDep) -> dict:
    return bridges_hub(user, db)


# ── Third-party hooks (Marg / Busy / Vyapar / custom) — BEFORE /{channel_id} ─


@router.get("/hooks/presets")
def hook_presets(user: CurrentUser, db: DbDep) -> dict:
    assert_perm(user, db, "settings.*", "bridges.*")
    return {"ok": True, "presets": cx.list_presets(), "events": sorted(cx.ALLOWED_EVENTS)}


@router.get("/hooks")
def hooks_list(user: CurrentUser, db: DbDep) -> dict:
    assert_perm(user, db, "settings.*", "bridges.*")
    items = []
    for h in cx.list_hooks(db, user.company_id):
        items.append(
            {
                **h,
                "inbound_path": cx.public_inbound_path(h["id"]),
                "token_fingerprint": cx.fingerprint_token(h.get("inbound_token") or ""),
            }
        )
    return {
        "ok": True,
        "hooks": items,
        "inbox": cx.inbox(db, user.company_id),
        "log": cx.activity_log(db, user.company_id),
        "presets": cx.list_presets(),
    }


class HookCreateIn(BaseModel):
    preset: str = "custom"
    name: str = ""
    direction: str = "both"
    outbound_url: str = ""
    events: list[str] | None = None


@router.post("/hooks")
def hooks_create(body: HookCreateIn, user: CurrentUser, db: DbDep) -> dict:
    assert_perm(user, db, "settings.*", "bridges.*")
    try:
        hook = cx.create_hook(
            db,
            user.company_id,
            preset=body.preset,
            name=body.name,
            direction=body.direction,
            outbound_url=body.outbound_url,
            events=body.events,
            created_by=getattr(user, "email", "") or "",
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    audit(
        db,
        company_id=user.company_id,
        user_id=user.id,
        action="hook_create",
        entity="third_party_hook",
        entity_id=hook["id"],
        detail={"preset": hook["preset"], "name": hook["name"]},
    )
    return {
        "ok": True,
        "hook": hook,
        "inbound_url_hint": cx.public_inbound_path(hook["id"]) + "?token=…",
        "message": f"Hook ready · {hook['name']} ({hook['preset']})",
    }


class HookPatchIn(BaseModel):
    name: str | None = None
    status: str | None = None
    direction: str | None = None
    outbound_url: str | None = None
    events: list[str] | None = None
    rotate_token: bool = False


@router.post("/hooks/{hook_id}")
def hooks_update(hook_id: str, body: HookPatchIn, user: CurrentUser, db: DbDep) -> dict:
    assert_perm(user, db, "settings.*", "bridges.*")
    try:
        hook = cx.update_hook(db, user.company_id, hook_id, body.model_dump(exclude_unset=True))
    except ValueError as exc:
        raise HTTPException(404 if "not found" in str(exc).lower() else 400, str(exc)) from exc
    return {"ok": True, "hook": hook, "message": "Hook updated"}


@router.post("/hooks/{hook_id}/delete")
def hooks_delete(hook_id: str, user: CurrentUser, db: DbDep) -> dict:
    assert_perm(user, db, "settings.*", "bridges.*")
    ok = cx.delete_hook(db, user.company_id, hook_id)
    if not ok:
        raise HTTPException(404, "Hook not found")
    return {"ok": True, "message": "Hook removed"}


class HookPushIn(BaseModel):
    event: str = "generic"
    payload: dict[str, Any] = Field(default_factory=dict)
    hook_id: str | None = None


@router.post("/hooks/push")
def hooks_push(body: HookPushIn, user: CurrentUser, db: DbDep) -> dict:
    assert_perm(user, db, "settings.*", "bridges.*", "sales.*")
    return cx.push_event(
        db,
        user.company_id,
        event=body.event,
        payload=body.payload or {"note": "manual test push"},
        hook_id=body.hook_id,
    )


@router.get("/intelligence")
def intelligence_state(user: CurrentUser, db: DbDep) -> dict:
    assert_perm(user, db, "settings.*", "bridges.*", "ai.*", "dashboard.*")
    from app.services.bridge_intelligence import get_state

    return {"ok": True, **get_state(db, user.company_id)}


@router.post("/intelligence/learn")
def intelligence_learn(user: CurrentUser, db: DbDep, auto_fix: bool = False) -> dict:
    """Run curriculum phases 1–5 + 7–9. Pass auto_fix=1 to include safe fix (phase 6)."""
    assert_perm(user, db, "settings.*", "bridges.*", "ai.*")
    from app.services.bridge_intelligence import run_learn_cycle

    return run_learn_cycle(db, user.company_id, auto_safe_fix=bool(auto_fix))


@router.post("/intelligence/learn-full")
def intelligence_learn_full(user: CurrentUser, db: DbDep) -> dict:
    """All 9 learning phases including safe improve — full internal curriculum."""
    assert_perm(user, db, "settings.*", "bridges.*", "ai.*")
    from app.services.bridge_intelligence import run_full_curriculum

    r = run_full_curriculum(db, user.company_id, auto_safe_fix=True)
    audit(
        db,
        company_id=user.company_id,
        user_id=user.id,
        action="bridge_intelligence_learn_full",
        entity="bridge_intelligence",
        entity_id="curriculum",
        detail={
            "accuracy": r.get("accuracy"),
            "trust": r.get("trust_score"),
            "phases": (r.get("run") or {}).get("phases_done"),
        },
    )
    return r


@router.post("/intelligence/improve")
def intelligence_improve(user: CurrentUser, db: DbDep) -> dict:
    """Safe improves only — empty GSTIN/barcode/party create. Never auto-fix money conflicts."""
    assert_perm(user, db, "settings.*", "bridges.*")
    from app.services.bridge_intelligence import apply_safe_improvements

    r = apply_safe_improvements(db, user.company_id)
    audit(
        db,
        company_id=user.company_id,
        user_id=user.id,
        action="bridge_intelligence_improve",
        entity="bridge_intelligence",
        entity_id="safe",
        detail={"count": r.get("count")},
    )
    return r


class HookInboundIn(BaseModel):
    event: str = "generic"
    payload: dict[str, Any] = Field(default_factory=dict)
    token: str = ""


@router.post("/hooks/inbound/{hook_id}")
def hooks_inbound(hook_id: str, body: HookInboundIn, request: Request, db: DbDep, token: str | None = None) -> dict:
    """Public inbound webhook — auth by hook token (query or body). No JWT."""
    tok = (token or body.token or request.headers.get("X-Kanha-Token") or "").strip()
    if not tok:
        raise HTTPException(401, "token required")
    try:
        return cx.receive_inbound(
            db,
            hook_id=hook_id,
            token=tok,
            event=body.event or "generic",
            payload=body.payload or {},
            headers=dict(request.headers),
        )
    except PermissionError as exc:
        raise HTTPException(403, str(exc)) from exc


class ModeIn(BaseModel):
    mode: str = Field(pattern="^(native|bridge|hybrid)$")


@router.post("/{channel_id}/mode")
def set_mode(channel_id: str, body: ModeIn, user: CurrentUser, db: DbDep) -> dict:
    if channel_id in ("hooks", "tally", "erp", "outbox", "channels", "seed-defaults", "intelligence"):
        raise HTTPException(404, "Not a channel")
    assert_perm(user, db, "settings.*", "bridges.*")
    try:
        st = br.set_bridge_mode(
            db,
            user.company_id,
            channel_id,
            body.mode,
            updated_by=getattr(user, "email", "") or getattr(user, "full_name", "") or "admin",
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    audit(
        db,
        company_id=user.company_id,
        user_id=user.id,
        action="bridge_mode",
        entity="bridge",
        entity_id=channel_id,
        detail={"mode": body.mode},
    )
    return {"ok": True, "channel_id": channel_id, "state": st, "message": f"{channel_id} → {body.mode}"}


@router.get("/outbox")
def outbox(user: CurrentUser, db: DbDep) -> dict:
    assert_perm(user, db, "settings.*", "bridges.*", "books.*")
    rows = list(reversed(br.get_outbox(db, user.company_id)))
    return {"ok": True, "jobs": rows, "count": len(rows)}


@router.get("/erp/targets")
def erp_targets(user: CurrentUser, db: DbDep) -> dict:
    """Tally + Marg + Busy + Vyapar + Other — data bridge catalog (alongside existing Tally)."""
    assert_perm(user, db, "settings.*", "bridges.*", "books.*", "accounting.*")
    return {
        "ok": True,
        "targets": br.list_erp_targets(),
        "note": "Existing Tally export/import APIs remain. Marg/other use /erp/{target}/export.",
    }


@router.post("/erp/{target}/export")
def erp_export(target: str, user: CurrentUser, db: DbDep) -> dict:
    assert_perm(user, db, "settings.*", "bridges.*", "books.*", "accounting.*")
    try:
        pack = br.build_erp_pack(db, user.company_id, target)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    job = br.enqueue(
        db,
        user.company_id,
        channel="accounting",
        action=f"{pack['target']}_export_pack",
        title=f"{pack['target_label']} export pack ready",
        payload={
            "format": pack["format"],
            "target": pack["target"],
            "vouchers": len(pack.get("vouchers") or []),
            "journals": len(pack.get("journal_vouchers") or []),
            "items": len(pack.get("items") or []),
        },
    )
    br.mark_outbox(
        db,
        user.company_id,
        job["id"],
        "exported",
        {"note": f"Download pack · import in {pack['target_label']}"},
    )
    return {
        "ok": True,
        "job_id": job["id"],
        "pack": pack,
        "message": f"{pack['target_label']} pack built · queued as exported",
    }


@router.get("/erp/{target}/pack")
def erp_pack_get(target: str, user: CurrentUser, db: DbDep) -> dict:
    assert_perm(user, db, "settings.*", "bridges.*", "books.*", "accounting.*")
    try:
        return br.build_erp_pack(db, user.company_id, target)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


class ErpImportIn(BaseModel):
    rows: list[dict[str, Any]] = Field(default_factory=list)
    source: str = ""


@router.post("/erp/{target}/import")
def erp_import(target: str, body: ErpImportIn, user: CurrentUser, db: DbDep) -> dict:
    assert_perm(user, db, "settings.*", "bridges.*", "books.*")
    tid = (target or "other").strip().lower()
    meta = next((t for t in br.list_erp_targets() if t["id"] == tid), None)
    if not meta:
        raise HTTPException(400, f"Unknown target {target}")
    rows = body.rows or []
    source = body.source or f"{tid}_csv"
    job = br.enqueue(
        db,
        user.company_id,
        channel="accounting",
        action=f"{tid}_import",
        title=f"{meta['label']} import · {len(rows)} rows",
        payload={"source": source, "target": tid, "rows": rows[:500], "count": len(rows)},
    )
    br.mark_outbox(
        db,
        user.company_id,
        job["id"],
        "imported",
        {"accepted": len(rows), "note": f"Stored on bridge outbox ({meta['label']})"},
    )
    learn = None
    try:
        from app.services.bridge_intelligence import learn_from_inbound, run_learn_cycle

        for row in rows[:30]:
            if isinstance(row, dict):
                learn_from_inbound(db, user.company_id, row, source=f"{tid}_import")
        learn = run_learn_cycle(db, user.company_id, limit=30)
    except Exception:
        learn = None
    return {
        "ok": True,
        "job_id": job["id"],
        "target": tid,
        "accepted": len(rows),
        "learn": learn,
        "message": f"Accepted {len(rows)} {meta['label']} rows into bridge"
        + (f" · trust {learn.get('trust_score')}" if learn else ""),
    }


# ── SBAC Tally desk: Parent mapping · Inactive · Errors ──────────────────────


@router.get("/tally/sync")
def tally_sync_get(user: CurrentUser, db: DbDep) -> dict:
    assert_perm(user, db, "settings.*", "bridges.*", "books.*", "accounting.*")
    return {"ok": True, **br.tally_sync_desk(db, user.company_id)}


class ParentMapIn(BaseModel):
    erp_parent: str
    tally_name: str


@router.post("/tally/parent-mapping")
def tally_parent_mapping(body: ParentMapIn, user: CurrentUser, db: DbDep) -> dict:
    """SBAC TallyErpparentmapping — map Kanha/ERP parent → Tally ledger name."""
    assert_perm(user, db, "settings.*", "bridges.*", "books.*", "accounting.*")
    try:
        data = br.upsert_parent_mapping(
            db, user.company_id, erp_parent=body.erp_parent, tally_name=body.tally_name
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    audit(
        db,
        company_id=user.company_id,
        user_id=user.id,
        action="tally_parent_map",
        entity="tally_sync",
        entity_id=body.erp_parent,
        detail={"tally_name": body.tally_name},
    )
    return {"ok": True, **data, "message": f"Mapped {body.erp_parent} → {body.tally_name}"}


class InactiveLedgerIn(BaseModel):
    name: str = ""
    code: str = ""
    inactive: bool = True


@router.post("/tally/inactive-ledgers")
def tally_inactive_ledger(body: InactiveLedgerIn, user: CurrentUser, db: DbDep) -> dict:
    """SBAC InactiveLedgerForTally — mark ledger inactive for Tally push."""
    assert_perm(user, db, "settings.*", "bridges.*", "books.*", "accounting.*")
    try:
        data = br.set_inactive_ledger(
            db, user.company_id, name=body.name, code=body.code, inactive=body.inactive
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return {
        "ok": True,
        **data,
        "message": f"Ledger {'inactive' if body.inactive else 'active'} for Tally",
    }


class InactiveItemIn(BaseModel):
    name: str = ""
    sku: str = ""
    inactive: bool = True


@router.post("/tally/inactive-items")
def tally_inactive_item(body: InactiveItemIn, user: CurrentUser, db: DbDep) -> dict:
    """SBAC InactiveItemForTally — mark item inactive for Tally push."""
    assert_perm(user, db, "settings.*", "bridges.*", "inventory.*", "books.*")
    try:
        data = br.set_inactive_item(
            db, user.company_id, name=body.name, sku=body.sku, inactive=body.inactive
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return {
        "ok": True,
        **data,
        "message": f"Item {'inactive' if body.inactive else 'active'} for Tally",
    }


@router.get("/tally/errors")
def tally_errors_get(
    user: CurrentUser,
    db: DbDep,
    from_date: str = "",
    to_date: str = "",
    doc_type: str = "",
) -> dict:
    """SBAC Tallyerror — filter by from/to + doc type (Contra/Journal/Payment/Purchase/Receipt/Sale)."""
    assert_perm(user, db, "settings.*", "bridges.*", "books.*", "accounting.*")
    rows = br.filter_tally_errors(
        db, user.company_id, from_date=from_date, to_date=to_date, doc_type=doc_type
    )
    return {"ok": True, "errors": rows, "count": len(rows)}


class TallyErrorIn(BaseModel):
    doc_type: str = "Sale"
    message: str = ""
    ref: str = ""
    from_date: str = ""
    to_date: str = ""


@router.post("/tally/errors")
def tally_errors_log(body: TallyErrorIn, user: CurrentUser, db: DbDep) -> dict:
    assert_perm(user, db, "settings.*", "bridges.*", "books.*")
    data = br.log_tally_error(
        db,
        user.company_id,
        doc_type=body.doc_type,
        message=body.message,
        ref=body.ref,
        from_date=body.from_date,
        to_date=body.to_date,
    )
    return {"ok": True, **data, "message": "Tally error logged"}


@router.post("/tally/export")
def tally_export(user: CurrentUser, db: DbDep) -> dict:
    """Existing Tally path — kept; delegates to unified ERP pack."""
    return erp_export("tally", user, db)


@router.get("/tally/pack")
def tally_pack_get(user: CurrentUser, db: DbDep) -> dict:
    assert_perm(user, db, "settings.*", "bridges.*", "books.*", "accounting.*")
    return br.build_tally_pack(db, user.company_id)


class TallyImportIn(BaseModel):
    rows: list[dict[str, Any]] = Field(default_factory=list)
    source: str = "tally_csv"


@router.post("/tally/import")
def tally_import(body: TallyImportIn, user: CurrentUser, db: DbDep) -> dict:
    """Existing Tally import — kept."""
    return erp_import("tally", ErpImportIn(rows=body.rows, source=body.source or "tally_csv"), user, db)


@router.post("/outbox/{job_id}/run")
def run_outbox_job(job_id: str, user: CurrentUser, db: DbDep) -> dict:
    assert_perm(user, db, "settings.*", "bridges.*")
    rows = br.get_outbox(db, user.company_id)
    job = next((j for j in rows if j.get("id") == job_id), None)
    if not job:
        raise HTTPException(404, "Job not found")
    updated = br.mark_outbox(
        db,
        user.company_id,
        job_id,
        "synced",
        {"note": "Demo-live bridge sync OK"},
    )
    return {"ok": True, "job": updated, "message": f"Bridge job {job_id} synced"}


@router.post("/seed-defaults")
def seed_defaults(user: CurrentUser, db: DbDep) -> dict:
    assert_perm(user, db, "settings.*", "bridges.*")
    from app.models import Company

    co = db.get(Company, user.company_id)
    if not co:
        raise HTTPException(404, "Company not found")
    sj = dict(co.settings_json or {})
    if not sj.get("bridges"):
        sj["bridges"] = br.default_bridges_state()
        co.settings_json = sj
        db.commit()
    return br.catalog_with_status(db, user.company_id)
