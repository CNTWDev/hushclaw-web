from pathlib import Path

import mistune
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Doc

router = APIRouter(prefix="/docs")
templates = Jinja2Templates(directory=Path(__file__).parent.parent / "templates")

_md = mistune.create_markdown(
    plugins=["strikethrough", "table", "task_lists"],
    escape=False,
)


@router.get("", response_class=HTMLResponse)
async def docs_index(request: Request, db: Session = Depends(get_db)):
    docs = (
        db.query(Doc)
        .filter(Doc.is_published == True)  # noqa: E712
        .order_by(Doc.created_at.desc())
        .all()
    )
    return templates.TemplateResponse(
        "docs/index.html", {"request": request, "docs": docs}
    )


@router.get("/{slug}", response_class=HTMLResponse)
async def doc_detail(slug: str, request: Request, db: Session = Depends(get_db)):
    doc = (
        db.query(Doc)
        .filter(Doc.slug == slug, Doc.is_published == True)  # noqa: E712
        .first()
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    content_html = _md(doc.content or "")
    return templates.TemplateResponse(
        "docs/detail.html",
        {"request": request, "doc": doc, "content_html": content_html},
    )
