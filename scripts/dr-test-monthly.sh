#!/usr/bin/env bash
# dr-test-monthly.sh - Monthly DR Test for Critical Services
# Schedule: 0 3 1 * * /home/vansh/homelab-prod/scripts/dr-test-monthly.sh >> /var/log/dr-test-monthly.log 2>&1

set -euo pipefail

# Configuration
DR_NAMESPACE="dr-test-$(date +%Y%m%d-%H%M%S)"
VELERO_NAMESPACE="velero"
KUBECONFIG_PRIMARY="/etc/rancher/k3s/k3s.yaml"
KUBECONFIG_DR="/etc/rancher/k3s/k3s-dr.yaml"
TELEGRAM_BOT_TOKEN="${TELEGRAM_BOT_TOKEN:-}"
TELEGRAM_CHAT_ID="${TELEGRAM_CHAT_ID:-}"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log() { echo -e "${GREEN}[DR-TEST]${NC} $1" | tee -a /var/log/dr-test-monthly.log; }
info() { echo -e "${BLUE}[INFO]${NC} $1" | tee -a /var/log/dr-test-monthly.log; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1" | tee -a /var/log/dr-test-monthly.log; }
fail() { echo -e "${RED}[FAIL]${NC} $1" | tee -a /var/log/dr-test-monthly.log; }

# Telegram notification
send_telegram() {
    local message="$1"
    if [[ -n "$TELEGRAM_BOT_TOKEN" && -n "$TELEGRAM_CHAT_ID" ]]; then
        curl -sf -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
            -d chat_id="${TELEGRAM_CHAT_ID}" \
            -d text="${message}" \
            -d parse_mode="Markdown" >/dev/null 2>&1 || warn "Failed to send Telegram notification"
    fi
}

# Cleanup on exit
cleanup() {
    log "Cleaning up DR test namespace: $DR_NAMESPACE"
    kubectl --kubeconfig="$KUBECONFIG_DR" delete namespace "$DR_NAMESPACE" --wait=false --ignore-not-found=true 2>/dev/null || true
}
trap cleanup EXIT

log "=== Monthly DR Test Started at $(date) ==="
send_telegram "🧪 *Monthly DR Test Started*\nTime: $(date '+%Y-%m-%d %H:%M:%S')\nDR Namespace: $DR_NAMESPACE"

# Check prerequisites
log "Checking prerequisites..."
command -v velero >/dev/null || fail "velero CLI not found"
command -v kubectl >/dev/null || fail "kubectl not found"
[[ -f "$KUBECONFIG_DR" ]] || fail "DR kubeconfig not found at $KUBECONFIG_DR"

# Check Velero is available
log "Checking Velero availability..."
if ! kubectl --kubeconfig="$KUBECONFIG_DR" get deployment velero -n "$VELERO_NAMESPACE" >/dev/null 2>&1; then
    warn "Velero not found on DR cluster, installing..."
    # Velero install would go here if needed
fi

# Get latest backup
log "Finding latest backup..."
LATEST_BACKUP=$(velero --kubeconfig="$KUBECONFIG_DR" backup get -o json 2>/dev/null | jq -r '.[0].metadata.name' 2>/dev/null || echo "")
if [[ -z "$LATEST_BACKUP" || "$LATEST_BACKUP" == "null" ]]; then
    fail "No backups found in Velero"
fi
log "Using backup: $LATEST_BACKUP"

# Create DR test namespace
log "Creating DR test namespace: $DR_NAMESPACE"
kubectl --kubeconfig="$KUBECONFIG_DR" create namespace "$DR_NAMESPACE" --dry-run=client -o yaml | kubectl --kubeconfig="$KUBECONFIG_DR" apply -f -

# Restore critical namespaces
CRITICAL_NAMESPACES=("apps" "databases" "secrets" "auth" "monitoring")
RESTORE_FAILED=0

for ns in "${CRITICAL_NAMESPACES[@]}"; do
    log "Restoring namespace: $ns -> $DR_NAMESPACE"
    
    if velero --kubeconfig="$KUBECONFIG_DR" restore create \
        --from-backup "$LATEST_BACKUP" \
        --namespace-mappings "$ns:$DR_NAMESPACE" \
        --include-namespaces "$ns" \
        --wait --timeout=300s 2>&1 | tee -a /var/log/dr-test-monthly.log; then
        log "✅ Restored $ns successfully"
    else
        warn "⚠️ Restore of $ns had issues"
        RESTORE_FAILED=$((RESTORE_FAILED + 1))
    fi
done

# Wait for pods to be ready
log "Waiting for pods to be ready in $DR_NAMESPACE..."
if kubectl --kubeconfig="$KUBECONFIG_DR" wait --for=condition=Ready pods --all -n "$DR_NAMESPACE" --timeout=300s 2>&1 | tee -a /var/log/dr-test-monthly.log; then
    log "✅ All pods ready"
else
    warn "⚠️ Some pods not ready within timeout"
    kubectl --kubeconfig="$KUBECONFIG_DR" get pods -n "$DR_NAMESPACE" -o wide | tee -a /var/log/dr-test-monthly.log
fi

# Health checks for critical services
log "Running health checks on critical services..."

# Nextcloud
if kubectl --kubeconfig="$KUBECONFIG_DR" exec -n "$DR_NAMESPACE" deploy/nextcloud -- curl -sf http://localhost:80/status.php >/dev/null 2>&1; then
    log "✅ Nextcloud health check passed"
else
    warn "⚠️ Nextcloud health check failed"
    RESTORE_FAILED=$((RESTORE_FAILED + 1))
fi

# Vaultwarden
if kubectl --kubeconfig="$KUBECONFIG_DR" exec -n "$DR_NAMESPACE" deploy/vaultwarden -- curl -sf http://localhost:80/alive >/dev/null 2>&1; then
    log "✅ Vaultwarden health check passed"
else
    warn "⚠️ Vaultwarden health check failed"
    RESTORE_FAILED=$((RESTORE_FAILED + 1))
fi

# PostgreSQL
if kubectl --kubeconfig="$KUBECONFIG_DR" exec -n "$DR_NAMESPACE" statefulset/postgresql -- pg_isready -U admin >/dev/null 2>&1; then
    log "✅ PostgreSQL health check passed"
else
    warn "⚠️ PostgreSQL health check failed"
    RESTORE_FAILED=$((RESTORE_FAILED + 1))
fi

# Redis
if kubectl --kubeconfig="$KUBECONFIG_DR" exec -n "$DR_NAMESPACE" statefulset/redis -- redis-cli ping >/dev/null 2>&1; then
    log "✅ Redis health check passed"
else
    warn "⚠️ Redis health check failed"
    RESTORE_FAILED=$((RESTORE_FAILED + 1))
fi

# Home Assistant
if kubectl --kubeconfig="$KUBECONFIG_DR" exec -n "$DR_NAMESPACE" deploy/home-assistant -- curl -sf http://localhost:8123 >/dev/null 2>&1; then
    log "✅ Home Assistant health check passed"
else
    warn "⚠️ Home Assistant health check failed"
    RESTORE_FAILED=$((RESTORE_FAILED + 1))
fi

# Prometheus
if kubectl --kubeconfig="$KUBECONFIG_DR" exec -n "$DR_NAMESPACE" deploy/prometheus -- curl -sf http://localhost:9090/-/healthy >/dev/null 2>&1; then
    log "✅ Prometheus health check passed"
else
    warn "⚠️ Prometheus health check failed"
    RESTORE_FAILED=$((RESTORE_FAILED + 1))
fi

# Grafana
if kubectl --kubeconfig="$KUBECONFIG_DR" exec -n "$DR_NAMESPACE" deploy/grafana -- curl -sf http://localhost:3000/api/health >/dev/null 2>&1; then
    log "✅ Grafana health check passed"
else
    warn "⚠️ Grafana health check failed"
    RESTORE_FAILED=$((RESTORE_FAILED + 1))
fi

# Summary
log "=== DR Test Summary ==="
log "DR Namespace: $DR_NAMESPACE"
log "Source Backup: $LATEST_BACKUP"
log "Namespaces Restored: ${#CRITICAL_NAMESPACES[@]}"
log "Health Checks Failed: $RESTORE_FAILED"

if [[ $RESTORE_FAILED -eq 0 ]]; then
    log "✅ DR TEST PASSED - All critical services restored and healthy"
    TEST_RESULT="PASSED"
    EMOJI="✅"
else
    warn "⚠️ DR TEST PARTIAL - $RESTORE_FAILED health checks failed"
    TEST_RESULT="PARTIAL"
    EMOJI="🟡"
fi

# Send notification
send_telegram "${EMOJI} *Monthly DR Test ${TEST_RESULT}*\nTime: $(date '+%Y-%m-%d %H:%M:%S')\nBackup: $LATEST_BACKUP\nFailed Checks: $RESTORE_FAILED\nNamespace: $DR_NAMESPACE"

# Keep namespace for inspection if failed
if [[ $RESTORE_FAILED -gt 0 ]]; then
    warn "Keeping DR test namespace for inspection: $DR_NAMESPACE"
    trap - EXIT  # Don't cleanup on exit
fi

log "=== Monthly DR Test Completed at $(date) ==="
exit $RESTORE_FAILED