#!/usr/bin/env bash
# update.sh - Pull latest images and recreate all stacks
# Schedule: 0 4 * * 0 /home/pi/pi4b-homelab/scripts/update.sh >> /var/log/homelab-update.log 2>&1

set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.."; pwd)"
log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"; }

STACKS=(
  "stacks/core/docker-compose.yml"
  "stacks/monitoring/docker-compose.yml"
  "stacks/apps/docker-compose.yml"
  "stacks/network/docker-compose.yml"
  "stacks/smarthome/docker-compose.yml"
)

log "Starting update of all stacks..."

for STACK in "${STACKS[@]}"; do
  FULL_PATH="$REPO_DIR/$STACK"
  if [[ -f "$FULL_PATH" ]]; then
    log "Updating: $STACK"
    docker compose -f "$FULL_PATH" pull
    docker compose -f "$FULL_PATH" up -d --remove-orphans
    log "  OK: $STACK"
  else
    log "  SKIP (not found): $FULL_PATH"
  fi
done

log "Pruning unused images..."
docker image prune -f

log "All stacks updated successfully."
