#!/usr/bin/env bash
# replicate-restic.sh - Cross-region Restic replication via rclone
# Schedule: Daily via systemd timer or GitHub Actions

set -euo pipefail

# Configuration
RCLONE_CONFIG="${RCLONE_CONFIG:-/home/vansh/.config/rclone/rclone.conf}"
B2_ACCOUNT_ID="${B2_ACCOUNT_ID}"
B2_ACCOUNT_KEY="${B2_ACCOUNT_KEY}"
AWS_ACCESS_KEY_ID="${AWS_ACCESS_KEY_ID}"
AWS_SECRET_ACCESS_KEY="${AWS_SECRET_ACCESS_KEY}"
S3_BUCKET="${S3_BUCKET:-homelab-backups-dr}"
GCS_BUCKET="${GCS_BUCKET:-homelab-backups-dr}"
RCLONE_BWLIMIT="${RCLONE_BWLIMIT:-50M}"
RCLONE_TRANSFERS="${RCLONE_TRANSFERS:-4}"
RCLONE_CHECKERS="${RCLONE_CHECKERS:-8}"
RCLONE_RETRIES="${RCLONE_RETRIES:-3}"
RCLONE_LOG_LEVEL="${RCLONE_LOG_LEVEL:-INFO}"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log() { echo -e "${GREEN}[RCLONE-REPLICATE]${NC} $1" | tee -a /var/log/rclone-replicate.log; }
info() { echo -e "${BLUE}[INFO]${NC} $1" | tee -a /var/log/rclone-replicate.log; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1" | tee -a /var/log/rclone-replicate.log; }
fail() { echo -e "${RED}[FAIL]${NC} $1" | tee -a /var/log/rclone-replicate.log; }

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

# Check rclone configuration
check_rclone_config() {
    log "Checking rclone configuration..."
    
    if [[ ! -f "$RCLONE_CONFIG" ]]; then
        warn "Rclone config not found at $RCLONE_CONFIG"
        return 1
    fi
    
    # Check required remotes
    REQUIRED_REMOTES=("b2-primary" "s3-dr" "gcs-dr")
    for remote in "${REQUIRED_REMOTES[@]}"; do
        if ! rclone --config "$RCLONE_CONFIG" listremotes | grep -q "^${remote}:$"; then
            warn "Remote '$remote' not configured in rclone"
            return 1
        fi
    done
    
    log "✅ Rclone configuration valid"
    return 0
}

# Replicate a single repository
replicate_repo() {
    local repo=$1
    local src="b2-primary:$repo"
    local dst_s3="s3-dr:${repo}-dr"
    local dst_gcs="gcs-dr:${repo}-dr"
    
    log "=== Replicating $repo ==="
    
    local start_time=$(date +%s)
    local failed=0
    
    # Replicate to AWS S3
    log "Replicating $repo to AWS S3..."
    if rclone --config "$RCLONE_CONFIG" sync \
        --progress \
        --transfers "$RCLONE_TRANSFERS" \
        --checkers "$RCLONE_CHECKERS" \
        --retries "$RCLONE_RETRIES" \
        --low-level-retries 10 \
        --bwlimit "$RCLONE_BWLIMIT" \
        --stats 1m \
        --stats-one-line \
        --log-level "$RCLONE_LOG_LEVEL" \
        --log-file "/var/log/rclone-s3-${repo}-$(date +%Y%m%d).log" \
        "$src" "$dst_s3"; then
        log "✅ $repo → S3 replication successful"
    else
        warn "❌ $repo → S3 replication failed"
        failed=$((failed + 1))
    fi
    
    # Replicate to GCS
    log "Replicating $repo to GCS..."
    if rclone --config "$RCLONE_CONFIG" sync \
        --progress \
        --transfers "$RCLONE_TRANSFERS" \
        --checkers "$RCLONE_CHECKERS" \
        --retries "$RCLONE_RETRIES" \
        --low-level-retries 10 \
        --bwlimit "$RCLONE_BWLIMIT" \
        --stats 1m \
        --stats-one-line \
        --log-level "$RCLONE_LOG_LEVEL" \
        --log-file "/var/log/rclone-gcs-${repo}-$(date +%Y%m%d).log" \
        "$src" "$dst_gcs"; then
        log "✅ $repo → GCS replication successful"
    else
        warn "❌ $repo → GCS replication failed"
        failed=$((failed + 1))
    fi
    
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))
    
    if [[ $failed -eq 0 ]]; then
        log "✅ $repo replication completed in ${duration}s"
        return 0
    else
        warn "❌ $repo replication had $failed failures"
        return 1
    fi
}

# Verify replication by comparing object counts
verify_replication() {
    local repo=$1
    local src="b2-primary:$repo"
    local dst_s3="s3-dr:${repo}-dr"
    local dst_gcs="gcs-dr:${repo}-dr"
    
    log "=== Verifying $repo replication ==="
    
    local b2_count=$(rclone --config "$RCLONE_CONFIG" lsf "$src" --files-only 2>/dev/null | wc -l)
    local s3_count=$(rclone --config "$RCLONE_CONFIG" lsf "$dst_s3" --files-only 2>/dev/null | wc -l)
    local gcs_count=$(rclone --config "$RCLONE_CONFIG" lsf "$dst_gcs" --files-only 2>/dev/null | wc -l)
    
    info "  B2 (source): $b2_count objects"
    info "  S3 (dest):   $s3_count objects"
    info "  GCS (dest):  $gcs_count objects"
    
    local match=true
    if [[ "$b2_count" -eq "$s3_count" && "$b2_count" -eq "$gcs_count" ]]; then
        log "✅ Object counts match across all regions ($b2_count objects)"
        return 0
    else
        warn "⚠️ Object count mismatch: B2=$b2_count, S3=$s3_count, GCS=$gcs_count"
        return 1
    fi
}

# Main replication function
main() {
    log "=== Starting Restic Cross-Region Replication at $(date) ==="
    send_telegram "☁️ *Restic Cross-Region Replication Started*\nTime: $(date '+%Y-%m-%d %H:%M:%S')"
    
    # Check prerequisites
    if ! command -v rclone >/dev/null 2>&1; then
        fail "rclone not installed"
        exit 1
    fi
    
    if ! check_rclone_config; then
        fail "Rclone configuration check failed"
        exit 1
    fi
    
    # Repositories to replicate
    REPOS=(
        "homelab-backups"
        "homelab-velero"
        "homelab-loki"
        "homelab-thanos"
    )
    
    local total_failed=0
    local start_time=$(date +%s)
    
    # Replicate each repository
    for repo in "${REPOS[@]}"; do
        replicate_repo "$repo" || {
            warn "Repository $repo replication failed"
        }
    done
    
    # Verify all replications
    local verify_failed=0
    for repo in "${REPOS[@]}"; do
        verify_replication "$repo" || verify_failed=$((verify_failed + 1))
    done
    
    local end_time=$(date +%s)
    local total_duration=$((end_time - start_time))
    
    # Summary
    log "=== Replication Summary ==="
    info "Duration: ${total_duration}s ($(echo "scale=2; $total_duration/60" | bc) minutes)"
    
    if [[ $verify_failed -eq 0 ]]; then
        log "✅ All replications completed and verified successfully"
        send_telegram "☁️ *Restic Cross-Region Replication COMPLETE*\nTime: $(date '+%Y-%m-%d %H:%M:%S')\nDuration: ${total_duration}s\nAll regions verified"
        exit 0
    else
        warn "⚠️ Replication completed with verification failures"
        send_telegram "⚠️ *Restic Cross-Region Replication - VERIFICATION ISSUES*\nTime: $(date '+%Y-%m-%d %H:%M:%S')\nSome regions failed verification"
        exit 1
    fi
}

# Run main
main "$@"