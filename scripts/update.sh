#!/usr/bin/env bash
# update.sh - Pull latest images and recreate all stacks
# Schedule: 0 4 * * 0 bash /home/vansh/homelab-prod/scripts/update.sh >> /var/log/homelab-update.log 2>&1

set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.."; pwd)"
log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"; }

STACKS=(
  "stacks/core/docker-compose.yml"
  "stacks/monitoring/docker-compose.yml"
  "stacks/apps/docker-compose.yml"
  "stacks/network/docker-compose.yml"
  "stacks/auth/docker-compose.yml"
  "stacks/crowdsec/docker-compose.yml"
  "stacks/tracing/docker-compose.yml"
  "stacks/uptime-kuma/docker-compose.yml"
  "stacks/smarthome/docker-compose.yml"
)

log "Starting pre-update health check..."
bash "$REPO_DIR/scripts/health-check.sh" || log "WARNING: Pre-update health check had failures"

log "Running pre-update backup..."
bash "$REPO_DIR/scripts/backup.sh" || log "WARNING: Pre-update backup had failures"

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

log "Running post-update health check..."
sleep 30
bash "$REPO_DIR/scripts/health-check.sh" || log "WARNING: Post-update health check had failures"

log "All stacks updated successfully."
