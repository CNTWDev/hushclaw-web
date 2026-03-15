from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import JSONResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.database import get_db
from app.models import Category, Skill, Rating

router = APIRouter()
templates = Jinja2Templates(directory=Path(__file__).parent.parent / "templates")

# Track which skill IDs have been incremented in this session (per request IP)
_install_incremented: set = set()


class RateRequest(BaseModel):
    score: int


@router.get("/skills")
async def skills_list(
    request: Request,
    db: Session = Depends(get_db),
    category: str = "",
    q: str = "",
    sort: str = "popular",
):
    categories = db.query(Category).all()
    query = db.query(Skill).filter(Skill.is_active == True)

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

    skills = query.all()

    return templates.TemplateResponse(
        "skills/index.html",
        {
            "request": request,
            "skills": skills,
            "categories": categories,
            "active_category": category,
            "search_query": q,
            "sort": sort,
        },
    )


@router.get("/skills/{skill_id}")
async def skill_detail(request: Request, skill_id: int, db: Session = Depends(get_db)):
    skill = db.query(Skill).filter(Skill.id == skill_id, Skill.is_active == True).first()
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")

    client_ip = request.client.host
    session_key = f"{skill_id}:{client_ip}"
    if session_key not in _install_incremented:
        skill.install_count += 1
        db.commit()
        _install_incremented.add(session_key)
        db.refresh(skill)

    user_rating = (
        db.query(Rating)
        .filter(Rating.skill_id == skill_id, Rating.ip_address == client_ip)
        .first()
    )

    return templates.TemplateResponse(
        "skills/detail.html",
        {
            "request": request,
            "skill": skill,
            "user_rating": user_rating.score if user_rating else 0,
        },
    )


@router.post("/skills/{skill_id}/rate")
async def rate_skill(skill_id: int, body: RateRequest, request: Request, db: Session = Depends(get_db)):
    if body.score < 1 or body.score > 5:
        raise HTTPException(status_code=400, detail="Score must be between 1 and 5")

    skill = db.query(Skill).filter(Skill.id == skill_id, Skill.is_active == True).first()
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")

    client_ip = request.client.host

    existing = (
        db.query(Rating)
        .filter(Rating.skill_id == skill_id, Rating.ip_address == client_ip)
        .first()
    )

    if existing:
        old_score = existing.score
        existing.score = body.score
        skill.rating_sum = skill.rating_sum - old_score + body.score
        db.commit()
    else:
        rating = Rating(skill_id=skill_id, ip_address=client_ip, score=body.score)
        db.add(rating)
        skill.rating_sum += body.score
        skill.rating_count += 1
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            existing = (
                db.query(Rating)
                .filter(Rating.skill_id == skill_id, Rating.ip_address == client_ip)
                .first()
            )
            if existing:
                old_score = existing.score
                existing.score = body.score
                skill.rating_sum = skill.rating_sum - old_score + body.score
                db.commit()

    db.refresh(skill)
    return JSONResponse({"avg_rating": skill.avg_rating, "rating_count": skill.rating_count})
