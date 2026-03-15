# hushclaw-web

A web application for browsing and rating skills/tools, built with FastAPI and SQLite.

## Tech Stack

- **Backend**: FastAPI + Uvicorn
- **Database**: SQLite + SQLAlchemy
- **Templates**: Jinja2
- **Python**: 3.11+

## Project Structure

```
hushclaw-web/
├── app/
│   ├── main.py          # App entry point
│   ├── database.py      # DB connection
│   ├── models.py        # SQLAlchemy models
│   └── routes/
│       ├── home.py      # Home page
│       ├── skills.py    # Skills listing & detail
│       └── admin.py     # Admin panel
├── static/              # CSS, JS, images
├── requirements.txt
├── seed_data.py         # Seed initial data
└── start.sh             # Local dev startup script
```

## Local Development (Mac)

```bash
./start.sh
```

This will automatically create a virtual environment, install dependencies, and start the server at `http://localhost:8000`.

Or manually:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

## Seed Data

```bash
source .venv/bin/activate
python seed_data.py
```

## Data Models

- **Category** — skill categories with icon and slug
- **Skill** — individual skills with title, description, platform, tags, ratings
- **Rating** — per-IP ratings (1 vote per user per skill)
