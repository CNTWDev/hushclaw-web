#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# hushclaw-web — one-line server installer & updater (Linux + systemd)
#
# Install (fresh server, run as root or via sudo):
#   curl -fsSL https://raw.githubusercontent.com/CNTWDev/hushclaw-web/master/install.sh | sudo bash
#
# After install, a `hushclaw-web` command is available:
#   hushclaw-web update            # pull latest code from GitHub, migrate, restart
#   hushclaw-web status            # service status + deployed commit
#   hushclaw-web logs [-f]         # service logs (journalctl)
#   hushclaw-web restart           # restart the service
#   hushclaw-web backup            # snapshot database + uploads
#   hushclaw-web rollback [--with-db]  # go back to the previously deployed commit
#   hushclaw-web uninstall [--purge]   # remove service (keeps data unless --purge)
#
# The same commands work without the CLI:
#   curl -fsSL https://raw.githubusercontent.com/CNTWDev/hushclaw-web/master/install.sh | sudo bash -s -- update
#
# Environment overrides (first install only; afterwards stored in
# /etc/hushclaw-web/deploy.conf):
#   HUSHCLAW_WEB_REPO    git URL            (default: https://github.com/CNTWDev/hushclaw-web.git)
#   HUSHCLAW_WEB_BRANCH  branch to track    (default: master)
#   HUSHCLAW_WEB_DIR     code directory     (default: /opt/hushclaw-web)
#   HUSHCLAW_WEB_DATA    data directory     (default: /var/lib/hushclaw-web)
#   HUSHCLAW_WEB_HOST    bind address       (default: 127.0.0.1, put nginx/caddy in front)
#   HUSHCLAW_WEB_PORT    port               (default: 8000)
#   HUSHCLAW_WEB_USER    service user       (default: hushclaw-web)
#   HUSHCLAW_WEB_IMPORT_DB  existing SQLite file to import on first install
# ─────────────────────────────────────────────────────────────────────────────

# Everything lives inside main() so `curl | bash` parses the whole file before
# running anything.
main() {
set -euo pipefail

SCRIPT_VERSION="1.0.0"
SERVICE="hushclaw-web"
CONF_DIR="/etc/hushclaw-web"
DEPLOY_CONF="$CONF_DIR/deploy.conf"
ENV_FILE="$CONF_DIR/hushclaw-web.env"
UNIT_FILE="/etc/systemd/system/$SERVICE.service"
CLI_PATH="/usr/local/bin/hushclaw-web"
KEEP_BACKUPS=10

# ── Output helpers ───────────────────────────────────────────────────────────
if [[ -t 1 ]]; then
  C_B=$'\033[1m'; C_G=$'\033[32m'; C_Y=$'\033[33m'; C_R=$'\033[31m'; C_0=$'\033[0m'
else
  C_B=""; C_G=""; C_Y=""; C_R=""; C_0=""
fi
info() { echo "${C_B}==>${C_0} $*"; }
ok()   { echo "${C_G}✓${C_0} $*"; }
warn() { echo "${C_Y}!${C_0} $*" >&2; }
die()  { echo "${C_R}✗${C_0} $*" >&2; exit 1; }

# ── Settings ─────────────────────────────────────────────────────────────────
load_settings() {
  # Stored settings win over defaults; env vars win only before first install.
  if [[ -f "$DEPLOY_CONF" ]]; then
    # shellcheck disable=SC1090
    source "$DEPLOY_CONF"
  fi
  REPO="${REPO:-${HUSHCLAW_WEB_REPO:-https://github.com/CNTWDev/hushclaw-web.git}}"
  BRANCH="${BRANCH:-${HUSHCLAW_WEB_BRANCH:-master}}"
  APP_DIR="${APP_DIR:-${HUSHCLAW_WEB_DIR:-/opt/hushclaw-web}}"
  DATA_DIR="${DATA_DIR:-${HUSHCLAW_WEB_DATA:-/var/lib/hushclaw-web}}"
  HOST="${HOST:-${HUSHCLAW_WEB_HOST:-127.0.0.1}}"
  PORT="${PORT:-${HUSHCLAW_WEB_PORT:-8000}}"
  RUN_USER="${RUN_USER:-${HUSHCLAW_WEB_USER:-hushclaw-web}}"
  VENV="$APP_DIR/.venv"
  DB_FILE="$DATA_DIR/hushclaw-web.db"
  BACKUP_DIR="$DATA_DIR/backups"
  HISTORY_FILE="$DATA_DIR/deploy-history"
}

save_settings() {
  mkdir -p "$CONF_DIR"
  cat > "$DEPLOY_CONF" <<EOF
# hushclaw-web deployment settings (written by install.sh, safe to edit)
REPO="$REPO"
BRANCH="$BRANCH"
APP_DIR="$APP_DIR"
DATA_DIR="$DATA_DIR"
HOST="$HOST"
PORT="$PORT"
RUN_USER="$RUN_USER"
EOF
  chmod 644 "$DEPLOY_CONF"
}

# ── Preconditions ────────────────────────────────────────────────────────────
require_root() {
  [[ $EUID -eq 0 ]] || die "Please run as root, e.g.  curl -fsSL <url> | sudo bash"
}

require_systemd() {
  command -v systemctl >/dev/null 2>&1 || die "systemd is required (systemctl not found)."
}

install_packages() {
  local need=()
  command -v git >/dev/null 2>&1 || need+=(git)
  command -v python3 >/dev/null 2>&1 || need+=(python3)
  if command -v python3 >/dev/null 2>&1 && ! python3 -c 'import ensurepip, venv' >/dev/null 2>&1; then
    need+=(venv)
  fi
  [[ ${#need[@]} -eq 0 ]] && return 0

  info "Installing system packages: ${need[*]}"
  if command -v apt-get >/dev/null 2>&1; then
    local pkgs=(git python3 python3-venv python3-pip)
    # Debian/Ubuntu split venv per minor version (python3.12-venv, ...).
    local pyver
    pyver="$(python3 -c 'import sys; print(f"{sys.version_info[0]}.{sys.version_info[1]}")' 2>/dev/null || true)"
    [[ -n "$pyver" ]] && pkgs+=("python${pyver}-venv")
    DEBIAN_FRONTEND=noninteractive apt-get update -y </dev/null
    DEBIAN_FRONTEND=noninteractive apt-get install -y "${pkgs[@]}" </dev/null \
      || DEBIAN_FRONTEND=noninteractive apt-get install -y git python3 python3-venv python3-pip </dev/null
  elif command -v dnf >/dev/null 2>&1; then
    dnf install -y git python3 python3-pip </dev/null
  elif command -v yum >/dev/null 2>&1; then
    yum install -y git python3 python3-pip </dev/null
  else
    die "Unsupported package manager. Install git and python3 (with venv) manually, then re-run."
  fi
}

check_python() {
  python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)' \
    || die "Python 3.10+ is required (found $(python3 --version 2>&1))."
}

ensure_user() {
  if ! id "$RUN_USER" >/dev/null 2>&1; then
    info "Creating system user $RUN_USER"
    useradd --system --home-dir "$DATA_DIR" --shell /usr/sbin/nologin "$RUN_USER"
  fi
}

# ── Code ─────────────────────────────────────────────────────────────────────
git_app() { git -C "$APP_DIR" "$@"; }

current_commit() { git_app rev-parse --short HEAD 2>/dev/null || echo "none"; }

fetch_code() {
  if [[ -d "$APP_DIR/.git" ]]; then
    git_app remote set-url origin "$REPO"
    git_app fetch --quiet origin "$BRANCH"
  else
    [[ -e "$APP_DIR" && -n "$(ls -A "$APP_DIR" 2>/dev/null)" ]] \
      && die "$APP_DIR exists and is not a git checkout. Move it away or set HUSHCLAW_WEB_DIR."
    info "Cloning $REPO ($BRANCH) into $APP_DIR"
    mkdir -p "$(dirname "$APP_DIR")"
    git clone --quiet --branch "$BRANCH" "$REPO" "$APP_DIR"
  fi
}

checkout_commit() {
  # Tracked files are replaced; untracked files (.venv, static/uploads/*) stay.
  git_app checkout --quiet -B "$BRANCH" "$1"
  git_app reset --quiet --hard "$1"
}

# ── Data ─────────────────────────────────────────────────────────────────────
write_env_file() {
  mkdir -p "$CONF_DIR"
  if [[ ! -f "$ENV_FILE" ]]; then
    local secret admin_pw
    secret="$(python3 -c 'import secrets; print(secrets.token_urlsafe(48))')"
    admin_pw="$(python3 -c 'import secrets; print(secrets.token_urlsafe(12))')"
    cat > "$ENV_FILE" <<EOF
# hushclaw-web runtime configuration. Edit, then: hushclaw-web restart
ADMIN_PASSWORD=$admin_pw
SECRET_KEY=$secret
DATABASE_URL=sqlite:///$DB_FILE

# Leave SMTP_HOST empty to print OTP codes to the service log
SMTP_HOST=
SMTP_PORT=587
SMTP_USER=
SMTP_PASSWORD=
SMTP_FROM=noreply@hushclaw.com

OTP_EXPIRE_MINUTES=10
TOKEN_EXPIRE_DAYS=30
MAX_UPLOAD_SIZE_MB=10
EOF
    NEW_ADMIN_PASSWORD="$admin_pw"
  fi
  chown root:"$RUN_USER" "$ENV_FILE"
  chmod 640 "$ENV_FILE"
}

prepare_data_dir() {
  mkdir -p "$DATA_DIR" "$BACKUP_DIR" "$APP_DIR/static/uploads"
  if [[ ! -f "$DB_FILE" ]]; then
    local seed="${HUSHCLAW_WEB_IMPORT_DB:-}"
    if [[ -n "$seed" ]]; then
      [[ -f "$seed" ]] || die "HUSHCLAW_WEB_IMPORT_DB=$seed not found."
      info "Importing database from $seed"
    elif [[ -f "$APP_DIR/hushclas.db" ]]; then
      seed="$APP_DIR/hushclas.db"
      info "Seeding database from the repository snapshot"
    fi
    [[ -n "$seed" ]] && sqlite_copy "$seed" "$DB_FILE"
  fi
  chown -R "$RUN_USER":"$RUN_USER" "$DATA_DIR" "$APP_DIR/static/uploads"
  chmod 750 "$DATA_DIR"
}

# Consistent copy of a live SQLite file (safe while the service is running).
sqlite_copy() {
  python3 - "$1" "$2" <<'PY'
import sqlite3, sys
src = sqlite3.connect(f"file:{sys.argv[1]}?mode=ro", uri=True)
dst = sqlite3.connect(sys.argv[2])
src.backup(dst)
dst.close(); src.close()
PY
}

backup_data() {
  local label="${1:-manual}" stamp dest
  stamp="$(date +%Y%m%d-%H%M%S)"
  dest="$BACKUP_DIR/$stamp-$(current_commit)-$label"
  mkdir -p "$dest"
  [[ -f "$DB_FILE" ]] && sqlite_copy "$DB_FILE" "$dest/hushclaw-web.db"
  if [[ -d "$APP_DIR/static/uploads" ]]; then
    tar -czf "$dest/uploads.tar.gz" -C "$APP_DIR/static" uploads
  fi
  chown -R "$RUN_USER":"$RUN_USER" "$dest"
  # Keep only the newest $KEEP_BACKUPS snapshots.
  { ls -1dt "$BACKUP_DIR"/*/ 2>/dev/null || true; } | tail -n +$((KEEP_BACKUPS + 1)) | xargs -r rm -rf
  LAST_BACKUP="$dest"
  echo "$dest"
}

restore_db() {
  local snap="$1"
  [[ -f "$snap/hushclaw-web.db" ]] || { warn "No database in $snap, skipping restore."; return 0; }
  cp "$snap/hushclaw-web.db" "$DB_FILE"
  chown "$RUN_USER":"$RUN_USER" "$DB_FILE"
}

# ── Python env + schema ──────────────────────────────────────────────────────
install_deps() {
  if [[ ! -x "$VENV/bin/python" ]]; then
    info "Creating virtualenv"
    python3 -m venv "$VENV"
  fi
  local stamp="$VENV/.requirements.sha256" want
  want="$(sha256sum "$APP_DIR/requirements.txt" | cut -d' ' -f1)"
  if [[ "$(cat "$stamp" 2>/dev/null)" != "$want" ]]; then
    info "Installing Python dependencies"
    "$VENV/bin/pip" install --quiet --upgrade pip
    "$VENV/bin/pip" install --quiet -r "$APP_DIR/requirements.txt"
    echo "$want" > "$stamp"
  fi
}

# Run a command inside the app dir with the runtime env loaded, as the service user.
run_app() {
  # shellcheck disable=SC1090
  ( cd "$APP_DIR" && set -a && source "$ENV_FILE" && set +a \
    && runuser -u "$RUN_USER" -- env DATABASE_URL="$DATABASE_URL" "$@" )
}

migrate_db() {
  info "Applying database migrations"
  # Databases created by Base.metadata.create_all() have tables but no
  # alembic_version row; stamp them so `upgrade head` does not recreate tables.
  local state
  state="$(python3 - "$DB_FILE" <<'PY'
import os, sqlite3, sys
p = sys.argv[1]
if not os.path.exists(p):
    print("empty"); sys.exit()
names = {r[0] for r in sqlite3.connect(p).execute("select name from sqlite_master where type='table'")}
print("versioned" if "alembic_version" in names else ("legacy" if names else "empty"))
PY
)"
  if [[ "$state" == "legacy" ]]; then
    warn "Database has no Alembic version; stamping it at head."
    run_app "$VENV/bin/alembic" stamp head
  fi
  run_app "$VENV/bin/alembic" upgrade head
}

# ── Port handling ────────────────────────────────────────────────────────────
# PIDs of processes holding a LISTEN socket on a TCP port. Reads /proc
# directly so it works without ss/lsof/fuser.
port_pids() {
  python3 - "$1" <<'PY'
import os, sys
port = int(sys.argv[1])
inodes = set()
for table in ("/proc/net/tcp", "/proc/net/tcp6"):
    try:
        lines = open(table).read().splitlines()[1:]
    except OSError:
        continue
    for line in lines:
        f = line.split()
        if f[3] == "0A" and int(f[1].rsplit(":", 1)[1], 16) == port:
            inodes.add(f[9])
pids = set()
for pid in filter(str.isdigit, os.listdir("/proc")):
    try:
        for fd in os.listdir(f"/proc/{pid}/fd"):
            link = os.readlink(f"/proc/{pid}/fd/{fd}")
            if link.startswith("socket:[") and link[8:-1] in inodes:
                pids.add(int(pid))
    except OSError:
        continue
print(" ".join(map(str, sorted(pids))))
PY
}

port_bindable() {
  python3 - "$HOST" "$1" <<'PY'
import socket, sys
s = socket.socket(socket.AF_INET6 if ":" in sys.argv[1] else socket.AF_INET)
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
try:
    s.bind((sys.argv[1], int(sys.argv[2])))
except OSError:
    sys.exit(1)
finally:
    s.close()
PY
}

port_free() { [[ -z "$(port_pids "$1")" ]] && port_bindable "$1"; }

proc_desc() { tr '\0' ' ' < "/proc/$1/cmdline" 2>/dev/null | cut -c1-120; }

# A process is "ours" when it runs from a hushclaw-web checkout: the systemd
# service, an older manual `./start.sh`/uvicorn run, or its --reload worker.
is_own_process() {
  local pid="$1" cwd cmd
  cwd="$(readlink "/proc/$pid/cwd" 2>/dev/null)" || return 1
  cwd="${cwd% (deleted)}"   # checkout was removed/re-cloned under a live process
  cmd="$(proc_desc "$pid")"
  [[ "$cmd" == *python* || "$cmd" == *uvicorn* ]] || return 1
  [[ "$cwd" == "$APP_DIR" || "$cmd" == *"$APP_DIR/"* ]] && return 0
  grep -q 'FastAPI(title="Hushclaw"' "$cwd/app/main.py" 2>/dev/null
}

stop_pids() {
  local pid _
  for pid in "$@"; do kill -TERM "$pid" 2>/dev/null || true; done
  for _ in $(seq 1 10); do
    local alive=0
    for pid in "$@"; do kill -0 "$pid" 2>/dev/null && alive=1; done
    [[ $alive -eq 0 ]] && return 0
    sleep 1
  done
  for pid in "$@"; do kill -KILL "$pid" 2>/dev/null || true; done
  sleep 1
}

# Make sure $PORT can be used by the service:
#   - held by an old hushclaw-web process (ours) → stop it, reuse the port
#   - held by some other program              → pick the next free port
ensure_port() {
  local pids own=() foreign=() pid
  pids="$(port_pids "$PORT")"
  for pid in $pids; do
    if is_own_process "$pid"; then own+=("$pid"); else foreign+=("$pid"); fi
  done
  if [[ ${#own[@]} -gt 0 ]]; then
    warn "Port $PORT is held by an old hushclaw-web process; stopping it:"
    for pid in "${own[@]}"; do echo "    pid $pid  $(proc_desc "$pid")"; done
    stop_pids "${own[@]}"
  fi
  if [[ ${#foreign[@]} -eq 0 ]] && port_free "$PORT"; then
    return 0
  fi
  if [[ ${#foreign[@]} -gt 0 ]]; then
    warn "Port $PORT is used by another program:"
    for pid in "${foreign[@]}"; do echo "    pid $pid  $(proc_desc "$pid")"; done
  else
    warn "Port $PORT cannot be bound (in use or not permitted)."
  fi
  [[ "${HUSHCLAW_WEB_STRICT_PORT:-0}" == "1" ]] \
    && die "HUSHCLAW_WEB_STRICT_PORT=1: free port $PORT or set HUSHCLAW_WEB_PORT and re-run."
  local candidate old="$PORT"
  for candidate in $(seq $((PORT + 1)) $((PORT + 200))); do
    if port_free "$candidate"; then
      PORT="$candidate"
      save_settings
      warn "Using port $PORT instead of $old (saved to $DEPLOY_CONF)."
      warn "If nginx/caddy proxies to 127.0.0.1:$old, point it at 127.0.0.1:$PORT."
      PORT_CHANGED_FROM="$old"
      return 0
    fi
  done
  die "No free port found between $((old + 1)) and $((old + 200))."
}

# Stop the service, clear the port, (re)write the unit and start again.
start_service() {
  systemctl stop "$SERVICE" 2>/dev/null || true
  ensure_port
  write_unit
  systemctl start "$SERVICE"
}

# ── Service ──────────────────────────────────────────────────────────────────
write_unit() {
  cat > "$UNIT_FILE" <<EOF
[Unit]
Description=HushClaw website (hushclaw-web)
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=$RUN_USER
Group=$RUN_USER
WorkingDirectory=$APP_DIR
EnvironmentFile=$ENV_FILE
ExecStart=$VENV/bin/uvicorn app.main:app --host $HOST --port $PORT --proxy-headers --forwarded-allow-ips 127.0.0.1
Restart=always
RestartSec=3
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
EOF
  systemctl daemon-reload
  systemctl enable --quiet "$SERVICE"
}

write_cli() {
  cat > "$CLI_PATH" <<EOF
#!/usr/bin/env bash
# hushclaw-web CLI — delegates to the installer inside the checkout, so the
# script is upgraded automatically together with the code.
exec bash "$APP_DIR/install.sh" "\$@"
EOF
  chmod 755 "$CLI_PATH"
}

health_check() {
  local url="http://127.0.0.1:$PORT/"
  for _ in $(seq 1 30); do
    if python3 -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('$url', timeout=3).status < 500 else 1)" >/dev/null 2>&1; then
      return 0
    fi
    sleep 1
  done
  return 1
}

record_deploy() {
  echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) $(git_app rev-parse HEAD)" >> "$HISTORY_FILE"
  chown "$RUN_USER":"$RUN_USER" "$HISTORY_FILE"
}

previous_deploy() {
  # Most recent recorded deployment that is not the current commit.
  [[ -f "$HISTORY_FILE" ]] || return 0
  tac "$HISTORY_FILE" | awk '{print $2}' | { grep -vx "$(git_app rev-parse HEAD)" || true; } | head -n 1
}

# ── Commands ─────────────────────────────────────────────────────────────────
cmd_install() {
  require_root; require_systemd
  load_settings
  if [[ -f "$UNIT_FILE" && -d "$APP_DIR/.git" ]]; then
    info "hushclaw-web is already installed; running update instead."
    cmd_update; return
  fi
  install_packages; check_python
  ensure_user
  fetch_code
  checkout_commit "origin/$BRANCH"
  save_settings
  # Hand off to the freshly cloned script so install logic matches the code.
  exec bash "$APP_DIR/install.sh" __finish install ""
}

cmd_update() {
  require_root; require_systemd
  load_settings
  [[ -d "$APP_DIR/.git" ]] || die "Not installed yet. Run the install command first."
  local before after
  before="$(git_app rev-parse HEAD)"
  info "Fetching latest code ($BRANCH)"
  fetch_code
  after="$(git_app rev-parse "origin/$BRANCH")"
  if [[ "$before" == "$after" && "${FORCE:-0}" != "1" ]]; then
    ok "Already up to date ($(current_commit)). Use 'hushclaw-web update --force' to redeploy."
    return 0
  fi
  info "Backing up data before update"
  backup_data "pre-update" >/dev/null
  info "Updating $(git_app rev-parse --short "$before") → $(git_app rev-parse --short "$after")"
  git_app log --oneline "$before..$after" 2>/dev/null | head -20 | sed 's/^/    /' || true
  checkout_commit "$after"
  # Hand off to the *new* version of this script for the rest of the update,
  # so fixes to the installer ship with the code.
  exec bash "$APP_DIR/install.sh" __finish update "$before" "$LAST_BACKUP"
}

# Second phase of install/update, always run by the freshly checked-out script.
cmd_finish() {
  local mode="$1" before="${2:-}" snapshot="${3:-}"
  require_root
  load_settings
  save_settings
  ensure_user
  write_env_file
  prepare_data_dir
  if ! { install_deps && migrate_db; }; then
    [[ "$mode" == "update" ]] && rollback_to "$before" "$snapshot"
    die "Deployment failed during dependency install or migration."
  fi
  write_cli
  info "Restarting service"
  start_service
  if ! health_check; then
    warn "Service did not become healthy on port $PORT."
    journalctl -u "$SERVICE" -n 30 --no-pager || true
    [[ "$mode" == "update" ]] && rollback_to "$before" "$snapshot"
    die "Deployment failed. See: journalctl -u $SERVICE -e"
  fi
  record_deploy
  ok "hushclaw-web $(current_commit) is running on http://$HOST:$PORT"
  [[ -n "${PORT_CHANGED_FROM:-}" ]] && warn "Port changed from $PORT_CHANGED_FROM to $PORT — update your reverse proxy."
  if [[ -n "${NEW_ADMIN_PASSWORD:-}" ]]; then
    echo
    echo "  Admin panel:     /admin"
    echo "  Admin password:  ${C_B}$NEW_ADMIN_PASSWORD${C_0}   (stored in $ENV_FILE)"
    echo "  Update later:    hushclaw-web update"
  fi
}

rollback_to() {
  local commit="$1" snapshot="${2:-}"
  [[ -n "$commit" ]] || return 0
  warn "Rolling back to $(git_app rev-parse --short "$commit")"
  checkout_commit "$commit"
  [[ -n "$snapshot" ]] && restore_db "$snapshot"
  install_deps || true
  start_service || true
  if health_check; then ok "Rolled back; previous version is serving again."; else warn "Rollback did not come up healthy either."; fi
}

cmd_rollback() {
  require_root; load_settings
  local target snap="" with_db=0
  [[ "${1:-}" == "--with-db" ]] && with_db=1
  target="$(previous_deploy)"
  [[ -n "$target" && "$target" != "$(git_app rev-parse HEAD)" ]] || die "No earlier deployment recorded."
  if [[ $with_db -eq 1 ]]; then
    # The snapshot taken right before we updated away from $target holds
    # the database as that version last saw it.
    local short; short="$(git_app rev-parse --short "$target")"
    snap="$({ ls -1dt "$BACKUP_DIR"/*-"$short"-pre-update/ 2>/dev/null || true; } | head -n 1)"
    snap="${snap%/}"
    [[ -n "$snap" ]] || die "No pre-update backup found for $short."
    info "Will restore database from $snap"
  fi
  backup_data "pre-rollback" >/dev/null
  rollback_to "$target" "$snap"
  record_deploy
}

cmd_restart() {
  require_root; require_systemd; load_settings
  start_service
  health_check || die "Service did not become healthy. See: journalctl -u $SERVICE -e"
  ok "Restarted on http://$HOST:$PORT"
}

cmd_status() {
  load_settings
  echo "Version:  $(current_commit) on $BRANCH  ($APP_DIR)"
  echo "Data:     $DATA_DIR"
  echo "Listen:   http://$HOST:$PORT"
  echo "Script:   $SCRIPT_VERSION"
  systemctl --no-pager status "$SERVICE" | head -n 5 || true
}

cmd_uninstall() {
  require_root; load_settings
  systemctl disable --now "$SERVICE" 2>/dev/null || true
  rm -f "$UNIT_FILE" "$CLI_PATH"
  systemctl daemon-reload
  if [[ "${1:-}" == "--purge" ]]; then
    rm -rf "$APP_DIR" "$DATA_DIR" "$CONF_DIR"
    ok "Removed service, code, data and config."
  else
    ok "Removed service. Code ($APP_DIR), data ($DATA_DIR) and config ($CONF_DIR) were kept."
  fi
}

usage() {
  cat <<EOF
hushclaw-web $SCRIPT_VERSION — server installer & updater

Usage: hushclaw-web <command>
  install                 install (or update, if already installed)
  update [--force]        pull latest code from GitHub, migrate, restart
  status                  deployed commit and service state
  logs [-f]               service logs
  restart                 restart the service
  backup                  snapshot database + uploads into $DATA_DIR/backups
  rollback [--with-db]    return to the previously deployed commit
  uninstall [--purge]     remove the service (keeps data unless --purge)
  version                 print the script version
EOF
}

local cmd="${1:-install}"; shift || true
case "$cmd" in
  install)   cmd_install ;;
  update)    [[ "${1:-}" == "--force" ]] && FORCE=1; cmd_update ;;
  __finish)  cmd_finish "$@" ;;
  status)    cmd_status ;;
  logs)      journalctl -u "$SERVICE" --no-pager -n 200 "$@" ;;
  restart)   cmd_restart ;;
  backup)    require_root; load_settings; info "Backup written to $(backup_data manual)" ;;
  rollback)  cmd_rollback "$@" ;;
  uninstall) cmd_uninstall "$@" ;;
  version)   echo "$SCRIPT_VERSION" ;;
  -h|--help|help) load_settings; usage ;;
  *) die "Unknown command: $cmd (try --help)" ;;
esac
}

# Keep on one line: bash must not read past this point after the checkout changes.
main "$@"; exit $?
