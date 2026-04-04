import hashlib
import os
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

load_dotenv()

from app.database import engine, Base
from app.routes import home, skills, admin
from app.routes import api
from app.routes import auth, account
from app.routes import docs

# Schema is managed by Alembic. Run `alembic upgrade head` before starting.
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Hushclaw", docs_url=None, redoc_url=None)

BASE_DIR = Path(__file__).parent

app.mount("/static", StaticFiles(directory=BASE_DIR.parent / "static"), name="static")

app.include_router(home.router)
app.include_router(skills.router)
app.include_router(admin.router)
app.include_router(api.router)
app.include_router(auth.router)
app.include_router(account.router)
app.include_router(docs.router)


@app.middleware("http")
async def attach_current_user(request: Request, call_next):
    """Resolve the session cookie into a User object and attach to request.state."""
    from app.auth_utils import COOKIE_NAME
    from app.database import SessionLocal
    from app.models import UserToken

    request.state.current_user = None
    token_raw = request.cookies.get(COOKIE_NAME)
    if token_raw:
        try:
            token_hash = hashlib.sha256(token_raw.encode()).hexdigest()
            db = SessionLocal()
            try:
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
                    request.state.current_user = record.user
            finally:
                db.close()
        except Exception:
            pass

    response = await call_next(request)
    return response
