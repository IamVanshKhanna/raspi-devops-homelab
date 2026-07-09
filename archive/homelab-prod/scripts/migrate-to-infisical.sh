#!/usr/bin/env bash
# migrate-to-infisical.sh - Migrate .env secrets to Infisical
# Run after Infisical is deployed and configured

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
ENV_FILE="${ROOT_DIR}/.env"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "ERROR: .env not found at $ENV_FILE"
  exit 1
fi

echo "Checking Infisical CLI..."
if ! command -v infisical &>/dev/null; then
  echo "Installing Infisical CLI..."
  curl -sSfL https://raw.githubusercontent.com/Infisical/infisical/main/install.sh | sh
fi

# Check if logged in
if ! infisical user get &>/dev/null; then
  echo "Please login to Infisical first:"
  echo "  infisical login"
  exit 1
fi

# Get project ID
PROJECT_ID="${INFISICAL_PROJECT_ID:-}"
if [[ -z "$PROJECT_ID" ]]; then
  echo "Available projects:"
  infisical project list
  read -rp "Enter Infisical Project ID: " PROJECT_ID
fi

ENV_SLUG="${INFISICAL_ENV:-production}"

echo "Migrating secrets from .env to Infisical (project: $PROJECT_ID, env: $ENV_SLUG)..."

# Parse .env and push to Infisical
# Skip comments, empty lines, and already-migrated keys
MIGRATED=0
SKIPPED=0

while IFS= read -r line; do
  # Skip comments and empty lines
  [[ "$line" =~ ^[[:space:]]*# ]] && continue
  [[ -z "${line// }" ]] && continue

  # Parse KEY=VALUE
  if [[ "$line" =~ ^([A-Z_][A-Z0-9_]*)=(.*)$ ]]; then
    KEY="${BASH_REMATCH[1]}"
    VALUE="${BASH_REMATCH[2]}"
    
    # Remove surrounding quotes if present
    VALUE="${VALUE%\"}"
    VALUE="${VALUE#\"}"
    VALUE="${VALUE%\'}"
    VALUE="${VALUE#\'}"

    # Skip placeholder values
    if [[ "$VALUE" =~ ^change_|^your_|^replacethis ]]; then
      echo "  ⏭ Skipping placeholder: $KEY"
      ((SKIPPED++))
      continue
    fi

    # Check if already exists in Infisical
    if infisical secrets get --projectId="$PROJECT_ID" --env="$ENV_SLUG" --key="$KEY" &>/dev/null; then
      echo "  ⏭ Already exists: $KEY"
      ((SKIPPED++))
      continue
    fi

    echo "  📤 Migrating: $KEY"
    if infisical secrets set --projectId="$PROJECT_ID" --env="$ENV_SLUG" --key="$KEY" --value="$VALUE"; then
      ((MIGRATED++))
    else
      echo "  ❌ Failed: $KEY"
    fi
  fi
done < "$ENV_FILE"

echo ""
echo "Migration complete:"
echo "  Migrated: $MIGRATED"
echo "  Skipped:  $SKIPPED"
echo ""
echo "Next steps:"
echo "1. Verify secrets in Infisical UI: https://infisical.yourdomain.com"
echo "2. Update deploy to use: infisical run --projectId=... --env=production -- docker compose up -d"
echo "3. Remove secrets from .env (keep only Infisical config vars)"
echo "4. Update CI/CD to use Infisical CLI for secret injection"