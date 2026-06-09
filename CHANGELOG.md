# Changelog — homelab-prod

> All notable changes. Follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

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

## [v1.1.0] — Planned (Observability Hardening)
### Added
- Loki + Promtail for centralized logs
- Alertmanager with Telegram/email receivers
- Grafana dashboards: RED metrics, SLO panels, per-service
- Uptime Kuma external monitoring stack
- Log/alert verification in `make verify-v1`

### Changed
- Prometheus scrape configs include Loki/Promtail targets
- Health check validates log pipeline

---

## [v1.2.0] — Planned (Secrets + Backup Automation)
### Added
- Infisical secret manager (self-hosted)
- `.env` migration to Infisical + inject at deploy
- Automated weekly restore test in CI
- Backup failure alerting
- Secret rotation runbook

### Security
- No plaintext secrets in repo or container env
- Audit log for secret access

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