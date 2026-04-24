#!/bin/bash
set -euo pipefail

cd "$(dirname "$0")/.."

ENV_FILE="${ENV_FILE:-.env.deploy}"
BACKUP_DIR="${BACKUP_DIR:-/var/backups/ghost}"
DATE="$(date +%Y%m%d_%H%M%S)"

mkdir -p "$BACKUP_DIR"

docker compose --env-file "$ENV_FILE" exec -T ghost tar czf - -C /var/lib/ghost/content . \
  > "$BACKUP_DIR/ghost_content_${DATE}.tar.gz"

find "$BACKUP_DIR" -name "ghost_content_*.tar.gz" -mtime +30 -delete

echo "Backup complete: ghost_content_${DATE}.tar.gz"
