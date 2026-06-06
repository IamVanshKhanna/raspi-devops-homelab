#!/usr/bin/env bash
# setup.sh - One-shot bootstrap for pi4b-homelab
# Usage: sudo bash scripts/setup.sh

set -euo pipefail

YELLOW='\033[1;33m'; GREEN='\033[0;32m'; RED='\033[0;31m'; NC='\033[0m'
log()  { echo -e "${GREEN}[SETUP]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC}  $1"; }
fail() { echo -e "${RED}[FAIL]${NC}  $1"; exit 1; }

[[ $EUID -ne 0 ]] && fail "Run as root: sudo bash scripts/setup.sh"

log "Updating system packages..."
apt-get update -qq && apt-get upgrade -y -qq

log "Installing dependencies..."
apt-get install -y -qq curl wget git vim htop ca-certificates gnupg \
  lsb-release apt-transport-https ufw fail2ban python3 python3-pip apache2-utils

log "Disabling swap..."
dphys-swapfile swapoff || true
dphys-swapfile uninstall || true
systemctl disable dphys-swapfile || true
swapoff -a

log "Setting GPU memory to 16MB..."
if ! grep -q "gpu_mem=16" /boot/firmware/config.txt 2>/dev/null; then
  echo "gpu_mem=16" >> /boot/firmware/config.txt
fi

log "Disabling systemd-resolved (frees port 53 for Pi-hole)..."
systemctl disable --now systemd-resolved || true
rm -f /etc/resolv.conf
echo "nameserver 1.1.1.1" > /etc/resolv.conf
echo "nameserver 8.8.8.8" >> /etc/resolv.conf

log "Installing Docker..."
if ! command -v docker &>/dev/null; then
  curl -fsSL https://get.docker.com | sh
  usermod -aG docker pi 2>/dev/null || usermod -aG docker "$SUDO_USER" 2>/dev/null || true
  systemctl enable docker && systemctl start docker
  log "Docker installed."
else
  warn "Docker already installed - skipping."
fi

log "Creating Docker proxy network..."
docker network create proxy 2>/dev/null || warn "Network 'proxy' already exists."

DATA_DIR="${DATA_DIR:-/mnt/data}"
log "Creating data directories at $DATA_DIR..."
mkdir -p \
  "$DATA_DIR/nextcloud/userdata" "$DATA_DIR/traefik/certs" \
  "$DATA_DIR/pihole/config" "$DATA_DIR/pihole/dnsmasq" \
  "$DATA_DIR/wireguard" "$DATA_DIR/homeassistant" \
  "$DATA_DIR/ollama" "$DATA_DIR/grafana" "$DATA_DIR/prometheus" \
  /mnt/backup
chown -R 1000:1000 "$DATA_DIR" || true

log "Setting acme.json permissions..."
touch "$DATA_DIR/traefik/certs/acme.json"
chmod 600 "$DATA_DIR/traefik/certs/acme.json"

log "Configuring UFW firewall..."
ufw --force reset
ufw default deny incoming && ufw default allow outgoing
ufw allow ssh && ufw allow 80/tcp && ufw allow 443/tcp
ufw allow 51820/udp && ufw allow 8123/tcp && ufw allow 53
ufw --force enable

log "Enabling fail2ban..."
systemctl enable fail2ban && systemctl start fail2ban

echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}  Setup complete! Next steps:${NC}"
echo -e "${GREEN}  1. Log out and back in (Docker group permissions)${NC}"
echo -e "${GREEN}  2. cp .env.example .env && nano .env${NC}"
echo -e "${GREEN}  3. docker compose -f stacks/core/docker-compose.yml up -d${NC}"
echo -e "${GREEN}  4. See docs/SETUP_GUIDE.md for full deployment steps${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
