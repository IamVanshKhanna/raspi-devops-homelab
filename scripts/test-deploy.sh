#!/usr/bin/env bash
set -euo pipefail

# =============================================================================
# test-deploy.sh — Post-deployment smoke tests
# Verifies all homelab services are reachable and responding.
#
# Usage:   bash scripts/test-deploy.sh [--verbose]
# Returns: 0 if all checks pass, 1 if any fail.
# =============================================================================

VERBOSE=false
[[ "${1:-}" == "--verbose" ]] && VERBOSE=true

PASS=0
FAIL=0
RESULTS=()

# --- Load environment variables --------------------------------------------
ENV_FILE="$(dirname "$0")/../.env"
if [[ -f "$ENV_FILE" ]]; then
    set -a
    source "$ENV_FILE"
    set +a
fi

DOMAIN="${DOMAIN:-localhost}"
HOST_IP="${HOST_IP:-$(hostname -I | awk '{print $1}')}"
TIMEOUT=10

log_pass() { RESULTS+=("  PASS  $1"); ((PASS++)); $VERBOSE && echo "  [OK]    $1"; }
log_fail() { RESULTS+=("  FAIL  $1 — $2"); ((FAIL++)); echo "  [FAIL]  $1 — $2"; }

check_url() {
    local label="$1" url="$2" expected_code="${3:-200}"
    local code
    code=$(curl -sk -o /dev/null -w "%{http_code}" --max-time "$TIMEOUT" "$url" 2>/dev/null || echo "000")
    if [[ "$code" == "$expected_code" ]] || [[ "$code" -ge 200 && "$code" -lt 400 ]]; then
        log_pass "$label ($code)"
    else
        log_fail "$label" "got HTTP $code, expected $expected_code — $url"
    fi
}

check_port() {
    local label="$1" host="$2" port="$3"
    if timeout "$TIMEOUT" bash -c "echo >/dev/tcp/$host/$port" 2>/dev/null; then
        log_pass "$label (port $port open)"
    else
        log_fail "$label" "port $port not reachable on $host"
    fi
}

check_docker() {
    local container="$1"
    local status
    status=$(docker inspect -f '{{.State.Status}}' "$container" 2>/dev/null || echo "missing")
    if [[ "$status" == "running" ]]; then
        log_pass "Container $container ($status)"
    else
        log_fail "Container $container" "status=$status"
    fi
}

echo "=== Homelab Smoke Tests ==="
echo "Domain: $DOMAIN | Host IP: $HOST_IP"
echo ""

# --- Container health checks (16 core services) ----------------------------
echo "--- Container Status ---"
check_docker "traefik"
check_docker "portainer"
check_docker "prometheus"
check_docker "alertmanager"
check_docker "loki"
check_docker "promtail"
check_docker "grafana"
check_docker "node-exporter"
check_docker "cadvisor"
check_docker "mariadb"
check_docker "redis"
check_docker "nextcloud"
check_docker "vaultwarden"
check_docker "ollama"
check_docker "pihole"
check_docker "pihole-exporter"
check_docker "wireguard"
check_docker "homeassistant"
check_docker "uptime-kuma"
check_docker "authelia"
check_docker "authelia-redis"
check_docker "crowdsec"
check_docker "crowdsec-db"
echo ""

# --- HTTP endpoint checks (Traefik-routed services) ------------------------
echo "--- HTTP Endpoints (https://*.${DOMAIN}) ---"
check_url "Traefik dashboard"  "https://traefik.${DOMAIN}"     200
check_url "Portainer UI"       "https://portainer.${DOMAIN}"   200
check_url "Grafana"            "https://grafana.${DOMAIN}"     200
check_url "Prometheus"         "http://${HOST_IP}:9090"        200
check_url "Alertmanager"       "http://${HOST_IP}:9093"        200
check_url "Nextcloud"          "https://cloud.${DOMAIN}"       200
check_url "Vaultwarden"        "https://vault.${DOMAIN}"       200
check_url "Uptime Kuma"        "https://uptime.${DOMAIN}"      200
check_url "Authelia"           "https://auth.${DOMAIN}"        200
echo ""

# --- Non-Traefik endpoints --------------------------------------------------
echo "--- Direct Port Checks ---"
check_port "Pi-hole DNS (53)"      "$HOST_IP" 53
check_port "Pi-hole Web (8053)"    "$HOST_IP" 8053
check_port "Home Assistant (8123)" "$HOST_IP" 8123
check_port "WireGuard UDP"         "$HOST_IP" 51820
check_port "Ollama API"            "127.0.0.1" 11434
echo ""

# --- Prometheus targets -----------------------------------------------------
echo "--- Prometheus Targets ---"
PROM_TARGETS=$(curl -sk "http://${HOST_IP}:9090/api/v1/targets" 2>/dev/null | \
    python3 -c "import sys,json; data=json.load(sys.stdin); [print(t['labels']['job'],t['health']) for t in data['data']['activeTargets']]" 2>/dev/null || echo "")
if [[ -n "$PROM_TARGETS" ]]; then
    UP_COUNT=$(echo "$PROM_TARGETS" | grep -c "up" || true)
    TOTAL_COUNT=$(echo "$PROM_TARGETS" | wc -l)
    log_pass "Prometheus targets ($UP_COUNT/$TOTAL_COUNT up)"
    $VERBOSE && echo "$PROM_TARGETS" | while read line; do echo "         $line"; done
else
    log_fail "Prometheus targets" "could not query /api/v1/targets"
fi
echo ""

# --- Summary ----------------------------------------------------------------
echo "=== Results: $PASS passed, $FAIL failed ==="
printf '%s\n' "${RESULTS[@]}"

if [[ $FAIL -gt 0 ]]; then
    echo ""
    echo "Fix failures before considering the deployment healthy."
    exit 1
fi

echo "All $PASS checks passed. Homelab is healthy!"
exit 0