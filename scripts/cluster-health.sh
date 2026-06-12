#!/usr/bin/env bash
# cluster-health.sh - Comprehensive cluster health check for K3s
# Usage: ./cluster-health.sh [--json] [--strict]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
JSON_OUTPUT=false
STRICT=false

for arg in "$@"; do
    case $arg in
        --json) JSON_OUTPUT=true ;;
        --strict) STRICT=true ;;
    esac
done

check_k3s() {
    local issues=0
    local warnings=0
    
    # Check k3s service
    if systemctl is-active --quiet k3s; then
        log "k3s service: active"
    else
        fail "k3s service: inactive" && ((issues++))
    fi
    
    # Check node readiness
    local ready_nodes=$(kubectl get nodes --no-headers 2>/dev/null | grep -c " Ready " || echo 0)
    local total_nodes=$(kubectl get nodes --no-headers 2>/dev/null | wc -l | xargs)
    if [ "$ready_nodes" -eq "$total_nodes" ] && [ "$total_nodes" -gt 0 ]; then
        log "Nodes: $ready_nodes/$total_nodes Ready"
    else
        fail "Nodes: $ready_nodes/$total_nodes Ready" && ((issues++))
    fi
    
    # Check system pods
    local not_ready=$(kubectl get pods -n kube-system --no-headers 2>/dev/null | grep -v "Running\|Completed" | wc -l | xargs)
    if [ "$not_ready" -eq 0 ]; then
        log "kube-system pods: all Running"
    else
        warn "kube-system pods: $not_ready not ready" && ((warnings++))
    fi
    
    # Check ArgoCD
    if kubectl get namespace argocd >/dev/null 2>&1; then
        local argocd_ready=$(kubectl get pods -n argocd --no-headers 2>/dev/null | grep -c "Running" || echo 0)
        local argocd_total=$(kubectl get pods -n argocd --no-headers 2>/dev/null | wc -l | xargs)
        if [ "$argocd_ready" -eq "$argocd_total" ] && [ "$argocd_total" -gt 0 ]; then
            log "ArgoCD: $argocd_ready/$argocd_total pods Ready"
        else
            warn "ArgoCD: $argocd_ready/$argocd_total pods Ready" && ((warnings++))
        fi
    fi
    
    # Check Longhorn
    if kubectl get namespace longhorn-system >/dev/null 2>&1; then
        local lh_ready=$(kubectl get pods -n longhorn-system --no-headers 2>/dev/null | grep -c "Running" || echo 0)
        local lh_total=$(kubectl get pods -n longhorn-system --no-headers 2>/dev/null | wc -l | xargs)
        if [ "$lh_ready" -eq "$lh_total" ] && [ "$lh_total" -gt 0 ]; then
            log "Longhorn: $lh_ready/$lh_total pods Ready"
        else
            warn "Longhorn: $lh_ready/$lh_total pods Ready" && ((warnings++))
        fi
    fi
    
    # Check Cert Manager
    if kubectl get namespace cert-manager >/dev/null 2>&1; then
        local cm_ready=$(kubectl get pods -n cert-manager --no-headers 2>/dev/null | grep -c "Running" || echo 0)
        local cm_total=$(kubectl get pods -n cert-manager --no-headers 2>/dev/null | wc -l | xargs)
        if [ "$cm_ready" -eq "$cm_total" ] && [ "$cm_total" -gt 0 ]; then
            log "Cert-Manager: $cm_ready/$cm_total pods Ready"
        else
            warn "Cert-Manager: $cm_ready/$cm_total pods Ready" && ((warnings++))
        fi
    fi
    
    # Check PVCs
    local pending_pvcs=$(kubectl get pvc --all-namespaces --no-headers 2>/dev/null | grep -c "Pending" || echo 0)
    if [ "$pending_pvcs" -eq 0 ]; then
        log "PVCs: all Bound"
    else
        warn "PVCs: $pending_pvcs Pending" && ((warnings++))
    fi
    
    # Check Longhorn volumes
    if kubectl get namespace longhorn-system >/dev/null 2>&1; then
        local degraded=$(kubectl exec -n longhorn-system deploy/longhorn-manager -- longhornctl volume list -o json 2>/dev/null | jq -r '.data[] | select(.state=="degraded" or .state=="faulted") | .name' 2>/dev/null | wc -l | xargs || echo 0)
        if [ "$degraded" -eq 0 ]; then
            log "Longhorn volumes: all Healthy"
        else
            fail "Longhorn volumes: $degraded degraded" && ((issues++))
        fi
    fi
    
    if $JSON_OUTPUT; then
        echo "{\"issues\": $issues, \"warnings\": $warnings}"
    fi
    
    if [ $issues -gt 0 ]; then
        exit 1
    elif [ $warnings -gt 0 ] && $STRICT; then
        exit 1
    fi
    exit 0
}

log() { echo "[OK] $1"; }
warn() { echo "[WARN] $1"; }
fail() { echo "[FAIL] $1"; }

check_k3s