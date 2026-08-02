from __future__ import annotations

import hashlib
import json
import shutil
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any

from app.core.config import BACKUP, DATA, ROOT, settings


def sqlite_db_path() -> Path | None:
    url = settings.database_url or ""
    if "sqlite" not in url.lower():
        return None
    raw = url.split("sqlite:///")[-1]
    src = Path(raw)
    if not src.is_absolute():
        cand = (ROOT / src).resolve()
        src = cand if cand.exists() else (DATA / "kanha_erp.db")
    if not src.exists():
        src = DATA / "kanha_erp.db"
    return src if src.exists() else None


def file_checksum(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def build_portable_pack(dest_dir: Path, *, seq: int, role_hint: str = "") -> dict[str, Any]:
    """
    Full portable ERP pack: DB + uploads + manifest.
    Same pack on every mirror = identical latest ERP state (no duplicate divergence).
    """
    dest_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    pack_root = dest_dir / f"kanha_portable_{stamp}"
    pack_root.mkdir(parents=True, exist_ok=True)

    db = sqlite_db_path()
    checksum = ""
    db_copied = None
    if db:
        db_copied = pack_root / "kanha_erp.db"
        shutil.copy2(db, db_copied)
        checksum = file_checksum(db_copied)

    uploads_src = DATA / "uploads"
    if uploads_src.exists():
        shutil.copytree(uploads_src, pack_root / "uploads", dirs_exist_ok=True)

    # Sanitized auto-config snapshot (NO secrets) — new server can auto-adopt
    config_snap = {
        "app": settings.app_name,
        "version": settings.app_version,
        "demo_mode": settings.demo_mode,
        "cluster_enabled": settings.cluster_enabled,
        "cluster_node_id": settings.cluster_node_id,
        "cluster_role": settings.cluster_role,
        "cluster_public_url": settings.cluster_public_url,
        "cluster_primary_url": settings.cluster_primary_url,
        "integrations_flags": {
            "whatsapp": settings.whatsapp_live,
            "llm": settings.llm_live,
            "razorpay": settings.razorpay_live,
            "gsp": settings.gsp_live,
            "maps": settings.maps_live,
        },
        "note": "Secrets NOT included. Paste API keys in .env on new host; demo adapters work until then.",
    }
    (pack_root / "config_snapshot.json").write_text(json.dumps(config_snap, indent=2), encoding="utf-8")

    # Minimal env template for spinning a new node from this pack
    env_txt = pack_root / "RESTORE.txt"
    env_txt.write_text(
        "\n".join(
            [
                f"{settings.app_name} PORTABLE ERP PACK",
                f"seq={seq}",
                f"checksum={checksum}",
                f"created={datetime.utcnow().isoformat()}Z",
                f"from_node={settings.cluster_node_id}",
                f"role_hint={role_hint or settings.cluster_role}",
                "",
                "RESTORE (auto-adopt friendly):",
                "1) Copy kanha_erp.db → project data/kanha_erp.db",
                "2) Copy uploads/ → data/uploads/",
                "3) Copy config_snapshot.json hints — OR open ERP → Resilience → Auto-configure",
                "4) Optional: set .env CLUSTER_ROLE=primary (or replica) + CLUSTER_PRIMARY_URL",
                "5) run.bat / run.prod.bat — Auto-configure fills node id / URLs from this machine",
                "6) Connectivity milte hi: Resilience → Adopt primary / Sync now",
                "",
                "BLACKOUT: if pack made during blackout, Unlock after restore when safe.",
                "",
            ]
        ),
        encoding="utf-8",
    )

    manifest = {
        "app": settings.app_name,
        "version": settings.app_version,
        "seq": seq,
        "checksum": checksum,
        "node_id": settings.cluster_node_id,
        "created_at": datetime.utcnow().isoformat() + "Z",
        "role_hint": role_hint or settings.cluster_role,
        "portable": True,
        "includes": ["kanha_erp.db", "uploads/", "config_snapshot.json", "RESTORE.txt"],
    }
    (pack_root / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    zip_path = dest_dir / f"kanha_portable_{stamp}.zip"
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for f in pack_root.rglob("*"):
            if f.is_file():
                zf.write(f, arcname=str(f.relative_to(pack_root)))

    # Keep latest pointer (always same name = no confusion which is current)
    latest = dest_dir / "LATEST"
    if latest.exists():
        shutil.rmtree(latest, ignore_errors=True)
    shutil.copytree(pack_root, latest)
    latest_zip = dest_dir / "LATEST.zip"
    if latest_zip.exists():
        latest_zip.unlink()
    shutil.copy2(zip_path, latest_zip)

    # prune old stamped packs (keep 5)
    old = sorted(dest_dir.glob("kanha_portable_*.zip"), key=lambda p: p.stat().st_mtime, reverse=True)
    for p in old[5:]:
        try:
            p.unlink()
        except OSError:
            pass
    for p in sorted(dest_dir.glob("kanha_portable_*"), key=lambda p: p.stat().st_mtime, reverse=True):
        if p.is_dir() and p.name != "LATEST":
            # keep dirs matching remaining zips only loosely — remove older dirs
            pass
    dirs = sorted([p for p in dest_dir.glob("kanha_portable_*") if p.is_dir()], key=lambda p: p.stat().st_mtime, reverse=True)
    for d in dirs[5:]:
        shutil.rmtree(d, ignore_errors=True)

    return {
        "ok": True,
        "pack_dir": str(pack_root),
        "zip": str(zip_path),
        "latest_dir": str(latest),
        "latest_zip": str(latest_zip),
        "checksum": checksum,
        "seq": seq,
        "size": zip_path.stat().st_size if zip_path.exists() else 0,
    }


def mirror_portable_to_all_sites(seq: int) -> dict[str, Any]:
    """Write identical portable ERP to 5 (+ optional user) places — same checksum everywhere."""
    results = []
    first: dict[str, Any] | None = None
    for i, path in enumerate(settings.mirror_paths(), start=1):
        r = build_portable_pack(path, seq=seq, role_hint="mirror")
        results.append({"site": i, "path": str(path), **r})
        if first is None:
            first = r
        elif first.get("checksum") and r.get("checksum") and first["checksum"] != r["checksum"]:
            r["dup_warning"] = "checksum mismatch — should not happen on same source"
    # also classic backup folder
    classic = build_portable_pack(BACKUP, seq=seq, role_hint="archive")
    return {
        "ok": True,
        "seq": seq,
        "checksum": (first or {}).get("checksum"),
        "mirrors": results,
        "archive": classic,
        "message": f"Identical portable ERP mirrored to {len(results)} sites + archive",
    }


def apply_portable_from_dir(source: Path) -> dict[str, Any]:
    """Replace local DB+uploads from a LATEST pack (atomic-ish)."""
    src = source
    if (source / "LATEST").exists():
        src = source / "LATEST"
    if (source / "manifest.json").exists():
        src = source
    db_src = src / "kanha_erp.db"
    if not db_src.exists():
        return {"ok": False, "error": f"No kanha_erp.db in {src}"}
    dest_db = sqlite_db_path() or (DATA / "kanha_erp.db")
    dest_db.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest_db.with_suffix(".db.incoming")
    shutil.copy2(db_src, tmp)
    # verify checksum if manifest present
    man = {}
    man_path = src / "manifest.json"
    if man_path.exists():
        man = json.loads(man_path.read_text(encoding="utf-8"))
        if man.get("checksum") and file_checksum(tmp) != man["checksum"]:
            tmp.unlink(missing_ok=True)
            return {"ok": False, "error": "checksum mismatch — refused corrupt pack"}
    bak = dest_db.with_suffix(".db.prev")
    if dest_db.exists():
        shutil.copy2(dest_db, bak)
    tmp.replace(dest_db)
    uploads_src = src / "uploads"
    if uploads_src.exists():
        shutil.copytree(uploads_src, DATA / "uploads", dirs_exist_ok=True)
    return {
        "ok": True,
        "applied_seq": man.get("seq"),
        "checksum": man.get("checksum") or file_checksum(dest_db),
        "db": str(dest_db),
        "previous": str(bak) if bak.exists() else None,
    }
