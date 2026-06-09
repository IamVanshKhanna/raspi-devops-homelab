# Changelog — homelab-prod

> All notable changes. Follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [v1.2.0] — 2026-06-09
### Added
- **Infisical secret manager** stack (PostgreSQL 16 + Redis 7 + Infisical 1.7.1)
- **Infisical health check** in `health-check.sh` and `make verify-secrets`
- **Infisical deployment phase** (`up-secrets`, `up-phase2` before monitoring)
- **Backup restore test script** (`scripts/restore-test.sh`) for CI/CD
- **Backup wrapper with alerting** (`scripts/backup-wrapper.sh`, `scripts/backup-alert.sh`)
- **Backup verification target** (`make verify-backup`)
- **Restore test Makefile target** (`make restore-test`)
- **Enhanced backup-test GitHub Action** with actual restore verification
- **Infisical environment variables** in `.env.example`
- **ADR-004**: Secrets Management — Infisical over .env Files

### Changed
- **Deployment order**: Secrets (Infisical) now deploys before Monitoring (phase 2)
- **Makefile**: Added `up-secrets`, `verify-secrets`, `verify-backup`, `restore-test` targets
- **Health check**: Added Infisical container checks
- **Backup test workflow**: Now runs actual restore test with restic
- **Deployment phases**: Now 6 phases (core → secrets → monitoring → apps → smarthome → uptime)

### Security
- **Infisical** for centralized secret management (PostgreSQL + Redis backend)
- **Backup alerting** via Telegram on failure
- **Restore test** validates backup integrity weekly in CI
- **ADR-004** documents secrets management rationale

### Documentation
- **ADR-004**: Secrets Management — Infisical over .env Files
- **SETUP_GUIDE.md**: Updated for v1.2 with Infisical setup
- **CHANGELOG.md**: v1.2 released
- **VERSION_ROADMAP.md**: v1.2 marked complete
- **New Makefile targets**: `up-secrets`, `verify-secrets`, `verify-backup`, `restore-test`

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

## [v1.3.0] — In Progress (Hermes Agent Expansion)
### Added (v1.3.0-rc1)
- Skill: `backup-ops` (list snapshots, trigger restore, verify)
- Skill: `security-audit` (Trivy summary, CVE triage)
- Skill: `capacity-plan` (RAM/disk trend, forecast)
- Cronjob: daily health summary via Telegram
- Skill: `homelab-ops` enhancements (log search, metrics query)
- ADR-005: Hermes Skills Architecture

### Changed
- Hermes health check includes skill metadata
- Updated HERMES_ON_PI.md with new skills

### Security
- Skills run with least privilege (read-only by default)

---

## [v1.4.0] — Planned (Security + Compliance)
### Added
- Authelia SSO + 2FA (ForwardAuth on all external)
- Cloudflare DNS-01 ACME → wildcard certs, port 80 closed
- CrowdSec / fail2ban hardening
- SBOM generation (Syft) + signing (Cosign) in CI
- Threat model doc (STRIDE) + incident runbooks

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