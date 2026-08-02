from __future__ import annotations

import re
import time
from collections import defaultdict, deque
from threading import Lock

from fastapi import HTTPException, Request, status

from app.core.config import settings

_lock = Lock()
_hits: dict[str, deque[float]] = defaultdict(deque)


def client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host or "unknown"
    return "unknown"


def check_login_rate_limit(request: Request) -> None:
    """Simple in-memory rate limit — good for single-node; Redis later for multi-node."""
    key = f"login:{client_ip(request)}"
    now = time.time()
    window = float(settings.login_rate_window_seconds)
    limit = int(settings.login_rate_limit)
    with _lock:
        q = _hits[key]
        while q and now - q[0] > window:
            q.popleft()
        if len(q) >= limit:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Too many login attempts. Retry after {int(window)}s.",
            )
        q.append(now)


def validate_password_strength(password: str, *, allow_demo: bool | None = None) -> None:
    """Raise 400 if password too weak for production."""
    allow = settings.demo_mode if allow_demo is None else allow_demo
    pw = password or ""
    if len(pw) < settings.min_password_length:
        raise HTTPException(400, f"Password must be at least {settings.min_password_length} characters")
    if allow:
        return
    if not re.search(r"[A-Za-z]", pw) or not re.search(r"\d", pw):
        raise HTTPException(400, "Password must include letters and numbers")
    if pw.lower() in {"admin123", "sales123", "password", "welcome@123", "12345678"}:
        raise HTTPException(400, "Password is too common — choose a stronger one")
