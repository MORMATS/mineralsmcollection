#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/isminerals/app}"
VENV_DIR="${VENV_DIR:-${APP_DIR}/.venv}"
PYTHON_BIN="${PYTHON_BIN:-python3}"
SERVICE_NAME="${SERVICE_NAME:-isminerals}"
APP_USER="${APP_USER:-isminerals}"

run_as_app() {
  sudo -u "$APP_USER" -H bash -lc "cd '$APP_DIR' && $*"
}

run_as_app "git pull --ff-only"

if [ ! -d "$VENV_DIR" ]; then
  run_as_app "'$PYTHON_BIN' -m venv '$VENV_DIR'"
fi

run_as_app "'$VENV_DIR/bin/python' -m pip install --upgrade pip"
run_as_app "'$VENV_DIR/bin/python' -m pip install -r requirements.txt"
run_as_app "'$VENV_DIR/bin/python' -m alembic upgrade head"

sudo systemctl restart "$SERVICE_NAME"
sleep 3
curl --fail --silent --show-error http://127.0.0.1:8501 >/dev/null
sudo systemctl --no-pager --full status "$SERVICE_NAME"
