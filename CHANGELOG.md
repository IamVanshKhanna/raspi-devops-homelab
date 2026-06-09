# Changelog — homelab-prod

> All notable changes. Follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [v1.2.0] — In Progress (Secrets + Backup Automation)

### Added (v1.2.0-rc1)
- **Infisical secret manager** stack (PostgreSQL + Redis + Infisical)
- **Infisical environment variables** in `.env.example` (AUTH_SECRET, ENCRYPTION_KEY, REDIS_PASSWORD)
- **Infisical health check** in `scripts/health-check.sh` and `make verify-secrets`
- **Infisical phase** in deployment (`up-phase2`, `up-secrets`)
- **Backup restore test script** (`scripts/restore-test.sh`) for CI/CD
- **Backup wrapper with alerting** (`scripts/backup-wrapper.sh`, `scripts/backup-alert.sh`)
- **Backup verification target** (`make verify-backup`)
- **Restore test Makefile target** (`make restore-test`)
- **Enhanced backup-test GitHub Action** with actual restore verification
- **Infisical environment variables** in `.env.example`

### Changed
- **Deployment order**: Secrets (Infisical) now deploys before Monitoring (phase 2)
- **Makefile**: Added `up-secrets`, `verify-secrets`, `verify-backup`, `restore-test` targets
- **Health check**: Added Infisical container checks
- **Backup test workflow**: Now runs actual restore test with restic

### Security
- **Infisical** for centralized secret management (PostgreSQL + Redis backend)
- **Backup alerting** via Telegram on failure
- **Restore test** validates backup integrity weekly in CI

### Documentation
- Updated `.env.example` with Infisical variables
- Added Infisical to `SETUP_GUIDE.md` (pending)

---

## [v1.1.0] — 2026-06-09
### Added
- Loki + Promtail for centralized log aggregation
- Alertmanager with Telegram receivers
- Prometheus alerting rules (infrastructure, containers, system)
- Grafana dashboards: System Overview, Containers, RED metrics
- Uptime Kuma stack for external monitoring
- `make verify-v1` includes Loki, Alertmanager, Uptime Kuma checks
- ZRAM 2 GB swap configuration in setup.sh
- Prometheus scrape configs for Loki, Promtail, Alertmanager
- Prometheus alerting rules: infrastructure, containers, system

### Changed
- Prometheus scrape configs updated for Loki, Promtail, Alertmanager
- Health check validates log pipeline + alerting + uptime
- Monitoring stack updated to v1.1 (Loki 2.9, Promtail 2.9, Alertmanager 0.26)
- Setup.sh adds ZRAM swap, restic, zram-tools packages

### Security
- Alertmanager Telegram integration for critical/warning alerts
- Prometheus alerting rules for OOM, restarts, disk, CPU, temp

### Documentation
- VERSION_ROADMAP.md: v1.1 marked complete
- SETUP_GUIDE.md: v1.1 services (Loki, Promtail, Alertmanager, Uptime Kuma)
- New dashboards: System Overview, Containers

---

## [v1.0.0] — 2026-06-09
### Added
- Core stack: Traefik v3, Portainer, Pi-hole, Tailscale
- Monitoring: Prometheus, Grafana, Node Exporter, cAdvisor
- Apps: Nextcloud + MariaDB + Redis, Vaultwarden, Ollama (gemma:2b)
- Smarthome: Home Assistant (host network)
- Hermes Agent (headless) with homelab profile + skills
- Restic → Backblaze B2 backup with retention
- ZRAM 2 GB swap configuration
- Health check + verification scripts
- 3 ADRs (orchestration, network, memory)
- Architecture diagram (SVG)
- Demo transcript
- GitHub Actions: compose-validate, trivy-scan, backup-test
- Renovate config for auto Docker updates
- VERSION_ROADMAP.md

### Security
- All external HTTPS via Traefik (Let's Encrypt HTTP-01)
- Basic auth on Traefik/Portainer dashboards
- Pi-hole DNSSEC enabled
- Tailscale exit node + ACLs ready

### Documentation
- README with quick start
- HERMES_ON_PI.md install guide
- V1_CHECKLIST.md acceptance criteria

---

## [v1.3.0] — Planned (Hermes Agent Expansion)
### Added
- Skill: `backup-ops` (snapshots, restore, verify)
- Skill: `security-audit` (Trivy summary, CVE triage)
- Skill: `capacity-plan` (RAM/disk trends, forecast)
- Cronjob: daily health summary via Telegram
- Optional: TTS for critical alerts

---

## [v1.4.0] — Planned (Security + Compliance)
### Added
- Authelia SSO + 2FA (ForwardAuth on all external)
- Cloudflare DNS-01 ACME → wildcard certs, port 80 closed
- CrowdSec / fail2ban hardening
- SBOM (Syft) + signing (Cosign) in CI
- Threat model (STRIDE) + incident runbooks

---

## [v2.0.0] — Planned (Platform Evolution: Auth)
### Breaking
- All external access via Authelia ForwardAuth
- Infisical for all secrets (no `.env`)
- DNS-01 only (port 80 closed)
- Tailscale ACLs aligned with Authelia groups

### Added
- Per-service RBAC groups (`admin`, `family`, `services`)
- Automated cert renewal monitoring

---

## Template for Future Releases

```markdown
## [vX.Y.Z] — YYYY-MM-DD
### Added
- Feature/service with brief description
### Changed
- Modification to existing behavior
### Deprecated
- Soon-to-be-removed feature
### Removed
- Deleted feature
### Fixed
- Bug fix with issue reference
### Security
- Vulnerability addressed or hardening
```