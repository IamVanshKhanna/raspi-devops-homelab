# homelab-prod

> **24/7 Raspberry Pi 4B (4 GB RAM, 2 TB SSD) homelab** — Docker Compose, Tailscale, Traefik, Prometheus/Grafana, Nextcloud, Vaultwarden, Ollama, Home Assistant, and a headless Hermes AI agent. All versioned, reproducible, and documented.

[![v1.0](https://img.shields.io/badge/version-v1.0-blue)](https://github.com/IamVanshKhanna/homelab-prod/releases/tag/v1.0)
[![CI](https://github.com/IamVanshKhanna/homelab-prod/actions/workflows/compose-validate.yml/badge.svg)](https://github.com/IamVanshKhanna/homelab-prod/actions/workflows/compose-validate.yml)
[![Trivy](https://github.com/IamVanshKhanna/homelab-prod/actions/workflows/trivy-scan.yml/badge.svg)](https://github.com/IamVanshKhanna/homelab-prod/actions/workflows/trivy-scan.yml)

---

## Hardware

| Component | Spec |
|-----------|------|
| SBC | Raspberry Pi 4B 4 GB RAM |
| Case | DeskPi 3B Pro (fan auto, SATA bay) |
| Storage | 2 TB 2.5" SATA SSD (USB 3.0 boot, no SD card) |
| Power | Official Pi 4 USB-C PSU (5V/3A) |
| OS | Raspberry Pi OS Lite 64-bit (Bookworm) |
| Network | Gigabit Ethernet + Tailscale mesh |
| Idle Power | ~5–10 W |

---

## Services (v1)

| Stack | Service | Access | RAM Limit |
|-------|---------|--------|-----------|
| **Core** | Traefik v3.0 | `traefik.domain` (TLS) | 128 MB |
| | Portainer 2.21 | `portainer.domain` | 256 MB |
| | Pi-hole 2024.07 | LAN `:8053` (DNS `:53`) | 256 MB |
| | Tailscale v1.68 | MagicDNS / Exit node | 64 MB |
| **Monitoring** | Prometheus 2.54 | `127.0.0.1:9090` | 512 MB |
| | Grafana 11.1 | `grafana.domain` | 256 MB |
| | Node Exporter 1.8 | `:9100` | 64 MB |
| | cAdvisor 0.49 | `:8080` | 128 MB |
| **Apps** | Nextcloud 29.0 | `cloud.domain` | 1 GB |
| | MariaDB 11.4 | internal | 512 MB |
| | Redis 7.2 | internal | 128 MB |
| | Vaultwarden 1.32 | `vault.domain` | 256 MB |
| | Ollama 0.3 + gemma:2b | `127.0.0.1:11434` | 2 GB |
| **Smarthome** | Home Assistant 2024.7 | LAN `:8123` (host net) | 512 MB |

**Total RAM budget:** ~3.8 GB / 4 GB (with 2 GB ZRAM swap)

---

## Quick Start (on Pi)

```bash
# 1. Clone
git clone https://github.com/IamVanshKhanna/homelab-prod.git
cd homelab-prod

# 2. Configure
cp .env.example .env
# Edit .env with your domain, emails, tokens, B2 keys

# 3. Deploy (phased)
make up-core
make up-monitoring
make up-apps
make up-smarthome

# 4. Pull LLM model
docker exec ollama ollama pull gemma:2b

# 5. Verify
make verify-v1
```

---

## Remote Access

- **SSH from anywhere:** `ssh vansh@pi4b-homelab` (via Tailscale MagicDNS)
- **Services:** All HTTPS via Traefik (`*.yourdomain.com`)
- **Exit node:** Route phone/laptop traffic through Pi via Tailscale

---

## Verification

```bash
make verify-v1
# Runs: health check, RAM < 3.9 GB, backup readability, Hermes responsiveness
```

---

## Backup

- **Tool:** Restic → Backblaze B2 (encrypted, deduplicated)
- **Schedule:** Daily incremental (cron), weekly verify
- **Retention:** 7 daily, 4 weekly, 6 monthly
- **Test:** `make verify-backup` passes

---

## Hermes AI Agent

- **Model:** `gemma:2b` (1.6 GB, ~15 tok/s on Pi 4)
- **Profile:** `homelab` with skills `homelab-ops`, `gitops-helper`
- **Access:** `hermes --profile homelab "health check"`
- **Capabilities:** Health summary, log inspection, safe restarts, CI proposals

---

## Documentation

| File | Description |
|------|-------------|
| `docs/ADR-001-orchestration.md` | Why Docker Compose over K3s |
| `docs/ADR-002-network-access.md` | Why Tailscale over WireGuard |
| `docs/ADR-003-memory.md` | ZRAM + limits + model choice |
| `docs/HERMES_ON_PI.md` | Install, profile, skills, systemd |
| `docs/V1_CHECKLIST.md` | v1 acceptance criteria |
| `docs/demo-transcript.md` | Recorded bring-up session |
| `docs/architecture.svg` | System diagram |

---

## GitHub Actions

| Workflow | Trigger | Purpose |
|----------|---------|---------|
| `compose-validate.yml` | Push/PR to compose/ | Validate all compose files |
| `trivy-scan.yml` | Weekly + push | Scan images for CRITICAL/HIGH CVEs |
| `backup-test.yml` | Weekly | Verify backup config exists |

---

## Renovate

Automated Docker image updates via `renovate.json` — grouped PRs, auto-merge on patch.

---

## Options Lab

See [homelab-options-lab](https://github.com/IamVanshKhanna/homelab-options-lab) for tool comparisons:
- Reverse proxies (Traefik vs NPM vs Caddy)
- VPNs (Tailscale vs WireGuard vs Headscale)
- Orchestration (Compose vs K3s vs Nomad)
- Auth (Authelia vs OAuth2-Proxy vs Keycloak)

---

## License

MIT — see `LICENSE`