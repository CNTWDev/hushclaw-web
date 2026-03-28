import hashlib
from datetime import datetime
from typing import Optional

from fastapi import Depends, Header, HTTPException, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, UserToken

COOKIE_NAME = "hc_session"


def _hash_token(token_raw: str) -> str:
    return hashlib.sha256(token_raw.encode()).hexdigest()


def _resolve_token_record(token_raw: str, db: Session) -> Optional[UserToken]:
    token_hash = _hash_token(token_raw)
    record = (
        db.query(UserToken)
        .filter(
            UserToken.token_hash == token_hash,
            UserToken.is_active == True,
            UserToken.expires_at > datetime.utcnow(),
        )
        .first()
    )
    if record:
        record.last_used_at = datetime.utcnow()
        db.commit()
    return record


def get_current_user(
    request: Request,
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
) -> Optional[User]:
    """Return the authenticated User or None. Does NOT raise on missing auth."""
    token_raw: Optional[str] = None

    if authorization and authorization.startswith("Bearer "):
        token_raw = authorization.removeprefix("Bearer ").strip()
    elif cookie := request.cookies.get(COOKIE_NAME):
        token_raw = cookie

    if not token_raw:
        return None

    record = _resolve_token_record(token_raw, db)
    return record.user if record else None


def require_user(
    request: Request,
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
) -> User:
    """Return the authenticated User, raise 401 if not authenticated."""
    user = get_current_user(request, authorization, db)
    if user is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is disabled")
    return user
