# HOMELAB SETUP GUIDE — How To Use Everything

> **Host:** AutoBot | **IP:** 192.168.68.59 | **OS:** Raspberry Pi OS 64-bit  
> **24 services running** | **Last updated:** 2026-06-13

---

## Quick Start — Open These Right Now

Open these in your browser (any device on same WiFi):

| What | URL | Username | Password |
|------|-----|----------|----------|
| **Pi-hole** (ad blocker) | http://192.168.68.59:8053/admin | — | `changeme_pihole` |
| **Home Assistant** | http://192.168.68.59:8123 | Set on first visit | Set on first visit |
| **Prometheus** | http://192.168.68.59:9090 | No auth | No auth |
| **Grafana** | http://192.168.68.59:3000 | `admin` | `changeme_grafana` |
| **Traefik** | https://192.168.68.59 | `admin` | `<CHANGE_ME_TRAEFIK_ADMIN_PASSWORD>` |
| **Uptime Kuma** | http://192.168.68.59:3001 | Set on first visit | Set on first visit |

> If any URL doesn't open: wait 30 seconds, refresh. Services need time to wake up.

---

## 1. Pi-hole — Block Ads Across Your Entire Network

### What it does
Blocks ads on EVERY device connected to your WiFi. No need to install ad blockers on each device.

### How to use
1. Open **http://192.168.68.59:8053/admin** in your browser
2. Login with password `changeme_pihole`
3. Dashboard shows: total queries, queries blocked, domains on blocklist

### Make it work for all devices
1. On your **router settings**, change DNS server to `192.168.68.59`
2. OR on each device, set DNS to `192.168.68.59`
3. Test: visit `http://doubleclick.net` — should return blank page

### How to change password
```bash
# SSH into Pi:
ssh vansh@192.168.68.59
docker exec pihole pihole -a -p NEWPASSWORD
```

---

## 2. Home Assistant — Smart Home Hub

### What it does
Control smart lights, sensors, cameras, thermostats from one app. Automations like "turn off lights when nobody is home."

### How to use
1. Open **http://192.168.68.59:8123** in your browser
2. Click "Create my smart home" → enter name, username, password
3. Add devices: Settings → Devices & Services → Add Integration
4. Create automations: Settings → Automations & Scenes

### Mobile App
- Install "Home Assistant" app from App Store / Play Store
- Enter `http://192.168.68.59:8123` as server URL
- Login with credentials you created

---

## 3. Nextcloud — Your Private Google Drive

### What it does
Store files, photos, calendars, contacts. Like Dropbox but on YOUR hardware. Everything stays on your Pi.

### How to use
1. Open **https://192.168.68.59** → click through "insecure connection" warning → redirects to Nextcloud
2. Login: Username `admin`, Password `changeme_nextcloud`
3. Upload files, create folders, share links with friends

### Desktop & Mobile Sync
- Install Nextcloud desktop app from https://nextcloud.com/install
- Server: `https://192.168.68.59`
- Install Nextcloud mobile app, same server URL

### How to change password
Login → click your avatar (top right) → Personal Settings → Security → Change Password

---

## 4. Vaultwarden — Password Manager

### What it does
Stores ALL your passwords securely. Syncs with Bitwarden apps on phone/laptop.

### How to use
1. Open **https://192.168.68.59** → login page → click "Create Account" at the bottom
2. Enter email, name, master password (make it STRONG — this protects everything)
3. Add passwords, credit cards, secure notes

### Browser Extension & Mobile App
- Install "Bitwarden" extension for Chrome/Firefox/Edge
- Click Settings → Server URL → `https://192.168.68.59`
- Login with your email and master password
- On phone: install Bitwarden app, set server to `https://192.168.68.59`

### Admin Panel
- URL: `https://192.168.68.59/admin`
- Token: `changeme_vaultwarden`
- Use this to manage users, view logs

---

## 5. Grafana — Beautiful Charts & Dashboards

### What it does
Shows live graphs of your Pi's health: CPU usage, memory, disk space, network traffic, container status.

### How to use
1. Open **http://192.168.68.59:3000**
2. Login: Username `admin`, Password `changeme_grafana`
3. Left menu → Dashboards → Homelab → see all your Pi stats
4. Explore → Select "Prometheus" → type queries like `node_memory_MemAvailable_bytes / 1024 / 1024`

### Built-in Dashboards
- **System Overview**: CPU, RAM, disk, network, temperature
- **Containers**: All Docker containers, resource usage per container
- **Pi Power Monitoring**: Electricity usage, power optimization

### How to change password
Login → click avatar (bottom left) → Change Password

---

## 6. Prometheus — Metrics Database

### What it does
Collects numbers from every service. Feeds data to Grafana for charts. Think of it as the "measurement engine."

### How to use
1. Open **http://192.168.68.59:9090**
2. Status → Targets: see ALL services being monitored (should show "UP" in green)
3. Graph: type queries like:
   - `container_memory_usage_bytes` — memory per container
   - `node_cpu_seconds_total` — CPU usage
   - `rate(traefik_requests_total[5m])` — requests per second

---

## 7. Ollama — Local AI (ChatGPT on Your Pi)

### What it does
Runs AI language models locally. No internet needed. Your data never leaves your Pi.

### How to use
```bash
# SSH into Pi first:
ssh vansh@192.168.68.59

# Pull a model (first time):
docker exec ollama ollama pull gemma:2b

# Chat with it:
docker exec -it ollama ollama run gemma:2b
# Type your question, press Enter. Type /bye to exit.

# Try another model:
docker exec ollama ollama pull llama3:8b  # Larger, slower, smarter
```

### Chat from your browser
Option: Set up Open WebUI as an additional container (coming soon in v2.13).

---

## 8. Uptime Kuma — Service Monitor

### What it does
Constantly checks if your services are online. Sends alerts (Telegram/Email) if something goes down.

### How to use
1. Open **http://192.168.68.59:3001** (or via Traefik at uptime.homelab.local)
2. Create admin account on first visit
3. Add a monitor: "+ Add New Monitor"
   - Monitor Type: HTTP(s)
   - URL: http://192.168.68.59:8123
   - Heartbeat Interval: 60 seconds
4. Set up notifications: Settings → Notifications → Telegram

---

## 9. Portainer — Docker Manager

### What it does
Web interface to manage all Docker containers. Start/stop/restart containers, view logs, without typing commands.

### How to use
1. Open **http://192.168.68.59:9000** (or via Traefik at portainer.homelab.local)
2. Create admin account on first visit
3. Click "Local" Docker environment
4. See all 24 containers, their status, resource usage, logs

---

## 10. WireGuard — VPN to Your Home

### What it does
Connect to your home network from anywhere. Access ALL services as if you're at home.

### How to use
1. SSH into Pi: `ssh vansh@192.168.68.59`
2. Get peer configs:
```bash
docker exec wireguard cat /config/peer_phone/peer_phone.conf
# OR show QR code for mobile:
docker exec wireguard sh -c "cat /config/peer_phone/peer_phone.conf | qrencode -t ansiutf8"
```
3. Install WireGuard app on phone/laptop
4. Add tunnel → scan QR code or paste config
5. Connect → you can now access all services at 192.168.68.59 from anywhere

---

## 11. Authelia — Login Gate (2FA)

### What it does
Adds a login page before any service. Protects with Two-Factor Authentication.

### How to use
1. Visit any protected service via Traefik (https://192.168.68.59)
2. You'll be redirected to Authelia login page
3. Login with your Authelia credentials (configured in `config/authelia/users_database.yml`)
4. Enter 2FA code from your authenticator app

### Adding 2FA
1. Login to Authelia → you'll be prompted to set up 2FA
2. Scan QR code with Google Authenticator / Authy
3. Enter the 6-digit code to verify

---

## 12. CrowdSec — Hack Protection

### What it does
Watches logs for hacking attempts. Automatically blocks malicious IPs.

### How to check it's working
```bash
ssh vansh@192.168.68.59
docker logs crowdsec --tail 20
# Look for lines like "ip:xxx blocked" or "processed 500 lines"
```

---

## 13. Loki + Promtail — Log Viewer

### What it does
Loki stores all container logs. Promtail ships logs to Loki. Viewable in Grafana.

### How to use
1. Open Grafana: http://192.168.68.59:3000
2. Left menu → Explore
3. Data source: Select "Loki"
4. Type: `{container_name="traefik"}` → view Traefik logs
5. Try: `{container_name=~"nextcloud|vaultwarden"}` → view multiple services
6. Filter by error: `{container_name="mariadb"} |= "ERROR"`

---

## 14. Alertmanager — Get Notified of Problems

### What it does
Sends alerts when: CPU too high, disk almost full, service down, memory low.

### How to check alerts
1. Open **http://192.168.68.59:9093**
2. Click "Alerts" → see all active alerts
3. If nothing shows: no problems right now (good!)

### Setting up Telegram alerts
1. Edit `.env` on Pi: add `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID`
2. Edit `config/alertmanager/alertmanager.yml` to add Telegram receiver
3. Restart: `docker restart alertmanager`

---

## 15. Tempo — Request Tracing

### What it does
Tracks requests as they travel between services. Helps find why something is slow.

### How to use
1. Open Grafana: http://192.168.68.59:3000
2. Explore → Data source: Select "Tempo"
3. Search for recent traces
4. Click a trace → see every step a request took

---

## 16. SSH — Remote Terminal

### What it does
Command-line access to the Pi from your laptop.

### How to use
```bash
# From Windows PowerShell / WSL / Terminal:
ssh vansh@192.168.68.59

# Enter your SSH key passphrase (if set)

# Useful commands once connected:
cd ~/homelab-prod
docker ps                          # See all containers
bash scripts/health-check.sh       # Check if everything is healthy
bash scripts/backup.sh             # Run backup
docker logs containername --tail 50 # See logs for any container
docker restart containername       # Restart a specific service
```

---

## Quick Troubleshooting

| Problem | Fix |
|---------|-----|
| Can't open any URL | Check Pi is powered on. Ping 192.168.68.59 |
| Website shows "Connection refused" | Service may be starting. Wait 30 sec, refresh |
| Service shows "502 Bad Gateway" | Container may have stopped. SSH in, run `docker ps` |
| Pi-hole not blocking ads | Set device DNS to 192.168.68.59 in WiFi settings |
| Grafana shows "no data" | Check Prometheus targets: http://192.168.68.59:9090/targets |
| Ollama model download stuck | `docker exec ollama ollama list` → check progress |
| Out of RAM (system slow) | Stop Ollama: `docker stop ollama` |

---

## Daily Tasks (5 minutes)

1. **Check health**: Open Uptime Kuma → all monitors should be green
2. **Check Pi-hole**: Open http://192.168.68.59:8053/admin → check blocked %
3. **Check storage**: `df -h /mnt/data` → should be <80% full
4. **Check Grafana**: CPU <80%, RAM <90%, disk OK

## Weekly Tasks (15 minutes)

1. **Update containers**: `cd ~/homelab-prod && bash scripts/update.sh`
2. **Run backup**: `bash scripts/backup.sh`
3. **Check logs**: Grafana → Explore → Loki → `|= "ERROR"` or `|= "FATAL"`
4. **Prune old images**: `docker image prune -a -f`

---

## Architecture Diagram

```
INTERNET
    │
    ▼
[Your Router] ── DNS: 192.168.68.59 (Pi-hole)
    │
    ├── WiFi ── Your Phone/Laptop
    │              │
    │              └── Access services at 192.168.68.59
    │
    ▼
[Raspberry Pi 4B — 192.168.68.59]
    │
    ├── Traefik (ports 80, 443) ── Routes traffic to services
    │     ├── https://cloud → Nextcloud
    │     ├── https://vault → Vaultwarden
    │     ├── https://uptime → Uptime Kuma
    │     └── https://traefik → Dashboard
    │
    ├── Pi-hole (port 53) ── DNS + Ad Blocking
    ├── WireGuard (port 51820/udp) ── VPN
    ├── Home Assistant (port 8123) ── Smart Home
    ├── Prometheus (port 9090) ── Metrics
    ├── Grafana (port 3000) ── Dashboards
    ├── Ollama (port 11434) ── Local AI
    └── ... 18 more services
```

---

## Services You Can Access RIGHT NOW

| # | Service | How to Access | What to do first |
|---|---------|--------------|-----------------|
| 1 | Pi-hole | http://192.168.68.59:8053/admin | Login, check dashboard |
| 2 | Home Assistant | http://192.168.68.59:8123 | Create account |
| 3 | Grafana | http://192.168.68.59:3000 | Login admin/changeme_grafana |
| 4 | Prometheus | http://192.168.68.59:9090 | Check targets |
| 5 | Ollama | SSH → `docker exec ollama ollama run gemma:2b` | Pull model first |
| 6 | Portainer | http://192.168.68.59:9000 | Create admin account |
| 7 | Uptime Kuma | http://192.168.68.59:3001 | Create account, add monitors |
| 8 | Nextcloud | https://192.168.68.59 | Login admin/changeme_nextcloud |
| 9 | Vaultwarden | https://192.168.68.59 | Create account via Bitwarden app |
| 10 | WireGuard | SSH → get peer config | Scan QR in WireGuard app |
| 11 | Traefik | https://192.168.68.59/dashboard/ | Login admin/<CHANGE_ME_TRAEFIK_ADMIN_PASSWORD> |
| 12 | Alertmanager | http://192.168.68.59:9093 | View alerts |
| 13 | Loki | Via Grafana Explore | Search logs |
| 14 | SSH | `ssh vansh@192.168.68.59` | Run `docker ps` |
| 15 | CrowdSec | SSH → `docker logs crowdsec` | Check blocked IPs |
| 16 | Tempo | Via Grafana Explore | Search traces |
| 17 | Authelia | Via Traefik → any service | Login, set up 2FA |