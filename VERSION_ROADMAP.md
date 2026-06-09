# Version Roadmap — homelab-prod

> Living document. Updated each release.

---

## Versioning Scheme
- **Major** (v1, v2): Architectural shifts, breaking changes, new stacks
- **Minor** (v1.1, v1.2): New services, features, non-breaking improvements
- **Patch** (v1.0.1): Bug fixes, dependency updates, doc corrections

---

## v1.x — Baseline (Current: v1.4 → v1.5 in progress)

| Version | Focus | Target | Status |
|---------|-------|--------|--------|
| **v1.0** | Production baseline | Day 1 | ✅ Released |
| **v1.1** | Observability hardening | 2 weeks | ✅ **Done** |
| **v1.2** | Secrets + backup automation | 4 weeks | ✅ **Done** |
| **v1.3** | Hermes agent expansion | 6 weeks | ✅ **Done** |
| **v1.4** | Security + compliance | 8 weeks | ✅ **Done** |
| **v1.5** | Supply chain hardening | 10 weeks | 🔄 **In Progress** |
| **v1.6** | Tracing + Automation | 12 weeks | 🔄 Planned |

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
- [ ] Migrate `.env` → Infisical, inject at deploy (Infisical CLI)
- [ ] Document secret rotation procedure

### v1.3 — Hermes Agent Expansion ✅ **COMPLETED**
- [x] Skill: `backup-ops` (list snapshots, trigger restore, verify)
- [x] Skill: `security-audit` (Trivy summary, CVE triage)
- [x] Skill: `capacity-plan` (RAM/disk trend, forecast)
- [x] Skill: `homelab-ops` enhancements (v1.1)
- [x] Skill: `gitops-helper` enhancements (v1.1)
- [x] ADR-005: Hermes Skills Architecture
- [x] HERMES_ON_PI.md updated with all 5 skills
- [ ] Cronjob: daily health summary via Telegram
- [ ] Voice TTS for critical alerts (optional)

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
- [ ] CrowdSec or fail2ban hardening (CrowdSec done)
- [ ] Document secret rotation procedure

### v1.5 — Supply Chain Hardening (Target: 10 weeks) 🔄 **In Progress**
- [x] **Syft SBOM** generation in CI (supply-chain.yml)
- [x] **Cosign keyless signing** (OIDC) in CI
- [x] **Trivy gate** in CI: fail on CRITICAL
- [x] **Renovate**: auto-merge only after Trivy pass
- [x] **Dependency Policy** document
- [x] **Dependency Policy Check** workflow (unpinned images, digest check)
- [x] **Daily quick Trivy scan** (HIGH+CRITICAL)
- [ ] Migrate images to digest pinning (`@sha256:`)
- [ ] SBOM attestation upload to registry
- [ ] Cosign verification in deploy pipeline

### v1.6 — Tracing + Automation (Target: 12 weeks)
- [ ] Tempo for distributed traces (OpenTelemetry sidecar)
- [ ] Grafana: logs + metrics + traces unified
- [ ] Cronjob: daily health summary via Telegram (Hermes)
- [ ] Voice TTS for critical alerts (optional)
- [ ] Correlation IDs across services

---

## v2.x — Platform Evolution (Quarterly)

| Version | Theme | Key Changes |
|---------|-------|-------------|
| **v2.0** | Supply Chain + Auth | Authelia, Infisical, DNS-01, SBOM, Cosign, port 80 closed |
| **v2.1** | Logging + Tracing | Loki, Tempo, distributed traces |
| **v2.2** | Multi-node Ready | K3s eval, external DB, shared storage |

### v2.0 — Supply Chain + Auth (Quarter 1)
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

### v2.1 — Logging + Tracing (Quarter 2)
- Loki + Promtail (replaces scattered `docker logs`)
- Tempo for traces (OpenTelemetry sidecar)
- Grafana: logs + metrics + traces unified
- Correlation IDs across services

### v2.2 — Multi-node Evaluation (Quarter 3)
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

## Current Sprint (v1.5 — Supply Chain Hardening)

```bash
# Branch
git checkout -b v1.5-supply-chain

# Remaining tasks for v1.5
# 1. Migrate all images to digest pinning (@sha256:)
# 2. SBOM attestation upload to registry
# 3. Cosign verification in deploy pipeline
# 4. PR → merge → tag v1.5
```

---

## Version Metadata (for automation)

```json
{
  "current": "v1.4",
  "next_minor": "v1.5",
  "next_major": "v2.0",
  "branches": {
    "main": "v1.4",
    "develop": "v1.5-wip"
  },
  "support": {
    "v1.x": "active",
    "v1.4": "released"
  }
}
```