#!/usr/bin/env bash
# argo-app-sync.sh - Sync ArgoCD applications selectively
# Usage: ./argo-app-sync.sh [--app <app-name>] [--all] [--dry-run]

set -euo pipefail

ARGOCD_SERVER="${ARGOCD_SERVER:-argocd.homelab.local}"
ARGOCD_AUTH_TOKEN="${ARGOCD_AUTH_TOKEN:-$ARGOCD_TOKEN}"
NAMESPACE="${ARGOCD_NAMESPACE:-argocd}"

sync_app() {
    local app=$1
    local dry_run=$2
    
    echo "Syncing $app..."
    if [ "$dry_run" = "true" ]; then
        argocd app sync "$app" --dry-run --server "$ARGOCD_SERVER" --auth-token "$ARGOCD_AUTH_TOKEN"
    else
        argocd app sync "$app" --server "$ARGOCD_SERVER" --auth-token "$ARGOCD_AUTH_TOKEN"
    fi
}

main() {
    local dry_run=false
    local apps=()
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            --app)
                apps+=("$2")
                shift 2
                ;;
            --all)
                apps=("all")
                shift
                ;;
            --dry-run)
                dry_run=true
                shift
                ;;
            *)
                echo "Unknown option: $1"
                exit 1
                ;;
        esac
    done
    
    if [ ${#apps[@]} -eq 0 ] || [[ "${apps[0]}" == "all" ]]; then
        # Get all apps
        mapfile -t apps < <(argocd app list -o name --server "$ARGOCD_SERVER" --auth-token "$ARGOCD_AUTH_TOKEN")
    fi
    
    for app in "${apps[@]}"; do
        sync_app "$app" "$dry_run"
    done
}

main "$@"