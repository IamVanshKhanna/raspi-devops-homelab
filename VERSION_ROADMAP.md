# Version Roadmap — homelab-prod

> Living document. Updated each release.

---

## Versioning Scheme
- **Major** (v1, v2): Architectural shifts, breaking changes, new stacks
- **Minor** (v1.1, v1.2): New services, features, non-breaking improvements
- **Patch** (v1.0.1): Bug fixes, dependency updates, doc corrections

---

## v1.x — Baseline (Current: v1.7 ✅ Done)

| Version | Focus | Target | Status |
|---------|-------|--------|--------|
| **v1.0** | Production baseline | Day 1 | ✅ **Released** |
| **v1.1** | Observability hardening | 2 weeks | ✅ **Done** |
| **v1.2** | Secrets + backup automation | 4 weeks | ✅ **Done** |
| **v1.3** | Hermes agent expansion | 6 weeks | ✅ **Done** |
| **v1.4** | Security + compliance | 8 weeks | ✅ **Done** |
| **v1.5** | Supply chain hardening | 10 weeks | ✅ **Done** |
| **v1.6** | Tracing + Automation | 12 weeks | ✅ **Done** |
| **v1.7** | Multi-node eval + GPU offload | 14 weeks | ✅ **Done** |

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

## v2.x — Platform Evolution (Quarterly)

| Version | Theme | Key Changes |
|---------|-------|-------------|
| **v2.0** | Supply Chain + Auth | Authelia, Infisical, DNS-01, SBOM, Cosign, port 80 closed |
| **v2.1** | Logging + Tracing | Loki, Tempo, distributed traces |
| **v2.2** | Multi-node Ready | K3s eval, external DB, shared storage |

### v2.0 — Supply Chain + Auth (Quarter 1) 🔄 **PLANNED — BREAKING CHANGES**
**Breaking:** All external access via Authelia ForwardAuth
- Authelia + Redis session store
- Traefik middleware: `forwardauth` on all routers
- Per-service groups: `admin`, `family`, `services`
- Tailscale ACLs aligned with Authelia groups
- Infisical for all secrets (no `.env` in repo)
- Cloudflare DNS-01 → wildcard certs, port 80 closed
- Syft SBOM on every image build
- Cosign keyless signing (OIDC)
- Trivy gate in CI: fail on CRITICAL
- Renovate: auto-merge only after Trivy pass
- Dependency policy doc

### v2.1 — Logging + Tracing (Month 5)
- Loki + Promtail (replaces scattered `docker logs`)
- Tempo for traces (OpenTelemetry sidecar)
- Grafana: logs + metrics + traces unified
- Correlation IDs across services

### v2.2 — Multi-node Ready (Quarter 3)
- K3s cluster on 2× Pi 4 (or Pi 5)
- External PostgreSQL (Patroni) + Redis Cluster
- Longhorn or Ceph for shared storage
- Decision: stay single-node or migrate

---

## v3.x — Advanced Capabilities (6+ months)

| Version | Theme |
|---------|-------|
| **v3.0** | AI/ML Platform — Ollama cluster, GPU offload, RAG pipeline |
| **v3.1** | Edge/OT — Home Assistant + Zigbee + Thread, Matter bridge |
| **v3.2** | Developer Platform — Gitea, Drone/Woodpecker CI, preview envs |

---

## Release Cadence

| Type | Frequency | Process |
|------|-----------|---------|
| Patch | As needed | Hotfix branch → PR → auto-patch Release |
| Minor | Monthly | Feature branch → PR → CHANGELOG → tag v1.x |
| Major | Quarterly | Epic branch → ADR → migration guide → tag v2.0 |

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
| **v1.7** | **2026-06-09** | **~1,200** | **K3s multi-node, GPU offload, Ollama cluster** |

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