# homelab-prod — Complete Project Summary

## 🎯 Project Vision
A production-grade, constraint-driven homelab on Raspberry Pi 4B (4GB RAM, 2TB SSD, DeskPi 3B Pro) demonstrating:
- **Constraint-driven engineering** (4GB RAM, 7W power, ARM64, headless)
- **Full SDLC** with GitOps, CI/CD, ADRs, runbooks
- **Security-first** architecture (STRIDE model, SSO, secrets, IDS)
- **Full observability** (metrics, logs, traces, alerts)
- **AI integration** (Hermes Agent with 7 skills)
- **Supply chain security** (SBOM, signing, vulnerability gates)

---

## 📦 Final Architecture (v1.6)

### Hardware
| Component | Spec |
|-----------|------|
| SBC | Raspberry Pi 4B 4GB RAM |
| Storage | 2TB SATA SSD (USB 3.0 boot) |
| Case | DeskPi 3B Pro (auto fan) |
| Network | Gigabit Ethernet + Tailscale mesh |
| Power | ~7W idle |

### Services (v1.6 — 17 containers / 9 stacks)

| Phase | Stack | Services | Memory Limit |
|-------|-------|----------|--------------|
| 1 | Core | Traefik, Portainer | 384 MB |
| 1 | Network | Pi-hole, WireGuard | 320 MB |
| 2 | Secrets | Infisical, PostgreSQL, Redis | 896 MB |
| 3 | Auth | Authelia, Redis | 320 MB |
| 4 | Monitoring | Prometheus, Grafana, Loki, Promtail, Alertmanager, Node Exporter, cAdvisor | 1.2 GB |
| 5 | Apps | Nextcloud, MariaDB, Redis, Vaultwarden, Ollama (gemma:2b) | 3.8 GB |
| 6 | Smarthome | Home Assistant (host net) | 512 MB |
| 7 | Uptime | Uptime Kuma | 128 MB |
| 8 | Security | CrowdSec, PostgreSQL | 384 MB |
| 9 | Tracing | Tempo, OpenTelemetry Collector | 768 MB |

**Total RAM Budget**: ~3.6 GB / 4 GB (with 2GB ZRAM swap buffer)

---

## 🧩 Hermes Agent (v1.6 — 7 Skills)

| Skill | Category | Trust | Key Commands |
|-------|----------|-------|--------------|
| homelab-ops | homelab | Medium | health, logs, safe restarts |
| gitops-helper | gitops | Medium | propose CI/docs/compose |
| backup-ops | backup | High | snapshots, verify, dry-run restore |
| security-audit | security | Medium | trivy scan, CVE report |
| capacity-plan | capacity | Low | disk/RAM forecasting, PromQL |
| **cronjob-ops** | homelab | Medium | daily summary, weekly report |
| **tts-alerts** | homelab | Medium | speak alert, read summary |

All skills follow **ADR-005 trust model**: read-only by default, confirmation required for destructive actions, explicit allowlists.

---

## 🔒 Security Achievements

| Feature | Implementation |
|---------|----------------|
| **Port 80 CLOSED** | DNS-01 challenge only (Cloudflare) |
| **SSO + 2FA** | Authelia ForwardAuth on all external routes |
| **Secrets** | Infisical (PostgreSQL + Redis backend) |
| **Intrusion Detection** | CrowdSec (log parsing + Telegram alerts) |
| **Threat Model** | STRIDE documented in ADR-006 |
| **Runbooks** | Service Down, Backup Failure, Security Incident |
| **Supply Chain** | Syft SBOM + Cosign signing + Trivy gate |

---

## 📊 Observability Stack

| Component | Purpose |
|-----------|---------|
| **Prometheus** | Metrics collection (30d retention) |
| **Grafana** | Dashboards: System Overview, Containers |
| **Loki + Promtail** | Centralized log aggregation |
| **Alertmanager** | Telegram alerts (critical/warning) |
| **Tempo** | Distributed tracing |
| **OTel Collector** | Trace collection via OTLP |
| **Uptime Kuma** | External uptime monitoring |
| **Prometheus Rules** | 18 alerting rules (infra, containers, system) |

---

## 🔄 CI/CD Pipeline

| Workflow | Trigger | Purpose |
|----------|---------|---------|
| compose-validate.yml | Push/PR to stacks/ | Validate all compose files |
| trivy-scan.yml | Daily + push | Quick vulnerability scan |
| supply-chain.yml | Weekly + push | SBOM, Cosign sign, Trivy gate, dependency policy |
| backup-test.yml | Weekly (Sun 5AM) | Restore test verification |

---

## 📚 Documentation Library

| Document | Purpose |
|----------|---------|
| **ADR-001** | Orchestration: Docker Compose over K3s |
| **ADR-002** | Network Access: Tailscale over WireGuard |
| **ADR-003** | Memory: ZRAM + limits + small model |
| **ADR-004** | Secrets: Infisical over .env |
| **ADR-005** | Hermes Skills Architecture |
| **ADR-006** | Threat Model (STRIDE) |
| **Runbooks** | Service Down, Backup Failure, Security Incident |
| **SETUP_GUIDE.md** | Phase-by-phase deployment |
| **HERMES_ON_PI.md** | Agent install + 7 skills |
| **DEPENDENCY_POLICY.md** | Supply chain governance |
| **VERSION_ROADMAP.md** | v1.0 → v3.2 plan |
| **CHANGELOG.md** | Keep a Changelog format |
| **Architecture SVG** | System diagram |

---

## 🚀 Deployment Commands

```bash
# On Pi (after setup.sh)
cd homelab-prod
make up-all          # Deploy all 9 phases
make verify-v1       # Full health check
make backup          # Run backup
make restore-test    # Test restore
```

---

## 📈 Version History

| Version | Date | Focus | Containers |
|---------|------|-------|------------|
| v1.0 | 2026-06-09 | Production baseline | 14 |
| v1.1 | 2026-06-09 | Observability | 18 |
| v1.2 | 2026-06-09 | Secrets + Backup | 20 |
| v1.3 | 2026-06-09 | Hermes Skills (5) | 20 |
| v1.4 | 2026-06-09 | Security (Authelia, CrowdSec) | 22 |
| v1.5 | 2026-06-09 | Supply Chain | 22 |
| **v1.6** | **2026-06-09** | **Tracing + Automation (7 skills)** | **23** |

---

## 🔮 Roadmap (v1.7 → v3.2)

| Version | Target | Focus |
|---------|--------|-------|
| v1.7 | 14 weeks | K3s cluster, GPU offload |
| v2.0 | Quarter 1 | Supply Chain + Auth (Breaking) |
| v2.1 | Quarter 2 | Tempo + OpenTelemetry |
| v2.2 | Quarter 3 | Multi-node (K3s, Patroni, Longhorn) |
| v3.0 | 6+ months | AI/ML Platform (Ollama cluster, RAG) |
| v3.1 | 6+ months | Edge/OT (Matter, Thread, Zigbee) |
| v3.2 | 6+ months | Developer Platform (Gitea, CI) |

---

## 🏆 Portfolio Highlights

| Category | Evidence |
|----------|----------|
| **Constraint Engineering** | 4GB RAM budget, ZRAM, model selection |
| **Full SDLC** | ADRs → CI/CD → Runbooks → Releases |
| **Security Engineering** | STRIDE, SSO, Secrets, IDS, Supply Chain |
| **Observability** | Metrics + Logs + Traces + Alerts |
| **Automation** | Hermes (7 skills), Cronjobs, TTS |
| **Documentation** | 6 ADRs, 3 Runbooks, 23 docs |
| **GitOps** | Compose, Renovate, Renovate gate, Supply chain |

---

## 🔗 Repositories

| Repo | URL | Visibility |
|------|-----|------------|
| **homelab-prod** | https://github.com/IamVanshKhanna/homelab-prod | Private |
| **homelab-options-lab** | https://github.com/IamVanshKhanna/homelab-options-lab | Public |

---

*Last Updated: 2026-06-09 | v1.6 Released*