# hushclaw-web

The official website and skill directory for [HushClaw](https://github.com/CNTWDev/hushclaw). The home page explains the product and how to install it, `/skills` lets people browse, submit and rate community skills, `/docs` hosts articles, and `/admin` is the management panel.

> HushClaw is a personal AI assistant that gets to know you deeply. It remembers your preferences, background and way of working, and it reflects on your feedback and corrections to keep improving. It runs on your own computer, so your memory and data stay yours.

Stack: FastAPI + Uvicorn · SQLite + SQLAlchemy + Alembic · Jinja2 · Python 3.10+

---

## One-line server install

Works on Linux servers with systemd (Ubuntu, Debian, CentOS, Rocky, …). Run as root or with sudo:

```bash
curl -fsSL https://raw.githubusercontent.com/CNTWDev/hushclaw-web/master/install.sh | sudo bash
```

The script:

1. Installs missing system packages (git, python3, python3-venv)
2. Creates the `hushclaw-web` system user and clones the code into `/opt/hushclaw-web`
3. Writes the runtime config `/etc/hushclaw-web/hushclaw-web.env`, with a random `SECRET_KEY` and admin password
4. Creates a virtualenv, installs Python dependencies and runs the database migrations (`alembic upgrade head`)
5. Registers and starts the systemd service `hushclaw-web`, then waits for a health check to pass
6. Installs the `hushclaw-web` management command

At the end it prints the admin password once. You can look it up again in the env file later. By default the service listens on `127.0.0.1:8000` only, so put a reverse proxy in front of it (see below).

You can override the defaults with environment variables. They only apply on the first install. After that, the values are stored in `/etc/hushclaw-web/deploy.conf`.

| Variable | Default | Meaning |
| --- | --- | --- |
| `HUSHCLAW_WEB_PORT` | `8000` | Service port |
| `HUSHCLAW_WEB_HOST` | `127.0.0.1` | Bind address. Use `0.0.0.0` if you don't run a reverse proxy |
| `HUSHCLAW_WEB_BRANCH` | `master` | Branch to track |
| `HUSHCLAW_WEB_DIR` | `/opt/hushclaw-web` | Code directory |
| `HUSHCLAW_WEB_DATA` | `/var/lib/hushclaw-web` | Data directory (database, backups) |
| `HUSHCLAW_WEB_IMPORT_DB` | empty | Existing SQLite database to import on first install |
| `HUSHCLAW_WEB_STRICT_PORT` | `0` | When `1`, fail if the port is taken instead of moving to another port |

Example:

```bash
curl -fsSL https://raw.githubusercontent.com/CNTWDev/hushclaw-web/master/install.sh \
  | sudo HUSHCLAW_WEB_PORT=9000 bash
```

## Updating to the latest code

```bash
sudo hushclaw-web update
```

An update runs these steps in order:

1. Fetch the latest code from GitHub
2. Back up the database and uploaded files
3. Switch to the new code
4. Reinstall dependencies if `requirements.txt` changed
5. Run the database migrations
6. Restart the service and run the health check

- If the site is already up to date, the command does nothing. Use `sudo hushclaw-web update --force` to redeploy anyway.
- **A failed health check rolls back automatically.** The code goes back to the previous version, the database is restored from the backup taken just before the update, and the old version is restarted.
- On a machine without the `hushclaw-web` command, you can update with a single line:

  ```bash
  curl -fsSL https://raw.githubusercontent.com/CNTWDev/hushclaw-web/master/install.sh | sudo bash -s -- update
  ```

- To update automatically, add a cron job. This one runs every day at 04:00:

  ```bash
  echo '0 4 * * * root /usr/local/bin/hushclaw-web update >> /var/log/hushclaw-web-update.log 2>&1' | sudo tee /etc/cron.d/hushclaw-web
  ```

## Commands

| Command | What it does |
| --- | --- |
| `sudo hushclaw-web update [--force]` | Pull the latest code and restart |
| `hushclaw-web status` | Deployed version, port and service state |
| `hushclaw-web logs [-f]` | Service logs |
| `sudo hushclaw-web restart` | Restart the service. Port conflicts are handled the same way as on install |
| `sudo hushclaw-web backup` | Back up the database and uploaded files |
| `sudo hushclaw-web rollback [--with-db]` | Go back to the previously deployed version. `--with-db` also restores the database from before that update |
| `sudo hushclaw-web uninstall [--purge]` | Remove the service. Code, data and config are kept unless you pass `--purge` |

## When the port is already in use

On install, update and restart, the script checks the port first. It handles two cases differently:

1. **The port is held by an old hushclaw-web process.** This covers an earlier manual `./start.sh` or `uvicorn` run that was never stopped. The script recognises the process as this project's, stops it (including `--reload` workers) and starts the service on the same port.
2. **The port is held by another program.** The script prints that program's PID and command line and moves to the next free port, for example 8001. It saves the new port to `deploy.conf` and reminds you to update the port in your reverse proxy. If you want a fixed port and would rather fail than move, set `HUSHCLAW_WEB_STRICT_PORT=1` when installing.

To change the port by hand, edit `PORT` in `/etc/hushclaw-web/deploy.conf` and run `sudo hushclaw-web restart`.

## Reverse proxy (nginx example)

```nginx
server {
    listen 80;
    server_name hushclaw.example.com;
    client_max_body_size 20m;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

The service runs with `--proxy-headers`, so features that count by IP, such as ratings, see the real visitor's address. For HTTPS, use certbot or switch to Caddy.

## Files and configuration

| Path | Contents |
| --- | --- |
| `/opt/hushclaw-web` | Code (a git checkout) and the `.venv` virtualenv |
| `/opt/hushclaw-web/static/uploads` | Uploaded files. Git updates don't touch them, and they are included in backups |
| `/var/lib/hushclaw-web/hushclaw-web.db` | Database |
| `/var/lib/hushclaw-web/backups/` | Backups taken before each update. The 10 most recent are kept |
| `/var/lib/hushclaw-web/deploy-history` | Time and commit of each successful deploy |
| `/etc/hushclaw-web/hushclaw-web.env` | Runtime config: admin password, `SECRET_KEY`, SMTP and so on. Run `sudo hushclaw-web restart` after editing |
| `/etc/hushclaw-web/deploy.conf` | Deploy config: repository, branch, directories, port |

### Migrating from a manual deployment

If the server already runs the site by hand, for example with `hushclas.db` in the repo directory, import the old database on first install:

```bash
curl -fsSL https://raw.githubusercontent.com/CNTWDev/hushclaw-web/master/install.sh \
  | sudo HUSHCLAW_WEB_IMPORT_DB=/path/to/old/hushclas.db bash
```

If the old process is still holding the same port, the script recognises it and stops it. Without this variable, a fresh install starts from the `hushclas.db` shipped in the repo, which contains the seed skills and categories. Copy any uploaded files to `/opt/hushclaw-web/static/uploads/` by hand.

## Upgrading the installer

- **The installer is upgraded together with the code.** The `hushclaw-web` command just runs the `install.sh` inside the code directory. After `update` pulls the new code, the **new** version of the script runs the remaining steps: dependencies, migrations, the systemd unit and the restart. So once a change to `install.sh` is merged into `master`, the server uses it on its next `update`. Nothing else is needed.
- The systemd unit and the `hushclaw-web` command are rewritten from the current script on every deploy. `deploy.conf` and `hushclaw-web.env` are only created when missing, so existing configuration is never overwritten.
- When you change the script:
  1. Bump `SCRIPT_VERSION` at the top (`hushclaw-web version` prints it).
  2. Keep it compatible with existing `deploy.conf` files: any new setting needs a default.
  3. Run a fresh install and an `update --force` on a test machine before merging.
- If a broken script change stops `update` from finishing, run `sudo hushclaw-web rollback` on the server to go back to the previous version. Alternatively, run `update` with the fixed script straight from GitHub using the one-line command above.

---

## Local development

```bash
./start.sh
```

This creates a virtualenv, installs dependencies and starts the server at `http://localhost:8000` with `--reload`. To do it by hand:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

Copy `.env.example` to `.env` to change local settings. `python seed_data.py` **deletes** all skills, categories and ratings before writing the seed data, so only run it locally.

### Project structure

```
hushclaw-web/
├── install.sh          # one-line server installer / updater
├── app/
│   ├── main.py         # app entry point
│   ├── database.py     # database connection
│   ├── models.py       # SQLAlchemy models
│   ├── routes/         # home / skills / docs / auth / account / api / admin
│   └── templates/      # Jinja2 templates
├── alembic/            # database migrations
├── static/             # CSS, JS, images, uploads
├── requirements.txt
├── seed_data.py        # seed data (wipes existing data)
└── start.sh            # local dev startup script
```

### Data models

- **Category**: skill categories
- **Skill**: title, description, platform, tags, ratings
- **Rating**: per-IP ratings (one vote per person per skill)
- **User / EmailOTP / UserToken**: email one-time-code sign-in
- **AppVersion**: client version management
- **Doc**: articles
