#!/usr/bin/env bash
set -euo pipefail

PYTHON_BIN="${PYTHON_BIN:-python3}"
SERVICE_NAME="${SERVICE_NAME:-isminerals}"

if [ -z "${APP_DIR:-}" ]; then
  SERVICE_APP_DIR="$(systemctl show "$SERVICE_NAME" --property=WorkingDirectory --value 2>/dev/null || true)"
  APP_DIR="${SERVICE_APP_DIR:-/opt/isminerals/app}"
fi

VENV_DIR="${VENV_DIR:-${APP_DIR}/.venv}"

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
