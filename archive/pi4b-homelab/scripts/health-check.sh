#!/usr/bin/env bash
# health-check.sh - Verify all homelab containers are running
# Schedule: */15 * * * * /home/pi/pi4b-homelab/scripts/health-check.sh >> /var/log/homelab-health.log 2>&1

set -euo pipefail

GREEN='\033[0;32m'; RED='\033[0;31m'; NC='\033[0m'
log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"; }

EXPECTED_CONTAINERS=(
  traefik portainer
  prometheus grafana node-exporter cadvisor
  nextcloud mariadb redis vaultwarden ollama
  pihole wireguard
  homeassistant
)

FAILED=0

log "--- Homelab Health Check ---"
printf "%-20s %-12s\n" "CONTAINER" "STATUS"
printf "%-20s %-12s\n" "-------------------" "----------"

for NAME in "${EXPECTED_CONTAINERS[@]}"; do
  STATUS=$(docker inspect --format='{{.State.Status}}' "$NAME" 2>/dev/null || echo "missing")
  if [[ "$STATUS" == "running" ]]; then
    printf "${GREEN}%-20s %-12s${NC}\n" "$NAME" "$STATUS"
  else
    printf "${RED}%-20s %-12s${NC}\n" "$NAME" "$STATUS"
    FAILED=$((FAILED + 1))
  fi
done

TOTAL=${#EXPECTED_CONTAINERS[@]}
RUNNING=$((TOTAL - FAILED))

echo ""
log "Result: $RUNNING/$TOTAL containers running."

if [[ $FAILED -gt 0 ]]; then
  log "WARNING: $FAILED container(s) are NOT running!"
  log "Check: docker ps -a"
  log "Logs:  docker logs <container_name>"
  exit 1
else
  log "All containers healthy."
  exit 0
fi
