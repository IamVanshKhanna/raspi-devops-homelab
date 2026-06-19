# homelab-prod

> **Production-grade multi-cluster homelab** — Raspberry Pi 4B/5 cluster (4/8 GB RAM, 2 TB NVMe) with cloud DR (AWS EKS/GCP GKE). K3s, GitOps (ArgoCD), Tailscale, Traefik, Linkerd mTLS, Prometheus/Thanos/Loki/Tempo, Nextcloud, Vaultwarden, Ollama, Home Assistant, Hermes AI agent. Full GitOps, DR, cost optimization, power management. All versioned, reproducible, and documented.

[![v2.10](https://img.shields.io/badge/version-v2.10-blue)](https://github.com/IamVanshKhanna/homelab-prod/releases/tag/v2.10)
[![CI](https://github.com/IamVanshKhanna/homelab-prod/actions/workflows/compose-validate.yml/badge.svg)](https://github.com/IamVanshKhanna/homelab-prod/actions/workflows/compose-validate.yml)
[![Supply Chain](https://github.com/IamVanshKhanna/homelab-prod/actions/workflows/supply-chain.yml/badge.svg)](https://github.com/IamVanshKhanna/homelab-prod/actions/workflows/supply-chain.yml)
[![Trivy](https://github.com/IamVanshKhanna/homelab-prod/actions/workflows/trivy-scan.yml/badge.svg)](https://github.com/IamVanshKhanna/homelab-prod/actions/workflows/trivy-scan.yml)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

---

## Architecture Overview

homelab-prod v2.10 is a **multi-cluster, production-grade homelab** with:

- **Primary**: Raspberry Pi 4B/5 K3s cluster (on-prem)
- **DR**: AWS EKS/GCP GKE with spot instances (70% cost savings)
- **GitOps**: ArgoCD ApplicationSet multi-cluster
- **Service Mesh**: Linkerd mTLS + Traefik ingress
- **Observability**: Thanos (metrics), Loki (logs), Tempo (traces)
- **Security**: Linkerd mTLS, Kyverno policies, Authelia SSO, Infisical secrets
- **DR**: Cross-region Velero, Submariner, Cloudflare DNS failover
- **Cost Ops**: Quotas, right-sizing, unused detection, spot DR, chargeback
- **Power Mgmt**: Pi CPU scaling, peripheral disable, monitoring

---

## Hardware

### Primary Site (on-prem)

| Component | Spec |
|-----------|------|
| **Control Plane** | Pi 4B 8GB (pi4-ctrl) — K3s control plane |
| **Workers** | 2× Pi 5 8GB (pi5-w1, pi5-w2) — Workloads |
| **Case** | DeskPi 3B Pro (fan auto, NVMe bay) |
| **Storage** | 2 TB NVMe SSD per Pi 5 (PCIe), 2 TB SATA SSD (Pi 4) |
| **Network** | Gigabit Ethernet + Tailscale mesh |
| **Idle Power** | ~10–15 W total |
| **OS** | Raspberry Pi OS Lite 64-bit (Bookworm) |

### Cloud DR (AWS EKS / GCP GKE)

| Component | Specification |
|-----------|---------------|
| **Platform** | AWS EKS (us-west-2) / GCP GKE (us-central1) |
| **Control Plane** | Managed EKS/GKE |
| **Workers** | Spot instances (t3.medium) — 3-10 nodes, auto-scaling |
| **Labels** | `lifecycle=spot`, `workload=spot-tolerant` |
| **Taints** | `dedicated=spot:NoSchedule` |
| **Cost Savings** | ~70% vs on-demand instances |

---

## Services (v2.10)

### Core Infrastructure

| Stack | Service | Replicas | RAM Limit | Access |
|-------|---------|----------|-----------|--------|
| **Ingress** | Traefik v3 + Linkerd mTLS | 2 | 256 MB | `*.homelab.local` (TLS) |
| **Auth** | Authelia + TOTP/WebAuthn | 1 | 256 MB | `auth.homelab.local` |
| **Secrets** | Infisical (PostgreSQL + Redis) | 1 | 512 MB | `secrets.homelab.local` |
| **Certs** | Cert-Manager + Let's Encrypt (DNS-01) | 1 | 128 MB | — |
| **DNS** | External-DNS + Cloudflare | 1 | 64 MB | — |
| **Proxy** | Exporter for hardware metrics | 1 | 64 MB | — |

### Core Platform

| Stack | Service | Replicas | RAM Limit | Access |
|-------|---------|----------|-----------|--------|
| **Cluster API** | CAPI + Metal3 (bare metal) | 1 | 256 MB | — |
| **ArgoCD** | GitOps + ApplicationSet (multi-cluster) | 1 | 512 MB | `argocd.homelab.local` |
| **Submariner** | Cross-cluster networking | — | 128 MB | — |
| **Lighthouse** | Cross-cluster service discovery | — | 128 MB | — |

### Observability (Thanos + Loki + Tempo)

| Stack | Service | Replicas | RAM Limit | Access |
|-------|---------|----------|-----------|--------|
| **Metrics** | Prometheus + Thanos Sidecar | 1 | 2 GB | `prometheus.homelab.local` |
| **Global Query** | Thanos Query (dedup, downsampling) | 2 | 512 MB | `thanos.homelab.local` |
| **Long-term Storage** | Thanos Store Gateway + S3 | 2 | 1 GB | — |
| **Compaction** | Thanos Compactor (downsampling) | 1 | 512 MB | — |
| **Alerting** | Thanos Ruler (global rules) | 2 | 256 MB | — |
| **Logs** | Loki (multi-tenant) + Promtail | 1 | 1 GB | `loki.homelab.local` |
| **Traces** | Tempo + OTEL Collector | 1 | 512 MB | `tempo.homelab.local` |
| **Visualization** | Grafana (dashboards, datasources) | 1 | 256 MB | `grafana.homelab.local` |
| **Alerting** | Alertmanager + Thanos Ruler | 1 | 128 MB | — |
| **Uptime** | Uptime Kuma | 1 | 128 MB | `uptime.homelab.local` |

### Applications

| Stack | Service | Replicas | RAM Limit | Access |
|-------|---------|----------|-----------|--------|
| **Files** | Nextcloud + MariaDB + Redis | 1 | 2 GB | `cloud.homelab.local` |
| **Passwords** | Vaultwarden | 1 | 256 MB | `vault.homelab.local` |
| **AI/ML** | Ollama (GPU offload, model registry) | 3 | 4 GB | `ai.homelab.local` |
| **Smarthome** | Home Assistant | 1 (host net) | 1 GB | `ha.homelab.local` |
| **Auth** | Authelia (OIDC, TOTP, WebAuthn) | 1 | 256 MB | `auth.homelab.local` |
| **Secrets** | Infisical | 1 | 512 MB | `secrets.homelab.local` |
| **Smarthome** | Home Assistant | 1 (host net) | 1 GB | `ha.homelab.local` |

### Security & Policy

| Stack | Service | Purpose |
|-------|---------|---------|
| **Policy** | Kyverno (12 policies) | Digest pinning, no :latest, limits, non-root, read-only rootfs, no host NS, capabilities |
| **Service Mesh** | Linkerd | mTLS mandatory, traffic split, authz policies |
| **SSO** | Authelia | OIDC, TOTP, WebAuthn, group-based (admin/family/services) |
| **Secrets** | Infisical | PostgreSQL + Redis, audit log, auto-rotation |
| **Certificates** | Cert-Manager | DNS-01 (Cloudflare), 90-day certs, port 80 closed |
| **Supply Chain** | Syft + Cosign + Trivy | SBOM (SPDX), keyless signing, CVE blocking |
| **Network Policy** | Calico + Kyverno | Default deny, 50+ explicit allow policies |

---

## v2.10 Cost Optimization Features

| Feature | Description | Savings |
|---------|-------------|---------|
| **Resource Quotas** | 4-tier quotas (P0-P3) across 12 namespaces | Prevents over-provisioning |
| **Right-Sizing** | Weekly VPA + Prometheus analysis (10%+ savings) | 10-30% CPU/Mem |
| **Unused Detection** | 8 categories (PVC, Secrets, Services, etc.) | $20-50/mo |
| **Spot DR Cluster** | EKS Spot (t3.medium) — 70% savings | ~$150-300/mo |
| **Cost Allocation** | Namespace/Team/Service chargeback | Full visibility |
| **Unused Detection** | 8 categories, PR creation | Automated cleanup |
| **Power Optimization** | Pi CPU scaling, peripherals off | 40-50% power reduction |
| **Backup Encryption** | Restic + Velero AES-256 verified | Compliance ready |

---

## v2.10 GitHub Actions (Automated)

| Workflow | Schedule | Purpose |
|----------|----------|---------|
| `supply-chain.yml` | Weekly + Push | Syft SBOM, Cosign sign, Trivy gate (CRITICAL block) |
| `rightsizing-analysis.yml` | Weekly Mon 6AM | VPA + Prometheus right-sizing |
| `unused-resource-detection.yml` | Weekly Sun 7AM | 8-category unused resource scan |
| `cost-allocation.yml` | Weekly Mon 5AM | Namespace/Team/Service chargeback |
| `dr-test-monthly.yml` | Monthly 1st 3AM | Critical services DR restore test |
| `dr-failover-quarterly.yml` | Quarterly 1st 4AM | Full DR failover + DNS failover |
| `incident-drill.yml` | Monthly 1st 4AM | 8-scenario incident response drill |
| `backup-encryption-verify.yml` | Weekly Sun 6AM | Restic/Velero/B2 encryption audit |
| `capacity-planning.yml` | Weekly Mon 6AM | 30/60/90d forecasting, disk/RAM exhaustion |
| `secrets-rotation.yml` | Monthly | Infisical secret rotation |

---

## Quick Start (on Pi)

```bash
# 1. Clone
git clone https://github.com/IamVanshKhanna/homelab-prod.git
cd homelab-prod

# 2. Configure
cp .env.example .env
# Edit .env with your domain, emails, tokens, B2/AWS keys

# 3. Bootstrap K3s + ArgoCD (single command)
make bootstrap

# 4. Deploy via ArgoCD (auto-sync)
# ArgoCD ApplicationSets deploy everything automatically

# 5. Verify
make verify-all
```

---

## Multi-Cluster GitOps (ArgoCD ApplicationSet)

```yaml
# Example: Deploy service to all production clusters
apiVersion: argoproj.io/v1alpha1
kind: ApplicationSet
metadata:
  name: production-services
spec:
  generators:
    - matrix:
        generators:
          - clusters:
              selector:
                matchLabels:
                  homelab.io/environment: production
          - git:
              repoURL: https://github.com/IamVanshKhanna/homelab-prod.git
              revision: HEAD
              directories:
                - path: config/argocd/services/production/*
  template:
    metadata:
      name: 'prod-{{path.basename}}-{{name}}'
    spec:
      project: homelab
      source:
        repoURL: https://github.com/IamVanshKhanna/homelab-prod.git
        targetRevision: HEAD
        path: '{{path}}'
      destination:
        server: '{{server}}'
```

---

## Disaster Recovery (v2.9+)

| Metric | P0 (Critical) | P1 (Important) | P2 (Standard) |
|--------|---------------|----------------|---------------|
| **RTO** | 4 hours | 12 hours | 24 hours |
| **RPO** | 6 hours | 12 hours | 24 hours |
| **Services** | Nextcloud, Vaultwarden, DBs, Auth | Home Assistant, Certs, Secrets | Monitoring, Logging |

### DR Automation
- **DNS Failover**: Cloudflare API (60s TTL) via GitHub Actions
- **Velero Restore**: Automated cross-region restore (S3 → EKS)
- **DNS Failover**: Automated Cloudflare DNS update (60s TTL)
- **Health Checks**: 8 critical services validated post-failover
- **Failback**: Automated with data sync verification

---

## Cost Optimization Summary

| Optimization | Monthly Savings | Annual Savings |
|--------------|-----------------|----------------|
| Spot DR Cluster | $150-300 | $2,000-3,500 |
| Right-Sizing | $50-150 | $600-1,800 |
| Unused Resources | $20-50 | $240-600 |
| Power Optimization | $10-20 | $120-240 |
| **Total Potential** | **$230-520** | **$2,700-6,140** |

---

## Power Optimization (Pi Hardware)

| Optimization | Power Savings | Monthly Savings |
|--------------|---------------|-----------------|
| CPU Governor (ondemand) | 15-20% | $0.30 |
| CPU Frequency Limit (1.5/2.0 GHz) | 10-15% | $0.18 |
| Disable HDMI/LEDs | 5-10% | $0.12 |
| Disable WiFi/BT (Ethernet) | 3-5% | $0.06 |
| SSD Power Management | 10-15% | $0.15 |
| **Total** | **40-50%** | **$0.80/mo ($9.60/yr per Pi)** |

---

## Quick Links

| Document | Description |
|----------|-------------|
| [Architecture](ARCHITECTURE.md) | Full system architecture |
| [Architecture Diagram](docs/architecture.svg) | System diagram |
| [ADR Index](docs/ADR-001-orchestration.md) | Architecture Decision Records |
| [Hermes on Pi](docs/HERMES_ON_PI.md) | AI agent install & skills |
| [DR Runbooks](docs/runbooks/) | Failover, failback, monthly tests |
| [Cost Optimization](docs/cost-optimization.md) | Quotas, spot, rightsizing, power |
| [Power Optimization](docs/power-optimization.md) | Pi CPU, peripherals, monitoring |
| [DR Runbooks](docs/runbooks/) | Failover, failback, monthly tests |

---

## Make Targets

```bash
# Core deployment
make bootstrap           # Bootstrap K3s + ArgoCD
make up-core             # Core stack (Traefik, Auth, Certs, DNS)
make up-monitoring       # Prometheus, Grafana, Loki, Tempo, Thanos
make up-apps             # Nextcloud, Vaultwarden, Ollama, HA
make up-smarthome        # Home Assistant
make up-all              # All stacks

# DR Operations
make backup              # Restic backup
make verify-backup       # Verify latest backup
make dr-test             # Monthly DR test
make dr-failover         # Full DR failover (DNS + Velero)
make dr-failback         # Failback to primary

# Cost & Optimization
make cost-report         # Weekly cost allocation
make rightsizing         # Right-sizing recommendations
make unused-detect       # Unused resource scan
make power-optimize      # Apply Pi power optimizations

# Verification
make verify-all          # Full health check
make verify-v1           # v1 acceptance criteria
make verify-v2           # v2 acceptance criteria
```

---

## Monitoring & Alerting

| Dashboard | URL |
|-----------|-----|
| **Grafana** | `https://grafana.homelab.local` |
| **Thanos Query** | `https://thanos.homelab.local` |
| **Loki (Logs)** | `https://loki.homelab.local` |
| **Tempo (Traces)** | `https://tempo.homelab.local` |
| **Prometheus** | `https://prometheus.homelab.local` |
| **Alertmanager** | `https://alertmanager.homelab.local` |
| **Grafana Power Dashboard** | `https://grafana.homelab.local/d/pi-power-monitoring` |
| **Cost Allocation** | `https://grafana.homelab.local/d/cost-allocation` |
| **Capacity Planning** | `https://grafana.homelab.local/d/capacity-planning` |

---

## License

MIT — see `LICENSE`