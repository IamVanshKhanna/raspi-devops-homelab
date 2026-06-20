# Pi4Homelab ??? Raspberry Pi 4B Server

A single Raspberry Pi 4B (4GB) running 27 Docker containers as a self-hosted homelab:
VPN, DNS, reverse proxy, password manager, monitoring, security, and file sync.
Remote managed via Telegram bot.

## Architecture

| Component | Detail |
|-----------|--------|
| **Board** | Raspberry Pi 4B, 4GB RAM |
| **Storage** | 1.9TB SSD (/dev/sda) |
| **OS** | Debian Trixie (aarch64) |
| **Orchestration** | Docker Compose (5 stacks) |
| **Reverse Proxy** | Traefik v3 with Tailscale HTTPS |
| **VPN** | WireGuard + Tailscale mesh |
| **DNS** | Pi-hole (network-wide ad blocking) |
| **Remote Access** | Tailscale MagicDNS ??? autobot.taila24d04.ts.net |
| **Fan Control** | DeskPi Pro PWM (manual or auto) |

## Stacks

| Stack | Directory | Services | Purpose |
|-------|-----------|----------|---------|
| **core** | stacks/core/ | traefik, portainer | Entry point, Docker management UI |
| **network** | stacks/network/ | pihole, pihole-exporter, wireguard | DNS ad-blocking, VPN server |
| **services** | stacks/services/ | vaultwarden, uptime-kuma | Password manager, uptime monitoring |
| **nas** | stacks/nas/ | samba, syncthing | File sharing, cross-device sync |
| **monitoring-pi** | stacks/monitoring-pi/ | node-exporter | Pi hardware metrics exporter |
| **monitoring** | stacks/monitoring/ | grafana, prometheus, loki, promtail, tempo, otel-collector, alertmanager, cadvisor | Full observability stack |
| **auth** | stacks/auth/ | authelia, authelia-redis | SSO portal with 2FA |
| **security** | stacks/security/ | crowdsec, crowdsec-db | Intrusion detection / IPS |
| **secrets** | stacks/secrets/ | infisical, infisical-db, infisical-redis | Secrets management platform |
| **apps** | stacks/apps/ | nextcloud, mariadb, redis, homeassistant | Cloud file sync, home automation |

## Remote Management (Telegram Bot)

The `tinybot/` directory contains a Python Telegram bot for remote server management.
Built with `python-telegram-bot`, no LLM ??? lightweight polling bot.

### Commands

| Command | Description |
|---------|-------------|
| `/health` | Pi CPU, RAM, temp, disk, uptime |
| `/fan` | Show DeskPi fan & GPIO status |
| `/fan 0-100` | Set fan speed manually (0=off, 25, 50, 75, 100) |
| `/fan auto` | Restore automatic DeskPi PWM control |
| `/docker` | List all active containers with ports |
| `/docker close <name>` | Stop a container |
| `/docker restart <name>` | Restart a container |
| `/search <query>` | Web search via DuckDuckGo |
| `/chatid` | Get your Telegram chat ID |
| `/help` | Show all commands |
| `/start` | Greeting |

## Backup

Weekly OS image backup to data partition via systemd timer.
- **Script:** `scripts/backup-os.sh`
- **Schedule:** Sunday 3:00 AM (systemd user timer)
- **Retention:** 4 weekly backups

## Setup

1. Clone the repo:
   ```bash
   git clone git@github.com:IamVanshKhanna/pi4homelab.git
   cd pi4homelab
   ```
2. Copy and configure environment:
   ```bash
   cp .env.example .env
   # Edit .env with your tokens, domains, passwords
   ```
3. Deploy stacks:
   ```bash
   docker compose -f stacks/core/docker-compose.yml up -d
   docker compose -f stacks/network/docker-compose.yml up -d
   # ... repeat for each stack
   ```
4. (Optional) Telegram bot:
   ```bash
   # Ensure TELEGRAM_BOT_TOKEN is set in .env
   systemctl --user enable --now tinybot.service
   ```
5. (Optional) DeskPi fan control:
   ```bash
   sudo systemctl enable --now deskpi.service
   ```

## Git History

```
7915a20 init: pi4homelab v1.0 ??? single Pi 4B, Docker Compose only
ff53161 clean: remove v2.x artifacts (K3s, ArgoCD, Helmfile, CI)
d8029ee clean: remove v2.x docs, K3s/Ansible scripts, Hermes, dotfiles
0f15c44 clean: remove multi-node configs
68ab336 fix: add defaults to NAS stack, inline tempo/otel configs
4e75475 refactor: optimized Pi stack v2 (K3s removed, swap off)
c9c3e2b fix(tinybot): enable lingering, fix stale paths, add /chatid
a4fe73e feat: /fan accepts speed args (0-100), fix load labels
b5c6683 feat: add /docker command (list/close/restart), drop sudo
```

## Purpose

This is a reference/portfolio project demonstrating:

- Docker Compose orchestration across multiple stacks
- Reverse proxy configuration (Traefik + Tailscale)
- VPN setup (WireGuard + Tailscale mesh)
- Network DNS filtering (Pi-hole)
- Security hardening (CrowdSec IPS, Authelia SSO, firewall)
- Observability (Prometheus, Grafana, Loki, Tempo)
- Remote device management (Telegram bot, DeskPi fan control)
- Automated backup (systemd timers)
- Git-based infrastructure-as-code

