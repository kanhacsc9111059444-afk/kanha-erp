from __future__ import annotations

from datetime import date, timedelta
from typing import Annotated, Any

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import decode_token
from app.models import User

security = HTTPBearer(auto_error=False)
DbDep = Annotated[Session, Depends(get_db)]


def get_current_user(
    db: DbDep,
    creds: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
) -> User:
    if not creds:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    payload = decode_token(creds.credentials)
    if not payload or not payload.get("sub"):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    user = db.query(User).filter(User.email == payload["sub"]).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User inactive")
    # Stolen phone / force logout: JWT session_epoch must match user.session_epoch
    token_se = int(payload.get("se") or 0)
    user_se = int(getattr(user, "session_epoch", 0) or 0)
    if token_se != user_se:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session revoked — login again (device logout / security wipe)",
        )
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def _role_permissions(user: User, db: Session) -> list[str]:
    if getattr(user, "is_superadmin", False):
        return ["*"]
    if not user.role_id:
        return []
    from app.models import Role

    role = db.get(Role, user.role_id)
    return list((role.permissions if role else []) or [])


def perm_match(granted: str, needed: str) -> bool:
    if granted == "*" or granted == needed:
        return True
    if granted.endswith(".*"):
        prefix = granted[:-1]  # "sales."
        return needed.startswith(prefix) or needed == granted[:-2]
    if needed.endswith(".*"):
        prefix = needed[:-1]
        return granted.startswith(prefix) or granted == needed[:-2]
    return False


def has_permission(user: User, db: Session, *needed: str) -> bool:
    if not needed:
        return True
    perms = _role_permissions(user, db)
    if "*" in perms:
        return True
    for need in needed:
        if any(perm_match(g, need) for g in perms):
            return True
    return False


def assert_perm(user: User, db: Session, *needed: str) -> None:
    if has_permission(user, db, *needed):
        return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=f"Permission required: {' or '.join(needed)}",
    )


def next_number(db: Session, company_id: int, model: Any, prefix: str) -> str:
    count = db.query(model).filter(model.company_id == company_id).count() + 1
    return f"{prefix}-{date.today().strftime('%Y%m')}-{count:04d}"


def audit(
    db: Session,
    *,
    company_id: int | None,
    user_id: int | None,
    action: str,
    entity: str,
    entity_id: str | None = None,
    detail: dict | None = None,
    request: Any | None = None,
) -> None:
    from app.models import AuditLog

    payload = dict(detail or {})
    if request is not None:
        try:
            from app.core.rate_limit import client_ip

            payload.setdefault("ip", client_ip(request))
            ua = request.headers.get("user-agent") or ""
            payload.setdefault("ua", ua[:180])
        except Exception:
            pass
    db.add(
        AuditLog(
            company_id=company_id,
            user_id=user_id,
            action=action,
            entity=entity,
            entity_id=entity_id,
            detail=payload,
        )
    )
