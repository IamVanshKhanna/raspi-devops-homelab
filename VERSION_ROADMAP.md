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

---

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
| **v2.0** | Supply Chain + Auth (BREAKING) | 4 weeks (Sprints 15-16) | 2026-12-22 – 2027-01-19 | 2027-01-19 | 🔄 **PLANNED — BREAKING CHANGES** |
| **v2.1** | Logging + Tracing | 4 weeks (Sprints 17-18) | 2027-01-19 – 2027-02-16 | 2027-02-16 | 🔄 **PLANNED** |
| **v2.2** | Multi-node Ready | 4 weeks (Sprints 19-20) | 2027-02-16 – 2027-03-16 | 2027-03-16 | 🔄 **PLANNED** |
| **v2.3** | Observability maturity | 4 weeks (Sprints 21-20) | 2027-03-16 – 2027-04-13 | 2027-04-13 | 🔄 **PLANNED** |
| **v2.4** | Supply chain maturity | 4 weeks (Sprints 21-22) | 2027-04-13 – 2027-05-11 | 2027-05-11 | 🔄 **PLANNED** |
| **v2.5** | Security hardening | 4 weeks (Sprints 23-24) | 2027-05-11 – 2027-06-08 | 2027-06-08 | 🔄 **PLANNED** |
| **v2.6** | Operational excellence | 4 weeks (Sprints 25-26) | 2027-06-08 – 2027-07-06 | 2027-07-06 | 🔄 **PLANNED** |
| **v2.7** | Performance optimization | 4 weeks (Sprints 27-28) | 2027-07-06 – 2027-08-03 | 2027-08-03 | 🔄 **PLANNED** |
| **v2.8** | Multi-cluster readiness | 4 weeks (Sprints 29-30) | 2027-08-03 – 2027-09-30 | 2027-09-30 | 🔄 **PLANNED** |
| **v2.9** | Disaster recovery maturity | 4 weeks (Sprints 31-32) | 2027-09-30 – 2027-10-28 | 2027-10-28 | 🔄 **PLANNED** |
| **v2.9** | Platform stability | 4 weeks (Sprints 33-34) | 2027-10-28 – 2027-11-25 | 2027-11-25 | 🔄 **PLANNED** |
| **v2.10** | Cost optimization | 4 weeks (Sprints 35-36) | 2027-11-25 – 2027-12-23 | 2027-12-23 | 🔄 **PLANNED** |
| **v2.11** | Documentation refresh | 4 weeks (Sprints 37-38) | 2027-12-23 – 2028-01-20 | 2028-01-20 | 🔄 **PLANNED** |
| **v2.11** | Year-end polish, v2.x stabilization | 4 weeks (Sprints 39-40) | 2028-01-20 – 2028-02-17 | 2028-02-17 | 🔄 **PLANNED** |
| **v2.11** | v2.x stabilization, v3.0 prep | 4 weeks (Sprints 41-42) | 2028-02-17 – 2028-03-17 | 2028-03-17 | 🔄 **PLANNED** |

### v2.0 — Supply Chain + Auth (Quarter 1) 🔄 **PLANNED — BREAKING CHANGES**
**Breaking:** All external access via Authelia ForwardAuth
- [ ] Authelia + Redis session store
- [ ] Traefik middleware: `forwardauth` on all routers
- [ ] Per-service groups: `admin`, `family`, `services`
- [ ] Tailscale ACLs aligned with Authelia groups
- [ ] Infisical for all secrets (no `.env` in repo)
- [ ] Cloudflare DNS-01 → wildcard certs, port 80 closed
- [ ] Syft SBOM on every image build
- [ ] Cosign keyless signing (OIDC)
- [ ] Trivy gate in CI: fail on CRITICAL
- [ ] Renovate: auto-merge only after Trivy pass
- [ ] Dependency policy doc
- [ ] Migration guide: `docs/MIGRATION_GUIDE_v2.md`
- [ ] ADR-008: v2.0 Breaking Migration — Docker Compose to K3s

### v2.1 — Logging + Tracing (Month 5) 🔄 **PLANNED**
- [ ] Loki + Promtail (replaces scattered `docker logs`)
- [ ] Tempo for traces (OpenTelemetry sidecar)
- [ ] Grafana: logs + metrics + traces unified
- [ ] Correlation IDs across services

### v2.2 — Multi-node Ready (Quarter 3) 🔄 **PLANNED**
- [ ] K3s cluster on 2× Pi 4 (or Pi 5)
- [ ] External PostgreSQL (Patroni) + Redis Cluster
- [ ] Longhorn or Ceph for shared storage
- [ ] Decision: stay single-node or migrate

### v2.3 — Observability Maturity (Month 7) 🔄 **PLANNED**
- [ ] SLO/SLI definitions for all services
- [ ] Burn rate alerting
- [ ] Distributed tracing sampling policies
- [ ] Log retention policies

### v2.4 — Supply Chain Maturity (Month 9) 🔄 **PLANNED**
- [ ] SBOM for all base images
- [ ] Cosign keyless signing for all images
- [ ] Trivy gate: block HIGH in production
- [ ] Renovate: group PRs by severity
- [ ] Dependency policy enforcement in CI

### v2.5 — Security Hardening (Month 11) 🔄 **PLANNED**
- [ ] mTLS between all services (Linkerd/Istio Ambient)
- [ ] Network policies for all namespaces
- [ ] Kyverno/OPA policies for admission control
- [ ] Regular pen testing schedule
- [ ] Secrets rotation automation

### v2.6 — Operational Excellence (Month 13) 🔄 **PLANNED**
- [ ] Runbook automation (Ansible/CLI)
- [ ] Chaos engineering (LitmusChaos)
- [ ] Capacity planning automation
- [ ] Incident response drills

### v2.7 — Performance Optimization (Month 15) 🔄 **PLANNED**
- [ ] Query optimization for all databases
- [ ] Cache warming strategies
- [ ] CDN integration (Cloudflare)
- [ ] Compression optimization (Brotli/Zstd)

### v2.8 — Multi-cluster Readiness (Month 17) 🔄 **PLANNED**
- [ ] Cluster API for cluster lifecycle
- [ ] Federated Prometheus/Loki
- [ ] Cross-cluster service discovery
- [ ] Disaster recovery to secondary region

### v2.9 — Disaster Recovery Maturity (Month 19) 🔄 **PLANNED**
- [ ] RTO/RPO documented for all services
- [ ] Automated failover testing
- [ ] Backup encryption verification
- [ ] Cross-region backup replication

### v2.10 — Cost Optimization (Month 21) 🔄 **PLANNED**
- [ ] Resource quotas and limits per namespace
- [ ] Spot/preemptible node integration
- [ ] Right-sizing recommendations automation
- [ ] Unused resource detection

### v2.11 — Documentation Refresh (Month 23) 🔄 **PLANNED**
- [ ] Architecture diagram refresh
- [ ] Runbook updates with new procedures
- [ ] API documentation (OpenAPI)
- [ ] Onboarding guide for new contributors

### v2.12 — v2.x Stabilization (Month 25) 🔄 **PLANNED**
- [ ] Feature freeze
- [ ] Regression test suite execution
- [ ] Performance baseline establishment
- [ ] Release candidate preparation

---

## v3.x — Advanced Capabilities (6+ months)

| Version | Theme | Target | Timeline | Estimated Date | Status |
|---------|-------|--------|----------|----------------|--------|
| **v3.0** | AI/ML Platform | 8 weeks (Sprints 43-46) | 2028-03-17 – 2028-05-12 | 2028-05-12 | 🔄 **PLANNED** |
| **v3.1** | Edge/OT — Matter, Thread, Zigbee | 8 weeks (Sprints 47-50) | 2028-05-12 – 2028-07-07 | 2028-07-07 | 🔄 **PLANNED** |
| **v3.2** | Developer Platform | 8 weeks (Sprints 51-54) | 2028-07-07 – 2028-09-01 | 2028-09-01 | 🔄 **PLANNED** |

### v3.0 — AI/ML Platform (6+ months) 🔄 **PLANNED**
- [ ] Ollama cluster with GPU offload (Pi 5 / Jetson)
- [ ] RAG pipeline (vector DB + embedding models)
- [ ] Local LLM fine-tuning pipeline
- [ ] Model registry and versioning
- [ ] Inference API with rate limiting
- [ ] Model performance benchmarking

### v3.1 — Edge/OT (6+ months) 🔄 **PLANNED**
- [ ] Matter/Thread/Zigbee bridge (OpenThread/OTBR)
- [ ] Home Assistant Matter integration
- [ ] Zigbee2MQTT / ZHA unification
- [ ] Thread border router (OpenThread)
- [ ] Matter device provisioning automation

### v3.2 — Developer Platform (6+ months) 🔄 **PLANNED**
- [ ] Gitea + Drone/Woodpecker CI
- [ ] Preview environments per PR
- [ ] Ephemeral environments per feature branch
- [ ] GitOps with ArgoCD/Flux
- [ ] Developer self-service portal (Backstage)
- [ ] Preview env TTL and cleanup

---

## Release Cadence

| Type | Frequency | Process |
|------|-----------|---------|
| Patch | As needed | Hotfix branch → PR → auto-patch Release |
| Minor | **2 weeks** | Feature branch → PR → CHANGELOG → tag v1.x |
| Major | **Quarterly (8 weeks)** | Epic branch → ADR → migration guide → tag v2.0 |

---

## Deprecation Policy
- Config formats: 2 minor versions notice
- Compose stacks: 1 major version notice
- Secrets migration: documented in ADR + runway

---

## Completed Versions Summary

| Version | Release Date | Lines Changed | Key Achievement |
|---------|--------------|---------------|-----------------|
| v1.0 | 2026-06-09 | ~2,000 | Production baseline (14 containers) |
| v1.1 | 2026-06-09 | ~1,500 | Observability stack (Loki, Alertmanager, Uptime Kuma) |
| v1.2 | 2026-06-09 | ~1,200 | Infisical secrets, backup automation |
| v1.3 | 2026-06-09 | ~800 | 3 new Hermes skills (5 total) |
| v1.4 | 2026-06-09 | ~1,000 | Authelia SSO, DNS-01, CrowdSec, runbooks |
| v1.5 | 2026-06-09 | ~800 | Supply chain (SBOM, Cosign, Trivy gate) |
| v1.6 | 2026-06-09 | ~800 | Tempo tracing, cronjob-ops, TTS alerts |
| v1.7 | 2026-06-09 | ~1,200 | K3s multi-node, GPU offload, Ollama cluster |

**Total: ~10,000+ lines of infrastructure code across 8 versions**

---

## Version Metadata (for automation)

```json
{
  "current": "v1.7",
  "next_minor": "v1.8",
  "next_major": "v2.0",
  "branches": {
    "main": "v1.7",
    "develop": "v2.0-wip"
  },
  "support": {
    "v1.x": "active",
    "v1.7": "released"
  }
}
```