# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

---

## [Unreleased]

---

## [1.1.0] - 2026-06-06

### Fixed
- `config/traefik/traefik.yml`: Replace hardcoded `email:` string with `${ACME_EMAIL}` environment variable
- `config/traefik/traefik.yml`: Enable access logging to `/logs/access.log`; enable Prometheus metrics endpoint
- `.gitignore`: Replace Python boilerplate with Docker/homelab-specific rules (secrets, TLS certs, logs, SSD data dirs, SSH keys)
- `stacks/apps/docker-compose.yml`: Add `apps_internal` bridge network to isolate MariaDB and Redis from the Traefik proxy network
- `stacks/apps/docker-compose.yml`: Add `healthcheck` on MariaDB and Redis; `nextcloud` now uses `condition: service_healthy`
- `stacks/apps/docker-compose.yml`: Bind Ollama to `127.0.0.1:11434` instead of `0.0.0.0`
- `scripts/setup.sh`: Use `$SUDO_USER` to detect target username instead of hardcoding `pi`
- `scripts/backup.sh`: Replace `docker volume ls` wildcard with explicit named volume list; skip ollama, prometheus, and traefik_certs volumes

### Changed
- All Docker image tags pinned to specific versions (no more `:latest`):
  - `portainer/portainer-ce:2.21.0`
  - `mariadb:11.4`
  - `redis:7.2-alpine`
  - `vaultwarden/server:1.32.0`
  - `ollama/ollama:0.3.14`
  - `prom/prometheus:v2.53.0`
  - `grafana/grafana:11.1.0`
  - `prom/node-exporter:v1.8.1`
  - `gcr.io/cadvisor/cadvisor:v0.49.1`
  - `pihole/pihole:2024.07.0`
  - `linuxserver/wireguard:1.0.20210914`
- All stacks: Add `mem_limit` and `cpus` resource constraints to every container
- `stacks/monitoring/docker-compose.yml`: Bind Prometheus to `127.0.0.1:9090` instead of `0.0.0.0`
- `stacks/core/docker-compose.yml`: Pass `ACME_EMAIL` as environment variable to Traefik container

### Added
- `.github/workflows/lint.yml`: CI pipeline — YAML lint, `docker compose config` validation for all 5 stacks, ShellCheck on bash scripts, `:latest` tag detection
- `.github/ISSUE_TEMPLATE/bug_report.md`: Structured bug report template
- `.github/ISSUE_TEMPLATE/feature_request.md`: Feature request template
- `.github/PULL_REQUEST_TEMPLATE.md`: PR checklist with stack, ARM64 test, and CI pass requirements

---

## [1.0.0] - 2026-06-06

### Added
- Initial release: full homelab stack on Raspberry Pi 4B 4GB + 2TB SSD
- Stacks: core (Traefik v3 + Portainer), monitoring (Prometheus + Grafana + Node Exporter + cAdvisor), apps (Nextcloud + MariaDB + Redis + Vaultwarden + Ollama), network (Pi-hole + WireGuard), smarthome (Home Assistant)
- Scripts: `setup.sh`, `backup.sh`, `update.sh`, `health-check.sh`
- Config: Traefik static + dynamic config, Prometheus scrape config, Grafana provisioning, Pi-hole custom DNS, WireGuard example
- Docs: `README.md`, `SETUP_GUIDE.md`, `ARCHITECTURE.md`, `SKILLS.md`, `TROUBLESHOOTING.md`
- MIT License
