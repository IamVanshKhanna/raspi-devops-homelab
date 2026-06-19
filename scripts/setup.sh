#!/usr/bin/env bash
# setup.sh - One-shot bootstrap for homelab-prod
# Usage: sudo bash scripts/setup.sh

set -euo pipefail

YELLOW='\033[1;33m'; GREEN='\033[0;32m'; RED='\033[0;31m'; NC='\033[0m'
log()  { echo -e "${GREEN}[SETUP]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
fail() { echo -e "${RED}[FAIL]${NC} $1"; exit 1; }

[[ $EUID -ne 0 ]] && fail "Run as root: sudo bash scripts/setup.sh"

# Detect the non-root user who invoked sudo (works with any username)
TARGET_USER="${SUDO_USER:-}"
if [[ -z "$TARGET_USER" ]]; then
  # Fallback: guess from home dirs if not run via sudo
  TARGET_USER=$(ls /home | head -1)
  warn "Could not detect SUDO_USER - guessing '$TARGET_USER'. Run with: sudo -E bash scripts/setup.sh"
fi
log "Target user for Docker group: $TARGET_USER"

log "Updating system packages..."
apt-get update -qq && apt-get upgrade -y -qq

log "Installing dependencies..."
# restic for backups, zram-tools for compressed swap
apt-get install -y -qq curl wget git vim htop ca-certificates gnupg \
  lsb-release apt-transport-https ufw fail2ban python3 python3-pip apache2-utils \
  restic zram-tools jq

log "Configuring ZRAM swap (2 GB compressed in RAM, no disk swap)..."
cat > /etc/systemd/zram-generator.conf << 'EOF'
[zram0]
zram-size = ram / 2
compression-algorithm = zstd
EOF
systemctl daemon-reload
systemctl start systemd-zram-setup@zram0.service || warn "ZRAM setup may need reboot"
swapon -s | grep -q zram && log "ZRAM active" || warn "ZRAM not active yet (may need reboot)"

log "Disabling traditional swap (improves SSD performance and Docker stability)..."
dphys-swapfile swapoff    2>/dev/null || true
dphys-swapfile uninstall  2>/dev/null || true
systemctl disable dphys-swapfile 2>/dev/null || true
swapoff -a

log "Setting GPU memory to 16MB (headless server - no display needed)..."
CONFIG_FILE="/boot/firmware/config.txt"
[[ -f "/boot/config.txt" ]] && CONFIG_FILE="/boot/config.txt"
if ! grep -q "gpu_mem=16" "$CONFIG_FILE" 2>/dev/null; then
  echo "gpu_mem=16" >> "$CONFIG_FILE"
fi

log "Disabling systemd-resolved (frees port 53 for Pi-hole)..."
systemctl disable --now systemd-resolved || true
rm -f /etc/resolv.conf
echo "nameserver 1.1.1.1" >  /etc/resolv.conf
echo "nameserver 8.8.8.8" >> /etc/resolv.conf

log "Installing Docker..."
if ! command -v docker &>/dev/null; then
  curl -fsSL https://get.docker.com | sh
  usermod -aG docker "$TARGET_USER" || warn "Could not add $TARGET_USER to docker group"
  systemctl enable docker && systemctl start docker
  log "Docker installed. NOTE: log out and back in for group changes to take effect."
else
  warn "Docker already installed - skipping."
  usermod -aG docker "$TARGET_USER" 2>/dev/null || true
fi

log "Creating Docker proxy network..."
docker network create proxy 2>/dev/null || warn "Network 'proxy' already exists."

DATA_DIR="${DATA_DIR:-/mnt/data}"
BACKUP_DIR="${BACKUP_DIR:-/mnt/backup}"
log "Creating data directories at $DATA_DIR and $BACKUP_DIR..."
mkdir -p \
  "$DATA_DIR/nextcloud/userdata" \
  "$DATA_DIR/traefik/certs" \
  "$DATA_DIR/pihole/config" \
  "$DATA_DIR/pihole/dnsmasq" \
  "$DATA_DIR/wireguard" \
  "$DATA_DIR/homeassistant" \
  "$DATA_DIR/ollama" \
  "$DATA_DIR/grafana" \
  "$DATA_DIR/prometheus" \
  "$DATA_DIR/loki" \
  "$DATA_DIR/restic-cache" \
  "$BACKUP_DIR" \
  "$BACKUP_DIR/logs"
chown -R 1000:1000 "$DATA_DIR" "$BACKUP_DIR" || true

log "Setting acme.json permissions (Traefik TLS certificate storage)..."
touch "$DATA_DIR/traefik/certs/acme.json"
chmod 600 "$DATA_DIR/traefik/certs/acme.json"

log "Configuring UFW firewall..."
ufw --force reset
ufw default deny incoming && ufw default allow outgoing
ufw allow ssh
ufw allow 80/tcp
ufw allow 443/tcp
ufw allow 51820/udp
ufw allow 8123/tcp
ufw allow 53
ufw --force enable
log "UFW enabled. Rules set."

log "Enabling fail2ban..."
systemctl enable fail2ban && systemctl start fail2ban

# Tailscale install (if not present)
if ! command -v tailscale &>/dev/null; then
  log "Installing Tailscale..."
  curl -fsSL https://tailscale.com/install.sh | sh
  log "Tailscale installed. Run 'sudo tailscale up' to authenticate."
else
  log "Tailscale already installed."
fi

echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN} Setup complete! Next steps:${NC}"
echo -e "${GREEN} 1. Log out and back in (Docker group permissions for $TARGET_USER)${NC}"
echo -e "${GREEN} 2. Reboot if ZRAM was just enabled: sudo reboot${NC}"
echo -e "${GREEN} 3. cp .env.example .env && nano .env${NC}"
echo -e "${GREEN} 4. sudo tailscale up --ssh --advertise-exit-node${NC}"
echo -e "${GREEN} 5. make up-phase1 (core + network)${NC}"
echo -e "${GREEN} 6. See docs/SETUP_GUIDE.md for full deployment steps${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"