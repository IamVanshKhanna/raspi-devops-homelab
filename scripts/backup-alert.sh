#!/usr/bin/env bash
# backup-alert.sh - Send alert on backup failure
# Called from cron wrapper or systemd timer
# Usage: ./backup-alert.sh "error message"

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
ENV_FILE="${ROOT_DIR}/.env"

# Load environment
if [[ -f "$ENV_FILE" ]]; then
  # shellcheck disable=SC1090
  set -a; source "$ENV_FILE"; set +a
fi

MESSAGE="${1:-Backup failed on $(hostname) at $(date)}"

# Send Telegram alert if configured
if [[ -n "${TELEGRAM_BOT_TOKEN:-}" && -n "${TELEGRAM_CHAT_ID:-}" ]]; then
  curl -s -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
    -d chat_id="${TELEGRAM_CHAT_ID}" \
    -d text="🚨 ${MESSAGE}" \
    -d parse_mode="Markdown" >/dev/null || true
fi

# Log to systemd journal
logger -t homelab-backup "ALERT: ${MESSAGE}"

echo "Alert sent: ${MESSAGE}"