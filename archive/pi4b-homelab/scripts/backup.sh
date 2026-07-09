#!/usr/bin/env bash
# backup.sh - Backs up named Docker volumes for pi4b-homelab
# Only backs up data volumes - NOT model weights, prometheus TSDB, or certs
# Schedule: 0 3 * * * /home/pi/pi4b-homelab/scripts/backup.sh >> /var/log/homelab-backup.log 2>&1

set -euo pipefail

BACKUP_ROOT="/mnt/backup"
DATE=$(date +%Y-%m-%d)
BACKUP_DIR="$BACKUP_ROOT/$DATE"
RETAIN_DAYS=7

GREEN='\033[0;32m'; RED='\033[0;31m'; NC='\033[0m'
log()  { echo -e "[$(date '+%Y-%m-%d %H:%M:%S')] ${GREEN}$1${NC}"; }
fail() { echo -e "[$(date '+%Y-%m-%d %H:%M:%S')] ${RED}FAILED: $1${NC}"; }

# Explicit list of volumes to back up.
# Intentionally EXCLUDES:
#   - ollama_data        (gigabytes of model weights - re-pull after restore)
#   - prometheus_data    (time-series metrics - not critical to restore)
#   - traefik_certs      (acme.json regenerates automatically from Let's Encrypt)
#   - grafana_data       (dashboards are provisioned from config/ files)
BACKUP_VOLUMES=(
  nextcloud_data
  mariadb_data
  redis_data
  vaultwarden_data
  homeassistant_config
  pihole_data
  pihole_dnsmasq
  wireguard_data
  portainer_data
)

log "Starting backup to $BACKUP_DIR"
mkdir -p "$BACKUP_DIR"

FAILED=0
for VOLUME in "${BACKUP_VOLUMES[@]}"; do
  # Check volume exists before trying to back it up
  if ! docker volume inspect "$VOLUME" &>/dev/null; then
    log "Skipping $VOLUME (not found - stack may not be deployed)"
    continue
  fi
  log "Backing up volume: $VOLUME"
  docker run --rm \
    -v "$VOLUME":/volume:ro \
    -v "$BACKUP_DIR":/backup \
    alpine \
    tar czf "/backup/${VOLUME}.tar.gz" -C /volume . \
    && log "  OK $VOLUME.tar.gz" \
    || { fail "$VOLUME"; FAILED=$((FAILED + 1)); }
done

log "Removing backups older than $RETAIN_DAYS days..."
find "$BACKUP_ROOT" -maxdepth 1 -type d -mtime +$RETAIN_DAYS -exec rm -rf {} + || true

SIZE=$(du -sh "$BACKUP_DIR" | cut -f1)
log "Backup complete. Size: $SIZE | Location: $BACKUP_DIR"
log "Volumes backed up: $((${#BACKUP_VOLUMES[@]} - FAILED)) / ${#BACKUP_VOLUMES[@]}"

if [[ $FAILED -gt 0 ]]; then
  fail "$FAILED volume(s) failed to back up - check logs above"
  exit 1
fi
