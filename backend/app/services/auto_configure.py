"""
Auto-configure — minimize manual setup by reading host/env/disk hints.
Never overwrites secrets the operator already set; only fills gaps + persists runtime adopt.
"""
from __future__ import annotations

import json
import os
import socket
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import DATA, ROOT, settings
from app.models import SyncState

RUNTIME_KEY = "runtime.adopt"
RUNTIME_FILE = DATA / "runtime_adopt.json"


def _hostname() -> str:
    try:
        return socket.gethostname() or "node"
    except Exception:
        return "node"


def _guess_public_url() -> str:
    host = os.environ.get("COMPUTERNAME") or _hostname()
    port = "8080"
    # Prefer loopback for local single-node; LAN IP if CLUSTER_PUBLIC_URL empty
    env_url = (os.environ.get("CLUSTER_PUBLIC_URL") or "").strip()
    if env_url:
        return env_url.rstrip("/")
    try:
        # Best-effort LAN IP without external traffic
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        if ip and not ip.startswith("127."):
            return f"http://{ip}:{port}"
    except Exception:
        pass
    return f"http://127.0.0.1:{port}"


def _writable_extra_drives() -> list[str]:
    """Windows-friendly: list free drive roots that look like backup targets."""
    found: list[str] = []
    if os.name == "nt":
        for letter in "DEFGHIJKLMNOPQRSTUVWXYZ":
            root = Path(f"{letter}:/")
            try:
                if root.exists():
                    probe = root / "KanhaERP_Mirrors"
                    # don't create — only suggest if parent writable
                    if os.access(str(root), os.W_OK):
                        found.append(str(probe))
            except Exception:
                continue
    else:
        for p in ("/mnt", "/media", "/var/backups"):
            if Path(p).exists() and os.access(p, os.W_OK):
                found.append(str(Path(p) / "KanhaERP_Mirrors"))
    return found[:5]


def discover(db: Session | None = None) -> dict[str, Any]:
    """Read hidden/system + env signals — report what can auto-fill."""
    host = _hostname()
    public = _guess_public_url()
    drives = _writable_extra_drives()
    env_present = {
        "SECRET_KEY": bool(os.environ.get("SECRET_KEY")),
        "DATABASE_URL": bool(os.environ.get("DATABASE_URL")),
        "WHATSAPP_TOKEN": bool(os.environ.get("WHATSAPP_TOKEN")),
        "LLM_API_KEY": bool(os.environ.get("LLM_API_KEY")),
        "RAZORPAY_KEY_ID": bool(os.environ.get("RAZORPAY_KEY_ID")),
        "CLUSTER_TOKEN": bool(os.environ.get("CLUSTER_TOKEN")),
        "CLUSTER_PRIMARY_URL": bool(os.environ.get("CLUSTER_PRIMARY_URL")),
        "CLUSTER_PUBLIC_URL": bool(os.environ.get("CLUSTER_PUBLIC_URL")),
    }
    gaps = [k for k, v in env_present.items() if not v and k in ("SECRET_KEY", "CLUSTER_TOKEN")]
    suggestions = {
        "cluster_node_id": f"node-{host.lower().replace(' ', '-')[:24]}",
        "cluster_public_url": public,
        "cluster_primary_url": (settings.cluster_primary_url or public).rstrip("/"),
        "mirror_suggestions": drives,
        "demo_mode": settings.demo_mode,
        "database": "sqlite" if "sqlite" in (settings.database_url or "").lower() else "postgres",
    }
    adopted = load_runtime_adopt()
    return {
        "ok": True,
        "hostname": host,
        "env_present": env_present,
        "manual_still_needed": gaps
        + (["WhatsApp / LLM / Razorpay keys — only when you want LIVE providers"] if True else []),
        "suggestions": suggestions,
        "adopted_runtime": adopted,
        "principle": (
            "Auto-configure fills node id, public URL, mirror disk hints from host. "
            "Secrets / API keys remain manual (or paste once in .env)."
        ),
        "scanned_at": datetime.utcnow().isoformat() + "Z",
    }


def load_runtime_adopt() -> dict[str, Any]:
    if RUNTIME_FILE.exists():
        try:
            return json.loads(RUNTIME_FILE.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def save_runtime_adopt(data: dict[str, Any], db: Session | None = None) -> dict[str, Any]:
    DATA.mkdir(parents=True, exist_ok=True)
    payload = {
        **data,
        "updated_at": datetime.utcnow().isoformat() + "Z",
    }
    RUNTIME_FILE.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    if db is not None:
        row = db.query(SyncState).filter(SyncState.key == RUNTIME_KEY).first()
        if not row:
            row = SyncState(key=RUNTIME_KEY, value={})
            db.add(row)
        row.value = payload
        db.flush()
    return payload


def apply_auto_config(db: Session, *, adopt_mirrors: bool = False) -> dict[str, Any]:
    """Apply safe auto suggestions into runtime (survives restart) + process settings."""
    info = discover(db)
    sug = info["suggestions"]
    adopted = {
        "cluster_node_id": sug["cluster_node_id"],
        "cluster_public_url": sug["cluster_public_url"],
        "cluster_primary_url": sug["cluster_primary_url"],
    }
    if adopt_mirrors and sug.get("mirror_suggestions"):
        adopted["mirror_suggestions"] = sug["mirror_suggestions"]

    save_runtime_adopt(adopted, db)

    # Live process adopt (no .env rewrite — safer)
    object.__setattr__(settings, "cluster_node_id", adopted["cluster_node_id"])
    object.__setattr__(settings, "cluster_public_url", adopted["cluster_public_url"])
    if not (os.environ.get("CLUSTER_PRIMARY_URL") or "").strip():
        object.__setattr__(settings, "cluster_primary_url", adopted["cluster_primary_url"])

    return {
        "ok": True,
        "applied": adopted,
        "manual_still_needed": info["manual_still_needed"],
        "message": "Auto-config applied — node identity + URLs adopted from this machine.",
        "note": "API keys (WhatsApp/LLM/Razorpay) still paste in .env when you want LIVE — until then demo adapters work.",
    }


def apply_runtime_on_startup() -> dict[str, Any]:
    """Called from main startup — restore adopted primary/node after reboot."""
    data = load_runtime_adopt()
    if not data:
        return {"ok": False, "applied": False}
    if data.get("cluster_node_id") and not (os.environ.get("CLUSTER_NODE_ID") or "").strip():
        object.__setattr__(settings, "cluster_node_id", data["cluster_node_id"])
    if data.get("cluster_public_url") and not (os.environ.get("CLUSTER_PUBLIC_URL") or "").strip():
        object.__setattr__(settings, "cluster_public_url", data["cluster_public_url"])
    if data.get("cluster_primary_url"):
        # Adopted primary wins over stale .env when connectivity moved
        object.__setattr__(settings, "cluster_primary_url", data["cluster_primary_url"])
        if data.get("cluster_role"):
            object.__setattr__(settings, "cluster_role", data["cluster_role"])
    return {"ok": True, "applied": True, "runtime": data}


def adopt_primary_url(url: str, *, role: str | None = None, db: Session | None = None) -> dict[str, Any]:
    """Persist + apply new primary when connectivity lands on another server."""
    url = (url or "").strip().rstrip("/")
    if not url:
        return {"ok": False, "error": "url required"}
    cur = load_runtime_adopt()
    cur["cluster_primary_url"] = url
    if role:
        cur["cluster_role"] = role
    save_runtime_adopt(cur, db)
    object.__setattr__(settings, "cluster_primary_url", url)
    if role:
        object.__setattr__(settings, "cluster_role", role)
    return {"ok": True, "primary_url": url, "role": role or settings.cluster_role, "message": f"Adopted primary → {url}"}
