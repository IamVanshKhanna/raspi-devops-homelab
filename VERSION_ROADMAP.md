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

## v2.x — Platform Evolution (Quarterly / 2-week sprints)

| Version | Focus | Target | Timeline | Estimated Date | Status |
|---------|-------|--------|----------|----------------|--------|
| **v2.0** | Supply Chain + Auth (BREAKING) | 4 weeks (Sprints 15-16) | 2026-12-22 – 2027-01-19 | 2027-01-19 | ✅ **Released** |
| **v2.1** | Logging + Tracing + GitOps | 4 weeks (Sprints 17-18) | 2027-01-19 – 2027-02-16 | 2027-02-16 | ✅ **Completed** |
| **v2.2** | Multi-node Ready | 4 weeks (Sprints 19-20) | 2027-02-16 – 2027-03-16 | 2027-03-16 | 🔄 **In Progress** |
| **v2.3** | Observability maturity | 4 weeks (Sprints 21-22) | 2027-03-16 – 2027-04-13 | 2027-04-13 | ✅ **Completed** |
| **v2.4** | Supply chain maturity | 4 weeks (Sprints 23-24) | 2027-04-13 – 2027-05-11 | 2027-05-11 | 🔄 **Planned** |
| **v2.5** | Security hardening | 4 weeks (Sprints 25-26) | 2027-05-11 – 2027-06-08 | 2027-06-08 | 🔄 **Planned** |
| **v2.6** | Operational excellence | 4 weeks (Sprints 25-26) | 2027-06-08 – 2027-07-06 | 2027-07-06 | 🔄 **Planned** |
| **v2.7** | Performance optimization | 4 weeks (Sprints 27-28) | 2027-07-06 – 2027-08-03 | 2027-08-03 | 🔄 **Planned** |
| **v2.8** | Multi-cluster readiness | 4 weeks (Sprints 29-30) | 2027-08-03 – 2027-09-30 | 2027-09-30 | 🔄 **Planned** |
| **v2.9** | Disaster recovery maturity | 4 weeks (Sprints 31-32) | 2027-09-30 – 2027-10-28 | 2027-10-28 | 🔄 **Planned** |
| **v2.10** | Cost optimization | 4 weeks (Sprints 35-36) | 2027-10-28 – 2027-11-25 | 2027-11-25 | 🔄 **Planned** |
| **v2.11** | Documentation refresh | 4 weeks (Sprints 37-38) | 2027-11-25 – 2027-12-23 | 2027-12-23 | 🔄 **Planned** |
| **v2.11** | Year-end polish, v2.x stabilization | 4 weeks (Sprints 39-40) | 2027-12-23 – 2028-01-20 | 2028-01-20 | 🔄 **Planned** |
| **v2.11** | v2.x stabilization, v3.0 prep | 4 weeks (Sprints 41-42) | 2028-01-20 – 2028-02-17 | 2028-02-17 | 🔄 **Planned** |

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
- [x] SLO Error Budget dashboard - `config/grafana/provisioning/dashboards/slo-error-budget.json`
- [x] Explicit GitHub Actions permissions - all workflows updated
- [x] Workflow validator script - `scripts/validate-workflows.py`

### v2.2 — Multi-node Ready (Month 3) 🔄 **In Progress**
- [x] K3s cluster setup script - `scripts/multi-node-setup.sh`
- [x] Multi-node documentation - `docs/MULTI_NODE_SETUP.md`
- [x] Multi-node setup script - `scripts/multi-node-setup.sh`
- [x] NetworkPolicies for zero-trust segmentation - `config/network-policies/`
- [x] NetworkPolicy README with traffic flow matrix
- [x] Automated deny/allow policy generation scripts
- [ ] K3s cluster on 2× Pi 4 (or Pi 5)
- [ ] External PostgreSQL (Patroni) + Redis Cluster
- [ ] Longhorn or Ceph for shared storage
- [ ] Decision: stay single-node or migrate

### v2.3 — Observability maturity (Month 5) ✅ **Completed**
- [x] SLO/SLI definitions for all services
- [x] Burn rate alerting
- [x] **Distributed tracing sampling policies** - `docs/DISTRIBUTED_TRACING_SAMPLING.md`
- [x] Log retention policies
- [x] SLO Error Budget dashboard
- [x] SLO dashboards for Grafana
- [x] NetworkPolicies for zero-trust
- [x] ArgoCD ApplicationSet for automated GitOps
- [x] ArgoCD health check script
- [x] Disaster recovery test script
- [x] **Correlation ID propagation across all services** - `docs/CORRELATION_ID_EXTRACTION.md`, `docs/DISTRIBUTED_TRACING_SAMPLING.md`
- [x] Promtail correlation ID extraction pipeline

### v2.4 — Supply chain maturity (Month 7) 🔄 **Planned**
- [ ] SBOM for all base images
- [ ] Cosign keyless signing for all images
- [ ] Trivy gate: block HIGH in production
- [ ] Renovate: group PRs by severity
- [ ] Dependency policy enforcement in CI

### v2.5 — Security hardening (Month 9) 🔄 **Planned**
- [ ] mTLS between all services (Linkerd/Istio Ambient)
- [ ] Network policies for all namespaces
- [ ] Kyverno/OPA policies for admission control
- [ ] Regular pen testing schedule
- [ ] Secrets rotation automation

### v2.6 — Operational excellence (Month 11) 🔄 **Planned**
- [ ] Runbook automation (Ansible/CLI)
- [ ] Chaos engineering (LitmusChaos)
- [ ] Capacity planning automation
- [ ] Incident response drills

### v2.7 — Performance optimization (Month 13) 🔄 **Planned**
- [ ] Query optimization for all databases
- [ ] Cache warming strategies
- [ ] CDN integration (Cloudflare)
- [ ] Compression optimization (Brotli/Zstd)

### v2.8 — Multi-cluster readiness (Month 15) 🔄 **Planned**
- [ ] Cluster API for cluster lifecycle
- [ ] Federated Prometheus/Loki
- [ ] Cross-cluster service discovery
- [ ] Disaster recovery to secondary region

### v2.9 — Disaster recovery maturity (Month 17) 🔄 **Planned**
- [ ] RTO/RPO documented for all services
- [ ] Automated failover testing
- [ ] Backup encryption verification
- [ ] Cross-region backup replication

### v2.10 — Cost optimization (Month 19) 🔄 **Planned**
- [ ] Resource quotas and limits per namespace
- [ ] Spot/preemptible node integration
- [ ] Right-sizing recommendations automation
- [ ] Unused resource detection

### v2.11 — Documentation refresh (Month 21) 🔄 **Planned**
- [ ] Architecture diagram refresh
- [ ] Runbook updates with new procedures
- [ ] API documentation (OpenAPI)
- [ ] Onboarding guide for new contributors

### v2.12 — v2.x stabilization, v3.0 prep (Month 23) 🔄 **Planned**
- [ ] Feature freeze
- [ ] Regression test suite execution
- [ ] Performance baseline establishment
- [ ] Release candidate preparation

---

## v3.x — Advanced Capabilities (6+ months)

| Version | Theme | Target | Timeline | Estimated Date | Status |
|---------|-------|--------|----------|----------------|--------|
| **v3.0** | AI/ML Platform | 8 weeks (Sprints 43-46) | 2028-03-17 – 2028-05-12 | 2028-05-12 | 🔄 **Planned** |
| **v3.1** | Edge/OT — Matter, Thread, Zigbee | 8 weeks (Sprints 47-50) | 2028-05-12 – 2028-07-07 | 2028-07-07 | 🔄 **Planned** |
| **v3.2** | Developer Platform | 8 weeks (Sprints 51-54) | 2028-07-07 – 2028-09-01 | 2028-09-01 | 🔄 **Planned** |

### v3.0 — AI/ML Platform (6+ months) 🔄 **Planned**
- [ ] Ollama cluster with GPU offload (Pi 5 / Jetson)
- [ ] RAG pipeline (vector DB + embedding models)
- [ ] Local LLM fine-tuning pipeline
- [ ] Model registry and versioning
- [ ] Inference API with rate limiting
- [ ] Model performance benchmarking

### v3.1 — Edge/OT (6+ months) 🔄 **Planned**
- [ ] Matter/Thread/Zigbee bridge (OpenThread/OTBR)
- [ ] Home Assistant Matter integration
- [ ] Zigbee2MQTT / ZHA unification
- [ ] Thread border router (OpenThread)
- [ ] Matter device provisioning automation

### v3.2 — Developer Platform (6+ months) 🔄 **Planned**
- [ ] Gitea + Drone/Woodpecker CI
- [ ] Preview environments per PR
- [ ] Ephemeral environments per feature branch
- [ ] GitOps with ArgoCD/Flux
- [ ] Developer self-service portal (Backstage)
- [ ] Preview env TTL and cleanup

---

## Release Cadence

| Line | Minor | Patch |
|------|-------|-------|
| v1.x | 2-week sprints (complete) | As needed |
| v2.x | 4-week quarters | As needed |

---

## Version Metadata (for automation)

```json
{
  "current": "v2.3",
  "next_minor": "v2.4",
  "next_major": "v3.0",
  "branches": {
    "main-v1": "v1.7",
    "develop-v2": "v2.3-wip"
  },
  "support": {
    "v1.x": "active",
    "v1.7": "released",
    "v2.x": "active",
    "v2.3": "completed"
  }
}
```