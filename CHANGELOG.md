# Changelog — homelab-prod

> All notable changes. Follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [v1.6.0] — 2026-06-09
### Added
- **Tempo + OpenTelemetry Collector** stack for distributed tracing
- **cronjob-ops** skill: Scheduled health summaries, weekly reports via Telegram
- **tts-alerts** skill: Text-to-speech for critical alerts (edge-tts, espeak)
- **Health check**: Tempo + OTEL Collector checks
- **Tempo** stack (config/tempo, stacks/tracing)
- **OpenTelemetry Collector** (otel-collector) with OTLP receivers
- **make verify-tracing** target for tracing verification
- **Daily health summary** systemd timer (`scripts/daily-health-summary.sh`, `homelab-daily-summary.{service,timer}`)
- **Supply chain verification** in deploy pipeline (`scripts/verify-supply-chain.sh`)
- **Image digest pinning** helper (`scripts/pin-images-to-digest.sh`)
- **Infisical migration** helper (`scripts/migrate-to-infisical.sh`)
- **Secret rotation documentation** (`docs/SECRET_ROTATION.md`)

### Changed
- **Makefile**: Added tracing stack (phase 9), up-tracing, verify-tracing
- **Health check**: Added Tempo + OTEL Collector checks
- **HERMES_ON_PI.md**: Added cronjob-ops and tts-alerts skills (now 7 total)
- **cronjob-ops skill**: Daily health summaries, weekly reports via Telegram
- **tts-alerts skill**: edge-tts/espeak for critical alerts

### Automation
- **cronjob-ops**: Daily health summaries via Telegram, weekly reports
- **tts-alerts**: edge-tts/espeak for critical alerts (optional)
- **Hermes skills**: Now 7 auto-loaded (homelab-ops, gitops-helper, backup-ops, security-audit, capacity-plan, cronjob-ops, tts-alerts)

### Scripts & Tools
- `scripts/daily-health-summary.sh` - Daily health summary generator
- `scripts/homelab-daily-summary.{service,timer}` - Systemd timer for daily summary
- `scripts/verify-supply-chain.sh` - Supply chain verification in deploy
- `scripts/pin-images-to-digest.sh` - Image digest pinning helper
- `scripts/migrate-to-infisical.sh` - Infisical migration helper
- `scripts/daily-health-summary.sh` - Daily health summary generator
- `scripts/homelab-daily-summary.{service,timer}` - Systemd timer
- `docs/SECRET_ROTATION.md` - Secret rotation procedures

### Security
- Skills follow ADR-005 trust model (read-only by default, confirmation required)

### Documentation
- **HERMES_ON_PI.md**: Added cronjob-ops and tts-alerts skills
- **VERSION_ROADMAP.md**: v1.6 marked complete
- **CHANGELOG.md**: v1.6 released

---

## [v1.5.0] — 2026-06-09
### Added
- **Supply Chain Security workflow** (supply-chain.yml)
  - Syft SBOM generation for all images (SPDX-JSON)
  - Cosign keyless signing (OIDC) for images
  - Trivy gate: fails build on CRITICAL vulnerabilities
  - Dependency Policy check (unpinned images, digest pinning check)
  - Daily quick Trivy scan (HIGH+CRITICAL)
- **DEPENDENCY_POLICY.md** — Comprehensive supply chain policy document
- **Dependency Policy Check** in CI (unpinned images check, digest pinning verification)

### Changed
- Trivy workflow split: daily quick scan + weekly full supply chain pipeline
- CI pipeline now enforces supply chain security end-to-end

### Security
- CI fails on CRITICAL vulnerabilities
- Unpinned images (`:latest`) blocked in CI
- SBOMs generated for all images (SPDX-JSON)
- Images signed with Cosign (keyless OIDC)

### Scripts & Tools
- `scripts/pin-images-to-digest.sh` - Migrate tags to digest pinning
- `scripts/verify-supply-chain.sh` - Supply chain verification in deploy
- `scripts/migrate-to-infisical.sh` - Infisical migration helper

### Documentation
- **DEPENDENCY_POLICY.md** — Complete supply chain policy

---

## [v1.4.0] — 2026-06-09
### Added
- **Authelia SSO + 2FA** stack (Redis 7 + Authelia 4.38)
- **Traefik ForwardAuth** middleware for all external services
- **Cloudflare DNS-01** ACME configuration (closes port 80)
- **CrowdSec** stack for intrusion detection (PostgreSQL + CrowdSec)
- **Runbooks**: Service Down, Backup Failure, Security Incident
- **ADR-006**: Threat Model (STRIDE) documentation
- **Syft + Cosign** in CI for SBOM + signing (workflow)
- **Makefile**: auth, crowdsec stacks and verify targets

### Changed
- **Traefik ForwardAuth** middleware on all external routers
- **ACME**: HTTP-01 → DNS-01 (Cloudflare) - closes port 80
- **Health check**: Added Authelia, CrowdSec checks
- **Makefile**: Added auth, crowdsec stacks and verify targets
- **Deployment phases**: Now 8 phases (core → secrets → auth → monitoring → apps → smarthome → uptime → crowdsec)

### Security
- All external access via Authelia ForwardAuth + 2FA
- DNS-01 only (port 80 closed)
- CrowdSec parsing logs for suspicious patterns
- ADR-006: Threat Model (STRIDE) documented
- Runbooks: Service Down, Backup Failure, Security Incident

### Documentation
- **ADR-006**: Threat Model (STRIDE)
- **Runbooks**: Service Down, Backup Failure, Security Incident
- **SETUP_GUIDE.md**: Updated for v1.4 (Authelia, CrowdSec, DNS-01 setup)
- **CHANGELOG.md**: v1.4 released
- **VERSION_ROADMAP.md**: v1.4 marked complete

---

## [v1.3.0] — 2026-06-09
### Added
- **3 new Hermes skills** for homelab operations:
  - **backup-ops**: Restic/B2 snapshot management (list, verify, dry-run restore)
  - **security-audit**: Trivy/Grype CVE scanning and triage
  - **capacity-plan**: Disk/RAM forecasting with PromQL projections
- **ADR-005**: Hermes Skills Architecture — trust model, skill structure, security
- **dotfiles/hermes/skills/** — 3 new skill definitions with allowlists

### Changed
- **HERMES_ON_PI.md**: Updated with all 5 skills (2 existing + 3 new), auto-loaded
- **Profile config**: All 5 skills now auto-loaded
- **Hermes health check** includes skill metadata

### Security
- All new skills follow ADR-005 trust model:
  - Read-only by default
  - Confirmation required for any destructive actions
  - Explicit allowlists, explicit forbidden lists
  - Least privilege (no sudo, no docker stop/kill/rm)

### Skills Summary
| Skill | Category | Trust | Auto-load | Key Commands |
|-------|----------|-------|-----------|--------------|
| homelab-ops | homelab | Medium | ✅ | health, logs, safe restarts |
| gitops-helper | gitops | Medium | ✅ | propose CI/docs/compose changes |
| **backup-ops** | backup | High | ✅ | snapshots, verify, dry-run restore |
| **security-audit** | security | Medium | ✅ | trivy scan, CVE report |
| **capacity-plan** | capacity | Low | ✅ | disk/RAM forecasting, PromQL |

### Documentation
- **ADR-005**: Hermes Skills Architecture
- **HERMES_ON_PI.md**: Updated with all 5 skills, usage examples
- **dotfiles/hermes/skills/**: 3 new skill definitions

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

## [v1.7.0] — Planned (Multi-node + GPU Offload)
### Added
- K3s cluster on 2× Pi 4/5
- External PostgreSQL (Patroni) + Redis Cluster
- Longhorn or Ceph for shared storage
- GPU offload for Ollama (if Pi 5 with GPU)
- Ollama cluster for LLM inference scaling

---

## [v2.0.0] — Planned (Platform Evolution: Supply Chain + Auth)
### Breaking
- All external access via Authelia ForwardAuth
- Infisical for all secrets (no `.env`)
- DNS-01 only (port 80 closed)
- Tailscale ACLs aligned with Authelia groups

### Added
- Per-service RBAC groups (`admin`, `family`, `services`)
- Automated cert renewal monitoring
- Syft SBOM on every image build
- Cosign keyless signing (OIDC)
- Trivy gate in CI: fail on CRITICAL
- Renovate: auto-merge only after Trivy pass

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