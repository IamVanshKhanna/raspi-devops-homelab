#!/usr/bin/env bash
# secrets-rotation.sh - Automated secrets rotation for homelab
# Schedule: 0 3 * * 0 /home/vansh/homelab-prod/scripts/secrets-rotation.sh >> /var/log/secrets-rotation.log 2>&1

set -euo pipefail

# Configuration
INFISICAL_URL="${INFISICAL_URL:-https://infisical.homelab.local}"
INFISICAL_PROJECT_ID="${INFISICAL_PROJECT_ID}"
INFISICAL_TOKEN="${INFISICAL_TOKEN}"
ROTATION_DAYS="${ROTATION_DAYS:-90}"
DRY_RUN="${DRY_RUN:-false}"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

log() { echo -e "${GREEN}[SECRETS-ROTATION]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
fail() { echo -e "${RED}[FAIL]${NC} $1"; exit 1; }

# Check prerequisites
[[ -n "$INFISICAL_PROJECT_ID" ]] || fail "INFISICAL_PROJECT_ID not set"
[[ -n "$INFISICAL_TOKEN" ]] || fail "INFISICAL_TOKEN not set"
command -v infisical >/dev/null || fail "infisical CLI not installed"
command -v kubectl >/dev/null || fail "kubectl not installed"

log "Starting secrets rotation (dry-run: $DRY_RUN)"

# Get all secrets from Infisical
log "Fetching secrets from Infisical..."
SECRETS=$(infisical secrets --projectId="$INFISICAL_PROJECT_ID" --env=production --plain --token="$INFISICAL_TOKEN" 2>/dev/null || fail "Failed to fetch secrets")

# Parse secrets and check age
echo "$SECRETS" | while IFS='=' read -r key value; do
    [[ -z "$key" ]] && continue

    # Get secret metadata (last rotated)
    METADATA=$(infisical secret get "$key" --projectId="$INFISICAL_PROJECT_ID" --env=production --metadata --token="$INFISICAL_TOKEN" 2>/dev/null || true)
    LAST_ROTATED=$(echo "$METADATA" | grep -o '"updatedAt":"[^"]*"' | cut -d'"' -f4)

    if [[ -n "$LAST_ROTATED" ]]; then
        LAST_EPOCH=$(date -d "$LAST_ROTATED" +%s 2>/dev/null || date -j -f "%Y-%m-%dT%H:%M:%S" "$LAST_ROTATED" +%s 2>/dev/null)
        NOW_EPOCH=$(date +%s)
        AGE_DAYS=$(( (NOW_EPOCH - LAST_EPOCH) / 86400 ))

        if [[ $AGE_DAYS -ge $ROTATION_DAYS ]]; then
            log "Secret $key is $AGE_DAYS days old (threshold: $ROTATION_DAYS) - rotating..."

            # Generate new secret based on type
            NEW_VALUE=""
            case "$key" in
                *PASSWORD*|*SECRET*|*TOKEN*|*KEY*)
                    NEW_VALUE=$(openssl rand -base64 32)
                    ;;
                *DB_PASSWORD*|*POSTGRES_PASSWORD*|*REDIS_PASSWORD*)
                    NEW_VALUE=$(openssl rand -base64 24)
                    ;;
                *JWT_SECRET*|*ENCRYPTION_KEY*)
                    NEW_VALUE=$(openssl rand -base64 48)
                    ;;
                *)
                    warn "Unknown secret type for $key, skipping auto-generation"
                    continue
                    ;;
            esac

            if [[ -n "$NEW_VALUE" ]]; then
                if [[ "$DRY_RUN" == "true" ]]; then
                    log "[DRY-RUN] Would rotate $key"
                else
                    # Update in Infisical
                    infisical secret set "$key=$NEW_VALUE" --projectId="$INFISICAL_PROJECT_ID" --env=production --token="$INFISICAL_TOKEN" \
                        && log "Rotated $key in Infisical" \
                        || fail "Failed to rotate $key in Infisical"

                    # Trigger reload in Kubernetes
                    log "Triggering reload for workloads using $key..."
                    kubectl rollout restart deployment -l infisical.secret="$key" --all-namespaces 2>/dev/null || true
                fi
            fi
        else
            log "Secret $key is $AGE_DAYS days old - not due for rotation"
        fi
    fi
done

# Rotate TLS certificates (Cert-Manager handles this automatically, but we can verify)
log "Checking TLS certificate expiry..."
kubectl get certificates -A -o jsonpath='{range .items[*]}{.metadata.namespace}{"\t"}{.metadata.name}{"\t"}{.status.notAfter}{"\n"}{end}' 2>/dev/null | \
while read ns name expiry; do
    [[ -z "$expiry" ]] && continue
    EXPIRY_EPOCH=$(date -d "$expiry" +%s 2>/dev/null || date -j -f "%Y-%m-%dT%H:%M:%SZ" "$expiry" +%s 2>/dev/null)
    NOW_EPOCH=$(date +%s)
    DAYS_LEFT=$(( (EXPIRY_EPOCH - NOW_EPOCH) / 86400 ))

    if [[ $DAYS_LEFT -le 30 ]]; then
        warn "Certificate $name in $ns expires in $DAYS_LEFT days"
    fi
done

log "Secrets rotation complete"