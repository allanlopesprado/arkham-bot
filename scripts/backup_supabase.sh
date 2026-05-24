#!/usr/bin/env bash
set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-./backups/local}"
RETENTION_DAYS="${RETENTION_DAYS:-30}"
TIMESTAMP="$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -p "$BACKUP_DIR"

if [[ -z "${DATABASE_URL:-}" ]]; then
  echo "DATABASE_URL is required for pg_dump backup." >&2
  exit 1
fi

OUT="$BACKUP_DIR/arkham_supabase_$TIMESTAMP.sql.gz"
pg_dump "$DATABASE_URL" --no-owner --no-privileges | gzip > "$OUT"
find "$BACKUP_DIR" -type f -name 'arkham_supabase_*.sql.gz' -mtime +"$RETENTION_DAYS" -delete
echo "$OUT"
