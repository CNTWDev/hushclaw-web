from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth_utils import get_current_user, require_user
from app.database import get_db
from app.models import Category, Rating, Skill, User

router = APIRouter()
templates = Jinja2Templates(directory=Path(__file__).parent.parent / "templates")

PAGE_SIZE = 18


# ── Skills list ───────────────────────────────────────────────────────────────


@router.get("/skills", response_class=HTMLResponse)
async def skills_list(
    request: Request,
    db: Session = Depends(get_db),
    category: str = Query(""),
    q: str = Query(""),
    sort: str = Query("popular"),
    page: int = Query(1, ge=1),
):
    categories = db.query(Category).all()
    query = db.query(Skill).filter(Skill.is_active == True, Skill.status == "approved")

    if category:
        cat = db.query(Category).filter(Category.slug == category).first()
        if cat:
            query = query.filter(Skill.category_id == cat.id)

    if q:
        query = query.filter(
            Skill.title.contains(q) | Skill.short_desc.contains(q) | Skill.tags.contains(q)
        )

    if sort == "newest":
        query = query.order_by(Skill.created_at.desc())
    elif sort == "rating":
        query = query.order_by((Skill.rating_sum / (Skill.rating_count + 1)).desc())
    else:
        query = query.order_by(Skill.install_count.desc())

    total = query.count()
    total_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
    page = min(page, total_pages)
    skills = query.offset((page - 1) * PAGE_SIZE).limit(PAGE_SIZE).all()

    return templates.TemplateResponse(
        "skills/index.html",
        {
            "request": request,
            "skills": skills,
            "categories": categories,
            "active_category": category,
            "search_query": q,
            "sort": sort,
            "page": page,
            "total_pages": total_pages,
            "total": total,
        },
    )


# ── Skill detail ──────────────────────────────────────────────────────────────


@router.get("/skills/{skill_id}", response_class=HTMLResponse)
async def skill_detail(
    request: Request,
    skill_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    skill = db.query(Skill).filter(
        Skill.id == skill_id, Skill.is_active == True, Skill.status == "approved"
    ).first()
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")

    user_rating = 0
    if current_user:
        rating_row = db.query(Rating).filter(
            Rating.skill_id == skill_id, Rating.user_id == current_user.id
        ).first()
        user_rating = rating_row.score if rating_row else 0
    else:
        client_ip = request.client.host
        rating_row = db.query(Rating).filter(
            Rating.skill_id == skill_id, Rating.ip_address == client_ip
        ).first()
        user_rating = rating_row.score if rating_row else 0

    return templates.TemplateResponse(
        "skills/detail.html",
        {
            "request": request,
            "skill": skill,
            "user_rating": user_rating,
            "current_user": current_user,
        },
    )


# ── Rate a skill (web, requires login) ───────────────────────────────────────


class RateRequest(BaseModel):
    score: int


@router.post("/skills/{skill_id}/rate")
async def rate_skill(
    skill_id: int,
    body: RateRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not 1 <= body.score <= 5:
        raise HTTPException(400, "Score must be between 1 and 5")

    skill = db.query(Skill).filter(
        Skill.id == skill_id, Skill.is_active == True, Skill.status == "approved"
    ).first()
    if not skill:
        raise HTTPException(404, "Skill not found")

    if current_user:
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
    else:
        # Anonymous: IP-based fallback
        client_ip = request.client.host
        existing = db.query(Rating).filter(
            Rating.skill_id == skill_id, Rating.ip_address == client_ip
        ).first()
        if existing:
            skill.rating_sum = skill.rating_sum - existing.score + body.score
            existing.score = body.score
        else:
            db.add(Rating(skill_id=skill_id, ip_address=client_ip, score=body.score))
            skill.rating_sum += body.score
            skill.rating_count += 1
            try:
                db.commit()
            except IntegrityError:
                db.rollback()

    db.commit()
    db.refresh(skill)
    return JSONResponse({"avg_rating": skill.avg_rating, "rating_count": skill.rating_count})


# ── Submit skill (web, requires login) ───────────────────────────────────────


@router.get("/skills/submit", response_class=HTMLResponse)
async def submit_page(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user),
):
    categories = db.query(Category).order_by(Category.name).all()
    return templates.TemplateResponse(
        "skills/submit.html",
        {"request": request, "categories": categories, "error": None},
    )


@router.post("/skills/submit", response_class=HTMLResponse)
async def submit_skill(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user),
):
    import re as _re
    from app.routes.api import slugify, compute_content_hash

    form = await request.form()
    title = (form.get("title") or "").strip()
    short_desc = (form.get("short_desc") or "").strip()
    description = (form.get("description") or "").strip()
    category_slug = (form.get("category_slug") or "").strip()
    platform = (form.get("platform") or "all").strip()
    tags = (form.get("tags") or "").strip()
    version = (form.get("version") or "1.0.0").strip()
    source_file = (form.get("source_file") or "").strip() or None

    categories = db.query(Category).order_by(Category.name).all()

    def _err(msg):
        return templates.TemplateResponse(
            "skills/submit.html",
            {
                "request": request, "categories": categories, "error": msg,
                "form": dict(form),
            },
            status_code=400,
        )

    if not title or not short_desc or not description or not category_slug:
        return _err("Title, short description, description, and category are required.")

    category = db.query(Category).filter(Category.slug == category_slug).first()
    if not category:
        return _err(f"Unknown category: {category_slug}")

    content_hash = compute_content_hash(title, description, short_desc, current_user.email, version)
    skill_slug = slugify(title)

    existing_by_hash = db.query(Skill).filter(Skill.content_hash == content_hash).first()
    if existing_by_hash:
        return RedirectResponse(f"/skills/{existing_by_hash.id}/status", status_code=302)

    existing_by_user = (
        db.query(Skill)
        .filter(Skill.user_id == current_user.id, Skill.skill_slug == skill_slug)
        .order_by(Skill.id.desc())
        .first()
    )

    if existing_by_user and existing_by_user.status == "pending":
        for attr, val in [
            ("title", title), ("short_desc", short_desc), ("description", description),
            ("category_id", category.id), ("platform", platform), ("tags", tags),
            ("version", version), ("source_file", source_file), ("content_hash", content_hash),
        ]:
            setattr(existing_by_user, attr, val)
        db.commit()
        return RedirectResponse(f"/skills/{existing_by_user.id}/status", status_code=302)

    parent_id = None
    if existing_by_user and existing_by_user.status == "approved":
        parent_id = existing_by_user.id

    skill = Skill(
        title=title, short_desc=short_desc, description=description,
        category_id=category.id, platform=platform,
        author=current_user.display_name or current_user.email,
        tags=tags, version=version, source_file=source_file,
        user_id=current_user.id, skill_slug=skill_slug, content_hash=content_hash,
        status="pending", is_active=False, parent_id=parent_id,
    )
    db.add(skill)
    db.commit()
    return RedirectResponse(f"/skills/{skill.id}/status", status_code=302)


# ── Submission status (web, own skill only) ───────────────────────────────────


@router.get("/skills/{skill_id}/status", response_class=HTMLResponse)
async def skill_status_page(
    request: Request,
    skill_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user),
):
    skill = db.query(Skill).filter(Skill.id == skill_id).first()
    if not skill:
        raise HTTPException(404, "Skill not found")
    if skill.user_id != current_user.id:
        raise HTTPException(403, "You can only view your own submissions")
    return templates.TemplateResponse(
        "skills/status.html",
        {"request": request, "skill": skill},
    )
