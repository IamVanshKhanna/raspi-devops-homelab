# pi4b-homelab

> 24/7 self-hosted homelab on Raspberry Pi 4B 4GB + DeskPi3 case + 2TB SSD.
> Full Docker stack: reverse proxy, monitoring, private cloud, password manager, AI inference, VPN, DNS ad-blocking, and smart home — all on ~7 watts.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-Raspberry%20Pi%204B-red)](https://www.raspberrypi.com/)
[![Docker](https://img.shields.io/badge/docker-compose-blue)](https://docs.docker.com/compose/)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)

---

## Table of Contents

- [Hardware](#hardware)
- [Architecture](#architecture)
- [Services](#services)
- [Repository Structure](#repository-structure)
- [Quick Start](#quick-start)
- [Deployment Order](#deployment-order)
- [Port Reference](#port-reference)
- [Backup Strategy](#backup-strategy)
- [Skills You Will Learn](#skills-you-will-learn)
- [Contributing](#contributing)
- [License](#license)

---

## Hardware

| Component | Spec |
|---|---|
| SBC | Raspberry Pi 4B 4GB RAM |
| Case | DeskPi3 (full-size 2.5" SATA bay, USB 3.0) |
| Storage | 2TB 2.5" SATA SSD (USB 3.0 boot, no SD card) |
| Power | Official Pi 4 USB-C PSU (5V/3A) |
| OS | Raspberry Pi OS Lite 64-bit (Bookworm) |
| Network | Gigabit Ethernet (recommended over Wi-Fi) |
| Idle Power | ~5-10W |

---

## Architecture

```
Internet
    |
[Router - Port Forward 80, 443, 51820]
    |
[Raspberry Pi 4B - Static LAN IP: 192.168.1.50]
    |
[Docker Engine]
    |
    +-- [Traefik]          <- Reverse proxy + auto TLS (Let's Encrypt)
    |       +-- Routes by hostname to each container
    |
    +-- [Portainer]        <- Docker management web UI
    +-- [Nextcloud]        <- Private cloud storage + calendar + contacts
    +-- [MariaDB]          <- Nextcloud database
    +-- [Redis]            <- Nextcloud memory cache
    +-- [Vaultwarden]      <- Password manager (Bitwarden-compatible)
    +-- [Ollama]           <- Local AI/LLM inference (Llama, Gemma, Mistral)
    +-- [Home Assistant]   <- Smart home (host network for mDNS/Zigbee)
    +-- [Pi-hole]          <- Network-wide DNS ad-blocking (port 53)
    +-- [WireGuard]        <- VPN server for remote access (port 51820)
    +-- [Prometheus]       <- Metrics time-series database
    +-- [Grafana]          <- Dashboards for all metrics
    +-- [Node Exporter]    <- Pi CPU/RAM/disk/temp metrics
    +-- [cAdvisor]         <- Per-container resource metrics
```

All services share Docker bridge network `proxy`.
Home Assistant uses `network_mode: host` for device discovery.
Pi-hole binds port 53 directly on the host.

---

## Services

| Service | Purpose | Access URL |
|---|---|---|
| Traefik | Reverse proxy + HTTPS | https://traefik.yourdomain.com |
| Portainer | Docker management UI | https://portainer.yourdomain.com |
| Nextcloud | Private cloud storage | https://cloud.yourdomain.com |
| Vaultwarden | Password manager | https://vault.yourdomain.com |
| Home Assistant | Smart home automation | http://192.168.1.50:8123 |
| Ollama | Local LLM inference | http://192.168.1.50:11434 |
| Pi-hole | DNS ad-blocking | http://192.168.1.50:8053/admin |
| WireGuard | VPN server | UDP 51820 |
| Prometheus | Metrics scraping + storage | http://192.168.1.50:9090 |
| Grafana | Metrics dashboards | https://grafana.yourdomain.com |
| Node Exporter | Host metrics | Internal only |
| cAdvisor | Container metrics | Internal only |
| MariaDB | Nextcloud database | Internal only |
| Redis | Nextcloud cache | Internal only |

---

## Repository Structure

```
pi4b-homelab/
+-- README.md
+-- .env.example
+-- .gitignore
+-- LICENSE
+-- CONTRIBUTING.md
+-- docs/
|   +-- SETUP_GUIDE.md
|   +-- ARCHITECTURE.md
|   +-- SKILLS.md
|   +-- TROUBLESHOOTING.md
+-- stacks/
|   +-- core/docker-compose.yml          # Traefik + Portainer
|   +-- monitoring/docker-compose.yml    # Prometheus + Grafana + exporters
|   +-- apps/docker-compose.yml          # Nextcloud + Vaultwarden + Ollama
|   +-- network/docker-compose.yml       # Pi-hole + WireGuard
|   +-- smarthome/docker-compose.yml     # Home Assistant
+-- config/
|   +-- traefik/traefik.yml
|   +-- traefik/dynamic.yml
|   +-- prometheus/prometheus.yml
|   +-- grafana/provisioning/datasources/prometheus.yml
|   +-- grafana/provisioning/dashboards/dashboard.yml
|   +-- pihole/custom.list
|   +-- wireguard/wg0.conf.example
+-- scripts/
    +-- setup.sh
    +-- backup.sh
    +-- update.sh
    +-- health-check.sh
```

---

## Quick Start

### Prerequisites
- Raspberry Pi 4B with Raspberry Pi OS Lite 64-bit on 2TB SSD
- SSD set as boot device via `raspi-config > Advanced > Boot Order > USB Boot`
- Static LAN IP set via router DHCP reservation
- (Optional) Free domain: [DuckDNS](https://www.duckdns.org)

### 1. Clone

```bash
git clone https://github.com/VK7160/pi4b-homelab.git
cd pi4b-homelab
```

### 2. Run setup script

```bash
chmod +x scripts/setup.sh
sudo bash scripts/setup.sh
```

### 3. Configure environment

```bash
cp .env.example .env
nano .env
```

### 4. Deploy stacks in order

```bash
docker compose -f stacks/core/docker-compose.yml up -d
docker compose -f stacks/monitoring/docker-compose.yml up -d
docker compose -f stacks/apps/docker-compose.yml up -d
docker compose -f stacks/network/docker-compose.yml up -d
docker compose -f stacks/smarthome/docker-compose.yml up -d
```

### 5. Verify all containers running

```bash
bash scripts/health-check.sh
```

---

## Deployment Order

| Step | Stack | Why |
|---|---|---|
| 1 | core | Traefik must exist before other services route through it |
| 2 | monitoring | Watch everything from the very start |
| 3 | apps | Nextcloud, Vaultwarden, Ollama |
| 4 | network | Pi-hole needs port 53, WireGuard needs 51820 |
| 5 | smarthome | Home Assistant uses host network - deploy last |

---

## Port Reference

| Port | Protocol | Service | Expose externally? |
|---|---|---|---|
| 80 | TCP | Traefik HTTP | Yes (redirects to HTTPS) |
| 443 | TCP | Traefik HTTPS | Yes |
| 51820 | UDP | WireGuard VPN | Yes |
| 8123 | TCP | Home Assistant | LAN only |
| 11434 | TCP | Ollama | LAN only |
| 8053 | TCP | Pi-hole UI | LAN only |
| 53 | UDP/TCP | Pi-hole DNS | LAN only |
| 9090 | TCP | Prometheus | LAN only |
| 9000/9443 | TCP | Portainer | Via Traefik |

---

## Backup Strategy

```bash
# Add to crontab -e
0 3 * * * /home/pi/pi4b-homelab/scripts/backup.sh >> /var/log/homelab-backup.log 2>&1
```

Backs up all named Docker volumes to `/mnt/backup/YYYY-MM-DD/`, retains 7 days.
See [scripts/backup.sh](scripts/backup.sh) for full details.

---

## Skills You Will Learn

See [docs/SKILLS.md](docs/SKILLS.md) for full breakdown with resume bullet points.

| Area | Technologies |
|---|---|
| Linux sysadmin | Raspberry Pi OS, systemd, SSH, ufw, fail2ban |
| Containerisation | Docker, Docker Compose, multi-stack architecture |
| Reverse proxy + TLS | Traefik v3, Let's Encrypt ACME |
| Monitoring | Prometheus, Grafana, Node Exporter, cAdvisor |
| Networking | WireGuard VPN, Pi-hole DNS, firewall rules |
| Self-hosted cloud | Nextcloud, MariaDB, Redis |
| Security | Vaultwarden, TLS hardening, rate limiting |
| AI/ML inference | Ollama, local LLM deployment |
| Smart home | Home Assistant, MQTT, automations |
| Scripting | Bash, backup, health monitoring, cron |
| IaC | Docker Compose as declarative infrastructure |
| Version control | Git, GitHub, structured repo management |

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

---

## License

MIT - see [LICENSE](LICENSE) for details.
