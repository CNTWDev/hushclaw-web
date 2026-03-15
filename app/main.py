import os
from pathlib import Path
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

load_dotenv()

from app.database import engine, Base
from app.routes import home, skills, admin

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Hushclaw", docs_url=None, redoc_url=None)

BASE_DIR = Path(__file__).parent

app.mount("/static", StaticFiles(directory=BASE_DIR.parent / "static"), name="static")

app.include_router(home.router)
app.include_router(skills.router)
app.include_router(admin.router)
