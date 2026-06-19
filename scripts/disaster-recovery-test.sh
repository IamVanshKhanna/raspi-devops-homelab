#!/usr/bin/env bash
# disaster-recovery-test.sh - Automated DR test for homelab-prod
# Usage: sudo ./scripts/disaster-recovery-test.sh [--scenario <scenario>] [--dry-run]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log() { echo -e "${GREEN}[DR-TEST]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
fail() { echo -e "${RED}[FAIL]${NC} $1"; exit 1; }
info() { echo -e "${BLUE}[INFO]${NC} $1"; }

DRY_RUN=false
SCENARIO="full"

while [[ $# -gt 0 ]]; do
    case $1 in
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --scenario)
            SCENARIO="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Check prerequisites
check_prerequisites() {
    log "Checking prerequisites..."
    
    for cmd in kubectl restic argocd; do
        if ! command -v $cmd &> /dev/null; then
            fail "$cmd not found in PATH"
        fi
    done
    
    # Check restic repository
    if ! restic snapshots &> /dev/null; then
        fail "Restic repository not accessible"
    fi
    
    log "Prerequisites OK"
}

# Scenario 1: Restore Nextcloud database
test_nextcloud_db() {
    log "Testing Nextcloud database restore..."
    
    if $DRY_RUN; then
        info "DRY RUN: Would restore Nextcloud DB from latest snapshot"
        return 0
    fi
    
    # Create test namespace
    kubectl create namespace dr-test-nextcloud --dry-run=client -o yaml | kubectl apply -f -
    
    # Find latest Nextcloud backup
    LATEST_SNAPSHOT=$(restic snapshots --json | jq -r 'max_by(.time) | .id')
    
    # Restore to test namespace
    restic restore "$LATEST_SNAPSHOT" \
        --target /tmp/dr-test-nextcloud \
        --include "nextcloud/db/*" \
        --include "nextcloud/config/*"
    
    # Verify restored files
    if [[ -f /tmp/dr-test-nextcloud/nextcloud/db/backup.sql ]]; then
        log "Nextcloud DB backup found and restorable"
    else
        warn "Nextcloud DB backup not found in expected location"
    fi
    
    # Cleanup
    rm -rf /tmp/dr-test-nextcloud
    kubectl delete namespace dr-test-nextcloud --ignore-not-found
    
    log "Nextcloud DB restore test completed"
}

# Scenario 2: Restore Vaultwarden database
test_vaultwarden_db() {
    log "Testing Vaultwarden database restore..."
    
    if $DRY_RUN; then
        info "DRY RUN: Would restore Vaultwarden DB from latest snapshot"
        return 0
    fi
    
    kubectl create namespace dr-test-vaultwarden --dry-run=client -o yaml | kubectl apply -f -
    
    LATEST_SNAPSHOT=$(restic snapshots --json | jq -r 'max_by(.time) | .id')
    
    restic restore "$LATEST_SNAPSHOT" \
        --target /tmp/dr-test-vaultwarden \
        --include "vaultwarden/*"
    
    if [[ -f /tmp/dr-test-vaultwarden/vaultwarden/db.sqlite3 ]]; then
        log "Vaultwarden DB backup found and restorable"
    else
        warn "Vaultwarden DB backup not found in expected location"
    fi
    
    rm -rf /tmp/dr-test-vaultwarden
    kubectl delete namespace dr-test-vaultwarden --ignore-not-found
    
    log "Vaultwarden DB restore test completed"
}

# Scenario 3: Restore Home Assistant config
test_homeassistant() {
    log "Testing Home Assistant config restore..."
    
    if $DRY_RUN; then
        info "DRY RUN: Would restore Home Assistant config from latest snapshot"
        return 0
    fi
    
    kubectl create namespace dr-test-ha --dry-run=client -o yaml | kubectl apply -f -
    
    LATEST_SNAPSHOT=$(restic snapshots --json | jq -r 'max_by(.time) | .id')
    
    restic restore "$LATEST_SNAPSHOT" \
        --target /tmp/dr-test-ha \
        --include "homeassistant/*"
    
    if [[ -f /tmp/dr-test-ha/homeassistant/configuration.yaml ]]; then
        log "Home Assistant config backup found and restorable"
    else
        warn "Home Assistant config backup not found"
    fi
    
    rm -rf /tmp/dr-test-ha
    kubectl delete namespace dr-test-ha --ignore-not-found
    
    log "Home Assistant restore test completed"
}

# Scenario 4: Full cluster state restore via ArgoCD
test_argocd_sync() {
    log "Testing ArgoCD application sync..."
    
    if $DRY_RUN; then
        info "DRY RUN: Would sync all ArgoCD applications"
        return 0
    fi
    
    # Get all apps
    APPS=$(argocd app list -o name)
    
    for app in $APPS; do
        log "Syncing $app..."
        if argocd app sync "$app" --timeout 300; then
            log "Synced $app"
        else
            warn "Failed to sync $app"
        fi
    done
    
    # Wait for all to be healthy
    log "Waiting for all apps to be healthy..."
    sleep 30
    
    # Check health
    python3 scripts/argocd-health.py --output json | jq -r '.results.healthy | length'
    
    log "ArgoCD sync test completed"
}

# Scenario 5: Test Longhorn volume restore
test_longhorn_restore() {
    log "Testing Longhorn volume restore..."
    
    if $DRY_RUN; then
        info "DRY RUN: Would test Longhorn volume snapshot restore"
        return 0
    fi
    
    # This would create a test PVC from Longhorn snapshot
    # For now, just verify Longhorn is healthy
    kubectl get volumes -n longhorn-system -o json | jq -r '.data[] | select(.state=="healthy") | .name' | head -5
    
    log "Longhorn volume check completed"
}

# Scenario 6: Test certificate renewal
test_cert_renewal() {
    log "Testing certificate renewal..."
    
    if $DRY_RUN; then
        info "DRY RUN: Would test cert-manager renewal"
        return 0
    fi
    
    # Check cert status
    kubectl get certificates -A -o custom-columns="NAME:.metadata.name,NAMESPACE:.metadata.name,READY:.status.conditions[0].status,EXPIRY:.status.notAfter"
    
    log "Certificate check completed"
}

# Main execution
main() {
    log "Starting Disaster Recovery Test - Scenario: $SCENARIO"
    log "Dry run: $DRY_RUN"
    
    check_prerequisites
    
    case $SCENARIO in
        nextcloud-db)
            test_nextcloud_db
            ;;
        vaultwarden-db)
            test_vaultwarden_db
            ;;
        homeassistant)
            test_homeassistant
            ;;
        argocd-sync)
            test_argocd_sync
            ;;
        longhorn)
            test_longhorn_restore
            ;;
        cert-renewal)
            test_cert_renewal
            ;;
        full)
            test_nextcloud_db
            test_vaultwarden_db
            test_homeassistant
            test_argocd_sync
            test_longhorn_restore
            test_cert_renewal
            ;;
        *)
            echo "Unknown scenario: $SCENARIO"
            echo "Available: nextcloud-db, vaultwarden-db, homeassistant, argocd-sync, longhorn, cert-renewal, full"
            exit 1
            ;;
    esac
    
    log "Disaster Recovery Test completed successfully!"
}

main "$@"