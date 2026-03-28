import hashlib
import os
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import text

load_dotenv()

from app.database import engine, Base
from app.routes import home, skills, admin
from app.routes import api
from app.routes import auth, account

Base.metadata.create_all(bind=engine)


def _run_migrations():
    """Add new columns / tables when upgrading an existing database."""
    with engine.connect() as conn:
        # ── skills table columns ────────────────────────────────────────────────
        result = conn.execute(text("PRAGMA table_info(skills)"))
        existing_cols = {row[1] for row in result.fetchall()}

        new_skill_columns = [
            ("client_id",    "VARCHAR(36)"),
            ("user_id",      "INTEGER"),
            ("skill_slug",   "VARCHAR(200)"),
            ("content_hash", "VARCHAR(64)"),
            ("version",      "VARCHAR(20) DEFAULT '1.0.0'"),
            # Use 'approved' default so pre-existing seeded rows are visible in the store
            ("status",       "VARCHAR(20) DEFAULT 'approved'"),
            ("review_note",  "TEXT"),
            ("source_file",  "TEXT"),
            ("parent_id",    "INTEGER"),
        ]

        for col_name, col_def in new_skill_columns:
            if col_name not in existing_cols:
                conn.execute(text(f"ALTER TABLE skills ADD COLUMN {col_name} {col_def}"))

        # ── ratings table columns ────────────────────────────────────────────────
        result = conn.execute(text("PRAGMA table_info(ratings)"))
        existing_rating_cols = {row[1] for row in result.fetchall()}
        if "user_id" not in existing_rating_cols:
            conn.execute(text("ALTER TABLE ratings ADD COLUMN user_id INTEGER"))

        # ── users table ─────────────────────────────────────────────────────────
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS users (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                email         VARCHAR(255) UNIQUE NOT NULL,
                display_name  VARCHAR(100),
                is_active     BOOLEAN DEFAULT 1,
                created_at    DATETIME,
                last_login_at DATETIME
            )
        """))

        # ── email_otps table ────────────────────────────────────────────────────
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS email_otps (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                email      VARCHAR(255) NOT NULL,
                code       VARCHAR(6) NOT NULL,
                expires_at DATETIME NOT NULL,
                used_at    DATETIME,
                attempts   INTEGER DEFAULT 0
            )
        """))

        # ── user_tokens table ───────────────────────────────────────────────────
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS user_tokens (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id      INTEGER NOT NULL REFERENCES users(id),
                token_hash   VARCHAR(64) UNIQUE NOT NULL,
                token_prefix VARCHAR(10) NOT NULL,
                name         VARCHAR(100),
                expires_at   DATETIME NOT NULL,
                last_used_at DATETIME,
                created_at   DATETIME,
                is_active    BOOLEAN DEFAULT 1
            )
        """))

        conn.commit()


_run_migrations()

app = FastAPI(title="Hushclaw", docs_url=None, redoc_url=None)

BASE_DIR = Path(__file__).parent

app.mount("/static", StaticFiles(directory=BASE_DIR.parent / "static"), name="static")

app.include_router(home.router)
app.include_router(skills.router)
app.include_router(admin.router)
app.include_router(api.router)
app.include_router(auth.router)
app.include_router(account.router)


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
