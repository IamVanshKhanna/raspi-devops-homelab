# Step-by-Step Setup Guide

Full setup from blank SSD to fully running homelab on Raspberry Pi 4B.

---

## Phase 1 — Flash OS to SSD

1. Download **Raspberry Pi Imager** on your computer
2. Select: `Raspberry Pi OS Lite (64-bit)` — Bookworm
3. Select your 2TB SSD as target (via USB adapter)
4. Click gear icon and set:
   - Hostname: `homelab`
   - Enable SSH with password
   - Username: `pi`, strong password
   - Timezone: `Australia/Melbourne`
5. Flash and insert SSD into DeskPi3

---

## Phase 2 — Boot from SSD

```bash
sudo raspi-config
# Advanced Options > Boot Order > USB Boot (B2)
# Reboot and remove SD card
```

---

## Phase 3 — Set Static IP

SSH in: `ssh pi@<your-pi-ip>`

Set static IP via router DHCP reservation (preferred) OR:

```bash
sudo nano /etc/dhcpcd.conf
# Add:
interface eth0
static ip_address=192.168.1.50/24
static routers=192.168.1.1
static domain_name_servers=1.1.1.1 8.8.8.8
```

```bash
sudo reboot
```

---

## Phase 4 — Clone Repo and Run Setup

```bash
sudo apt-get install -y git
git clone https://github.com/VK7160/pi4b-homelab.git
cd pi4b-homelab
chmod +x scripts/setup.sh
sudo bash scripts/setup.sh
```

Log out and back in after completion (Docker group permissions):
```bash
exit
ssh pi@192.168.1.50
```

---

## Phase 5 — Configure Environment

```bash
cp .env.example .env
nano .env
```

Fill in every value. Generate strong passwords:
```bash
openssl rand -base64 32           # general passwords
openssl rand -base64 48           # Vaultwarden admin token
echo $(htpasswd -nB admin) | sed -e 's/\$/\$\$/g'  # Traefik basic auth
```

> Never commit your `.env` — it is in `.gitignore`

---

## Phase 6 — Free Domain (DuckDNS)

1. Sign in at https://www.duckdns.org
2. Create subdomain e.g. `myhomelab.duckdns.org`
3. Point to your home public IP
4. Auto-update cron on Pi:

```bash
mkdir -p ~/duckdns
nano ~/duckdns/duck.sh
# Paste:
echo url="https://www.duckdns.org/update?domains=YOUR_SUBDOMAIN&token=YOUR_TOKEN&ip=" | curl -k -o ~/duckdns/duck.log -K -
chmod +x ~/duckdns/duck.sh
crontab -e
# Add: */5 * * * * ~/duckdns/duck.sh >/dev/null 2>&1
```

5. Forward on router: `80 TCP`, `443 TCP`, `51820 UDP` → `192.168.1.50`

---

## Phase 7 — Deploy Stacks In Order

```bash
# 1. Core (Traefik + Portainer) - ALWAYS FIRST
docker compose -f stacks/core/docker-compose.yml up -d
docker logs traefik --tail 20

# 2. Monitoring (Prometheus + Grafana)
docker compose -f stacks/monitoring/docker-compose.yml up -d

# 3. Apps (Nextcloud + Vaultwarden + Ollama)
docker compose -f stacks/apps/docker-compose.yml up -d
# Wait 2-3 mins for Nextcloud DB init

# Pull an Ollama model (use small models on 4GB RAM)
docker exec ollama ollama pull gemma:2b

# 4. Network (Pi-hole + WireGuard)
docker compose -f stacks/network/docker-compose.yml up -d

# 5. Smart Home (Home Assistant)
docker compose -f stacks/smarthome/docker-compose.yml up -d
```

---

## Phase 8 — Schedule Maintenance

```bash
crontab -e
```

Add:
```bash
# Daily backup at 3am
0 3 * * * /home/pi/pi4b-homelab/scripts/backup.sh >> /var/log/homelab-backup.log 2>&1

# Health check every 15 minutes
*/15 * * * * /home/pi/pi4b-homelab/scripts/health-check.sh >> /var/log/homelab-health.log 2>&1

# Weekly update Sunday 4am
0 4 * * 0 /home/pi/pi4b-homelab/scripts/update.sh >> /var/log/homelab-update.log 2>&1

# DuckDNS update every 5 minutes
*/5 * * * * ~/duckdns/duck.sh >/dev/null 2>&1
```

---

## Phase 9 — Verify

```bash
bash scripts/health-check.sh
docker ps
vcgencmd measure_temp   # Should be 45-55C at idle
df -h                   # Check disk usage
```

---

## Service Access URLs

| Service | URL |
|---|---|
| Traefik dashboard | https://traefik.yourdomain.com |
| Portainer | https://portainer.yourdomain.com |
| Nextcloud | https://cloud.yourdomain.com |
| Vaultwarden | https://vault.yourdomain.com |
| Grafana | https://grafana.yourdomain.com |
| Home Assistant | http://192.168.1.50:8123 |
| Pi-hole | http://192.168.1.50:8053/admin |
| Ollama API | http://192.168.1.50:11434 |
| Prometheus | http://192.168.1.50:9090 |
