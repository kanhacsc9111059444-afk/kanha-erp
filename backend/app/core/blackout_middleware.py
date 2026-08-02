"""Block all business writes during emergency blackout."""
from __future__ import annotations

from typing import Callable

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

_MUTATING = {"POST", "PUT", "PATCH", "DELETE"}

# Always allowed even in blackout (unlock / export / auth / health / HA peer sync)
_ALLOW_EXACT = {
    "/api/health",
    "/api/auth/login",
    "/api/brand/public",
    "/api/ha/blackout",
    "/api/ha/blackout/engage",
    "/api/ha/blackout/unlock",
    "/api/ha/portable/download",
    "/api/ha/auto-config",
    "/api/ha/auto-config/apply",
    "/api/ha/adopt",
    "/api/ha/public-status",
}

_ALLOW_PREFIX = (
    "/api/ha/heartbeat",
    "/api/ha/snapshot",
    "/api/ha/events",
    "/api/ha/status",
    "/api/ha/risks",
    "/api/ha/portable",
    "/api/ha/blackout",
    "/api/auth/",
    "/api/bridges/hooks/inbound/",
    "/api/meta/whatsapp/webhook",
)


class BlackoutLockdownMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        method = request.method.upper()
        path = request.url.path

        if method == "OPTIONS" or method not in _MUTATING:
            return await call_next(request)
        if not path.startswith("/api/"):
            return await call_next(request)
        if path in _ALLOW_EXACT or any(path.startswith(p) for p in _ALLOW_PREFIX):
            return await call_next(request)

        try:
            from app.services.blackout import is_blackout

            if not is_blackout():
                return await call_next(request)
        except Exception:
            return await call_next(request)

        return JSONResponse(
            {
                "detail": (
                    "EMERGENCY BLACKOUT — entries locked. "
                    "Download portable ERP pack from Resilience, or Unlock when safe. "
                    "Connectivity milte hi pack restore / adopt karo."
                ),
                "blackout": True,
                "code": "BLACKOUT_LOCKDOWN",
                "hint": "Open #/ha → Emergency Blackout → Download portable / Unlock",
            },
            status_code=503,
        )
