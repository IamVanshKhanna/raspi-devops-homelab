#!/usr/bin/env bash
set -euo pipefail

# =============================================================================
# status-report.sh — Telegram status reporter for homelab-prod
# Sends docker stats, uptime, disk usage, and health check summary via Telegram Bot API.
#
# Usage:   bash scripts/status-report.sh
# Cron:    0 */2 * * * bash /home/vansh/homelab-prod/scripts/status-report.sh
# =============================================================================

BOT_TOKEN="8788089547:AAGm7HhcXnDu49MvxhJXIvaZheMHvA6JTow"
CHAT_ID="8005846986"
TELEGRAM_API="https://api.telegram.org/bot${BOT_TOKEN}"

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.."; pwd)"

send_msg() {
    local text="$1"
    curl -s -X POST "${TELEGRAM_API}/sendMessage" \
        -H "Content-Type: application/json" \
        -d "$(jq -n --arg text "$text" --arg chat_id "$CHAT_ID" \
            '{chat_id: $chat_id, text: $text, parse_mode: "Markdown"}')" \
        > /dev/null 2>&1 || true
}

TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S %Z')
HOSTNAME=$(hostname)
UPTIME=$(uptime -p 2>/dev/null | sed 's/up //' || uptime | awk -F'up' '{print $2}' | awk -F',' '{print $1}' | xargs)
LOAD=$(uptime | awk -F'load average:' '{print $2}' | xargs)
MEM=$(free -h | awk '/^Mem:/ {print $3"/"$2 " (" $3/$2*100 "%" ")"}')
DISK=$(df -h / | awk 'NR==2 {print $3"/"$2 " (" $5 ")"}')
DATA_DISK=$(df -h /mnt/data 2>/dev/null | awk 'NR==2 {print $3"/"$2 " (" $5 ")"}' || echo "N/A")

CONTAINERS_TOTAL=$(docker ps -q 2>/dev/null | wc -l)
CONTAINERS_HEALTHY=$(docker ps --filter "health=healthy" -q 2>/dev/null | wc -l)
CONTAINERS_UNHEALTHY=$(docker ps --filter "health=unhealthy" -q 2>/dev/null | wc -l)
CONTAINERS_STOPPED=$(docker ps -a --filter "status=exited" -q 2>/dev/null | wc -l)

HEALTH_CHECK_OUTPUT=$(bash "$REPO_DIR/scripts/health-check.sh" 2>&1 || true)
HEALTH_EXIT=$?

if [ $HEALTH_EXIT -eq 0 ]; then
    HEALTH_STATUS="All healthy"
else
    HEALTH_STATUS="Issues found"
fi

REPORT="*${HOSTNAME}* — Status Report
_${TIMESTAMP}_

*Health:* ${HEALTH_STATUS} (${CONTAINERS_HEALTHY:-0}/${CONTAINERS_TOTAL:-0} up, ${CONTAINERS_UNHEALTHY:-0} unhealthy, ${CONTAINERS_STOPPED:-0} stopped)

*Uptime:* ${UPTIME}
*Load:* ${LOAD}
*RAM:* ${MEM}
*Disk (/):* ${DISK}
*Data (/mnt/data):* ${DATA_DISK}"

send_msg "$REPORT"
echo "Status report sent to Telegram"

# If there are unhealthy containers, send detailed alert
if [ "${CONTAINERS_UNHEALTHY:-0}" -gt 0 ]; then
    DETAIL=$(docker ps --filter "health=unhealthy" --format '{{.Names}}: {{.Status}}' 2>/dev/null || echo "")
    send_msg "*ALERT: Unhealthy containers detected*
${DETAIL}"
fi

exit 0