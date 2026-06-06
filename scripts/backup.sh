#!/usr/bin/env bash
# backup.sh - Backs up all named Docker volumes
# Schedule: 0 3 * * * /home/pi/pi4b-homelab/scripts/backup.sh >> /var/log/homelab-backup.log 2>&1

set -euo pipefail

BACKUP_ROOT="/mnt/backup"
DATE=$(date +%Y-%m-%d)
BACKUP_DIR="$BACKUP_ROOT/$DATE"
RETAIN_DAYS=7

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"; }

log "Starting backup to $BACKUP_DIR"
mkdir -p "$BACKUP_DIR"

VOLUMES=$(docker volume ls --format '{{.Name}}')

for VOLUME in $VOLUMES; do
  log "Backing up volume: $VOLUME"
  docker run --rm \
    -v "$VOLUME":/volume:ro \
    -v "$BACKUP_DIR":/backup \
    alpine \
    tar czf "/backup/${VOLUME}.tar.gz" -C /volume . \
    && log "  OK $VOLUME.tar.gz" \
    || log "  FAILED: $VOLUME"
done

log "Removing backups older than $RETAIN_DAYS days..."
find "$BACKUP_ROOT" -maxdepth 1 -type d -mtime +$RETAIN_DAYS -exec rm -rf {} + || true

SIZE=$(du -sh "$BACKUP_DIR" | cut -f1)
log "Backup complete. Size: $SIZE | Location: $BACKUP_DIR"
