#!/usr/bin/env bash
set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-/var/backups/isminerals}"
UPLOAD_DIR="${UPLOAD_DIR:-/var/lib/isminerals/uploads}"
RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-7}"

if [ -z "${DATABASE_URL:-}" ]; then
  echo "DATABASE_URL is required for backups." >&2
  exit 1
fi

mkdir -p "$BACKUP_DIR"
timestamp="$(date -u +%Y%m%dT%H%M%SZ)"

pg_dump "$DATABASE_URL" --format=custom --file="${BACKUP_DIR}/isminerals-db-${timestamp}.dump"

if [ -d "$UPLOAD_DIR" ]; then
  tar -C "$(dirname "$UPLOAD_DIR")" -czf "${BACKUP_DIR}/isminerals-uploads-${timestamp}.tar.gz" "$(basename "$UPLOAD_DIR")"
fi

find "$BACKUP_DIR" -type f \( -name "isminerals-db-*.dump" -o -name "isminerals-uploads-*.tar.gz" \) -mtime +"$RETENTION_DAYS" -delete
