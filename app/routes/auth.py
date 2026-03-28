import hashlib
import os
import random
import secrets
import smtplib
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from typing import Optional

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from app.auth_utils import COOKIE_NAME
from app.database import get_db
from app.models import EmailOTP, User, UserToken

router = APIRouter(prefix="/auth", tags=["auth"])
templates = Jinja2Templates(directory=Path(__file__).parent.parent / "templates")

OTP_EXPIRE_MINUTES = int(os.getenv("OTP_EXPIRE_MINUTES", "10"))
TOKEN_EXPIRE_DAYS = int(os.getenv("TOKEN_EXPIRE_DAYS", "30"))
SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM = os.getenv("SMTP_FROM", SMTP_USER)


# ── Helpers ─────────────────────────────────────────────────────────────────


def _generate_otp() -> str:
    return str(random.SystemRandom().randint(100000, 999999))


def _send_otp_email(to_email: str, code: str) -> None:
    subject = "Your Hushclaw login code"
    body = (
        f"Your verification code is: {code}\n\n"
        f"This code expires in {OTP_EXPIRE_MINUTES} minutes.\n"
        "If you did not request this, please ignore this email."
    )
    if not SMTP_HOST:
        # Dev fallback: print to console
        print(f"[DEV] OTP for {to_email}: {code}")
        return

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = SMTP_FROM
    msg["To"] = to_email

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.ehlo()
        server.starttls()
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.send_message(msg)


def _create_token(user: User, name: Optional[str], db: Session) -> str:
    token_raw = "hc_" + secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(token_raw.encode()).hexdigest()
    token_prefix = token_raw[:10]
    expires_at = datetime.utcnow() + timedelta(days=TOKEN_EXPIRE_DAYS)

    record = UserToken(
        user_id=user.id,
        token_hash=token_hash,
        token_prefix=token_prefix,
        name=name or "Unknown",
        expires_at=expires_at,
    )
    db.add(record)

    user.last_login_at = datetime.utcnow()
    db.commit()
    return token_raw


def _get_or_create_user(email: str, db: Session) -> User:
    user = db.query(User).filter(User.email == email).first()
    if not user:
        user = User(email=email)
        db.add(user)
        db.commit()
        db.refresh(user)
    return user


def _validate_otp(email: str, code: str, db: Session) -> EmailOTP:
    otp = (
        db.query(EmailOTP)
        .filter(
            EmailOTP.email == email,
            EmailOTP.used_at == None,  # noqa: E711
            EmailOTP.expires_at > datetime.utcnow(),
        )
        .order_by(EmailOTP.id.desc())
        .first()
    )

    if not otp:
        raise HTTPException(status_code=400, detail="No valid code found. Please request a new one.")

    if otp.attempts >= 3:
        raise HTTPException(status_code=400, detail="Code invalidated after too many attempts. Please request a new one.")

    if otp.code != code:
        otp.attempts += 1
        db.commit()
        remaining = 3 - otp.attempts
        raise HTTPException(status_code=400, detail=f"Invalid code. {remaining} attempt(s) remaining.")

    otp.used_at = datetime.utcnow()
    db.commit()
    return otp


def _send_code_logic(email: str, db: Session) -> None:
    # 60-second cooldown: reject if there's an unused OTP created within the last 60s
    recent = (
        db.query(EmailOTP)
        .filter(
            EmailOTP.email == email,
            EmailOTP.used_at == None,  # noqa: E711
            EmailOTP.expires_at > datetime.utcnow() + timedelta(seconds=(OTP_EXPIRE_MINUTES * 60 - 60)),
        )
        .first()
    )
    if recent:
        raise HTTPException(status_code=429, detail="Please wait 60 seconds before requesting a new code.")

    code = _generate_otp()
    expires_at = datetime.utcnow() + timedelta(minutes=OTP_EXPIRE_MINUTES)
    otp = EmailOTP(email=email, code=code, expires_at=expires_at)
    db.add(otp)
    db.commit()

    _send_otp_email(email, code)


# ── Web routes ───────────────────────────────────────────────────────────────


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("auth/login.html", {"request": request})


@router.post("/send-code", response_class=HTMLResponse)
async def web_send_code(
    request: Request,
    email: str = Form(...),
    db: Session = Depends(get_db),
):
    try:
        _send_code_logic(email.strip().lower(), db)
    except HTTPException as exc:
        return templates.TemplateResponse(
            "auth/login.html",
            {"request": request, "error": exc.detail, "step": "email", "email": email},
            status_code=exc.status_code,
        )
    return templates.TemplateResponse(
        "auth/login.html",
        {"request": request, "step": "code", "email": email.strip().lower()},
    )


@router.post("/verify-code")
async def web_verify_code(
    request: Request,
    email: str = Form(...),
    code: str = Form(...),
    db: Session = Depends(get_db),
):
    try:
        _validate_otp(email.strip().lower(), code.strip(), db)
    except HTTPException as exc:
        return templates.TemplateResponse(
            "auth/login.html",
            {"request": request, "error": exc.detail, "step": "code", "email": email},
            status_code=exc.status_code,
        )

    user = _get_or_create_user(email.strip().lower(), db)
    ua = request.headers.get("user-agent", "Web")[:60]
    token_raw = _create_token(user, name=ua, db=db)

    resp = RedirectResponse(url="/account", status_code=302)
    resp.set_cookie(
        COOKIE_NAME,
        token_raw,
        httponly=True,
        samesite="lax",
        max_age=TOKEN_EXPIRE_DAYS * 86400,
    )
    return resp


@router.post("/logout")
async def logout(request: Request):
    resp = RedirectResponse(url="/auth/login", status_code=302)
    resp.delete_cookie(COOKIE_NAME)
    return resp
