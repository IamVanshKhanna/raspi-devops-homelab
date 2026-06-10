# Disaster Recovery Runbook - Service RTO/RPO Matrix

## Overview
This document defines Recovery Time Objectives (RTO) and Recovery Point Objectives (RPO) for all homelab services, organized by criticality tier.

## Service Tiers

| Tier | Description | RTO Target | RPO Target | Strategy |
|------|-------------|------------|------------|----------|
| **P0 - Critical** | Revenue-generating, user-facing, data-critical | 4 hours | 6 hours | Warm standby + Velero sync |
| **P1 - Important** | Core infrastructure, auth, secrets | 12 hours | 12 hours | Velero + ArgoCD |
| **P2 - Standard** | Monitoring, logging, tracing | 24 hours | 24 hours | Velero |
| **P3 - Optional** | Chaos engineering, benchmarks | 72 hours | 72 hours | Scheduled restore test |

---

## P0 - Critical Services (RTO: 4h, RPO: 6h)

| Service | Namespace | Data Type | Backup Method | Restore Priority | Validation |
|---------|-----------|-----------|---------------|------------------|------------|
| **Nextcloud** | apps | Files + DB (PostgreSQL) | Restic (files) + Velero (K8s) + pg_dump | 1 | Login, file sync, share access |
| **Vaultwarden** | apps | DB (SQLite) + attachments | Restic + Velero | 2 | Login, vault access, sync |
| **PostgreSQL** | databases | All application DBs | Velero + pg_dump + Patroni | 1 | pg_isready, query test |
| **Redis** | databases | Sessions, cache, queues | Velero + RDB/AOF | 2 | redis-cli ping, key count |
| **Authelia** | auth | User DB + sessions | Velero + Restic (config) | 1 | SSO login, 2FA |
| **Infisical** | secrets | All secrets | Velero + Restic (encrypted export) | 1 | Secret read/write |
| **Traefik** | traefik | Config + certs | Velero + ACME cert backup | 1 | HTTPS access, cert validity |

### Nextcloud Detailed Recovery
```bash
# 1. Restore PostgreSQL database
velero restore create --from-backup <backup> --include-namespaces databases --namespace-mappings databases:dr-test

# 2. Restore Nextcloud PVC data
restic restore latest --target /mnt/restore/nextcloud --include /mnt/data/nextcloud

# 3. Deploy Nextcloud to DR namespace
helm upgrade --install nextcloud nextcloud/nextcloud -n dr-test --set externalDatabase.host=postgresql.databases

# 4. Run occ maintenance:mode --off
kubectl exec -n dr-test deploy/nextcloud -- occ maintenance:mode --off
```

### Vaultwarden Detailed Recovery
```bash
# 1. Restore SQLite database
velero restore create --from-backup <backup> --include-namespaces apps --namespace-mappings apps:dr-test

# 2. Verify vaultwarden can read database
kubectl exec -n dr-test deploy/vaultwarden -- sqlite3 /data/db.sqlite3 "SELECT COUNT(*) FROM ciphers;"
```

---

## P1 - Important Services (RTO: 12h, RPO: 12h)

| Service | Namespace | Data Type | Backup Method | Restore Priority | Validation |
|---------|-----------|-----------|---------------|------------------|------------|
| **Home Assistant** | smarthome | Config + SQLite DB | Restic + Velero | 3 | Dashboard loads, entities respond |
| **Cert-Manager** | cert-manager | Certificates + ACME | Velero + cert backup | 2 | Cert validity, renewal works |
| **External-DNS** | external-dns | DNS records | Velero | 3 | DNS records resolve |
| **Submariner** | submariner-operator | Cluster connections | Velero | 3 | Cross-cluster connectivity |

### Home Assistant Detailed Recovery
```bash
# 1. Restore config directory
restic restore latest --target /mnt/restore/homeassistant --include /mnt/data/homeassistant

# 2. Deploy Home Assistant
helm upgrade --install homeassistant homeassistant/homeassistant -n dr-test \
  --set persistence.enabled=true \
  --set persistence.existingClaim=home-assistant-data

# 3. Verify core entities
curl -H "Authorization: Bearer $HA_TOKEN" https://ha.dr.homelab.local/api/states
```

---

## P2 - Standard Services (RTO: 24h, RPO: 24h)

| Service | Namespace | Data Type | Backup Method | Restore Priority | Validation |
|---------|-----------|-----------|---------------|------------------|------------|
| **Prometheus** | monitoring | Metrics + rules | Velero + snapshot | 4 | Query works, alerts fire |
| **Grafana** | monitoring | Dashboards + config | Velero + dashboard export | 4 | Dashboards load |
| **Alertmanager** | monitoring | Alert config + silencing | Velero | 4 | Alerts route correctly |
| **Loki** | logging | Logs + config | Velero + S3 | 4 | Log queries work |
| **Tempo** | tracing | Traces + config | Velero + S3 | 4 | Trace queries work |
| **Promtail** | logging | Config only | Velero | 5 | Logs ingesting |
| **CrowdSec** | security | Decisions + config | Velero + DB dump | 5 | Decisions apply |

### Prometheus Detailed Recovery
```bash
# 1. Restore Prometheus PVC
velero restore create --from-backup <backup> --include-namespaces monitoring

# 2. Verify metrics ingestion
curl -s "https://prometheus.dr.homelab.local/api/v1/query?query=up" | jq '.data.result | length'
```

### Loki Detailed Recovery
```bash
# 1. Restore Loki S3 data (cross-region replication)
# 2. Deploy Loki stack
helm upgrade --install loki grafana/loki-stack -n dr-test
# 3. Verify log queries
curl -s "https://loki.dr.homelab.local/loki/api/v1/query?query={job=~\"kubernetes.*\"}" | jq '.data.result | length'
```

---

## P3 - Optional Services (RTO: 72h, RPO: 72h)

| Service | Namespace | Backup Method | Validation |
|---------|-----------|---------------|------------|
| **LitmusChaos** | litmus | Velero | Experiments run |
| **k6/Benchmarks** | - | Git repo | Benchmarks execute |
| **Cache Warming** | - | Config only | Cache populated |

---

## DR Test Schedule

| Test Type | Frequency | Automation | Services Tested |
|-----------|-----------|------------|-----------------|
| **Velero Backup Verify** | Daily | GitHub Actions | All |
| **Critical Services DR Test** | Monthly | GitHub Actions + Script | P0 services |
| **Full DR Failover** | Quarterly | Manual + Script | All services |
| **Failback Test** | Quarterly | Manual | All services |
| **RTO/RPO Measurement** | Per test | Automated timing | Tested services |

---

## RTO/RPO Measurement Template

```markdown
# DR Test Results - {{DATE}}

## Test Type: {{Monthly/Quarterly}}
## Backup Used: {{BACKUP_NAME}} ({{BACKUP_AGE}})

## RTO Measurements
| Service | Target RTO | Actual RTO | Status |
|---------|------------|------------|--------|
| Nextcloud | 4h | {{ACTUAL}} | {{PASS/FAIL}} |
| Vaultwarden | 4h | {{ACTUAL}} | {{PASS/FAIL}} |
| PostgreSQL | 4h | {{ACTUAL}} | {{PASS/FAIL}} |
| Authelia | 4h | {{ACTUAL}} | {{PASS/FAIL}} |
| Infisical | 4h | {{ACTUAL}} | {{PASS/FAIL}} |

## RPO Measurements
| Service | Target RPO | Data Loss | Status |
|---------|------------|-----------|--------|
| Nextcloud files | 6h | {{DATA_LOSS}} | {{PASS/FAIL}} |
| Vaultwarden vaults | 6h | {{DATA_LOSS}} | {{PASS/FAIL}} |
| PostgreSQL | 6h | {{DATA_LOSS}} | {{PASS/FAIL}} |

## Overall Result: {{PASS/PARTIAL/FAIL}}
## Notes: {{NOTES}}
```

---

## Escalation Contacts

| Role | Primary | Secondary | Notification |
|------|---------|-----------|--------------|
| DR Lead | Vansh | - | Telegram + Email |
| Platform | Vansh | - | Telegram |
| On-Call | Vansh | - | Telegram + PagerDuty |
| Communication | Vansh | - | Telegram + Status Page |

---

## Runbook Links

| Runbook | Location |
|---------|----------|
| Full DR Failover | `docs/runbooks/dr-failover.md` |
| Failback to Primary | `docs/runbooks/dr-failback.md` |
| Monthly DR Test | `scripts/dr-test-monthly.sh` |
| Quarterly DR Test | `scripts/dr-test-quarterly.sh` |
| Velero Operations | `docs/runbooks/velero-operations.md` |
| Restic Operations | `docs/runbooks/restic-operations.md` |
| DNS Failover | `scripts/dns-failover.sh` |
| Cloudflare Config | `config/cloudflare/failover.json` |

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-06-09 | Vansh | Initial RTO/RPO matrix |
| 1.1 | TBD | | Quarterly update |