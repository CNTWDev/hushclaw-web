from fastapi import APIRouter, Request, Depends
from fastapi.templating import Jinja2Templates
from pathlib import Path
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Category, Skill

router = APIRouter()
templates = Jinja2Templates(directory=Path(__file__).parent.parent / "templates")


@router.get("/")
async def index(request: Request, db: Session = Depends(get_db)):
    categories = db.query(Category).all()
    featured_skills = (
        db.query(Skill)
        .filter(Skill.is_active == True)
        .order_by(Skill.install_count.desc())
        .limit(6)
        .all()
    )
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "categories": categories,
            "featured_skills": featured_skills,
        },
    )
