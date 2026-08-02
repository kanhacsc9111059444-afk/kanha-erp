from __future__ import annotations

from typing import Callable

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings
from app.core.deps import has_permission
from app.core.database import SessionLocal
from app.core.security import decode_token
from app.models import User

# Most-specific prefixes first
_WRITE_RULES: list[tuple[str, list[str]]] = [
    ("/api/sales/pos", ["pos.*", "sales.*"]),
    ("/api/sales", ["sales.*", "pos.*"]),
    ("/api/crm", ["crm.*"]),
    ("/api/dealers", ["dealers.*", "crm.*"]),
    ("/api/portal", ["dealers.*", "crm.*", "sales.*"]),
    ("/api/pricing", ["dealers.*", "sales.*", "settings.*"]),
    ("/api/purchase", ["purchase.*"]),
    ("/api/inventory", ["inventory.*", "settings.*"]),
    ("/api/logistics", ["logistics.*", "sales.*"]),
    ("/api/rfid", ["rfid.*", "inventory.*", "logistics.*"]),
    ("/api/manufacturing", ["manufacturing.*"]),
    ("/api/quality", ["quality.*"]),
    ("/api/hrms", ["hrms.*"]),
    ("/api/projects", ["projects.*"]),
    ("/api/service", ["service.*"]),
    ("/api/documents", ["documents.*"]),
    ("/api/reports", ["reports.*"]),
    ("/api/bi", ["bi.*"]),
    ("/api/ai", ["ai.*", "agents.*"]),
    ("/api/agents", ["agents.*", "agents.view", "automation.*"]),
    ("/api/automation", ["automation.*", "settings.*"]),
    ("/api/comms", ["comms.*", "whatsapp.*", "crm.*"]),
    ("/api/whatsapp", ["whatsapp.*", "comms.*", "crm.*"]),
    ("/api/compliance", ["compliance.*", "compliance.view", "agents.*"]),
    ("/api/payments", ["sales.*", "accounting.*", "settings.*"]),
    ("/api/accounting", ["accounting.*"]),
    ("/api/users", ["settings.*"]),
    ("/api/modules", ["settings.*"]),
    ("/api/custom-fields", ["settings.*"]),
    ("/api/brand", ["settings.*"]),
    ("/api/ha", ["ha.*", "settings.*"]),
    ("/api/rules", ["automation.*", "settings.*", "agents.*"]),
    ("/api/watch", ["watch.*", "settings.*", "hrms.*"]),
    ("/api/bridges", ["bridges.*", "settings.*", "books.*", "accounting.*"]),
    ("/api/company/profile", ["settings.*"]),
    ("/api/company/profiles", ["settings.*"]),
    ("/api/drafts", []),  # any authenticated user — own drafts
    ("/api/activity", []),  # page/logout tracking — any authenticated user
    ("/api/security", ["settings.*", "hrms.*", "reports.*"]),
    ("/api/auth/revoke-sessions", []),
    ("/api/auth/change-password", []),
    ("/api/auth/theme", []),  # any authenticated user
    ("/api/notifications", []),  # any authenticated user
    ("/api/ops/backup", ["settings.*"]),
    ("/api/ops/purge-demo", ["settings.*"]),
    ("/api/ops/modules-overview", ["settings.*", "dashboard.*", "reports.*"]),
]

_SKIP_AUTH = {
    "/api/health",
    "/api/auth/login",
    "/api/brand/public",
    "/api/core-control/unlock",  # owner master pass → recovery session (rate limited)
}

# Prefix skips (token validated inside handler)
_SKIP_PREFIX_PUBLIC = (
    "/api/bridges/hooks/inbound/",
    "/api/meta/whatsapp/webhook",
)

# Peer cluster routes authenticate via X-Cluster-Token themselves
_SKIP_PREFIX_TOKEN = (
    "/api/ha/heartbeat",
    "/api/ha/snapshot",
    "/api/ha/events",
    "/api/ha/public-status",
)

_MUTATING = {"POST", "PUT", "PATCH", "DELETE"}


def _needed_for(path: str) -> list[str] | None:
    for prefix, perms in _WRITE_RULES:
        if path.startswith(prefix):
            return perms
    if path.startswith("/api/"):
        return ["settings.*"]  # unknown write → admin only
    return None


class RbacWriteMiddleware(BaseHTTPMiddleware):
    """Enforce role permissions on mutating /api/* routes (go-live hard RBAC)."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        path = request.url.path
        method = request.method.upper()

        if path in _SKIP_AUTH or method == "OPTIONS":
            return await call_next(request)

        if any(path.startswith(p) for p in _SKIP_PREFIX_TOKEN):
            return await call_next(request)

        if any(path.startswith(p) for p in _SKIP_PREFIX_PUBLIC):
            return await call_next(request)

        # Hot replica: block business writes — primary is sole writer (no split-brain)
        if (
            settings.cluster_enabled
            and settings.cluster_role == "replica"
            and method in _MUTATING
            and path.startswith("/api/")
            and not path.startswith("/api/ha/")
            and not path.startswith("/api/auth/")
        ):
            return JSONResponse(
                {
                    "detail": (
                        "This node is a HOT REPLICA (read/sync only). "
                        f"Writes go to primary: {settings.cluster_primary_url}. "
                        "If primary is down, use Resilience → Promote / auto-failover."
                    ),
                    "primary_url": settings.cluster_primary_url,
                    "role": "replica",
                    "redirect_writes": True,
                },
                status_code=409,
            )

        if method not in _MUTATING or not path.startswith("/api/"):
            return await call_next(request)

        auth = request.headers.get("authorization") or ""
        token = auth[7:].strip() if auth.lower().startswith("bearer ") else ""
        if not token:
            return JSONResponse({"detail": "Not authenticated"}, status_code=401)

        payload = decode_token(token)
        if not payload or not payload.get("sub"):
            return JSONResponse({"detail": "Invalid token"}, status_code=401)

        needed = _needed_for(path)
        if needed is None:
            return await call_next(request)

        db = SessionLocal()
        try:
            user = db.query(User).filter(User.email == payload["sub"]).first()
            if not user or not user.is_active:
                return JSONResponse({"detail": "User inactive"}, status_code=401)
            if not needed:
                return await call_next(request)
            if has_permission(user, db, *needed):
                return await call_next(request)
            return JSONResponse(
                {"detail": f"Permission required: {' or '.join(needed)}"},
                status_code=403,
            )
        finally:
            db.close()
