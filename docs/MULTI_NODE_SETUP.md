# Multi-Node K3s Cluster Setup

## Overview
Automated setup for a multi-node K3s cluster with HA PostgreSQL (Patroni), Redis Cluster, Longhorn distributed storage, and full observability stack.

## Prerequisites
- 2+ Raspberry Pi 4/5 (4GB+ RAM each)
- Raspberry Pi OS Lite 64-bit (Bookworm)
- Static IPs for all nodes
- Domain with Cloudflare DNS
- Backblaze B2 bucket for backups
- SSH keys exchanged between nodes

## Node Topology
| Node | Role | IP | Labels |
|------|------|-----|--------|
| node-1 | Control Plane + Worker | 192.168.1.50 | control-plane=true, worker=true |
| node-2 | Worker | 192.168.1.51 | worker=true |
| node-3 | Worker | 192.168.1.52 | worker=true |

## Quick Start
```bash
# On control plane (node-1)
sudo ./scripts/multi-node-setup.sh

# Enter credentials when prompted:
# - Cloudflare API Token
# - ACME Email (Let's Encrypt)
# - B2 Account ID & Application Key
```

## What Gets Installed

### Core Infrastructure
| Component | Version | Namespace | Purpose |
|-----------|---------|-----------|---------|
| K3s | v1.28.5+k3s1 | kube-system | Kubernetes distribution |
| Longhorn | v1.6.0 | longhorn-system | Distributed block storage |
| Cert-Manager | v1.13.0 | cert-manager | TLS certificates |
| External-DNS | v1.15.0 | external-dns | DNS management |

### Observability Stack
| Component | Version | Namespace | Purpose |
|-----------|---------|-----------|---------|
| Prometheus Stack | kube-prometheus-stack 58.0.0 | monitoring | Metrics, alerts |
| Grafana | 11.1.3 | monitoring | Dashboards |
| Loki Stack | 5.0.0 | logging | Log aggregation |
| Tempo | 2.4.0 | tracing | Distributed tracing |
| Promtail | 2.9.0 | logging | Log shipping |

### Databases (HA)
| Component | Version | Namespace | Replicas |
|-----------|---------|-----------|----------|
| PostgreSQL (Patroni) | 15 | databases | 3 |
| Redis Cluster | 7-alpine | databases | 3 |

### Operators
| Operator | Version | Namespace | Manages |
|----------|---------|-----------|---------|
| Postgres Operator | 1.13.0 | postgres-system | PostgreSQL clusters |
| Redis Operator | 1.1.0 | databases | Redis clusters |

## Storage Configuration
- **Storage Class**: Longhorn (default)
- **Replica Count**: 2 (default)
- **Backup Target**: Backblaze B2 (s3://homelab-backups@us-east-1)
- **Backup Schedule**: Daily at 3 AM

## TLS Configuration
- **ACME Challenge**: DNS-01 (Cloudflare)
- **Cluster Issuer**: letsencrypt-prod
- **Port 80**: CLOSED (pure DNS-01)
- **Wildcard Certs**: *.homelab.local

## Network Policies
- **CNI**: Flannel (default K3s)
- **Service Mesh**: None (Authelia ForwardAuth at ingress)
- **Ingress**: Traefik (disabled in K3s, deployed via Traefik chart)

## Post-Install Verification
```bash
# Check nodes
kubectl get nodes -o wide

# Check all pods
kubectl get pods -A

# Check storage
kubectl get pv,pvc -A

# Check databases
kubectl get postgresql -n databases
kubectl get redis -n databases

# Check Longhorn
kubectl get pods -n longhorn-system
```

## ArgoCD Applications
All applications are deployed via ArgoCD from `argocd/applications/`:
- Core: traefik, portainer, infisical
- Auth: authelia, authelia-db, authelia-redis
- Monitoring: prometheus, loki, tempo, alertmanager
- Apps: nextcloud, vaultwarden, ollama, homeassistant
- Uptime: uptime-kuma
- Security: crowdsec, crowdsec-db
- Infrastructure: longhorn, cert-manager, external-dns, postgres-operator, redis-operator

## Backup Configuration
| Target | Frequency | Retention |
|--------|-----------|-----------|
| Longhorn Volumes | Daily 3 AM | 7 daily, 4 weekly, 6 monthly |
| PostgreSQL (Patroni) | Continuous (WAL) | 30 days |
| Redis | Daily snapshot | 7 days |
| ConfigMaps/Secrets | Daily | 30 days |

## Failover Testing
```bash
# Test Longhorn replica failover
kubectl delete pod -n longhorn-system -l app=longhorn-manager

# Test PostgreSQL failover
kubectl exec -n databases homelab-postgres-0 -- patronictl failover homelab-postgres

# Test Redis failover
kubectl exec -n databases homelab-redis-0 -- redis-cli FAILOVER
```

## Monitoring & Alerting
- **Grafana**: https://grafana.homelab.local
- **Prometheus**: https://prometheus.homelab.local
- **Loki**: https://loki.homelab.local
- **Tempo**: https://tempo.homelab.local
- **Alertmanager**: https://alertmanager.homelab.local

## Credentials Management
All secrets stored in Infisical:
```
infisical.homelab.local
```
- Cloudflare API Token
- B2 Account ID & Key
- Database passwords
- API tokens

## Scaling
| Component | Min Replicas | Max Replicas | Scaling Trigger |
|-----------|--------------|--------------|-----------------|
| Ollama | 2 | 6 | CPU > 70%, Memory > 80% |
| PostgreSQL | 3 | 3 | Manual (Patroni) |
| Redis | 3 | 3 | Manual |
| Longhorn | N/A | N/A | Auto-rebalance |

## Upgrading
```bash
# K3s upgrade
curl -sfL https://get.k3s.io | INSTALL_K3S_VERSION="v1.29.x+k3s1" sh -s -

# Helm chart upgrades
helm repo update
helm upgrade --install longhorn longhorn/longhorn -n longhorn-system -f values.yaml
```

## Troubleshooting
| Issue | Check | Resolution |
|-------|-------|------------|
| Node not Ready | `kubectl describe node <node>` | Check k3s agent, container runtime |
| PVC Pending | `kubectl describe pvc <pvc>` | Check Longhorn replica availability |
| Cert not issued | `kubectl describe certificate` | Verify Cloudflare DNS, cert-manager logs |
| Longhorn degraded | `kubectl get volumes -n longhorn-system` | Wait for replica rebuild, check disk space |

## Resources
- [K3s Docs](https://docs.k3s.io)
- [Longhorn Docs](https://longhorn.io/docs)
- [Patroni Docs](https://patroni.readthedocs.io)
- [Cert Manager Docs](https://cert-manager.io/docs)