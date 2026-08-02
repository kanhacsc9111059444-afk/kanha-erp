"""Multi-site HA / portable ERP APIs."""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Header, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app.core.config import settings
from app.core.deps import CurrentUser, DbDep, assert_perm
from app.core.database import SessionLocal
from app.services.ha_cluster import (
    cluster_status,
    current_seq,
    events_since,
    promote_self,
    publish_snapshot,
    record_peer_heartbeat,
    upsert_self_node,
)
from app.services.ha_portable import file_checksum, mirror_portable_to_all_sites, sqlite_db_path
from app.services.ha_sync import ha_tick, pull_latest_from_primary

router = APIRouter(prefix="/api/ha", tags=["ha"])


def _check_cluster_token(token: str | None) -> None:
    if not token or token != settings.cluster_token:
        raise HTTPException(401, "Invalid cluster token")


@router.get("/status")
def ha_status(user: CurrentUser, db: DbDep) -> dict:
    assert_perm(user, db, "settings.*", "ha.*")
    return cluster_status(db)


@router.get("/risks")
def ha_risks(user: CurrentUser, db: DbDep) -> dict:
    """Realtime production risks + what protections are ON."""
    assert_perm(user, db, "settings.*", "ha.*")
    from app.services.ha_protect import assess_risks

    return assess_risks(db)


@router.get("/public-status")
def ha_public_status(x_cluster_token: str | None = Header(default=None, alias="X-Cluster-Token")) -> dict:
    """Peer-visible status (token)."""
    _check_cluster_token(x_cluster_token)
    db = SessionLocal()
    try:
        return cluster_status(db)
    finally:
        db.close()


class HeartbeatIn(BaseModel):
    node_id: str
    role: str = "replica"
    public_url: str = ""
    priority: int = 100
    last_seq: int = 0
    last_checksum: str = ""
    fence_epoch: int = 0


@router.post("/heartbeat")
def ha_heartbeat(
    body: HeartbeatIn,
    x_cluster_token: str | None = Header(default=None, alias="X-Cluster-Token"),
) -> dict:
    _check_cluster_token(x_cluster_token)
    db = SessionLocal()
    try:
        node = record_peer_heartbeat(db, body.model_dump())
        upsert_self_node(db)
        from app.services.ha_protect import apply_peer_fence

        demote = apply_peer_fence(db, body.model_dump())
        db.commit()
        out = {"ok": True, "received": node.node_id, "self_role": settings.cluster_role}
        if demote:
            out["demoted"] = demote
        return out
    finally:
        db.close()


@router.get("/snapshot/meta")
def snapshot_meta(x_cluster_token: str | None = Header(default=None, alias="X-Cluster-Token")) -> dict:
    _check_cluster_token(x_cluster_token)
    db = SessionLocal()
    try:
        db_path = sqlite_db_path()
        return {
            "seq": current_seq(db),
            "checksum": file_checksum(db_path) if db_path else "",
            "node_id": settings.cluster_node_id,
            "role": settings.cluster_role,
            "app": settings.app_name,
            "version": settings.app_version,
        }
    finally:
        db.close()


@router.get("/snapshot/download")
def snapshot_download(x_cluster_token: str | None = Header(default=None, alias="X-Cluster-Token")):
    _check_cluster_token(x_cluster_token)
    # Prefer first mirror LATEST.zip, else build quickly into data/mirrors/site-1
    mirrors = settings.mirror_paths()
    for m in mirrors:
        z = m / "LATEST.zip"
        if z.exists():
            return FileResponse(z, filename="LATEST.zip", media_type="application/zip")
    db = SessionLocal()
    try:
        publish_snapshot(db)
    finally:
        db.close()
    z = mirrors[0] / "LATEST.zip"
    if not z.exists():
        raise HTTPException(404, "Snapshot not available")
    return FileResponse(z, filename="LATEST.zip", media_type="application/zip")


@router.get("/events")
def ha_events(
    since: int = 0,
    x_cluster_token: str | None = Header(default=None, alias="X-Cluster-Token"),
) -> dict:
    _check_cluster_token(x_cluster_token)
    db = SessionLocal()
    try:
        return {"events": events_since(db, since), "head_seq": current_seq(db)}
    finally:
        db.close()


@router.post("/publish")
def ha_publish(user: CurrentUser, db: DbDep) -> dict:
    assert_perm(user, db, "settings.*", "ha.*")
    return publish_snapshot(db)


@router.post("/sync-now")
def ha_sync_now(user: CurrentUser, db: DbDep) -> dict:
    assert_perm(user, db, "settings.*", "ha.*")
    if settings.cluster_role == "primary":
        return publish_snapshot(db)
    return pull_latest_from_primary()


@router.post("/promote")
def ha_promote(user: CurrentUser, db: DbDep) -> dict:
    assert_perm(user, db, "settings.*", "ha.*")
    return promote_self(db, reason="admin_force")


@router.post("/tick")
def ha_run_tick(user: CurrentUser, db: DbDep) -> dict:
    assert_perm(user, db, "settings.*", "ha.*")
    return ha_tick()


@router.post("/mirror-all")
def ha_mirror_all(user: CurrentUser, db: DbDep) -> dict:
    assert_perm(user, db, "settings.*", "ha.*")
    seq = current_seq(db) or 1
    return mirror_portable_to_all_sites(seq)


@router.get("/failed-entries")
def ha_failed_entries(user: CurrentUser, db: DbDep, status: str = "pending") -> dict:
    """Entry crashes waiting for Re-enter / dismiss."""
    assert_perm(user, db, "settings.*", "ha.*")
    from app.services.ha_heal import list_failed_entries

    st = status if status != "all" else None
    rows = list_failed_entries(db, status=st)
    return {"ok": True, "count": len(rows), "entries": rows}


class HealIn(BaseModel):
    note: str = ""
    status: str = "healed"  # healed | reentered | dismissed


@router.post("/failed-entries/{entry_id}/heal")
def ha_heal_entry(entry_id: int, body: HealIn, user: CurrentUser, db: DbDep) -> dict:
    assert_perm(user, db, "settings.*", "ha.*")
    from app.services.ha_heal import mark_healed

    return mark_healed(db, entry_id, note=body.note or f"Healed by {user.email}", status=body.status)


@router.post("/failed-entries/{entry_id}/reenter")
def ha_reenter(entry_id: int, user: CurrentUser, db: DbDep) -> dict:
    """Return saved payload so UI can replay the entry (auto re-entry after crash)."""
    assert_perm(user, db, "settings.*", "ha.*")
    from app.models import FailedEntry

    row = db.get(FailedEntry, entry_id)
    if not row:
        raise HTTPException(404, "Failed entry not found")
    if row.heal_status not in ("pending", "healed"):
        raise HTTPException(400, f"Entry status is {row.heal_status}")
    return {
        "ok": True,
        "mode": "client_replay",
        "message": "Payload ready — UI will replay the entry",
        "reentry": {
            "id": row.id,
            "method": row.method,
            "path": row.path,
            "body": row.payload or {},
        },
    }


# ── Emergency blackout + portable + auto-config ───────────────────────────────


class BlackoutEngageIn(BaseModel):
    confirm: str
    reason: str = "disaster / blackout / connectivity loss"


class BlackoutUnlockIn(BaseModel):
    confirm: str


@router.get("/blackout")
def ha_blackout_status(user: CurrentUser, db: DbDep) -> dict:
    assert_perm(user, db, "settings.*", "ha.*")
    from app.services.blackout import blackout_status

    return {"ok": True, **blackout_status(db)}


@router.post("/blackout/engage")
def ha_blackout_engage(body: BlackoutEngageIn, user: CurrentUser, db: DbDep) -> dict:
    """Disaster mode: freeze entries + save portable ERP to all mirrors."""
    assert_perm(user, db, "settings.*", "ha.*")
    from app.services.blackout import CONFIRM_ENGAGE, engage_blackout

    if (body.confirm or "").strip() != CONFIRM_ENGAGE:
        raise HTTPException(400, f'Type exactly "{CONFIRM_ENGAGE}" to engage blackout')
    result = engage_blackout(db, reason=body.reason, engaged_by=user.email, mirror=True)
    db.commit()
    return result


@router.post("/blackout/unlock")
def ha_blackout_unlock(body: BlackoutUnlockIn, user: CurrentUser, db: DbDep) -> dict:
    assert_perm(user, db, "settings.*", "ha.*")
    from app.services.blackout import CONFIRM_UNLOCK, unlock_blackout

    if (body.confirm or "").strip() != CONFIRM_UNLOCK:
        raise HTTPException(400, f'Type exactly "{CONFIRM_UNLOCK}" to resume live entries')
    result = unlock_blackout(db, unlocked_by=user.email)
    db.commit()
    return result


@router.get("/portable/download")
def ha_portable_download(user: CurrentUser, db: DbDep):
    """Download latest portable ERP zip (works during blackout)."""
    assert_perm(user, db, "settings.*", "ha.*")
    from app.core.config import BACKUP
    from app.services.ha_cluster import current_seq
    from app.services.ha_portable import build_portable_pack

    latest = BACKUP / "LATEST.zip"
    if not latest.exists():
        build_portable_pack(BACKUP, seq=current_seq(db) + 1, role_hint="download")
        db.commit()
    if not latest.exists():
        raise HTTPException(404, "Portable pack not found — try Mirror all first")
    return FileResponse(
        path=str(latest),
        filename=f"kanha_portable_erp.zip",
        media_type="application/zip",
    )


@router.get("/auto-config")
def ha_auto_config(user: CurrentUser, db: DbDep) -> dict:
    assert_perm(user, db, "settings.*", "ha.*")
    from app.services.auto_configure import discover

    return discover(db)


class AutoConfigApplyIn(BaseModel):
    adopt_mirrors: bool = False


@router.post("/auto-config/apply")
def ha_auto_config_apply(body: AutoConfigApplyIn, user: CurrentUser, db: DbDep) -> dict:
    assert_perm(user, db, "settings.*", "ha.*")
    from app.services.auto_configure import apply_auto_config

    result = apply_auto_config(db, adopt_mirrors=body.adopt_mirrors)
    db.commit()
    return result


class AdoptIn(BaseModel):
    primary_url: str
    role: str = "replica"  # replica | primary


@router.post("/adopt")
def ha_adopt(body: AdoptIn, user: CurrentUser, db: DbDep) -> dict:
    """Adopt another server as primary when connectivity returns elsewhere."""
    assert_perm(user, db, "settings.*", "ha.*")
    from app.services.auto_configure import adopt_primary_url

    url = (body.primary_url or "").strip().rstrip("/")
    if not url.startswith("http"):
        raise HTTPException(400, "primary_url must be http(s)://…")
    result = adopt_primary_url(url, role=(body.role or "replica").lower(), db=db)
    db.commit()
    # Best-effort reachability probe
    probe = {"reachable": False}
    try:
        import httpx

        with httpx.Client(timeout=5) as client:
            r = client.get(f"{url}/api/health")
            probe = {"reachable": r.status_code < 500, "status": r.status_code}
    except Exception as e:
        probe = {"reachable": False, "error": str(e)}
    result["probe"] = probe
    result["message"] = (
        f"Adopted {url} — sync/writes will follow this primary when reachable."
        if probe.get("reachable")
        else f"Adopted {url} (offline now) — will connect when that server is up."
    )
    return result
