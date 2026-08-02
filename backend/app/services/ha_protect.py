"""Realtime HA risk detection + protective guards (split-brain, same-disk, probe, lock)."""
from __future__ import annotations

import logging
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx
from sqlalchemy.orm import Session

from app.core.config import DATA, settings
from app.models import SyncState

log = logging.getLogger("kanha.ha.protect")

APPLY_LOCK = DATA / ".ha_apply.lock"
_PROBE_FAILS: dict[str, int] = {}


def _get_state(db: Session, key: str) -> dict:
    row = db.query(SyncState).filter(SyncState.key == key).first()
    return dict(row.value or {}) if row else {}


def _set_state(db: Session, key: str, value: dict) -> None:
    row = db.query(SyncState).filter(SyncState.key == key).first()
    if not row:
        db.add(SyncState(key=key, value=value))
    else:
        row.value = value
    db.flush()


def fence_epoch(db: Session) -> int:
    """Monotonic fencing token — higher wins; old primary must demote."""
    return int(_get_state(db, "fence").get("epoch") or 1)


def bump_fence(db: Session, *, reason: str = "") -> int:
    st = _get_state(db, "fence")
    epoch = int(st.get("epoch") or 1) + 1
    st.update(
        {
            "epoch": epoch,
            "holder": settings.cluster_node_id,
            "reason": reason,
            "at": datetime.utcnow().isoformat() + "Z",
        }
    )
    _set_state(db, "fence", st)
    db.flush()
    return epoch


def set_fence_if_higher(db: Session, epoch: int, holder: str = "") -> bool:
    cur = fence_epoch(db)
    if int(epoch or 0) <= cur:
        return False
    _set_state(
        db,
        "fence",
        {
            "epoch": int(epoch),
            "holder": holder or "",
            "reason": "learned_from_peer",
            "at": datetime.utcnow().isoformat() + "Z",
        },
    )
    return True


def acquire_apply_lock(ttl_sec: int = 120) -> bool:
    """Prevent two pack applies overlapping (corrupt DB risk)."""
    DATA.mkdir(parents=True, exist_ok=True)
    now = time.time()
    if APPLY_LOCK.exists():
        try:
            age = now - APPLY_LOCK.stat().st_mtime
            if age < ttl_sec:
                return False
        except OSError:
            pass
    APPLY_LOCK.write_text(f"{settings.cluster_node_id}:{now}", encoding="utf-8")
    return True


def release_apply_lock() -> None:
    try:
        if APPLY_LOCK.exists():
            APPLY_LOCK.unlink()
    except OSError:
        pass


def _disk_key(path: Path) -> str:
    try:
        resolved = path.resolve()
    except Exception:
        resolved = path
    # Windows drive letter, else first 2 path parts
    drive = getattr(resolved, "drive", None) or ""
    if drive:
        return drive.upper()
    parts = resolved.parts
    if len(parts) >= 2:
        return str(Path(parts[0]) / parts[1])
    return str(resolved)


def same_disk_mirror_risk() -> dict[str, Any]:
    """5 mirrors on same disk = false redundancy (one disk crash kills all)."""
    paths = list(settings.mirror_paths())
    by_disk: dict[str, list[str]] = {}
    for p in paths:
        k = _disk_key(p)
        by_disk.setdefault(k, []).append(str(p))
    crowded = {k: v for k, v in by_disk.items() if len(v) > 1}
    # Default auto mirrors under data/mirrors are always same disk
    auto_only = all(not getattr(settings, f"backup_mirror_{i}", "").strip() for i in range(1, 6))
    return {
        "ok": len(crowded) == 0 and not auto_only,
        "severity": bool(crowded) or auto_only,
        "by_disk": by_disk,
        "message": (
            "Mirrors share same disk — set BACKUP_MIRROR_1..5 on different drives/NAS"
            if (crowded or auto_only)
            else "Mirrors on separate disks"
        ),
    }


def probe_url_alive(url: str, timeout: float = 4.0) -> dict[str, Any]:
    url = (url or "").rstrip("/")
    if not url:
        return {"ok": False, "error": "empty url"}
    try:
        with httpx.Client(timeout=timeout) as client:
            r = client.get(
                f"{url}/api/ha/public-status",
                headers={"X-Cluster-Token": settings.cluster_token},
            )
            if r.status_code < 400:
                return {"ok": True, "status": r.status_code, "body": r.json()}
            # fallback health
            h = client.get(f"{url}/api/health")
            return {"ok": h.status_code < 400, "status": h.status_code, "via": "health"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def primary_probe_allows_failover(primary_url: str) -> dict[str, Any]:
    """
    Require repeated failed probes before promote — avoids blip false failover.
    """
    key = (primary_url or "").rstrip("/") or "none"
    result = probe_url_alive(key) if key != "none" else {"ok": False, "error": "no primary"}
    if result.get("ok"):
        _PROBE_FAILS[key] = 0
        return {
            "allow_failover": False,
            "reason": "primary_still_reachable",
            "probe": result,
            "fail_count": 0,
        }
    _PROBE_FAILS[key] = int(_PROBE_FAILS.get(key, 0)) + 1
    need = max(2, int(getattr(settings, "cluster_min_failover_probes", 2) or 2))
    fails = _PROBE_FAILS[key]
    return {
        "allow_failover": fails >= need,
        "reason": "probes_failed" if fails >= need else "waiting_more_probes",
        "probe": result,
        "fail_count": fails,
        "need": need,
    }


def demote_self_to_replica(db: Session, *, reason: str, new_primary_url: str = "") -> dict[str, Any]:
    """Split-brain guard: if we learn a higher fence epoch primary exists, step down."""
    from app.models import ClusterNode

    object.__setattr__(settings, "cluster_role", "replica")
    if new_primary_url:
        object.__setattr__(settings, "cluster_primary_url", new_primary_url.rstrip("/"))
        try:
            from app.services.auto_configure import adopt_primary_url

            adopt_primary_url(new_primary_url, role="replica", db=db)
        except Exception:
            pass
    node = db.query(ClusterNode).filter(ClusterNode.node_id == settings.cluster_node_id).first()
    if node:
        node.role = "replica"
        node.status = "demoted"
    db.flush()
    log.warning("Demoted to replica: %s", reason)
    return {
        "ok": True,
        "demoted": settings.cluster_node_id,
        "reason": reason,
        "primary_url": settings.cluster_primary_url,
    }


def apply_peer_fence(db: Session, body: dict) -> dict[str, Any] | None:
    """
    On heartbeat: if peer is primary with higher/equal fence and we also think we are primary
    → demote the lower epoch (or lower priority on tie).
    """
    peer_epoch = int(body.get("fence_epoch") or 0)
    peer_role = (body.get("role") or "").lower()
    peer_url = body.get("public_url") or ""
    peer_priority = int(body.get("priority") or 0)
    if peer_role != "primary" or peer_epoch <= 0:
        return None
    mine = fence_epoch(db)
    set_fence_if_higher(db, peer_epoch, body.get("node_id") or "")
    if settings.cluster_role != "primary":
        # learn new primary URL
        if peer_url and peer_url.rstrip("/") != (settings.cluster_primary_url or "").rstrip("/"):
            object.__setattr__(settings, "cluster_primary_url", peer_url.rstrip("/"))
        return None
    # Both claim primary
    if peer_epoch > mine:
        return demote_self_to_replica(db, reason=f"peer_higher_fence_{peer_epoch}", new_primary_url=peer_url)
    if peer_epoch == mine and peer_priority > int(settings.cluster_priority):
        return demote_self_to_replica(db, reason="peer_same_fence_higher_priority", new_primary_url=peer_url)
    if peer_epoch == mine and peer_priority == int(settings.cluster_priority):
        # Deterministic: lower node_id wins stay; higher demotes
        if (body.get("node_id") or "") < settings.cluster_node_id:
            return demote_self_to_replica(db, reason="peer_tie_break_node_id", new_primary_url=peer_url)
    return None


def assess_risks(db: Session) -> dict[str, Any]:
    """Realtime risk board — what will bite us in production."""
    disk = same_disk_mirror_risk()
    token_default = settings.cluster_token in ("", "kanha-cluster-change-me")
    peers = settings.peer_urls()
    sqlite = "sqlite" in (settings.database_url or "").lower()
    epoch = fence_epoch(db)
    risks = [
        {
            "id": "split_brain",
            "severity": "critical",
            "title": "Split-brain (2 primaries)",
            "issue": "Network partition ke baad do nodes writes accept kar sakte hain → duplicate invoices/stock.",
            "protection": "Fence epoch + heartbeat demote + probe-before-promote (implemented).",
            "ok": True,
            "status": f"fence_epoch={epoch}",
        },
        {
            "id": "false_failover",
            "severity": "high",
            "title": "False failover on network blip",
            "issue": "Primary zinda hai lekin heartbeat miss → galat promote.",
            "protection": f"Need {getattr(settings, 'cluster_min_failover_probes', 2)} failed HTTP probes before promote.",
            "ok": True,
            "status": "probe gate ON",
        },
        {
            "id": "same_disk_mirrors",
            "severity": "critical",
            "title": "All mirrors on one disk",
            "issue": "5 folders same drive pe = disk crash pe saath me gaye.",
            "protection": "Set BACKUP_MIRROR_1..5 on different drives/NAS + BACKUP_USER_PACK USB.",
            "ok": disk.get("ok"),
            "status": disk.get("message"),
        },
        {
            "id": "no_peers",
            "severity": "high",
            "title": "No live peer nodes",
            "issue": "Sirf mirrors hain, koi hot replica nahi → primary crash pe auto ERP continue nahi.",
            "protection": "Kam se kam 1 replica machine + CLUSTER_PEERS set karo.",
            "ok": bool(peers) or settings.demo_mode,
            "status": f"peers={len(peers)}",
        },
        {
            "id": "cluster_token",
            "severity": "critical",
            "title": "Default CLUSTER_TOKEN",
            "issue": "Koi bhi fake node cluster join / snapshot le sakta hai.",
            "protection": "Strong shared CLUSTER_TOKEN on all nodes.",
            "ok": not token_default or settings.demo_mode,
            "status": "default" if token_default else "custom",
        },
        {
            "id": "client_stale_url",
            "severity": "high",
            "title": "Users still hit dead primary URL",
            "issue": "Failover hone ke baad browser purane server pe writes bhejta rahe.",
            "protection": "UI 409 → redirect primary_url; prefer floating DNS/VIP.",
            "ok": True,
            "status": "client redirect ON",
        },
        {
            "id": "duplicate_reentry",
            "severity": "medium",
            "title": "Re-enter creates duplicate docs",
            "issue": "Crash ke baad user Re-enter → double invoice.",
            "protection": "X-Idempotency-Key on writes + failed-entry replay keys.",
            "ok": True,
            "status": "idempotency middleware ON",
        },
        {
            "id": "sqlite_limits",
            "severity": "medium",
            "title": "SQLite pack sync lag",
            "issue": "File snapshot sync seconds-level lag; heavy multi-site → prefer Postgres streaming later.",
            "protection": "Apply lock + checksum verify; go-live Postgres recommended.",
            "ok": not sqlite or settings.demo_mode,
            "status": "sqlite" if sqlite else "postgres",
        },
        {
            "id": "apply_corruption",
            "severity": "high",
            "title": "Crash mid pack-apply",
            "issue": "Replica apply beech me toot jaye → corrupt DB.",
            "protection": "Apply lock + .db.incoming + .db.prev rollback + checksum.",
            "ok": True,
            "status": "locked apply ON",
        },
        {
            "id": "old_primary_returns",
            "severity": "critical",
            "title": "Old primary comes back online",
            "issue": "Purana primary phir writes le → split data.",
            "protection": "On heartbeat sees higher fence → auto demote to replica.",
            "ok": True,
            "status": "auto-demote ON",
        },
    ]
    open_risks = [r for r in risks if not r["ok"]]
    return {
        "ok": len(open_risks) == 0,
        "open_count": len(open_risks),
        "fence_epoch": epoch,
        "disk": disk,
        "risks": risks,
        "message": "All protective guards green" if not open_risks else f"{len(open_risks)} risks need config action",
    }
