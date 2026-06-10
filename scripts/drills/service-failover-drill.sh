#!/usr/bin/env bash
# service-failover-drill.sh - Test service failover scenarios
# Usage: ./service-failover-drill.sh [service-name]

set -euo pipefail

KUBECONFIG="/etc/rancher/k3s/k3s.yaml"
SERVICE="${1:-}"

log() { echo -e "\033[0;32m[FAILOVER] $1\033[0m"; }
warn() { echo -e "\033[1;33m[WARN] $1\033[0m"; }
fail() { echo -e "\033[0;31m[FAIL] $1\033[0m"; exit 1; }

test_service_failover() {
    local service_name=$1
    local namespace=$2
    local label_selector=$3
    
    log "Testing failover for $service_name in $namespace"
    
    # Get current pods
    PODS=$(kubectl --kubeconfig="$KUBECONFIG" get pods -n "$namespace" -l "$label_selector" -o jsonpath='{.items[*].metadata.name}' 2>/dev/null || echo "")
    
    if [[ -z "$PODS" ]]; then
        warn "No pods found for $service_name"
        return 1
    fi
    
    FIRST_POD=$(echo $PODS | awk '{print $1}')
    log "Current pod: $FIRST_POD"
    
    # Check if deployment has multiple replicas
    REPLICAS=$(kubectl --kubeconfig="$KUBECONFIG" get deployment -n "$namespace" -l "$label_selector" -o jsonpath='{.items[0].spec.replicas}' 2>/dev/null || echo "1")
    
    if [[ "$REPLICAS" -eq 1 ]]; then
        warn "Only 1 replica - testing pod recreation (not true failover)"
    fi
    
    # Delete pod
    log "Deleting pod: $FIRST_POD"
    kubectl --kubeconfig="$KUBECONFIG" delete pod "$FIRST_POD" -n "$namespace" --wait=false
    
    # Wait for new pod
    log "Waiting for new pod to be ready..."
    local timeout=120
    local elapsed=0
    while [[ $elapsed -lt $timeout ]]; do
        NEW_PODS=$(kubectl --kubeconfig="$KUBECONFIG" get pods -n "$namespace" -l "$label_selector" --field-selector=status.phase=Running -o jsonpath='{.items[*].metadata.name}' 2>/dev/null || echo "")
        if [[ -n "$NEW_PODS" ]] && [[ "$NEW_PODS" != *"$FIRST_POD"* ]]; then
            READY=$(kubectl --kubeconfig="$KUBECONFIG" get pods -n "$namespace" -l "$label_selector" -o jsonpath='{.items[?(@.metadata.name!="'$FIRST_POD'")].status.conditions[?(@.type=="Ready")].status}' 2>/dev/null || echo "False")
            if [[ "$READY" == "True" ]]; then
                log "✅ New pod ready: $NEW_PODS"
                return 0
            fi
        fi
        sleep 5
        elapsed=$((elapsed + 5))
    done
    
    warn "⚠️ Failover timeout for $service_name"
    return 1
}

# Main
case "$SERVICE" in
    "nextcloud")
        test_service_failover "nextcloud" "apps" "app.kubernetes.io/name=nextcloud"
        ;;
    "vaultwarden")
        test_service_failover "vaultwarden" "apps" "app.kubernetes.io/name=vaultwarden"
        ;;
    "homeassistant")
        test_service_failover "homeassistant" "smarthome" "app.kubernetes.io/name=home-assistant"
        ;;
    "ollama")
        test_service_failover "ollama" "ai" "app.kubernetes.io/name=ollama"
        ;;
    "grafana")
        test_service_failover "grafana" "monitoring" "app.kubernetes.io/name=grafana"
        ;;
    "prometheus")
        test_service_failover "prometheus" "monitoring" "app.kubernetes.io/name=prometheus"
        ;;
    "loki")
        test_service_failover "loki" "logging" "app.kubernetes.io/name=loki"
        ;;
    "tempo")
        test_service_failover "tempo" "tracing" "app.kubernetes.io/name=tempo"
        ;;
    "authelia")
        test_service_failover "authelia" "auth" "app.kubernetes.io/name=authelia"
        ;;
    "infisical")
        test_service_failover "infisical" "secrets" "app.kubernetes.io/name=infisical"
        ;;
    "traefik")
        test_service_failover "traefik" "traefik" "app.kubernetes.io/name=traefik"
        ;;
    "all")
        log "Running failover tests for all services..."
        for svc in nextcloud vaultwarden homeassistant ollama grafana prometheus loki tempo authelia infisical traefik; do
            test_service_failover "$svc" "$(case $svc in
                nextcloud|vaultwarden) echo apps ;;
                homeassistant) echo smarthome ;;
                ollama) echo ai ;;
                grafana|prometheus) echo monitoring ;;
                loki) echo logging ;;
                tempo) echo tracing ;;
                authelia) echo auth ;;
                infisical) echo secrets ;;
                traefik) echo traefik ;;
            esac)" "app.kubernetes.io/name=$svc" || true
            sleep 30
        done
        ;;
    *)
        echo "Usage: $0 {nextcloud|vaultwarden|homeassistant|ollama|grafana|prometheus|loki|tempo|authelia|infisical|traefik|all}"
        exit 1
        ;;
esac