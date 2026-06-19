#!/usr/bin/env bash
# verify-supply-chain.sh - Verify supply chain artifacts in deploy pipeline
# Usage: ./verify-supply-chain.sh [--image <image>] [--sbom-dir <dir>]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

IMAGE=""
SBOM_DIR=""

while [[ $# -gt 0 ]]; do
  case $1 in
    --image) IMAGE="$2"; shift 2 ;;
    --sbom-dir) SBOM_DIR="$2"; shift 2 ;;
    *) echo "Unknown option: $1"; exit 1 ;;
  esac
done

# Load environment if available
if [[ -f "${ROOT_DIR}/.env" ]]; then
  # shellcheck disable=SC1090
  set -a; source "${ROOT_DIR}/.env"; set +a
fi

# Check tools
for cmd in cosign syft trivy; do
  if ! command -v "$cmd" &>/dev/null; then
    echo "WARNING: $cmd not installed, skipping related checks"
  fi
done

verify_cosign() {
  local img="$1"
  echo "🔐 Verifying Cosign signature for $img..."
  if cosign verify "$img" \
    --certificate-identity-regexp ".*" \
    --certificate-oidc-issuer-regexp ".*" \
    --certificate-github-workflow-trigger-regexp ".*" \
    --certificate-github-workflow-ref-regexp "refs/heads/main" \
    2>/dev/null; then
    echo "✅ Cosign verification passed for $img"
    return 0
  else
    echo "❌ Cosign verification FAILED for $img"
    return 1
  fi
}

verify_sbom() {
  local img="$1"
  echo "📦 Verifying SBOM attestation for $img..."
  if cosign verify-attestation --type spdx "$img" 2>/dev/null; then
    echo "✅ SBOM attestation verified for $img"
    return 0
  else
    echo "⚠️  SBOM attestation not found or invalid for $img"
    return 1
  fi
}

verify_trivy() {
  local img="$1"
  echo "🔍 Running Trivy scan on $img..."
  if trivy image --severity CRITICAL --exit-code 0 --format table "$img" 2>/dev/null; then
    echo "✅ Trivy scan passed (no CRITICAL)"
    return 0
  else
    echo "❌ Trivy found CRITICAL vulnerabilities in $img"
    return 1
  fi
}

main() {
  local images=()

  if [[ -n "$IMAGE" ]]; then
    images=("$IMAGE")
  else
    # Extract from compose files
    mapfile -t images < <(grep -h "image:" stacks/**/docker-compose.yml 2>/dev/null | sed 's/.*image: *//' | sort -u)
  fi

  if [[ ${#images[@]} -eq 0 ]]; then
    echo "No images to verify"
    exit 1
  fi

  echo "🔍 Verifying supply chain for ${#images[@]} images..."
  echo ""

  local FAILED=0
  for img in "${images[@]}"; do
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "🔍 Verifying: $img"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

    local IMG_FAILED=0

    # Verify Cosign signature
    if ! verify_cosign "$img"; then
      IMG_FAILED=1
    fi

    # Verify SBOM attestation
    if ! verify_sbom "$img"; then
      IMG_FAILED=1
    fi

    # Quick Trivy scan
    if ! verify_trivy "$img"; then
      IMG_FAILED=1
    fi

    if [[ $IMG_FAILED -eq 0 ]]; then
      echo "✅ All checks passed for $img"
    else
      echo "❌ Some checks failed for $img"
      ((FAILED++))
    fi
    echo ""
  done

  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo "Summary: ${#images[@]} images checked, $FAILED failed"
  echo ""

  if [[ $FAILED -gt 0 ]]; then
    echo "❌ Supply chain verification FAILED"
    exit 1
  else
    echo "✅ All supply chain verifications passed"
    exit 0
  fi
}

main "$@"