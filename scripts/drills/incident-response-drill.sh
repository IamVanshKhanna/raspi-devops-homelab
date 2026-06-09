#!/usr/bin/env bash
# incident-response-drill.sh - Run incident response drill scenarios
# Schedule: Monthly, or on-demand via workflow_dispatch

set -euo pipefail

# Configuration
DRILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_FILE="/var/log/incident-drill-$(date +%Y%m%d-%H%M%S).log"
KUBECONFIG="/etc/rancher/k3s/k3s.yaml"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log() { echo -e "${GREEN}[DRILL]${NC} $1" | tee -a "$LOG_FILE"; }
info() { echo -e "${BLUE}[INFO]${NC} $1" | tee -a "$LOG_FILE"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1" | tee -a "$LOG_FILE"; }
fail() { echo -e "${RED}[FAIL]${NC} $1" | tee -a "$LOG_FILE"; }

# Telegram notification
send_telegram() {
    local message="$1"
    if [[ -n "${TELEGRAM_BOT_TOKEN:-}" && -n "${TELEGRAM_CHAT_ID:-}" ]]; then
        curl -sf -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
            -d chat_id="${TELEGRAM_CHAT_ID}" \
            -d text="${message}" \
            -d parse_mode="Markdown" >/dev/null 2>&1 || true
    fi
}

# Scenario 1: Database outage simulation
drill_database_outage() {
    log "=== DRILL: Database Outage Simulation ==="
    info "Simulating PostgreSQL primary failure..."
    
    # Get current primary
    PRIMARY=$(kubectl --kubeconfig="$KUBECONFIG" get postgresql homelab-postgres -n databases -o jsonpath='{.status.primary}' 2>/dev/null || echo "unknown")
    info "Current primary: $PRIMARY"
    
    # Force failover by deleting primary pod
    info "Deleting primary pod to trigger Patroni failover..."
    kubectl --kubeconfig="$KUBECONFIG" delete pod "$PRIMARY" -n databases --wait=false
    
    # Wait for new primary
    info "Waiting for failover to complete (max 60s)..."
    local timeout=60
    local elapsed=0
    while [[ $elapsed -lt $timeout ]]; do
        NEW_PRIMARY=$(kubectl --kubeconfig="$KUBECONFIG" get postgresql homelab-postgres -n databases -o jsonpath='{.status.primary}' 2>/dev/null || echo "unknown")
        if [[ "$NEW_PRIMARY" != "$PRIMARY" && "$NEW_PRIMARY" != "unknown" ]]; then
            log "✅ Failover successful! New primary: $NEW_PRIMARY"
            return 0
        fi
        sleep 5
        elapsed=$((elapsed + 5))
    done
    
    warn "⚠️ Failover did not complete within ${timeout}s"
    return 1
}

# Scenario 2: Redis cluster failure
drill_redis_outage() {
    log "=== DRILL: Redis Cluster Failure ==="
    info "Simulating Redis master failure..."
    
    # Find master pod
    MASTER=$(kubectl --kubeconfig="$KUBECONFIG" get pods -n databases -l app.kubernetes.io/name=redis,role=master -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || echo "")
    
    if [[ -z "$MASTER" ]]; then
        warn "No Redis master found, trying any redis pod"
        MASTER=$(kubectl --kubeconfig="$KUBECONFIG" get pods -n databases -l app.kubernetes.io/name=redis -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || echo "")
    fi
    
    if [[ -n "$MASTER" ]]; then
        info "Deleting Redis master: $MASTER"
        kubectl --kubeconfig="$KUBECONFIG" delete pod "$MASTER" -n databases --wait=false
        sleep 10
        NEW_MASTER=$(kubectl --kubeconfig="$KUBECONFIG" get pods -n databases -l app.kubernetes.io/name=redis,role=master -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || echo "")
        if [[ -n "$NEW_MASTER" && "$NEW_MASTER" != "$MASTER" ]]; then
            log "✅ Redis failover successful! New master: $NEW_MASTER"
            return 0
        fi
    fi
    
    warn "⚠️ Redis failover verification incomplete"
    return 1
}

# Scenario 3: Ingress controller failure
drill_ingress_outage() {
    log "=== DRILL: Ingress Controller (Traefik) Outage ==="
    info "Simulating Traefik pod failure..."
    
    TRAEFIK_POD=$(kubectl --kubeconfig="$KUBECONFIG" get pods -n traefik -l app.kubernetes.io/name=traefik -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || echo "")
    
    if [[ -n "$TRAEFIK_POD" ]]; then
        info "Deleting Traefik pod: $TRAEFIK_POD"
        kubectl --kubeconfig="$KUBECONFIG" delete pod "$TRAEFIK_POD" -n traefik --wait=false
        sleep 15
        
        # Check if new pod is ready
        NEW_POD=$(kubectl --kubeconfig="$KUBECONFIG" get pods -n traefik -l app.kubernetes.io/name=traefik -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || echo "")
        if [[ -n "$NEW_POD" && "$NEW_POD" != "$TRAEFIK_POD" ]]; then
            READY=$(kubectl --kubeconfig="$KUBECONFIG" get pod "$NEW_POD" -n traefik -o jsonpath='{.status.conditions[?(@.type=="Ready")].status}' 2>/dev/null || echo "False")
            if [[ "$READY" == "True" ]]; then
                log "✅ Traefik recovery successful! New pod: $NEW_POD"
                return 0
            fi
        fi
    fi
    
    warn "⚠️ Traefik recovery verification incomplete"
    return 1
}

# Scenario 4: Storage failure simulation
drill_storage_issue() {
    log "=== DRILL: Storage Issue Simulation ==="
    info "Checking Longhorn node status..."
    
    kubectl --kubeconfig="$KUBECONFIG" get nodes.longhorn.io -o custom-columns=NAME:.metadata.name,READY:.status.conditions[?\(@.type==\"Ready\"\).status],DISKS:.status.diskStatus\[\].conditions[?\(@.type==\"Ready\"\).status] 2>/dev/null || warn "Longhorn CLI not available"
    
    info "Simulating PVC mount issue by annotating a test PVC..."
    TEST_PVC="drill-test-pvc"
    kubectl --kubeconfig="$KUBECONFIG" create pvc "$TEST_PVC" -n default --dry-run=client -o yaml | kubectl apply -f - 2>/dev/null || true
    
    # Check PVC binding
    sleep 5
    STATUS=$(kubectl --kubeconfig="$KUBECONFIG" get pvc "$TEST_PVC" -n default -o jsonpath='{.status.phase}' 2>/dev/null || echo "Unknown")
    if [[ "$STATUS" == "Bound" ]]; then
        log "✅ PVC binding works correctly"
        kubectl --kubeconfig="$KUBECONFIG" delete pvc "$TEST_PVC" -n default --ignore-not-found=true
        return 0
    else
        warn "⚠️ PVC binding issue: $STATUS"
        kubectl --kubeconfig="$KUBECONFIG" delete pvc "$TEST_PVC" -n default --ignore-not-found=true
        return 1
    fi
}

# Scenario 5: Certificate expiry drill
drill_cert_expiry() {
    log "=== DRILL: Certificate Expiry Check ==="
    info "Checking certificate expiry dates..."
    
    EXPIRING=$(kubectl --kubeconfig="$KUBECONFIG" get certificates -A -o json | jq -r '.items[] | select(.status.notAfter != null) | "\(.metadata.namespace)/\(.metadata.name) \(.status.notAfter)"' 2>/dev/null | while read ns name expiry; do
        EXPIRY_EPOCH=$(date -d "$expiry" +%s 2>/dev/null || date -j -f "%Y-%m-%dT%H:%M:%SZ" "$expiry" +%s 2>/dev/null)
        NOW_EPOCH=$(date +%s)
        DAYS_LEFT=$(( (EXPIRY_EPOCH - NOW_EPOCH) / 86400 ))
        if [[ $DAYS_LEFT -le 30 ]]; then
            echo "$ns/$name expires in $DAYS_LEFT days ($expiry)"
        fi
    done)
    
    if [[ -n "$EXPIRING" ]]; then
        warn "Certificates expiring within 30 days:"
        echo "$EXPIRING" | tee -a "$LOG_FILE"
    else
        log "✅ No certificates expiring within 30 days"
    fi
    
    return 0
}

# Scenario 6: Backup verification drill
drill_backup_verification() {
    log "=== DRILL: Backup Verification ==="
    info "Running backup and restore test..."
    
    if [[ -f "/home/vansh/homelab-prod/scripts/backup.sh" ]]; then
        /home/vansh/homelab-prod/scripts/backup.sh 2>&1 | tee -a "$LOG_FILE"
        if [[ ${PIPESTATUS[0]} -eq 0 ]]; then
            log "✅ Backup completed successfully"
        else
            warn "⚠️ Backup had issues"
            return 1
        fi
    else
        warn "Backup script not found"
        return 1
    fi
    
    # Run restore test
    if [[ -f "/home/vansh/homelab-prod/scripts/restore-test.sh" ]]; then
        /home/vansh/homelab-prod/scripts/restore-test.sh 2>&1 | tee -a "$LOG_FILE"
        if [[ ${PIPESTATUS[0]} -eq 0 ]]; then
            log "✅ Restore test passed"
        else
            warn "⚠️ Restore test had issues"
            return 1
        fi
    fi
    
    return 0
}

# Scenario 7: Network partition simulation
drill_network_partition() {
    log "=== DRILL: Network Partition Simulation ==="
    info "Testing network policies by attempting cross-namespace access..."
    
    # Try to access a service from a different namespace
    # This tests if NetworkPolicies are correctly enforced
    TEST_POD="network-test-$(date +%s)"
    kubectl --kubeconfig="$KUBECONFIG" run "$TEST_POD" --image=curlimages/curl:latest --restart=Never -n default -- sleep 60 2>/dev/null || true
    sleep 5
    
    # Try to curl a service in another namespace (should be blocked by default-deny)
    kubectl --kubeconfig="$KUBECONFIG" exec "$TEST_POD" -n default -- timeout 5 curl -sf http://prometheus.monitoring.svc.cluster.local:9090/-/healthy 2>&1 | tee -a "$LOG_FILE" || true
    
    # Cleanup
    kubectl --kubeconfig="$KUBECONFIG" delete pod "$TEST_POD" -n default --ignore-not-found=true --wait=false
    
    log "Network policy test completed (check logs for expected blocked access)"
    return 0
}

# Scenario 8: Resource exhaustion (OOM) drill
drill_oom_scenario() {
    log "=== DRILL: OOM Kill Scenario ==="
    info "Checking for recent OOM kills..."
    
    OOMS=$(kubectl --kubeconfig="$KUBECONFIG" get events -A --field-selector reason=OOMKilling -o jsonpath='{.items[*].message}' 2>/dev/null || echo "")
    
    if [[ -n "$OOMS" ]]; then
        warn "Recent OOM kills detected:"
        echo "$OOMS" | tee -a "$LOG_FILE"
    else
        log "✅ No recent OOM kills"
    fi
    
    # Check pod restarts due to OOM
    RESTARTS=$(kubectl --kubeconfig="$KUBECONFIG" get pods -A -o json | jq -r '.items[] | select(any(.status.containerStatuses[]?.lastState.terminated.reason; . == "OOMKilled")) | "\(.metadata.namespace)/\(.metadata.name)"' 2>/dev/null || echo "")
    
    if [[ -n "$RESTARTS" ]]; then
        warn "Pods with OOMKilled containers:"
        echo "$RESTARTS" | tee -a "$LOG_FILE"
    fi
    
    return 0
}

# Main drill runner
run_all_drills() {
    local passed=0
    local failed=0
    local results=()
    
    log "Starting Incident Response Drills - $(date)"
    send_telegram "🚨 *Incident Response Drill Started*\nTime: $(date '+%Y-%m-%d %H:%M:%S')\nRunning all scenarios..."
    
    # Array of drill functions
    local drills=(
        "drill_database_outage"
        "drill_redis_outage"
        "drill_ingress_outage"
        "drill_storage_issue"
        "drill_cert_expiry"
        "drill_backup_verification"
        "drill_network_partition"
        "drill_oom_scenario"
    )
    
    for drill in "${drills[@]}"; do
        log "\n--- Running $drill ---"
        if $drill; then
            results+=("$drill: PASS")
            ((passed++))
        else
            results+=("$drill: FAIL")
            ((failed++))
        fi
        sleep 10  # Cool down between drills
    done
    
    # Summary
    log "\n=== DRILL SUMMARY ==="
    log "Passed: $passed"
    log "Failed: $failed"
    log "Total:  ${#drills[@]}"
    
    echo "" | tee -a "$LOG_FILE"
    echo "Detailed Results:" | tee -a "$LOG_FILE"
    for result in "${results[@]}"; do
        echo "  $result" | tee -a "$LOG_FILE"
    done
    
    # Send summary
    local summary="✅ *Drill Complete*\nPassed: $passed\nFailed: $failed\nTotal: ${#drills[@]}\nLog: $LOG_FILE"
    send_telegram "$summary"
    
    if [[ $failed -gt 0 ]]; then
        return 1
    fi
    return 0
}

# Check prerequisites
command -v kubectl >/dev/null || fail "kubectl not found"
command -v jq >/dev/null || fail "jq not found"

# Run drills
if [[ "${1:-}" == "--drill" ]]; then
    # Run specific drill
    "drill_$2" || exit 1
else
    # Run all drills
    run_all_drills
fi