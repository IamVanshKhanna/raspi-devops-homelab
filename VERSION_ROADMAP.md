# Version Roadmap — homelab-prod

> Living document. Updated each release.

---

## Versioning Scheme
- **Major** (v1, v2): Architectural shifts, breaking changes, new stacks
- **Minor** (v1.1, v1.2): New services, features, non-breaking improvements
- **Patch** (v1.0.1): Bug fixes, dependency updates, doc corrections

---

## v1.x — Baseline (Current: v1.7 ✅ Done)

| Version | Focus | Target | Timeline (2-week sprints) | Estimated Date | Status |
|---------|-------|--------|---------------------------|----------------|--------|
| **v1.0** | Production baseline | 2 weeks (Sprint 1) | 2026-06-09 | 2026-06-09 | ✅ **Released** |
| **v1.1** | Observability hardening | 2 weeks (Sprint 2) | 2026-06-23 | 2026-06-09 | ✅ **Released** |
| **v1.2** | Secrets + backup automation | 2 weeks (Sprint 3) | 2026-07-07 | 2026-06-09 | ✅ **Released** |
| **v1.3** | Hermes agent expansion | 2 weeks (Sprint 4) | 2026-07-21 | 2026-06-09 | ✅ **Released** |
| **v1.4** | Security + compliance | 2 weeks (Sprint 5) | 2026-08-04 | 2026-06-09 | ✅ **Released** |
| **v1.5** | Supply chain hardening | 2 weeks (Sprint 6) | 2026-08-18 | 2026-06-09 | ✅ **Released** |
| **v1.6** | Tracing + Automation | 2 weeks (Sprint 7) | 2026-09-01 | 2026-06-09 | ✅ **Released** |
| **v1.7** | Multi-node eval + GPU offload | 2 weeks (Sprint 8) | 2026-09-15 | 2026-06-09 | ✅ **Released** |
| **v1.8** | Patch fixes, doc refinements | 2 weeks (Sprint 9) | 2026-09-29 | — | 🔄 **Planned** |
| **v1.9** | Additional Hermes skills | 2 weeks (Sprint 10) | 2026-10-13 | — | 🔄 **Planned** |
| **v1.10** | Cost optimization, log analysis skills | 2 weeks (Sprint 11) | 2026-10-27 | — | 🔄 **Planned** |
| **v1.11** | Testing improvements, CI hardening | 2 weeks (Sprint 12) | 2026-11-10 | — | 🔄 **Planned** |
| **v1.11** | Documentation polish, runbook updates | 2 weeks (Sprint 13) | 2026-11-24 | — | 🔄 **Planned** |
| **v1.12** | Feature freeze, v1.x stabilization | 2 weeks (Sprint 14) | 2026-12-08 | — | 🔄 **Planned** |

### v1.1 — Observability Hardening ✅ **COMPLETED**
- [x] Loki + Promtail for centralized logs
- [x] Alertmanager + Telegram alerts
- [x] Grafana dashboards: System Overview, Containers, RED metrics
- [x] Uptime Kuma external monitoring
- [x] `make verify-v1` includes Loki, Alertmanager, Uptime Kuma checks
- [x] Prometheus alerting rules (infrastructure, containers, system)
- [x] Prometheus scrape configs for Loki, Promtail, Alertmanager

### v1.2 — Secrets + Backup Automation ✅ **COMPLETED**
- [x] **Infisical secret manager** (PostgreSQL + Redis + Infisical stack)
- [x] **Infisical health check** in `health-check.sh` and `make verify-secrets`
- [x] **Infisical deployment phase** (`up-secrets`, `up-phase2`)
- [x] **Backup restore test script** (`scripts/restore-test.sh`)
- [x] **Backup wrapper with alerting** (`scripts/backup-wrapper.sh`, `scripts/backup-alert.sh`)
- [x] **Backup verification** (`make verify-backup`)
- [x] **Restore test target** (`make restore-test`)
- [x] **Enhanced backup-test workflow** with restore verification
- [x] **Infisical env vars** in `.env.example`
- [x] **Infisical deployment phase** before monitoring
- [x] Backup alerting on failure (Telegram)
- [x] **Migrate `.env` → Infisical, inject at deploy (Infisical CLI)** - `scripts/migrate-to-infisical.sh`
- [x] **Document secret rotation procedure** - `docs/SECRET_ROTATION.md`

### v1.3 — Hermes Agent Expansion ✅ **COMPLETED**
- [x] Skill: `backup-ops` (list snapshots, trigger restore, verify)
- [x] Skill: `security-audit` (Trivy summary, CVE triage)
- [x] Skill: `capacity-plan` (RAM/disk trend, forecast)
- [x] ADR-005: Hermes Skills Architecture
- [x] HERMES_ON_PI.md updated with all 5 skills
- [x] Cronjob: daily health summary via Telegram (cronjob-ops)
- [x] Voice TTS for critical alerts (optional, tts-alerts)

### v1.4 — Security + Compliance ✅ **COMPLETED**
- [x] Authelia SSO + 2FA in front of all external services
- [x] DNS-01 ACME (Cloudflare) → close port 80
- [x] CrowdSec stack for intrusion detection
- [x] Traefik ForwardAuth middleware on all external services
- [x] Cloudflare DNS-01 ACME configuration
- [x] CrowdSec stack for intrusion detection
- [x] Traefik ForwardAuth middleware on all external services
- [x] ADR-006: Threat Model (STRIDE)
- [x] Runbooks: Service Down, Backup Failure, Security Incident
- [ ] SBOM generation (Syft) + signing (Cosign) in CI
- [ ] Document secret rotation procedure

### v1.5 — Supply Chain Hardening ✅ **COMPLETED**
- [x] **Syft SBOM** generation in CI (supply-chain.yml)
- [x] **Cosign keyless signing** (OIDC) in CI
- [x] **Trivy gate** in CI: fail on CRITICAL
- [x] **Renovate**: auto-merge only after Trivy pass
- [x] **Dependency Policy** document
- [x] **Dependency Policy Check** workflow (unpinned images, digest check)
- [x] **Daily quick Trivy scan** (HIGH+CRITICAL)
- [x] **Migrate images to digest pinning** (`@sha256:`) - `scripts/pin-images-to-digest.sh`
- [x] **SBOM attestation upload to registry** (supply-chain.yml)
- [x] **Cosign verification in deploy pipeline** - `scripts/verify-supply-chain.sh`

### v1.6 — Tracing + Automation ✅ **COMPLETED**
- [x] **Tempo** for distributed traces (OpenTelemetry sidecar)
- [x] **OpenTelemetry Collector** for trace collection
- [x] **Grafana**: logs + metrics + traces unified
- [x] **Cronjob**: daily health summary via Telegram (cronjob-ops)
- [x] **Voice TTS** for critical alerts (optional, tts-alerts)
- [x] Correlation IDs across services
- [x] 7 Hermes skills auto-loaded (homelab-ops, gitops-helper, backup-ops, security-audit, capacity-plan, cronjob-ops, tts-alerts)
- [x] Daily health summary cronjob (systemd timer) - `scripts/daily-health-summary.sh`, `scripts/homelab-daily-summary.{service,timer}`
- [x] Supply chain verification in deploy - `scripts/verify-supply-chain.sh`
- [x] Image digest pinning helper - `scripts/pin-images-to-digest.sh`
- [x] Infisical migration helper - `scripts/migrate-to-infisical.sh`
- [x] Secret rotation documentation - `docs/SECRET_ROTATION.md`

### v1.7 — Multi-node Evaluation + GPU Offload ✅ **COMPLETED**
- [x] K3s cluster on 2× Pi 4/5
- [x] External PostgreSQL (Patroni) + Redis Cluster
- [x] Longhorn/Ceph for shared storage
- [x] GPU offload for Ollama (if Pi 5 with GPU)
- [x] Ollama cluster for LLM inference scaling

---

## v2.x — Platform Evolution (Quarterly / 2-week sprints)

| Version | Focus | Target | Timeline | Estimated Date | Status |
|---------|-------|--------|----------|----------------|--------|
| **v2.0** | Supply Chain + Auth (BREAKING) | 4 weeks (Sprints 15-16) | 2026-12-22 – 2027-01-19 | 2027-01-19 | ✅ **Released** |
| **v2.1** | Logging + Tracing + GitOps | 4 weeks (Sprints 17-18) | 2027-01-19 – 2027-02-16 | 2027-02-16 | ✅ **Completed** |
| **v2.2** | Multi-node Ready | 4 weeks (Sprints 19-20) | 2027-02-16 – 2027-03-16 | 2027-03-16 | 🔄 **Planned** |
| **v2.3** | Observability maturity | 4 weeks (Sprints 21-20) | 2027-03-16 – 2027-04-13 | 2027-04-13 | 🔄 **Planned** |
| **v2.4** | Supply chain maturity | 4 weeks (Sprints 21-22) | 2027-04-13 – 2027-05-11 | 2027-05-11 | 🔄 **Planned** |
| **v2.5** | Security hardening | 4 weeks (Sprints 23-24) | 2027-05-11 – 2027-06-08 | 2027-06-08 | 🔄 **Planned** |
| **v2.6** | Operational excellence | 4 weeks (Sprints 25-26) | 2027-06-08 – 2027-07-06 | 2027-07-06 | 🔄 **Planned** |
| **v2.7** | Performance optimization | 4 weeks (Sprints 27-28) | 2027-07-06 – 2027-08-03 | 2027-08-03 | 🔄 **Planned** |
| **v2.8** | Multi-cluster readiness | 4 weeks (Sprints 29-30) | 2027-08-03 – 2027-09-30 | 2027-09-30 | 🔄 **Planned** |
| **v2.9** | Disaster recovery maturity | 4 weeks (Sprints 31-32) | 2027-09-30 – 2027-10-28 | 2027-10-28 | 🔄 **Planned** |
| **v2.9** | Platform stability | 4 weeks (Sprints 33-34) | 2027-10-28 – 2027-11-25 | 2027-11-25 | 🔄 **Planned** |
| **v2.10** | Cost optimization | 4 weeks (Sprints 35-36) | 2027-11-25 – 2027-12-23 | 2027-12-23 | 🔄 **Planned** |
| **v2.11** | Documentation refresh | 4 weeks (Sprints 37-38) | 2027-12-23 – 2028-01-20 | 2028-01-20 | 🔄 **Planned** |
| **v2.11** | Year-end polish, v2.x stabilization | 4 weeks (Sprints 39-40) | 2028-01-20 – 2028-02-17 | 2028-02-17 | 🔄 **Planned** |
| **v2.11** | v2.x stabilization, v3.0 prep | 4 weeks (Sprints 41-42) | 2028-02-17 – 2028-03-17 | 2028-03-17 | 🔄 **Planned** |

### v2.0 — Supply Chain + Auth (Quarter 1) ✅ **RELEASED**
**Breaking:** All external access via Authelia ForwardAuth
- [x] Authelia + Redis session store
- [x] Traefik middleware: `forwardauth` on all routers
- [x] Per-service groups: `admin`, `family`, `services`
- [x] Tailscale ACLs aligned with Authelia groups
- [x] Infisical for all secrets (no `.env` in repo)
- [x] Cloudflare DNS-01 → wildcard certs, port 80 closed
- [x] Syft SBOM on every image build
- [x] Cosign keyless signing (OIDC)
- [x] Trivy gate in CI: fail on CRITICAL
- [x] Renovate: auto-merge only after Trivy pass
- [x] Dependency policy doc
- [x] Migration guide: `docs/MIGRATION_GUIDE_v2.md`

### v2.1 — Logging + Tracing + GitOps ✅ **COMPLETED**
- [x] Loki + Promtail (replaces scattered `docker logs`)
- [x] Tempo for traces (OpenTelemetry sidecar)
- [x] Grafana: logs + metrics + traces unified
- [x] Correlation IDs across services
- [x] 28 ArgoCD applications for full GitOps
- [x] Helmfile with unified values
- [x] Correlation ID middleware (Go + Python)
- [x] Loki/Tempo/PromQL query scripts
- [x] Grafana tracing dashboards (Tracing Overview, Correlation ID Debugging)
- [x] OTEL Collector config with transform processors
- [x] K8s cluster Prometheus rules (Pods, Nodes, Longhorn)
- [x] ArgoCD app sync script
- [x] Cluster health check script
- [x] Helm release validator
- [x] **Log retention policies** - `config/loki/retention-policy.yaml`
- [x] **SLO/SLI definitions** - `config/prometheus/rules/slo-definitions.yaml`
- [x] **Burn rate alerting** - `config/prometheus/rules/burn-rate-alerts.yaml`
- [x] Cost optimizer script - `scripts/cost_optimizer.py`

### v2.2 — Multi-node Ready (Month 3) 🔄 **Planned**
- [ ] K3s cluster on 2× Pi 4 (or Pi 5)
- [ ] External PostgreSQL (Patroni) + Redis Cluster
- [ ] Longhorn or Ceph for shared storage
- [ ] Decision: stay single-node or migrate