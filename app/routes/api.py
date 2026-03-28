import hashlib
import os
import re
import uuid
from pathlib import Path
from typing import Optional

import aiofiles
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from pydantic import BaseModel, EmailStr
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth_utils import require_user
from app.database import get_db
from app.models import Category, Rating, Skill, User

_UPLOAD_DIR = Path(__file__).parent.parent.parent / "static" / "uploads"
_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

_ALLOWED_EXTENSIONS = {".zip", ".py", ".json", ".yaml", ".yml", ".md", ".txt"}
_MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_SIZE_MB", "10"))

router = APIRouter(prefix="/api/v1")


# ── Helpers ──────────────────────────────────────────────────────────────────


def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    return text[:200]


def compute_content_hash(
    title: str, description: str, short_desc: str, author: str, version: str
) -> str:
    parts = sorted(
        [title.strip(), description.strip(), short_desc.strip(), author.strip(), version.strip()]
    )
    return hashlib.sha256("|".join(parts).encode()).hexdigest()


def _skill_summary(s: Skill) -> dict:
    return {
        "id": s.id,
        "title": s.title,
        "short_desc": s.short_desc,
        "author": s.author,
        "version": s.version,
        "platform": s.platform,
        "tags": s.tags,
        "category": s.category.slug if s.category else None,
        "category_name": s.category.name if s.category else None,
        "install_count": s.install_count,
        "avg_rating": s.avg_rating,
        "rating_count": s.rating_count,
        "created_at": s.created_at.isoformat() if s.created_at else None,
    }


def _skill_detail(s: Skill) -> dict:
    return {
        **_skill_summary(s),
        "description": s.description,
    }


# ── 1. Categories ─────────────────────────────────────────────────────────────


@router.get("/categories")
async def list_categories(db: Session = Depends(get_db)):
    """List all categories with their approved skill count."""
    cats = db.query(Category).order_by(Category.name).all()
    return [
        {
            "slug": c.slug,
            "name": c.name,
            "icon": c.icon,
            "skill_count": db.query(Skill)
            .filter(Skill.category_id == c.id, Skill.status == "approved", Skill.is_active == True)
            .count(),
        }
        for c in cats
    ]


# ── 2. Skills list (search + filter + paginate) ───────────────────────────────


_SORT_OPTIONS = {"popular", "newest", "oldest", "rating"}


@router.get("/skills")
async def list_skills(
    category: Optional[str] = Query(None, description="Filter by category slug"),
    q: Optional[str] = Query(None, description="Search in title / short_desc / tags"),
    platform: Optional[str] = Query(None, description="all / mac / windows"),
    sort: str = Query("popular", description="popular | newest | oldest | rating"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """Search and list approved skills with pagination."""
    if sort not in _SORT_OPTIONS:
        raise HTTPException(400, f"sort must be one of: {', '.join(sorted(_SORT_OPTIONS))}")

    query = db.query(Skill).filter(Skill.status == "approved", Skill.is_active == True)

    if category:
        query = query.join(Category).filter(Category.slug == category)
    if platform:
        query = query.filter(Skill.platform == platform)
    if q:
        like = f"%{q}%"
        query = query.filter(
            Skill.title.ilike(like) | Skill.short_desc.ilike(like) | Skill.tags.ilike(like)
        )

    if sort == "newest":
        query = query.order_by(Skill.created_at.desc())
    elif sort == "oldest":
        query = query.order_by(Skill.created_at.asc())
    elif sort == "rating":
        query = query.order_by((Skill.rating_sum / (Skill.rating_count + 1)).desc())
    else:
        query = query.order_by(Skill.install_count.desc())

    total = query.count()
    total_pages = max(1, (total + page_size - 1) // page_size)

    if page > total_pages and total > 0:
        raise HTTPException(400, f"page {page} exceeds total_pages {total_pages}")

    rows = query.offset((page - 1) * page_size).limit(page_size).all()
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
        "has_prev": page > 1,
        "has_next": page < total_pages,
        "items": [_skill_summary(s) for s in rows],
    }


# ── 3. Skill detail (public, no source_file) ──────────────────────────────────


@router.get("/skills/{skill_id}")
async def get_skill(skill_id: int, db: Session = Depends(get_db)):
    """Return full metadata for an approved skill (no source_file)."""
    skill = db.query(Skill).filter(
        Skill.id == skill_id, Skill.status == "approved", Skill.is_active == True
    ).first()
    if not skill:
        raise HTTPException(404, "Skill not found")
    return _skill_detail(skill)


# ── 4. Download (public, returns source_file + increments install_count) ──────


@router.get("/skills/{skill_id}/download")
async def download_skill(skill_id: int, db: Session = Depends(get_db)):
    """Download full metadata + source_file. Increments install count."""
    skill = db.query(Skill).filter(
        Skill.id == skill_id, Skill.status == "approved", Skill.is_active == True
    ).first()
    if not skill:
        raise HTTPException(404, "Skill not found or not yet approved")
    skill.install_count += 1
    db.commit()
    db.refresh(skill)
    return {
        **_skill_detail(skill),
        "source_file": skill.source_file,
    }


# ── 5. Upload (auth required) ─────────────────────────────────────────────────


class SkillUploadRequest(BaseModel):
    title: str
    short_desc: str
    description: str
    category_slug: str
    platform: str = "all"
    tags: str = ""
    version: str = "1.0.0"
    source_file: Optional[str] = None


@router.post("/skills", status_code=201)
async def upload_skill(
    payload: SkillUploadRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user),
):
    """
    Submit a skill for review. Requires authentication.
    Deduplication: exact content hash → duplicate; same user+slug → update/re-submit.
    """
    category = db.query(Category).filter(Category.slug == payload.category_slug).first()
    if not category:
        raise HTTPException(400, f"Unknown category: {payload.category_slug}")

    content_hash = compute_content_hash(
        payload.title, payload.description, payload.short_desc,
        current_user.email, payload.version,
    )
    skill_slug = slugify(payload.title)

    # 1. Exact content match → idempotent
    existing_by_hash = db.query(Skill).filter(Skill.content_hash == content_hash).first()
    if existing_by_hash:
        return {
            "id": existing_by_hash.id,
            "status": existing_by_hash.status,
            "action": "duplicate",
            "message": "Identical skill already exists.",
        }

    # 2. Same user + slug → update or re-submit
    existing_by_user = (
        db.query(Skill)
        .filter(Skill.user_id == current_user.id, Skill.skill_slug == skill_slug)
        .order_by(Skill.id.desc())
        .first()
    )

    if existing_by_user:
        if existing_by_user.status == "pending":
            for attr, val in [
                ("title", payload.title), ("short_desc", payload.short_desc),
                ("description", payload.description), ("category_id", category.id),
                ("platform", payload.platform), ("tags", payload.tags),
                ("version", payload.version), ("source_file", payload.source_file),
                ("content_hash", content_hash),
            ]:
                setattr(existing_by_user, attr, val)
            db.commit()
            return {"id": existing_by_user.id, "status": "pending", "action": "updated",
                    "message": "Your pending skill has been updated."}

        elif existing_by_user.status == "approved":
            skill = Skill(
                title=payload.title, short_desc=payload.short_desc,
                description=payload.description, category_id=category.id,
                platform=payload.platform, author=current_user.display_name or current_user.email,
                tags=payload.tags, version=payload.version, source_file=payload.source_file,
                user_id=current_user.id, skill_slug=skill_slug, content_hash=content_hash,
                status="pending", is_active=False, parent_id=existing_by_user.id,
            )
            db.add(skill)
            db.commit()
            return {"id": skill.id, "status": "pending", "action": "updated",
                    "message": "Update submitted for review."}

        else:  # rejected → fresh retry
            skill = Skill(
                title=payload.title, short_desc=payload.short_desc,
                description=payload.description, category_id=category.id,
                platform=payload.platform, author=current_user.display_name or current_user.email,
                tags=payload.tags, version=payload.version, source_file=payload.source_file,
                user_id=current_user.id, skill_slug=skill_slug, content_hash=content_hash,
                status="pending", is_active=False,
            )
            db.add(skill)
            db.commit()
            return {"id": skill.id, "status": "pending", "action": "created",
                    "message": "Your skill is pending review."}

    # 3. Brand new submission
    skill = Skill(
        title=payload.title, short_desc=payload.short_desc,
        description=payload.description, category_id=category.id,
        platform=payload.platform, author=current_user.display_name or current_user.email,
        tags=payload.tags, version=payload.version, source_file=payload.source_file,
        user_id=current_user.id, skill_slug=skill_slug, content_hash=content_hash,
        status="pending", is_active=False,
    )
    db.add(skill)
    db.commit()
    return {"id": skill.id, "status": "pending", "action": "created",
            "message": "Your skill is pending review."}


# ── 6. Rate a skill (auth required) ──────────────────────────────────────────


class RateRequest(BaseModel):
    score: int


@router.post("/skills/{skill_id}/rate")
async def rate_skill(
    skill_id: int,
    body: RateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user),
):
    """Rate a skill 1–5. One rating per user; updates on re-submit."""
    if not 1 <= body.score <= 5:
        raise HTTPException(400, "Score must be between 1 and 5")

    skill = db.query(Skill).filter(
        Skill.id == skill_id, Skill.status == "approved", Skill.is_active == True
    ).first()
    if not skill:
        raise HTTPException(404, "Skill not found")

    existing = db.query(Rating).filter(
        Rating.skill_id == skill_id, Rating.user_id == current_user.id
    ).first()

    if existing:
        skill.rating_sum = skill.rating_sum - existing.score + body.score
        existing.score = body.score
    else:
        db.add(Rating(skill_id=skill_id, user_id=current_user.id,
                      ip_address="user", score=body.score))
        skill.rating_sum += body.score
        skill.rating_count += 1
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            existing = db.query(Rating).filter(
                Rating.skill_id == skill_id, Rating.user_id == current_user.id
            ).first()
            if existing:
                skill.rating_sum = skill.rating_sum - existing.score + body.score
                existing.score = body.score

    db.commit()
    db.refresh(skill)
    return {"avg_rating": skill.avg_rating, "rating_count": skill.rating_count}


# ── 7. Submission status (auth required, own skills only) ─────────────────────


@router.get("/skills/{skill_id}/status")
async def get_skill_status(
    skill_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user),
):
    """Check review status of your own submitted skill."""
    skill = db.query(Skill).filter(Skill.id == skill_id).first()
    if not skill:
        raise HTTPException(404, "Skill not found")
    if skill.user_id != current_user.id:
        raise HTTPException(403, "You can only check the status of your own submissions")
    return {
        "id": skill.id,
        "title": skill.title,
        "status": skill.status,
        "review_note": skill.review_note,
        "submitted_at": skill.created_at.isoformat() if skill.created_at else None,
    }


# ── Auth endpoints ────────────────────────────────────────────────────────────


class SendCodeRequest(BaseModel):
    email: EmailStr


class VerifyCodeRequest(BaseModel):
    email: EmailStr
    code: str
    client_name: Optional[str] = None


@router.post("/auth/send-code")
async def api_send_code(payload: SendCodeRequest, db: Session = Depends(get_db)):
    """Send a 6-digit OTP to the given email. Rate-limited to once per 60 seconds."""
    from app.routes.auth import _send_code_logic
    _send_code_logic(str(payload.email).strip().lower(), db)
    return {"detail": "Verification code sent. Check your email."}


@router.post("/auth/verify-code")
async def api_verify_code(payload: VerifyCodeRequest, db: Session = Depends(get_db)):
    """Verify OTP and return a Bearer token valid for 30 days."""
    from app.routes.auth import _validate_otp, _get_or_create_user, _create_token
    import os
    email = str(payload.email).strip().lower()
    _validate_otp(email, payload.code.strip(), db)
    user = _get_or_create_user(email, db)
    token_raw = _create_token(user, name=payload.client_name or "API Client", db=db)
    expire_days = int(os.getenv("TOKEN_EXPIRE_DAYS", "30"))
    return {"access_token": token_raw, "token_type": "bearer", "expires_in": expire_days * 86400}


# ── Account ───────────────────────────────────────────────────────────────────


@router.get("/account/me")
async def api_me(current_user: User = Depends(require_user)):
    """Return the current authenticated user's profile."""
    return {
        "id": current_user.id,
        "email": current_user.email,
        "display_name": current_user.display_name,
        "created_at": current_user.created_at.isoformat() if current_user.created_at else None,
        "last_login_at": current_user.last_login_at.isoformat() if current_user.last_login_at else None,
    }


# ── File upload ───────────────────────────────────────────────────────────────


@router.post("/files/upload")
async def upload_file(
    file: UploadFile = File(...),
    current_user: User = Depends(require_user),
):
    """
    Upload a skill file (step 1 of 2).
    Returns a file_url to pass as source_file when submitting a skill.

    Allowed types: .zip .py .json .yaml .yml .md .txt
    Max size: MAX_UPLOAD_SIZE_MB (default 10 MB)
    """
    # Extension check
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in _ALLOWED_EXTENSIONS:
        raise HTTPException(
            400,
            f"File type '{suffix}' not allowed. Allowed: {', '.join(sorted(_ALLOWED_EXTENSIONS))}",
        )

    # Read content and enforce size limit
    max_bytes = _MAX_UPLOAD_MB * 1024 * 1024
    content = await file.read(max_bytes + 1)
    if len(content) > max_bytes:
        raise HTTPException(
            413,
            f"File too large. Maximum allowed size is {_MAX_UPLOAD_MB} MB.",
        )

    # Generate unique filename: {user_id}_{8-char uuid}{ext}
    short_id = uuid.uuid4().hex[:8]
    stored_name = f"{current_user.id}_{short_id}{suffix}"
    dest = _UPLOAD_DIR / stored_name

    async with aiofiles.open(dest, "wb") as f:
        await f.write(content)

    return {
        "file_url": f"/static/uploads/{stored_name}",
        "filename": stored_name,
        "size": len(content),
    }
