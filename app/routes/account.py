from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.auth_utils import COOKIE_NAME, require_user
from app.database import get_db
from app.models import User, UserToken

router = APIRouter(prefix="/account", tags=["account"])
templates = Jinja2Templates(directory=Path(__file__).parent.parent / "templates")


@router.get("", response_class=HTMLResponse)
async def account_page(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user),
):
    tokens = (
        db.query(UserToken)
        .filter(
            UserToken.user_id == current_user.id,
            UserToken.is_active == True,
            UserToken.expires_at > datetime.utcnow(),
        )
        .order_by(UserToken.created_at.desc())
        .all()
    )
    return templates.TemplateResponse(
        "account/index.html",
        {"request": request, "user": current_user, "tokens": tokens},
    )


@router.post("/tokens/{token_id}/revoke")
async def revoke_token(
    token_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user),
):
    token = (
        db.query(UserToken)
        .filter(UserToken.id == token_id, UserToken.user_id == current_user.id)
        .first()
    )
    if not token:
        raise HTTPException(status_code=404, detail="Token not found")

    token.is_active = False
    db.commit()

    # If the revoked token is the one currently used in the browser, log out
    current_cookie = request.cookies.get(COOKIE_NAME, "")
    import hashlib
    current_hash = hashlib.sha256(current_cookie.encode()).hexdigest() if current_cookie else ""
    if current_hash == token.token_hash:
        resp = RedirectResponse(url="/auth/login", status_code=302)
        resp.delete_cookie(COOKIE_NAME)
        return resp

    return RedirectResponse(url="/account", status_code=302)
