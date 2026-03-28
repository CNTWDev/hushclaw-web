import os
from typing import Optional
from fastapi import APIRouter, Request, Depends, Form, HTTPException, Query
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
from sqlalchemy.orm import Session
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from app.database import get_db
from app.models import Category, Skill, User

router = APIRouter(prefix="/admin")
templates = Jinja2Templates(directory=Path(__file__).parent.parent / "templates")

SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-me")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")
serializer = URLSafeTimedSerializer(SECRET_KEY)
COOKIE_NAME = "admin_session"


def get_admin_session(request: Request):
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        return None
    try:
        data = serializer.loads(token, max_age=86400)
        if data.get("admin"):
            return data
    except (BadSignature, SignatureExpired):
        pass
    return None


def require_admin(request: Request):
    session = get_admin_session(request)
    if not session:
        raise HTTPException(status_code=302, headers={"Location": "/admin/login"})
    return session


@router.get("/login")
async def login_page(request: Request):
    return templates.TemplateResponse("admin/login.html", {"request": request, "error": None})


@router.post("/login")
async def login(request: Request, password: str = Form(...)):
    if password == ADMIN_PASSWORD:
        token = serializer.dumps({"admin": True})
        response = RedirectResponse(url="/admin", status_code=302)
        response.set_cookie(COOKIE_NAME, token, httponly=True, max_age=86400)
        return response
    return templates.TemplateResponse(
        "admin/login.html", {"request": request, "error": "Invalid password"}
    )


@router.get("/logout")
async def logout():
    response = RedirectResponse(url="/admin/login", status_code=302)
    response.delete_cookie(COOKIE_NAME)
    return response


@router.get("")
async def dashboard(
    request: Request,
    db: Session = Depends(get_db),
    status: Optional[str] = Query(None),
):
    require_admin(request)
    query = db.query(Skill)
    if status:
        query = query.filter(Skill.status == status)
    # Default: pending first, then others
    skills = query.order_by(
        (Skill.status == "pending").desc(),
        Skill.created_at.desc(),
    ).all()
    categories = db.query(Category).all()
    pending_count = db.query(Skill).filter(Skill.status == "pending").count()
    user_count = db.query(User).count()
    return templates.TemplateResponse(
        "admin/dashboard.html",
        {
            "request": request,
            "skills": skills,
            "categories": categories,
            "pending_count": pending_count,
            "user_count": user_count,
            "status_filter": status or "",
        },
    )


@router.get("/skills/new")
async def new_skill_form(request: Request, db: Session = Depends(get_db)):
    require_admin(request)
    categories = db.query(Category).all()
    return templates.TemplateResponse(
        "admin/skill_form.html",
        {"request": request, "skill": None, "categories": categories, "error": None},
    )


@router.post("/skills/new")
async def create_skill(
    request: Request,
    db: Session = Depends(get_db),
    title: str = Form(...),
    short_desc: str = Form(...),
    description: str = Form(...),
    category_id: int = Form(...),
    platform: str = Form("all"),
    author: str = Form("Hushclaw Team"),
    tags: str = Form(""),
    is_active: bool = Form(True),
):
    require_admin(request)
    skill = Skill(
        title=title,
        short_desc=short_desc,
        description=description,
        category_id=category_id,
        platform=platform,
        author=author,
        tags=tags,
        is_active=is_active,
    )
    db.add(skill)
    db.commit()
    return RedirectResponse(url="/admin", status_code=302)


@router.get("/skills/{skill_id}/edit")
async def edit_skill_form(skill_id: int, request: Request, db: Session = Depends(get_db)):
    require_admin(request)
    skill = db.query(Skill).filter(Skill.id == skill_id).first()
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    categories = db.query(Category).all()
    return templates.TemplateResponse(
        "admin/skill_form.html",
        {"request": request, "skill": skill, "categories": categories, "error": None},
    )


@router.post("/skills/{skill_id}/edit")
async def update_skill(
    skill_id: int,
    request: Request,
    db: Session = Depends(get_db),
    title: str = Form(...),
    short_desc: str = Form(...),
    description: str = Form(...),
    category_id: int = Form(...),
    platform: str = Form("all"),
    author: str = Form("Hushclaw Team"),
    tags: str = Form(""),
    is_active: str = Form("on"),
):
    require_admin(request)
    skill = db.query(Skill).filter(Skill.id == skill_id).first()
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    skill.title = title
    skill.short_desc = short_desc
    skill.description = description
    skill.category_id = category_id
    skill.platform = platform
    skill.author = author
    skill.tags = tags
    skill.is_active = is_active == "on"
    db.commit()
    return RedirectResponse(url="/admin", status_code=302)


@router.post("/skills/{skill_id}/delete")
async def delete_skill(skill_id: int, request: Request, db: Session = Depends(get_db)):
    require_admin(request)
    skill = db.query(Skill).filter(Skill.id == skill_id).first()
    if skill:
        db.delete(skill)
        db.commit()
    return RedirectResponse(url="/admin", status_code=302)


@router.get("/categories/new")
async def new_category_form(request: Request):
    require_admin(request)
    return templates.TemplateResponse(
        "admin/category_form.html", {"request": request, "category": None, "error": None}
    )


@router.post("/categories/new")
async def create_category(
    request: Request,
    db: Session = Depends(get_db),
    name: str = Form(...),
    slug: str = Form(...),
    icon: str = Form("📦"),
):
    require_admin(request)
    cat = Category(name=name, slug=slug, icon=icon)
    db.add(cat)
    db.commit()
    return RedirectResponse(url="/admin", status_code=302)


@router.post("/categories/{cat_id}/delete")
async def delete_category(cat_id: int, request: Request, db: Session = Depends(get_db)):
    require_admin(request)
    cat = db.query(Category).filter(Category.id == cat_id).first()
    if cat:
        db.delete(cat)
        db.commit()
    return RedirectResponse(url="/admin", status_code=302)


@router.post("/skills/{skill_id}/approve")
async def approve_skill(skill_id: int, request: Request, db: Session = Depends(get_db)):
    require_admin(request)
    skill = db.query(Skill).filter(Skill.id == skill_id).first()
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")

    if skill.parent_id:
        # Promote update: copy content onto the parent approved record
        parent = db.query(Skill).filter(Skill.id == skill.parent_id).first()
        if parent:
            parent.title = skill.title
            parent.short_desc = skill.short_desc
            parent.description = skill.description
            parent.category_id = skill.category_id
            parent.platform = skill.platform
            parent.author = skill.author
            parent.tags = skill.tags
            parent.version = skill.version
            parent.source_file = skill.source_file
            parent.content_hash = skill.content_hash
            parent.review_note = None
        db.delete(skill)
    else:
        skill.status = "approved"
        skill.is_active = True
        skill.review_note = None

    db.commit()
    return RedirectResponse(url="/admin", status_code=302)


@router.post("/skills/{skill_id}/reject")
async def reject_skill(
    skill_id: int,
    request: Request,
    db: Session = Depends(get_db),
    review_note: str = Form(""),
):
    require_admin(request)
    skill = db.query(Skill).filter(Skill.id == skill_id).first()
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    skill.status = "rejected"
    skill.is_active = False
    skill.review_note = review_note.strip() or None
    db.commit()
    return RedirectResponse(url="/admin", status_code=302)
