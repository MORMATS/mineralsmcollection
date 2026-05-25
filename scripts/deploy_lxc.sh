#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/minerales/app}"
VENV_DIR="${VENV_DIR:-${APP_DIR}/.venv}"
PYTHON_BIN="${PYTHON_BIN:-python3}"
SERVICE_NAME="${SERVICE_NAME:-isminerals}"

cd "$APP_DIR"

git pull --ff-only

if [ ! -d "$VENV_DIR" ]; then
  "$PYTHON_BIN" -m venv "$VENV_DIR"
fi

"$VENV_DIR/bin/python" -m pip install --upgrade pip
"$VENV_DIR/bin/python" -m pip install -r requirements.txt
"$VENV_DIR/bin/python" -m alembic upgrade head

systemctl restart "$SERVICE_NAME"

sleep 3
curl --fail --silent --show-error http://127.0.0.1:8501 >/dev/null

systemctl --no-pager --full status "$SERVICE_NAME"