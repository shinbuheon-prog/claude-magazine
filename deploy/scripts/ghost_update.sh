#!/bin/bash
set -euo pipefail

cd "$(dirname "$0")/.."

ENV_FILE="${ENV_FILE:-.env.deploy}"

echo "Backup before update..."
ENV_FILE="$ENV_FILE" ./scripts/ghost_backup.sh

echo "Pulling latest Ghost 5.x image..."
docker compose --env-file "$ENV_FILE" pull ghost

echo "Restarting Ghost..."
docker compose --env-file "$ENV_FILE" up -d ghost

echo "Waiting for health check..."
sleep 30
docker compose --env-file "$ENV_FILE" ps
