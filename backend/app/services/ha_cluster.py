from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import ClusterNode, SyncEvent, SyncState
from app.services.ha_portable import file_checksum, mirror_portable_to_all_sites, sqlite_db_path

log = logging.getLogger("kanha.ha")


def _get_state(db: Session, key: str) -> dict:
    row = db.query(SyncState).filter(SyncState.key == key).first()
    return dict(row.value or {}) if row else {}


def _set_state(db: Session, key: str, value: dict) -> None:
    row = db.query(SyncState).filter(SyncState.key == key).first()
    if not row:
        row = SyncState(key=key, value=value)
        db.add(row)
    else:
        row.value = value
    db.flush()


def current_seq(db: Session) -> int:
    st = _get_state(db, "replication")
    return int(st.get("seq") or 0)


def bump_seq(db: Session, checksum: str = "") -> int:
    st = _get_state(db, "replication")
    seq = int(st.get("seq") or 0) + 1
    st.update({"seq": seq, "checksum": checksum, "updated_at": datetime.utcnow().isoformat() + "Z"})
    _set_state(db, "replication", st)
    db.add(
        SyncEvent(
            seq=seq,
            event_type="snapshot",
            entity="database",
            entity_id=str(seq),
            payload={"node_id": settings.cluster_node_id, "checksum": checksum},
            checksum=checksum,
        )
    )
    db.flush()
    return seq


def upsert_self_node(db: Session, *, checksum: str = "", seq: int | None = None) -> ClusterNode:
    node = db.query(ClusterNode).filter(ClusterNode.node_id == settings.cluster_node_id).first()
    if not node:
        node = ClusterNode(node_id=settings.cluster_node_id)
        db.add(node)
    node.role = settings.cluster_role
    node.public_url = settings.cluster_public_url
    node.priority = int(settings.cluster_priority)
    node.last_heartbeat = datetime.utcnow()
    node.status = "online"
    if seq is not None:
        node.last_seq = seq
    if checksum:
        node.last_checksum = checksum
    node.meta = {
        **(node.meta or {}),
        "app_version": settings.app_version,
        "is_primary_config": settings.cluster_role == "primary",
    }
    db.flush()
    return node


def record_peer_heartbeat(db: Session, body: dict) -> ClusterNode:
    nid = body.get("node_id") or ""
    if not nid:
        raise ValueError("node_id required")
    node = db.query(ClusterNode).filter(ClusterNode.node_id == nid).first()
    if not node:
        node = ClusterNode(node_id=nid)
        db.add(node)
    node.role = body.get("role") or node.role
    node.public_url = body.get("public_url") or node.public_url
    node.priority = int(body.get("priority") or node.priority or 100)
    node.last_seq = int(body.get("last_seq") or node.last_seq or 0)
    node.last_checksum = body.get("last_checksum") or node.last_checksum
    node.last_heartbeat = datetime.utcnow()
    node.status = "online"
    db.flush()
    return node


def mark_stale_nodes(db: Session) -> list[str]:
    cut = datetime.utcnow() - timedelta(seconds=int(settings.cluster_failover_after_seconds))
    stale = []
    for n in db.query(ClusterNode).all():
        if n.node_id == settings.cluster_node_id:
            continue
        if not n.last_heartbeat or n.last_heartbeat < cut:
            if n.status != "offline":
                n.status = "stale" if n.last_heartbeat else "offline"
                stale.append(n.node_id)
    db.flush()
    return stale


def cluster_status(db: Session) -> dict[str, Any]:
    upsert_self_node(db)
    mark_stale_nodes(db)
    nodes = db.query(ClusterNode).order_by(ClusterNode.priority.desc()).all()
    seq = current_seq(db)
    db_path = sqlite_db_path()
    checksum = file_checksum(db_path) if db_path else ""
    primary = next((n for n in nodes if n.role == "primary" and n.status in ("online", "promoted")), None)
    mirrors = []
    for i, p in enumerate(settings.mirror_paths(), start=1):
        latest_zip = p / "LATEST.zip"
        latest_dir = p / "LATEST"
        has_latest = latest_zip.exists() or latest_dir.exists()
        m_sum = ""
        if latest_zip.exists():
            try:
                m_sum = file_checksum(latest_zip)[:16]
            except Exception:
                m_sum = ""
        mirrors.append(
            {
                "site": f"site-{i}" if i <= 5 else "user-pack",
                "path": str(p),
                "has_latest": has_latest,
                "checksum": m_sum,
            }
        )
    out: dict[str, Any] = {
        "enabled": settings.cluster_enabled,
        "architecture": "primary_writer + hot_replicas + 5_identical_mirrors",
        "why_not_5_writers": (
            "5 simultaneous writers cause split-brain/duplicacy. "
            "One primary writes; replicas stay byte-identical via sync; "
            "any replica can promote in seconds if primary dies."
        ),
        "seq": seq,
        "role": settings.cluster_role,
        "node_id": settings.cluster_node_id,
        "primary_url": settings.cluster_primary_url,
        "self": {
            "node_id": settings.cluster_node_id,
            "role": settings.cluster_role,
            "url": settings.cluster_public_url,
            "primary_url": settings.cluster_primary_url,
            "priority": settings.cluster_priority,
            "seq": seq,
            "checksum": checksum,
        },
        "primary": {
            "node_id": primary.node_id if primary else settings.cluster_node_id,
            "url": primary.public_url if primary else settings.cluster_primary_url,
            "status": primary.status if primary else "self",
        },
        "nodes": [
            {
                "node_id": n.node_id,
                "role": n.role,
                "public_url": n.public_url,
                "url": n.public_url,
                "priority": n.priority,
                "last_seq": n.last_seq,
                "checksum": n.last_checksum,
                "last_heartbeat": n.last_heartbeat.isoformat() + "Z" if n.last_heartbeat else None,
                "heartbeat": n.last_heartbeat.isoformat() + "Z" if n.last_heartbeat else None,
                "status": n.status,
            }
            for n in nodes
        ],
        "mirrors": mirrors,
        "mirrors_configured": len(mirrors),
        "peers": settings.peer_urls(),
        "sync_seconds": settings.cluster_sync_seconds,
        "failover_after_seconds": settings.cluster_failover_after_seconds,
    }
    try:
        from app.services.ha_protect import assess_risks, fence_epoch

        out["fence_epoch"] = fence_epoch(db)
        risks = assess_risks(db)
        out["risks_open"] = risks.get("open_count")
        out["risks_ok"] = risks.get("ok")
    except Exception:
        out["fence_epoch"] = 1
    return out


def promote_self(db: Session, reason: str = "manual") -> dict[str, Any]:
    """Become primary writer — bumps fence epoch so old primary must demote."""
    from app.services.ha_protect import bump_fence

    for n in db.query(ClusterNode).all():
        if n.node_id != settings.cluster_node_id and n.role == "primary":
            n.role = "replica"
            n.status = "stale"
    self_node = upsert_self_node(db)
    self_node.role = "primary"
    self_node.status = "promoted"
    object.__setattr__(settings, "cluster_role", "primary")
    object.__setattr__(settings, "cluster_primary_url", settings.cluster_public_url)
    try:
        from app.services.auto_configure import adopt_primary_url

        adopt_primary_url(settings.cluster_public_url, role="primary", db=db)
    except Exception:
        pass
    epoch = bump_fence(db, reason=reason)
    seq = bump_seq(db, self_node.last_checksum or "")
    db.add(
        SyncEvent(
            seq=seq,
            event_type="failover",
            entity="cluster",
            entity_id=settings.cluster_node_id,
            payload={"reason": reason, "node_id": settings.cluster_node_id, "fence_epoch": epoch},
            checksum=self_node.last_checksum or "",
        )
    )
    db.commit()
    return {
        "ok": True,
        "promoted": settings.cluster_node_id,
        "seq": seq,
        "fence_epoch": epoch,
        "reason": reason,
        "message": f"{settings.cluster_node_id} is now PRIMARY (fence={epoch}) — writes continue here",
    }


def maybe_autofailover(db: Session) -> dict[str, Any] | None:
    if not settings.cluster_enabled:
        return None
    if settings.cluster_role == "primary":
        return None
    status = cluster_status(db)
    primary = next((n for n in status["nodes"] if n["role"] == "primary"), None)
    cut = datetime.utcnow() - timedelta(seconds=int(settings.cluster_failover_after_seconds))
    primary_dead = False
    if not primary:
        primary_dead = True
    else:
        hb = primary.get("heartbeat")
        if not hb:
            primary_dead = True
        else:
            try:
                ts = datetime.fromisoformat(hb.replace("Z", ""))
                primary_dead = ts < cut
            except Exception:
                primary_dead = True
    if not primary_dead:
        return None

    from app.services.ha_protect import primary_probe_allows_failover

    probe_url = (primary or {}).get("public_url") or (primary or {}).get("url") or settings.cluster_primary_url
    if getattr(settings, "cluster_require_probe", True):
        gate = primary_probe_allows_failover(probe_url)
        if not gate.get("allow_failover"):
            return {
                "ok": False,
                "waiting": True,
                "message": (
                    f"Primary looks stale locally — {gate.get('reason')} "
                    f"({gate.get('fail_count')}/{gate.get('need')})"
                ),
                "probe": gate,
            }

    candidates = [n for n in status["nodes"] if n["status"] == "online" and n["role"] != "primary"]
    if not candidates:
        candidates = [status["self"]]
    best = max(candidates, key=lambda n: int(n.get("priority") or 0))
    if best.get("node_id") != settings.cluster_node_id:
        return {
            "ok": False,
            "waiting": True,
            "message": f"Primary dead — waiting for higher priority node {best.get('node_id')} to promote",
            "best": best,
        }
    return promote_self(db, reason="auto_failover_primary_stale")


def publish_snapshot(db: Session) -> dict[str, Any]:
    """Primary: bump seq (only if data changed), mirror identical packs to 5 sites."""
    if settings.cluster_role != "primary" and settings.cluster_enabled:
        return {"ok": False, "error": "Only primary publishes snapshots", "role": settings.cluster_role}
    db_path = sqlite_db_path()
    checksum = file_checksum(db_path) if db_path else ""
    st = _get_state(db, "replication")
    prev_sum = st.get("checksum") or ""
    seq = current_seq(db)
    if checksum and checksum == prev_sum and seq > 0:
        mirrors = mirror_portable_to_all_sites(seq)
        upsert_self_node(db, checksum=checksum, seq=seq)
        db.commit()
        return {
            "ok": True,
            "seq": seq,
            "checksum": checksum,
            "unchanged": True,
            "mirrors": mirrors,
            "message": f"Data unchanged — refreshed {len(settings.mirror_paths())} mirrors at seq {seq}",
        }
    seq = bump_seq(db, checksum)
    upsert_self_node(db, checksum=checksum, seq=seq)
    mirrors = mirror_portable_to_all_sites(seq)
    db.commit()
    return {
        "ok": True,
        "seq": seq,
        "checksum": checksum,
        "mirrors": mirrors,
        "message": f"Published seq {seq} to {len(settings.mirror_paths())} identical sites",
    }


def events_since(db: Session, since_seq: int, limit: int = 100) -> list[dict]:
    rows = (
        db.query(SyncEvent)
        .filter(SyncEvent.seq > since_seq)
        .order_by(SyncEvent.seq.asc())
        .limit(limit)
        .all()
    )
    return [
        {
            "seq": r.seq,
            "event_type": r.event_type,
            "entity": r.entity,
            "entity_id": r.entity_id,
            "payload": r.payload,
            "checksum": r.checksum,
            "created_at": r.created_at.isoformat() + "Z" if r.created_at else None,
        }
        for r in rows
    ]
