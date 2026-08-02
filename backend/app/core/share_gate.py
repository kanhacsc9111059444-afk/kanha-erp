"""Optional public-share gate: HTTP Basic Auth before ERP UI/API.

Enable with env:
  SHARE_GATE_USER=viewer
  SHARE_GATE_PASSWORD=YourSharePass

When password empty → gate disabled.

IMPORTANT: After ERP login, requests use Authorization: Bearer.
Those must pass the gate (otherwise browser keeps asking password).
Localhost is never gated (owner local use).
"""
from __future__ import annotations

import secrets
from base64 import b64decode

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.config import settings


class ShareGateMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        user = (getattr(settings, "share_gate_user", None) or "").strip()
        password = (getattr(settings, "share_gate_password", None) or "").strip()
        if not password:
            return await call_next(request)

        # Owner local PC — no extra password
        client = (request.client.host if request.client else "") or ""
        if client in ("127.0.0.1", "::1", "localhost"):
            return await call_next(request)

        path = request.url.path or ""
        if path in ("/api/health",):
            return await call_next(request)

        auth = request.headers.get("authorization") or ""
        low = auth.lower()

        # Already logged into ERP → do NOT ask share password again
        if low.startswith("bearer ") and auth.split(" ", 1)[-1].strip():
            return await call_next(request)

        expected_user = user or "viewer"
        ok = False
        if low.startswith("basic "):
            try:
                raw = b64decode(auth.split(" ", 1)[1].strip()).decode("utf-8")
                got_user, _, got_pass = raw.partition(":")
                ok = secrets.compare_digest(got_user, expected_user) and secrets.compare_digest(
                    got_pass, password
                )
            except Exception:
                ok = False

        if not ok:
            return Response(
                content="KanhaERP private share — password required.",
                status_code=401,
                headers={"WWW-Authenticate": 'Basic realm="KanhaERP Share"'},
                media_type="text/plain",
            )
        return await call_next(request)
