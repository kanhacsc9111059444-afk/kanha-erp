from __future__ import annotations

import logging
import shutil
import tempfile
from pathlib import Path
from typing import Any

import httpx

from app.core.config import DATA, settings
from app.core.database import SessionLocal
from app.services.ha_cluster import (
    current_seq,
    maybe_autofailover,
    publish_snapshot,
    record_peer_heartbeat,
    upsert_self_node,
)
from app.services.ha_portable import apply_portable_from_dir, file_checksum, sqlite_db_path

log = logging.getLogger("kanha.ha.sync")


def _headers() -> dict[str, str]:
    return {"X-Cluster-Token": settings.cluster_token, "Content-Type": "application/json"}


def push_heartbeat_to_peers() -> list[dict]:
    db = SessionLocal()
    out = []
    try:
        self_node = upsert_self_node(db)
        db.commit()
        from app.services.ha_protect import fence_epoch

        epoch = fence_epoch(db)
        payload = {
            "node_id": settings.cluster_node_id,
            "role": settings.cluster_role,
            "public_url": settings.cluster_public_url,
            "priority": settings.cluster_priority,
            "last_seq": self_node.last_seq,
            "last_checksum": self_node.last_checksum,
            "fence_epoch": epoch,
        }
        for url in settings.peer_urls():
            try:
                with httpx.Client(timeout=8) as client:
                    r = client.post(f"{url}/api/ha/heartbeat", json=payload, headers=_headers())
                    out.append({"url": url, "status": r.status_code, "ok": r.status_code < 400})
            except Exception as e:
                out.append({"url": url, "ok": False, "error": str(e)})
    finally:
        db.close()
    return out


def pull_latest_from_primary() -> dict[str, Any]:
    """Replica: download LATEST portable pack from primary and apply (same data, no dup diverge)."""
    if settings.cluster_role == "primary":
        return {"ok": True, "skipped": True, "reason": "primary does not pull"}
    primary = (settings.cluster_primary_url or "").rstrip("/")
    if not primary:
        return {"ok": False, "error": "CLUSTER_PRIMARY_URL empty"}
    try:
        with httpx.Client(timeout=120) as client:
            meta = client.get(f"{primary}/api/ha/snapshot/meta", headers=_headers())
            if meta.status_code >= 400:
                return {"ok": False, "error": f"meta {meta.status_code}", "body": meta.text[:200]}
            info = meta.json()
            local_seq = 0
            db = SessionLocal()
            try:
                local_seq = current_seq(db)
                db_path = sqlite_db_path()
                local_sum = file_checksum(db_path) if db_path else ""
            finally:
                db.close()
            if info.get("seq", 0) <= local_seq and info.get("checksum") == local_sum:
                return {"ok": True, "synced": False, "message": "Already on latest identical data", "seq": local_seq}

            # download zip
            with client.stream("GET", f"{primary}/api/ha/snapshot/download", headers=_headers()) as r:
                if r.status_code >= 400:
                    return {"ok": False, "error": f"download {r.status_code}"}
                tmpdir = Path(tempfile.mkdtemp(prefix="kanha_sync_"))
                zip_path = tmpdir / "LATEST.zip"
                with zip_path.open("wb") as f:
                    for chunk in r.iter_bytes():
                        f.write(chunk)
            extract = tmpdir / "extract"
            extract.mkdir()
            shutil.unpack_archive(str(zip_path), str(extract))
            from app.services.ha_protect import acquire_apply_lock, release_apply_lock

            if not acquire_apply_lock():
                shutil.rmtree(tmpdir, ignore_errors=True)
                return {"ok": False, "error": "Another pack apply in progress — retry next tick"}
            try:
                applied = apply_portable_from_dir(extract)
            finally:
                release_apply_lock()
            if not applied.get("ok"):
                return applied
            # refresh ORM engine connection — next requests see new file
            db2 = SessionLocal()
            try:
                upsert_self_node(db2, checksum=applied.get("checksum") or "", seq=int(applied.get("applied_seq") or info.get("seq") or 0))
                from app.services.ha_cluster import _set_state

                _set_state(
                    db2,
                    "replication",
                    {
                        "seq": int(applied.get("applied_seq") or info.get("seq") or 0),
                        "checksum": applied.get("checksum"),
                        "pulled_from": primary,
                    },
                )
                db2.commit()
            finally:
                db2.close()
            shutil.rmtree(tmpdir, ignore_errors=True)
            return {
                "ok": True,
                "synced": True,
                "from": primary,
                "seq": applied.get("applied_seq") or info.get("seq"),
                "checksum": applied.get("checksum"),
                "message": "Replica now identical to primary latest data",
            }
    except Exception as e:
        log.exception("pull failed")
        return {"ok": False, "error": str(e)}


def ha_tick() -> dict[str, Any]:
    """Periodic: heartbeat, failover check, primary publish mirrors, replica pull."""
    if not settings.cluster_enabled:
        return {"ok": True, "disabled": True}
    result: dict[str, Any] = {"ok": True, "role": settings.cluster_role}
    result["heartbeats"] = push_heartbeat_to_peers()
    db = SessionLocal()
    try:
        fo = maybe_autofailover(db)
        if fo:
            result["failover"] = fo
        if settings.cluster_role == "primary":
            result["publish"] = publish_snapshot(db)
        else:
            result["pull"] = pull_latest_from_primary()
    finally:
        db.close()
    return result
