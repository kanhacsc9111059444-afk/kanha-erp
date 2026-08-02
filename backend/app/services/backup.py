from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path

from app.core.config import BACKUP, DATA, settings


def backup_sqlite() -> dict:
    """Copy SQLite DB into data/backups with timestamp."""
    url = settings.database_url or ""
    if "sqlite" not in url.lower():
        return {
            "ok": False,
            "note": "Non-SQLite DB — use pg_dump / managed backups",
            "database_url_engine": url.split("://", 1)[0] if "://" in url else "unknown",
        }
    # sqlite:////path or sqlite:///./data/...
    raw = url.split("sqlite:///")[-1]
    src = Path(raw)
    if not src.is_absolute():
        src = (DATA.parent / src).resolve() if not src.exists() else src.resolve()
    if not src.exists():
        # default project db
        src = DATA / "kanha_erp.db"
    if not src.exists():
        return {"ok": False, "error": f"DB file not found: {src}"}
    BACKUP.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dest = BACKUP / f"kanha_erp_{stamp}.db"
    shutil.copy2(src, dest)
    # keep last 14
    files = sorted(BACKUP.glob("kanha_erp_*.db"), key=lambda p: p.stat().st_mtime, reverse=True)
    for old in files[14:]:
        try:
            old.unlink()
        except OSError:
            pass
    return {"ok": True, "path": str(dest), "size": dest.stat().st_size}
