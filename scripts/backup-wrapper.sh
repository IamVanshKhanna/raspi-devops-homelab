#!/usr/bin/env bash
# backup-wrapper.sh - Wrapper for backup.sh with alerting on failure
# Usage: ./backup-wrapper.sh (intended for cron)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Run backup and capture exit code
./scripts/backup.sh
BACKUP_EXIT=$?

if [[ $BACKUP_EXIT -eq 0 ]]; then
  echo "Backup completed successfully"
else
  ./scripts/backup-alert.sh "Backup FAILED on $(hostname) at $(date) with exit code $BACKUP_EXIT"
  exit $BACKUP_EXIT
fi