"""Seed the database with sample categories and skills."""
import os
import sys
from datetime import datetime, timedelta
import random

sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv
load_dotenv()

from app.database import engine, SessionLocal, Base
from app.models import Category, Skill, Rating

Base.metadata.create_all(bind=engine)

db = SessionLocal()

# Clear existing data
db.query(Rating).delete()
db.query(Skill).delete()
db.query(Category).delete()
db.commit()

# ── Categories ─────────────────────────────────────────────────────────────────
categories_data = [
    ("System",       "system",      "⚙️",  "Core capabilities — shell commands, file management, browser control"),
    ("Search",       "search",      "🔍",  "Information retrieval — web search, summarization, data scraping"),
    ("Data & Docs",  "data-docs",   "📊",  "Processing & analysis — PDF, Excel, databases, visualization"),
    ("Automation",   "automation",  "🤖",  "Task execution — workflows, scheduling, batch processing, monitoring"),
    ("Integrations", "integrations","🔌",  "External connectors — Notion, GitHub, DingTalk, cloud services"),
    ("Creative",     "creative",    "✍️",  "Content generation — text, images, ideation, editing"),
    ("Agent Brain",  "agent-brain", "🧠",  "Agent enhancements — memory, self-evolution, skill management"),
    ("Security",     "security",    "🔒",  "Risk control — permission guards, credential management, security review"),
]

cats = {}
for name, slug, icon, _ in categories_data:
    cat = Category(name=name, slug=slug, icon=icon)
    db.add(cat)
    db.flush()
    cats[slug] = cat

db.commit()

# ── Skills ─────────────────────────────────────────────────────────────────────
skills_data = [

    # ── System ──────────────────────────────────────────────────────────────────
    {
        "title": "Shell Command Runner",
        "short_desc": "Execute shell commands via natural language — no terminal required",
        "description": "Describe what you want to do in plain English and HushClaw translates it into safe shell commands:\n\n• Supports file operations, process management, network diagnostics\n• Previews the command before execution\n• Captures stdout/stderr and explains the output\n• Maintains a history of executed commands\n\nRuns locally — nothing leaves your machine.",
        "category": "system",
        "platform": "all",
        "install_count": 4100,
        "rating_sum": 260,
        "rating_count": 58,
        "author": "HushClaw Team",
        "tags": "shell, terminal, system, commands",
    },
    {
        "title": "Smart File Manager",
        "short_desc": "Organise, rename, and move files using natural language instructions",
        "description": "Tell the agent what you want — it handles the rest:\n\n• Bulk rename with patterns (date, sequence, regex)\n• Auto-sort downloads folder by file type\n• Find and remove duplicates\n• Archive old files by date\n\nWorks with any local directory. Dry-run mode available before making changes.",
        "category": "system",
        "platform": "all",
        "install_count": 3200,
        "rating_sum": 198,
        "rating_count": 44,
        "author": "HushClaw Team",
        "tags": "files, organise, rename, batch",
    },
    {
        "title": "Browser Agent",
        "short_desc": "Control your browser with plain-text instructions — click, fill, scrape",
        "description": "Give the agent a goal and it navigates the web on your behalf:\n\n• Click buttons, fill forms, scroll pages\n• Extract structured data from any website\n• Handle login flows and multi-step navigation\n• Screenshot any page on demand\n\nUses HushClaw's built-in browser UI at localhost:8765.",
        "category": "system",
        "platform": "all",
        "install_count": 5800,
        "rating_sum": 370,
        "rating_count": 82,
        "author": "HushClaw Team",
        "tags": "browser, automation, scrape, control",
    },

    # ── Search ───────────────────────────────────────────────────────────────────
    {
        "title": "Web Search & Summarise",
        "short_desc": "Search the web and get a concise AI summary — no tab-switching needed",
        "description": "Ask a question and the agent:\n\n• Queries multiple search engines in parallel\n• Fetches and reads the top results\n• Produces a structured summary with source citations\n• Highlights conflicting information across sources\n\nSupports follow-up questions with full context retained.",
        "category": "search",
        "platform": "all",
        "install_count": 6300,
        "rating_sum": 410,
        "rating_count": 91,
        "author": "HushClaw Team",
        "tags": "search, web, summary, research",
    },
    {
        "title": "Academic Paper Tracker",
        "short_desc": "Monitor arXiv and Semantic Scholar for new papers matching your keywords",
        "description": "Set your research keywords and the agent:\n\n• Scans arXiv, Semantic Scholar, and Google Scholar daily\n• Summarises each paper in 3–5 sentences\n• Ranks by citation count and recency\n• Exports BibTeX references on demand\n\nPerfect for staying current without information overload.",
        "category": "search",
        "platform": "all",
        "install_count": 1850,
        "rating_sum": 122,
        "rating_count": 27,
        "author": "HushClaw Team",
        "tags": "arxiv, research, papers, academic",
    },
    {
        "title": "Data Scraper",
        "short_desc": "Extract structured data from any website into CSV or JSON",
        "description": "Point the agent at a URL and describe what data you want:\n\n• Handles pagination automatically\n• Respects robots.txt and rate limits\n• Cleans and deduplicates output\n• Exports to CSV, JSON, or SQLite\n\nNo CSS selector knowledge required — the agent infers structure from context.",
        "category": "search",
        "platform": "all",
        "install_count": 2900,
        "rating_sum": 185,
        "rating_count": 41,
        "author": "HushClaw Team",
        "tags": "scrape, data, extract, csv",
    },

    # ── Data & Docs ───────────────────────────────────────────────────────────────
    {
        "title": "PDF Analyser",
        "short_desc": "Ask questions about any PDF — contracts, reports, research papers",
        "description": "Drop a PDF and start asking questions:\n\n• Extracts and indexes full text with local vector search\n• Answers questions with page-level citations\n• Summarises key sections on demand\n• Compares multiple PDFs side by side\n\nAll processing happens locally — your documents never leave the machine.",
        "category": "data-docs",
        "platform": "all",
        "install_count": 4700,
        "rating_sum": 305,
        "rating_count": 68,
        "author": "HushClaw Team",
        "tags": "pdf, document, analyse, rag",
    },
    {
        "title": "Excel / CSV Assistant",
        "short_desc": "Manipulate spreadsheets with natural language — no formulas needed",
        "description": "Describe the transformation you need:\n\n• Filter, sort, group, and pivot data\n• Generate charts and summary statistics\n• Merge multiple sheets or files\n• Write back results to a new Excel file\n\nSupports .xlsx, .csv, and .tsv formats.",
        "category": "data-docs",
        "platform": "all",
        "install_count": 3500,
        "rating_sum": 225,
        "rating_count": 50,
        "author": "HushClaw Team",
        "tags": "excel, csv, spreadsheet, data",
    },
    {
        "title": "SQLite Query Agent",
        "short_desc": "Query any SQLite database using plain English",
        "description": "Point the agent at a .db file:\n\n• Inspects schema automatically\n• Translates natural language to SQL\n• Explains query results in plain English\n• Exports query output to CSV\n\nSafe read-only mode available to prevent accidental writes.",
        "category": "data-docs",
        "platform": "all",
        "install_count": 1400,
        "rating_sum": 92,
        "rating_count": 20,
        "author": "HushClaw Team",
        "tags": "sql, sqlite, database, query",
    },

    # ── Automation ───────────────────────────────────────────────────────────────
    {
        "title": "Scheduled Task Runner",
        "short_desc": "Run any HushClaw skill on a cron schedule — no cron syntax needed",
        "description": "Say 'run every morning at 9am' and the agent sets it up:\n\n• Natural language schedule configuration\n• Runs skills in the background while you work\n• Logs execution history with timestamps\n• Sends a desktop notification on completion or failure\n\nPersists schedules across sessions via SQLite.",
        "category": "automation",
        "platform": "all",
        "install_count": 2600,
        "rating_sum": 168,
        "rating_count": 37,
        "author": "HushClaw Team",
        "tags": "schedule, cron, automation, recurring",
    },
    {
        "title": "Batch Processor",
        "short_desc": "Apply any skill to hundreds of files or URLs in one command",
        "description": "Feed a list of inputs and let the agent process them all:\n\n• Parallel execution with configurable concurrency\n• Progress bar and ETA\n• Retry failed items automatically\n• Collects all results into a single report\n\nWorks with files, URLs, or any line-delimited input.",
        "category": "automation",
        "platform": "all",
        "install_count": 1900,
        "rating_sum": 124,
        "rating_count": 28,
        "author": "HushClaw Team",
        "tags": "batch, bulk, parallel, processing",
    },
    {
        "title": "Site Monitor",
        "short_desc": "Watch any webpage for changes and alert you when something updates",
        "description": "Set a URL and the content you care about:\n\n• Checks on a configurable interval\n• Diffs the page content and highlights changes\n• Sends a desktop notification when a change is detected\n• Stores change history locally\n\nUseful for tracking job postings, product availability, or news pages.",
        "category": "automation",
        "platform": "all",
        "install_count": 3100,
        "rating_sum": 200,
        "rating_count": 45,
        "author": "HushClaw Team",
        "tags": "monitor, watch, alert, changes",
    },

    # ── Integrations ─────────────────────────────────────────────────────────────
    {
        "title": "Notion Sync",
        "short_desc": "Read and write Notion pages and databases from HushClaw",
        "description": "Connect your Notion workspace:\n\n• Query database entries with natural language filters\n• Create and update pages from agent output\n• Sync local markdown files to Notion\n• Build daily briefings from multiple databases\n\nRequires a Notion API key — stored locally in your config.",
        "category": "integrations",
        "platform": "all",
        "install_count": 2200,
        "rating_sum": 143,
        "rating_count": 32,
        "author": "HushClaw Team",
        "tags": "notion, productivity, sync, notes",
    },
    {
        "title": "GitHub Assistant",
        "short_desc": "Manage issues, PRs, and repos via natural language",
        "description": "Talk to your GitHub repos:\n\n• Create, list, and close issues\n• Summarise open PRs and their diffs\n• Search code across repos\n• Post comments and labels\n\nUses the GitHub REST API — requires a personal access token.",
        "category": "integrations",
        "platform": "all",
        "install_count": 1700,
        "rating_sum": 110,
        "rating_count": 24,
        "author": "HushClaw Team",
        "tags": "github, git, issues, pr, devtools",
    },
    {
        "title": "Cloud Storage Bridge",
        "short_desc": "Upload, download, and organise files across S3, R2, and OSS",
        "description": "Manage cloud object storage with plain English:\n\n• Upload files or entire directories\n• Generate presigned URLs\n• Sync local folders with a bucket\n• List and delete objects with pattern matching\n\nSupports AWS S3, Cloudflare R2, and Alibaba OSS.",
        "category": "integrations",
        "platform": "all",
        "install_count": 980,
        "rating_sum": 64,
        "rating_count": 14,
        "author": "HushClaw Team",
        "tags": "s3, r2, oss, cloud, storage",
    },

    # ── Creative ──────────────────────────────────────────────────────────────────
    {
        "title": "Long-form Writer",
        "short_desc": "Draft articles, reports, and docs with structured AI assistance",
        "description": "Provide a topic and outline — the agent does the writing:\n\n• Generates structured drafts section by section\n• Maintains consistent tone and style throughout\n• Suggests headings and transitions\n• Exports to Markdown or plain text\n\nBuilt-in token budget management ensures long documents stay coherent.",
        "category": "creative",
        "platform": "all",
        "install_count": 3800,
        "rating_sum": 245,
        "rating_count": 54,
        "author": "HushClaw Team",
        "tags": "writing, content, article, draft",
    },
    {
        "title": "Copy Polisher",
        "short_desc": "Improve tone, clarity, and grammar of any text in seconds",
        "description": "Paste your draft and choose a target style:\n\n• Formal / casual / technical / persuasive modes\n• Highlights weak sentences and suggests rewrites\n• Checks for consistency in terminology\n• Outputs a clean diff so you can accept changes selectively\n\nWorks great for emails, docs, READMEs, and marketing copy.",
        "category": "creative",
        "platform": "all",
        "install_count": 4500,
        "rating_sum": 292,
        "rating_count": 65,
        "author": "HushClaw Team",
        "tags": "editing, writing, polish, grammar",
    },
    {
        "title": "Image Prompt Engineer",
        "short_desc": "Turn a rough idea into an optimised prompt for Stable Diffusion or DALL·E",
        "description": "Describe what you have in mind — the agent refines it:\n\n• Expands vague ideas into detailed, stylistically rich prompts\n• Suggests negative prompts to avoid common artefacts\n• Offers multiple prompt variations to compare\n• Stores your prompt history locally\n\nCompatible with SD, SDXL, Flux, DALL·E 3, and Midjourney.",
        "category": "creative",
        "platform": "all",
        "install_count": 2700,
        "rating_sum": 175,
        "rating_count": 39,
        "author": "HushClaw Team",
        "tags": "image, stable-diffusion, prompt, dall-e",
    },

    # ── Agent Brain ───────────────────────────────────────────────────────────────
    {
        "title": "Persistent Memory Manager",
        "short_desc": "Search, review, and curate your agent's long-term memory store",
        "description": "HushClaw stores memories in SQLite FTS5. This skill gives you full control:\n\n• Full-text search across all stored memories\n• Tag and categorise memory entries\n• Merge duplicates and prune stale notes\n• Export memory store to JSON for backup\n\nMemories written here persist across all future sessions.",
        "category": "agent-brain",
        "platform": "all",
        "install_count": 2100,
        "rating_sum": 136,
        "rating_count": 30,
        "author": "HushClaw Team",
        "tags": "memory, persistence, rag, knowledge",
    },
    {
        "title": "Skill Manager",
        "short_desc": "Install, update, enable, or disable HushClaw skills from the UI",
        "description": "Manage your skill library without touching the filesystem:\n\n• Browse installed skills and their metadata\n• Install skills from the store with one click\n• Toggle skills on/off without deleting them\n• Check for updates and apply them\n\nSkill files are stored in ~/.config/hushclaw/tools/.",
        "category": "agent-brain",
        "platform": "all",
        "install_count": 1600,
        "rating_sum": 104,
        "rating_count": 23,
        "author": "HushClaw Team",
        "tags": "skills, plugins, tools, management",
    },
    {
        "title": "Self-reflection Loop",
        "short_desc": "Let the agent review its last session and suggest improvements",
        "description": "After each session, this skill:\n\n• Reviews the conversation history for repeated mistakes\n• Drafts new memory notes to avoid the same errors\n• Suggests prompt or config adjustments\n• Logs a structured reflection summary locally\n\nHelps the agent get smarter over time through structured introspection.",
        "category": "agent-brain",
        "platform": "all",
        "install_count": 890,
        "rating_sum": 58,
        "rating_count": 13,
        "author": "HushClaw Team",
        "tags": "reflection, self-improvement, memory, meta",
    },

    # ── Security ──────────────────────────────────────────────────────────────────
    {
        "title": "Credential Vault",
        "short_desc": "Store and retrieve API keys and passwords securely via the agent",
        "description": "Never paste secrets into a prompt again:\n\n• Encrypts credentials with AES-256 using a local master password\n• Injects secrets into tool calls at runtime — never stored in logs\n• Supports rotation reminders\n• Audit log of every credential access\n\nSecrets are stored in your OS native keychain where available.",
        "category": "security",
        "platform": "all",
        "install_count": 1300,
        "rating_sum": 85,
        "rating_count": 19,
        "author": "HushClaw Team",
        "tags": "secrets, credentials, security, vault",
    },
    {
        "title": "Permission Guard",
        "short_desc": "Define allow/deny rules for which tools and paths the agent can touch",
        "description": "Set fine-grained boundaries for agent actions:\n\n• Whitelist specific directories for file operations\n• Block network calls to sensitive domains\n• Require confirmation before destructive operations\n• Log all tool invocations with their arguments\n\nRules are defined in a simple TOML config and hot-reloaded.",
        "category": "security",
        "platform": "all",
        "install_count": 950,
        "rating_sum": 62,
        "rating_count": 14,
        "author": "HushClaw Team",
        "tags": "permissions, guardrails, safety, policy",
    },
    {
        "title": "Security Auditor",
        "short_desc": "Scan your codebase or config files for common security issues",
        "description": "Point the agent at a directory:\n\n• Detects hardcoded secrets (API keys, passwords, tokens)\n• Flags insecure patterns (eval, shell injection, open redirects)\n• Checks dependency versions against known CVEs\n• Generates a structured report with severity ratings\n\nRuns entirely locally — no code is sent to external services.",
        "category": "security",
        "platform": "all",
        "install_count": 1100,
        "rating_sum": 72,
        "rating_count": 16,
        "author": "HushClaw Team",
        "tags": "security, audit, cve, secrets, scan",
    },
]

base_date = datetime.utcnow()
for i, s in enumerate(skills_data):
    cat = cats[s["category"]]
    created = base_date - timedelta(days=random.randint(1, 180))
    skill = Skill(
        title=s["title"],
        short_desc=s["short_desc"],
        description=s["description"],
        category_id=cat.id,
        platform=s["platform"],
        install_count=s["install_count"],
        rating_sum=s["rating_sum"],
        rating_count=s["rating_count"],
        author=s["author"],
        tags=s["tags"],
        is_active=True,
        status="approved",
        created_at=created,
    )
    db.add(skill)

db.commit()
db.close()

print(f"✅ Seeding complete")
print(f"   Categories : {len(categories_data)}")
print(f"   Skills     : {len(skills_data)}")
print(f"\nRun : uvicorn app.main:app --reload --port 8000")
print(f"Open: http://localhost:8000")
