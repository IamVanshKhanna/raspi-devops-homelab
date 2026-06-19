#!/usr/bin/env bash
# restore-test.sh - Automated restore test for CI/CD
# Run weekly via cron or GitHub Actions to verify backup integrity
# Usage: ./restore-test.sh [--snapshot latest] [--target /mnt/restore-test]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
ENV_FILE="${ROOT_DIR}/.env"

# Load environment
if [[ -f "$ENV_FILE" ]]; then
  # shellcheck disable=SC1090
  set -a; source "$ENV_FILE"; set +a
else
  echo "ERROR: .env not found at $ENV_FILE" >&2
  exit 1
fi

# Required
: "${RESTIC_REPOSITORY:?RESTIC_REPOSITORY not set}"
: "${RESTIC_PASSWORD:?RESTIC_PASSWORD not set}"
: "${B2_ACCOUNT_ID:?B2_ACCOUNT_ID not set}"
: "${B2_ACCOUNT_KEY:?B2_ACCOUNT_KEY not set}"

# Optional args
SNAPSHOT="${1:-latest}"
RESTORE_TARGET="${2:-/mnt/restore-test}"

export RESTIC_REPOSITORY
export RESTIC_PASSWORD
export B2_ACCOUNT_ID
export B2_ACCOUNT_KEY

echo "=== Restore Test Started: $(date -Is) ==="
echo "Repository: $RESTIC_REPOSITORY"
echo "Snapshot: $SNAPSHOT"
echo "Target: $RESTORE_TARGET"

# Verify repo access
echo "Verifying repository access..."
restic snapshots --latest 1 | grep -q "snapshot" || {
  echo "ERROR: No snapshots found"
  exit 1
}

# Get snapshot ID
if [[ "$SNAPSHOT" == "latest" ]]; then
  SNAPSHOT_ID=$(restic snapshots --latest 1 --json | jq -r '.[0].short_id')
else
  SNAPSHOT_ID="$SNAPSHOT"
fi

echo "Using snapshot: $SNAPSHOT_ID"

# Clean target
rm -rf "$RESTORE_TARGET"
mkdir -p "$RESTORE_TARGET"

# Restore
echo "Restoring snapshot $SNAPSHOT_ID to $RESTORE_TARGET..."
restic restore "$SNAPSHOT_ID" --target "$RESTORE_TARGET"

# Verify key files exist
echo "Verifying restored files..."
KEY_FILES=(
  "$RESTORE_TARGET/home/vansh/homelab-prod/.env.example"
  "$RESTORE_TARGET/home/vansh/homelab-prod/Makefile"
  "$RESTORE_TARGET/home/vansh/homelab-prod/README.md"
)

for f in "${KEY_FILES[@]}"; do
  if [[ -f "$f" ]]; then
    echo "✓ Found: $f"
  else
    echo "✗ MISSING: $f"
    exit 1
  fi
done

# Check data directories
DATA_DIRS=(
  "$RESTORE_TARGET/mnt/data/nextcloud/userdata"
  "$RESTORE_TARGET/mnt/data/vaultwarden"
)

for d in "${DATA_DIRS[@]}"; do
  if [[ -d "$d" ]]; then
    echo "✓ Data dir exists: $d"
  else
    echo "⚠ Data dir missing (may be empty): $d"
  fi
done

# Cleanup
echo "Cleaning up test restore..."
rm -rf "$RESTORE_TARGET"

echo "=== Restore Test PASSED: $(date -Is) ==="
exit 0