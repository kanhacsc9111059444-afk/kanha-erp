"""Capture crashing / 5xx mutating API calls into FailedEntry heal queue."""
from __future__ import annotations

import logging
from typing import Callable

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.database import SessionLocal
from app.core.security import decode_token
from app.services.ha_heal import parse_body_bytes, record_failed_entry, should_capture

log = logging.getLogger("kanha.heal.mw")


class FailedEntryMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        path = request.url.path
        method = request.method.upper()
        capture = should_capture(path, method)
        body_bytes = b""
        if capture:
            body_bytes = await request.body()

            async def receive():
                return {"type": "http.request", "body": body_bytes, "more_body": False}

            request = Request(request.scope, receive)

        try:
            response = await call_next(request)
        except Exception as exc:
            if capture:
                self._safe_record(request, body_bytes, 500, str(exc))
            return JSONResponse(
                {
                    "detail": "Entry failed and was auto-rolled back. Open Resilience → Failed entries to Re-enter.",
                    "healed": True,
                    "error": str(exc)[:500],
                },
                status_code=500,
            )

        if capture and response.status_code >= 500:
            detail = f"HTTP {response.status_code}"
            self._safe_record(request, body_bytes, response.status_code, detail)
        return response

    def _safe_record(self, request: Request, body_bytes: bytes, status_code: int, error: str) -> None:
        db = SessionLocal()
        try:
            try:
                db.rollback()
            except Exception:
                pass
            email = ""
            auth = request.headers.get("authorization") or ""
            token = auth[7:].strip() if auth.lower().startswith("bearer ") else ""
            if token:
                payload = decode_token(token) or {}
                email = str(payload.get("sub") or "")
            record_failed_entry(
                db,
                path=request.url.path,
                method=request.method,
                status_code=status_code,
                error_message=error,
                payload=parse_body_bytes(body_bytes),
                user_email=email,
            )
            db.commit()
        except Exception:
            log.exception("failed to record FailedEntry")
            try:
                db.rollback()
            except Exception:
                pass
        finally:
            db.close()
