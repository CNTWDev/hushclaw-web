# HushClaw

Lightweight, token-first AI Agent framework with persistent memory and a built-in browser UI. Zero mandatory dependencies — pure Python stdlib.

## Features

- **Browser UI** — full chat interface served at `http://localhost:8765`; sessions, memories, and multi-agent management panels; setup wizard on first launch
- **Token-first design** — explicit token budget per context section; Anthropic KV-cache support for the stable prefix
- **Persistent memory** — notes survive across sessions via SQLite FTS5 + local vector search
- **Zero hard dependencies** — runs with Python 3.11+ stdlib only (`sqlite3`, `tomllib`, `asyncio`, `urllib`)
- **Multiple providers** — Anthropic (urllib or SDK), Ollama, OpenAI-compatible
- **ReAct loop** — tool use with pluggable ContextEngine for lossless compaction
- **Plugin tools** — drop `.py` files into `~/.config/hushclaw/tools/` to extend
- **Multi-agent** — sequential pipelines, session-affinity pools, agent-to-agent delegation
- **Native storage paths** — macOS `~/Library/Application Support/hushclaw/`, Linux `~/.local/share/hushclaw/`

## Install

**macOS / Linux**

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/CNTWDev/hushclaw/master/install.sh)
```

**Windows**

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
Invoke-WebRequest -Uri https://raw.githubusercontent.com/CNTWDev/hushclaw/master/install.ps1 -OutFile install.ps1
.\install.ps1
```

---

## hushclaw-web

The official skill directory for HushClaw — browse, discover, and rate community skills.

### Tech Stack

- **Backend**: FastAPI + Uvicorn
- **Database**: SQLite + SQLAlchemy
- **Templates**: Jinja2
- **Python**: 3.11+

### Project Structure

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

### Local Development (Mac)

```bash
./start.sh
```

Automatically creates a virtual environment, installs dependencies, and starts the server at `http://localhost:8000`.

Or manually:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### Seed Data

```bash
source .venv/bin/activate
python seed_data.py
```

### Data Models

- **Category** — skill categories with icon and slug
- **Skill** — title, description, platform, tags, ratings
- **Rating** — per-IP ratings (1 vote per user per skill)
