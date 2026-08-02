"""Idempotency keys — stop duplicate invoices on retry / Re-enter."""
from __future__ import annotations

import hashlib
import logging
from datetime import datetime
from typing import Callable

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.database import SessionLocal
from app.models import SyncState

log = logging.getLogger("kanha.idem")
_MUTATING = {"POST", "PUT", "PATCH"}


def _get(db, key: str) -> dict | None:
    row = db.query(SyncState).filter(SyncState.key == f"idem:{key}").first()
    return dict(row.value or {}) if row else None


def _set(db, key: str, value: dict) -> None:
    full = f"idem:{key}"
    row = db.query(SyncState).filter(SyncState.key == full).first()
    if not row:
        db.add(SyncState(key=full, value=value))
    else:
        row.value = value
    db.commit()


class IdempotencyMiddleware(BaseHTTPMiddleware):
    """
    If client sends X-Idempotency-Key and that key already succeeded once,
    return the saved ack instead of creating a second invoice/order.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        method = request.method.upper()
        path = request.url.path
        key = request.headers.get("x-idempotency-key") or ""
        if method not in _MUTATING or not path.startswith("/api/") or not key:
            return await call_next(request)
        if path.startswith("/api/ha/") or path.startswith("/api/auth/") or path.startswith("/api/drafts"):
            return await call_next(request)

        safe_key = hashlib.sha256(f"{method}:{path}:{key}".encode()).hexdigest()[:48]
        db = SessionLocal()
        try:
            cached = _get(db, safe_key)
            if cached and cached.get("done"):
                return JSONResponse(
                    {
                        "ok": True,
                        "idempotent_replay": True,
                        "detail": "Same request already applied — duplicate blocked",
                        "original_at": cached.get("at"),
                        "path": path,
                    },
                    status_code=200,
                    headers={"X-Idempotent-Replay": "1"},
                )
        finally:
            db.close()

        response = await call_next(request)
        if 200 <= response.status_code < 300:
            db2 = SessionLocal()
            try:
                _set(
                    db2,
                    safe_key,
                    {"done": True, "status_code": response.status_code, "at": datetime.utcnow().isoformat() + "Z", "path": path},
                )
            except Exception:
                log.exception("idempotency store failed")
            finally:
                db2.close()
        return response
