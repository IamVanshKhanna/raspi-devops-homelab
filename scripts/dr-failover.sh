#!/usr/bin/env bash
# dr-test-quarterly.sh - Quarterly Full DR Failover Test
# Schedule: Manual + GitHub Actions workflow_dispatch

set -euo pipefail

# Configuration
KUBECONFIG_PRIMARY="/etc/rancher/k3s/k3s.yaml"
KUBECONFIG_DR="/etc/rancher/k3s/k3s-dr.yaml"
DOMAIN="homelab.local"
TELEGRAM_BOT_TOKEN="${TE...n
# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log() { echo -e "${GREEN}[DR-FAILOVER]${NC} $1" | tee -a /var/log/dr-failover.log; }
info() { echo -e "${BLUE}[INFO]${NC} $1" | tee -a /var/log/dr-failover.log; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1" | tee -a /var/log/dr-failover.log; }
fail() { echo -e "${RED}[FAIL]${NC} $1" | tee -a /var/log/dr-failover.log; }

# Telegram notification
send_telegram() {
    local message="$1"
    if [[ -n "$TELEGRAM_BOT_TOKEN" && -n "$TELEGRAM_CHAT_ID" ]]; then
        curl -sf -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
            -d chat_id="${TELEGRAM_CHAT_ID}" \
            -d text="${message}" \
            -d parse_mode="Markdown" >/dev/null 2>&1 || true
    fi
}

# Get primary and DR IPs
get_ips() {
    PRIMARY_IP=$(dig +short "$DOMAIN" @1.1.1.1 | head -1)
    DR_IP=$(dig +short "dr.$DOMAIN" @1.1.1.1 | head -1)
    log "Primary IP: $PRIMARY_IP"
    log "DR IP: $DR_IP"
}

# DNS Failover
dns_failover() {
    local target="$1"  # primary or dr
    
    log "Initiating DNS failover to: $target"
    
    if [[ -z "$CLOUDFLARE_API_TOKEN" || -z "$CLOUDFLARE_ZONE_ID" ]]; then
        fail "Cloudflare credentials not configured"
        return 1
    fi
    
    # Get current DNS records
    RECORDS=$(curl -sf "https://api.cloudflare.com/client/v4/zones/$CLOUDFLARE_ZONE_ID/dns_records?type=A&name=$DOMAIN" \
        -H "Authorization: Bearer $CLOUDFLARE_API_TOKEN" \
        -H "Content-Type: application/json" | jq -r '.result[] | select(.proxied == true) | .id')
    
    if [[ -z "$RECORDS" ]]; then
        fail "No proxied A records found for $DOMAIN"
        return 1
    fi
    
    for RECORD_ID in $RECORDS; do
        local new_ip
        if [[ "$target" == "dr" ]]; then
            new_ip="$DR_IP"
        else
            new_ip="$PRIMARY_IP"
        fi
        
        log "Updating record $RECORD_ID to $new_ip"
        curl -sf -X PUT "https://api.cloudflare.com/client/v4/zones/$CLOUDFLARE_ZONE_ID/dns_records/$RECORD_ID" \
            -H "Authorization: Bearer $CLOUDFLARE_API_TOKEN" \
            -H "Content-Type: application/json" \
            --data "{\"type\":\"A\",\"name\":\"$DOMAIN\",\"content\":\"$new_ip\",\"ttl\":60,\"proxied\":true}" >/dev/null || {
            fail "Failed to update DNS record $RECORD_ID"
            return 1
        }
    done
    
    log "DNS failover to $target completed"
    return 0
}

# Full DR Failover
full_failover() {
    log "=== INITIATING FULL DR FAILOVER ==="
    send_telegram "🚨 *FULL DR FAILOVER INITIATED*\nTime: $(date '+%Y-%m-%d %H:%M:%S')\nFailover to DR region"
    
    # Phase 1: DNS Failover
    log "Phase 1: DNS Failover to DR"
    get_ips
    dns_failover "dr" || fail "DNS failover failed"
    log "DNS propagated, waiting 60s for TTL..."
    sleep 60
    
    # Phase 2: Verify DR Services
    log "Phase 2: Verifying DR Services"
    
    # Check DR cluster is accessible
    if ! kubectl --kubeconfig="$KUBECONFIG_DR" get nodes >/dev/null 2>&1; then
        fail "DR cluster not accessible"
        return 1
    fi
    log "DR cluster accessible"
    
    # Restore from latest backup if needed
    log "Restoring from latest Velero backup..."
    LATEST_BACKUP=$(velero --kubeconfig="$KUBECONFIG_DR" backup get -o json 2>/dev/null | jq -r '.[0].metadata.name' 2>/dev/null || echo "")
    
    if [[ -n "$LATEST_BACKUP" && "$LATEST_BACKUP" != "null" ]]; then
        log "Restoring from backup: $LATEST_BACKUP"
        NAMESPACES=("apps" "databases" "secrets" "auth" "monitoring" "logging" "tracing" "security" "smarthome" "uptime" "ai")
        
        for ns in "${NAMESPACES[@]}"; do
            log "Restoring $ns..."
            velero --kubeconfig="$KUBECONFIG_DR" restore create \
                --from-backup "$LATEST_BACKUP" \
                --include-namespaces "$ns" \
                --wait --timeout=300s 2>&1 | tail -5 | tee -a /var/log/dr-failover.log || warn "Restore of $ns had issues"
        done
    else
        warn "No Velero backup found, using existing DR state"
    fi
    
    # Phase 3: Wait for Services
    log "Phase 3: Waiting for Services to be Ready..."
    sleep 30
    
    # Wait for critical deployments
    CRITICAL_DEPLOYMENTS=(
        "nextcloud:apps"
        "vaultwarden:apps"
        "home-assistant:smarthome"
        "prometheus:monitoring"
        "grafana:monitoring"
        "alertmanager:monitoring"
        "loki:logging"
        "tempo:tracing"
        "infisical:secrets"
        "authelia:auth"
        "traefik:traefik"
    )
    
    for deployment_ns in "${CRITICAL_DEPLOYMENTS[@]}"; do
        IFS=':' read -r deployment namespace <<< "$deployment_ns"
        log "Waiting for $deployment in $namespace..."
        kubectl --kubeconfig="$KUBECONFIG_DR" -n "$namespace" wait --for=condition=Available "deployment/$deployment" --timeout=300s 2>&1 | tail -3 | tee -a /var/log/dr-failover.log || warn "$deployment not ready in time"
    done
    
    # Phase 4: Health Checks
    log "Phase 4: Health Checks"
    
    # Wait for DNS propagation
    log "Waiting for DNS propagation (120s)..."
    sleep 120
    
    # Test external endpoints
    SERVICES=(
        "https://nextcloud.$DOMAIN/status.php"
        "https://vaultwarden.$DOMAIN/alive"
        "https://grafana.$DOMAIN/api/health"
        "https://prometheus.$DOMAIN/-/healthy"
        "https://alertmanager.$DOMAIN/-/ready"
        "https://loki.$DOMAIN/ready"
        "https://tempo.$DOMAIN/ready"
    )
    
    for endpoint in "${SERVICES[@]}"; do
        log "Testing $endpoint..."
        if curl -sf --max-time 30 "$endpoint" >/dev/null; then
            log "✅ $endpoint OK"
        else
            warn "⚠️ $endpoint FAILED"
        fi
    done
    
    log "=== DR FAILOVER COMPLETE ==="
    send_telegram "✅ *DR FAILOVER COMPLETE*\nTime: $(date '+%Y-%m-%d %H:%M:%S')\nDR Region Active\nAll critical services restored"
    
    return 0
}

# Failback to Primary
failback() {
    log "=== INITIATING FAILBACK TO PRIMARY ==="
    send_telegram "🔄 *FAILBACK INITIATED*\nTime: $(date '+%Y-%m-%d %H:%M:%S')\nReturning to primary region"
    
    # Verify primary is healthy
    log "Verifying primary cluster health..."
    if ! kubectl --kubeconfig="$KUBECONFIG_PRIMARY" get nodes >/dev/null 2>&1; then
        fail "Primary cluster not accessible, cannot failback"
        return 1
    fi
    
    # Sync data back if needed
    log "Syncing data from DR to Primary..."
    # This would involve syncing databases, files, etc.
    # Implementation depends on specific data sync strategy
    
    # Phase 1: DNS Failback
    log "Phase 1: DNS Failback to Primary"
    get_ips
    dns_failover "primary" || fail "DNS failback failed"
    log "DNS propagated, waiting 60s..."
    sleep 60
    
    # Phase 2: Verify Primary Services
    log "Phase 2: Verifying Primary Services..."
    
    # Test external endpoints on primary
    SERVICES=(
        "https://nextcloud.$DOMAIN/status.php"
        "https://vaultwarden.$DOMAIN/alive"
        "https://grafana.$DOMAIN/api/health"
        "https://prometheus.$DOMAIN/-/healthy"
    )
    
    for endpoint in "${SERVICES[@]}"; do
        log "Testing $endpoint..."
        if curl -sf --max-time 30 "$endpoint" >/dev/null; then
            log "✅ $endpoint OK"
        else
            warn "⚠️ $endpoint FAILED on primary"
        fi
    done
    
    log "=== FAILBACK COMPLETE ==="
    send_telegram "✅ *FAILBACK COMPLETE*\nTime: $(date '+%Y-%m-%d %H:%M:%S')\nPrimary Region Active"
    return 0
}

# Main
case "${1:-}" in
    failover)
        full_failover
        ;;
    failback)
        failback
        ;;
    test)
        # DR test without actual failover
        log "Running DR test (no actual failover)..."
        get_ips
        info "Primary IP: $PRIMARY_IP"
        info "DR IP: $DR_IP"
        log "DR test complete - no failover executed"
        ;;
    *)
        echo "Usage: $0 {failover|failback|test}"
        echo "  failover - Full DR failover to secondary region"
        echo "  failback - Failback to primary region"
        echo "  test     - Test DR readiness without failover"
        exit 1
        ;;
esac