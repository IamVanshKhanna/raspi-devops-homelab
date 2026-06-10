#!/usr/bin/env bash
# capacity-report.sh - Wrapper for capacity-plan.py
# Schedule: 0 6 * * 1 /home/vansh/homelab-prod/scripts/capacity-report.sh >> /var/log/capacity-report.log 2>&1

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CAPACITY_SCRIPT="${SCRIPT_DIR}/capacity-plan.py"
REPORT_DIR="/home/vansh/homelab-prod/capacity-reports"
TELEGRAM_BOT_TOKEN="${TELEGRAM_BOT_TOKEN}"
TELEGRAM_CHAT_ID="${TELEGRAM_CHAT_ID}"
PROMETHEUS_URL="${PROMETHEUS_URL:-http://prometheus.monitoring.svc.cluster.local:9090}"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

log() { echo -e "${GREEN}[CAPACITY-REPORT]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
fail() { echo -e "${RED}[FAIL]${NC} $1"; exit 1; }

# Check prerequisites
command -v python3 >/dev/null || fail "python3 not installed"
[[ -f "$CAPACITY_SCRIPT" ]] || fail "capacity-plan.py not found at $CAPACITY_SCRIPT"

# Run capacity plan
log "Running capacity planning analysis..."
python3 "$CAPACITY_SCRIPT" \
    --prometheus-url "$PROMETHEUS_URL" \
    --output-dir "$REPORT_DIR"

EXIT_CODE=$?

# Send Telegram notification if configured
if [[ -n "$TELEGRAM_BOT_TOKEN" && -n "$TELEGRAM_CHAT_ID" ]]; then
    LATEST_REPORT="${REPORT_DIR}/capacity_report_latest.json"
    
    if [[ -f "$LATEST_REPORT" ]]; then
        # Extract summary for Telegram
        DISK_USAGE=$(jq -r '.current_metrics.disk_usage_pct.formatted // "N/A"' "$LATEST_REPORT")
        MEM_USAGE=$(jq -r '.current_metrics.memory_usage_pct.formatted // "N/A"' "$LATEST_REPORT")
        CPU_USAGE=$(jq -r '.current_metrics.cpu_usage_pct.formatted // "N/A"' "$LATEST_REPORT")
        DISK_EXHAUSTION=$(jq -r '.disk_exhaustion_estimate // "Unknown"' "$LATEST_REPORT")
        ALERTS=$(jq -r '.alerts | length' "$LATEST_REPORT")
        
        MESSAGE="📊 *Capacity Report Summary*
*Disk:* $DISK_USAGE
*Memory:* $MEM_USAGE
*CPU:* $CPU_USAGE
*Disk Exhaustion:* $DISK_EXHAUSTION
*Alerts:* $ALERTS
*Time:* $(date '+%Y-%m-%d %H:%M:%S')"
        
        # Determine emoji based on exit code
        case $EXIT_CODE in
            0) EMOJI="✅" ;;
            1) EMOJI="🔴" ;;
            2) EMOJI="🟡" ;;
            *) EMOJI="❓" ;;
        esac
        
        MESSAGE="${EMOJI} ${MESSAGE}"
        
        curl -sf -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
            -d chat_id="${TELEGRAM_CHAT_ID}" \
            -d text="${MESSAGE}" \
            -d parse_mode="Markdown" >/dev/null 2>&1 || warn "Failed to send Telegram notification"
    fi
fi

# Cleanup old reports (keep last 30 days)
find "$REPORT_DIR" -name "capacity_report_*.json" -mtime +30 -delete 2>/dev/null || true

log "Capacity report completed with exit code: $EXIT_CODE"
exit $EXIT_CODE