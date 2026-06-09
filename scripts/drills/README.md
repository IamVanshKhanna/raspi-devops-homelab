# Incident Response Drills for Homelab

This directory contains scripts and configurations for running incident response drills and disaster recovery tests.

## Overview

Regular incident response drills ensure:
- Team readiness for real incidents
- Automation works as expected
- RTO/RPO targets are achievable
- Runbooks are accurate and up-to-date

## Drill Categories

### 1. Component Failure Drills
| Drill | Description | Frequency |
|-------|-------------|-----------|
| Database Outage | Simulate PostgreSQL primary failure, verify Patroni failover | Monthly |
| Redis Outage | Simulate Redis master failure, verify cluster recovery | Monthly |
| Ingress Outage | Simulate Traefik failure, verify pod recreation | Monthly |
| Storage Issue | Verify Longhorn PVC binding and recovery | Monthly |

### 2. Security Drills
| Drill | Description | Frequency |
|-------|-------------|-----------|
| Certificate Expiry | Check all certs, verify auto-renewal | Monthly |
| Network Policy Test | Verify zero-trust network segmentation | Quarterly |
| Secret Rotation | Test Infisical secret rotation | Monthly |

### 3. Data Protection Drills
| Drill | Description | Frequency |
|-------|-------------|-----------|
| Backup Verification | Run backup + restore test | Weekly |
| Full DR Test | Restore critical services to DR namespace | Monthly |

### 4. Resource Drills
| Drill | Description | Frequency |
|-------|-------------|-----------|
| OOM Scenario | Check for OOM kills, verify limits | Monthly |
| Capacity Alert | Verify capacity planning alerts | Weekly |

## Running Drills

### Automated (GitHub Actions)
```bash
# Trigger monthly full drill
gh workflow run incident-drill.yml

# Trigger specific drill
gh workflow run incident-drill.yml -f drill_type=database
```

### Manual (On Cluster)
```bash
# Run all drills
./scripts/drills/incident-response-drill.sh

# Run specific drill
./scripts/drills/incident-response-drill.sh --drill database_outage

# Test service failover
./scripts/drills/service-failover-drill.sh nextcloud

# Test all service failovers
./scripts/drills/service-failover-drill.sh all
```

### Ansible Playbooks
```bash
# Full disaster recovery test
ansible-playbook -i inventory/hosts.yml playbooks/disaster-recovery-full.yml

# Health check
ansible-playbook -i inventory/hosts.yml playbooks/health-check.yml
```

## Drill Scenarios Detail

### Database Outage (PostgreSQL/Patroni)
1. Identify current primary
2. Delete primary pod
3. Verify new primary elected within 30s
4. Verify application connectivity restored

### Redis Cluster Failure
1. Identify master pod
2. Delete master pod
3. Verify new master elected
3. Verify Redis connectivity

### Ingress Controller Failure
1. Delete Traefik pod
2. Verify new pod scheduled and Ready
3. Verify external access restored

### Certificate Expiry Check
1. List all cert-manager certificates
2. Check expiry dates
3. Alert on certs < 30 days
4. Verify auto-renewal working

### Backup Verification
1. Run restic backup
2. Verify snapshot created
3. Run restore-test.sh
4. Verify data integrity

### Full DR Test
1. Create isolated DR namespace
2. Restore critical data from backup
3. Deploy test instances of Nextcloud, Vaultwarden, Home Assistant
4. Verify service connectivity
5. Document RTO/RPO
6. Cleanup

## Expected RTO/RPO Targets

| Service | RTO (Recovery Time) | RPO (Recovery Point) |
|---------|---------------------|----------------------|
| PostgreSQL | < 30s (auto-failover) | < 1s (synchronous) |
| Redis | < 30s (auto-failover) | < 1s (synchronous) |
| Traefik | < 60s (pod recreation) | 0 (stateless) |
| Nextcloud | < 5min (pod + PVC) | < 24h (daily backup) |
| Vaultwarden | < 5min (pod + PVC) | < 24h (daily backup) |
| Home Assistant | < 5min (pod + PVC) | < 24h (daily backup) |
| Full DR | < 30min (automated) | < 24h (daily backup) |

## Runbook Integration

Each drill should:
1. Follow corresponding runbook in `docs/runbooks/`
2. Update runbook if discrepancies found
3. Document actual vs expected times
4. File issues for any failures

## Alerting During Drills

Drills generate alerts - ensure:
- Alertmanager routing configured for drill namespace
- Telegram/email notifications distinguish drills from real incidents
- On-call team notified of scheduled drills

## Reporting

After each drill:
1. Log saved to `/var/log/incident-drill-<timestamp>.log`
2. Summary sent to Telegram
3. Failed drills create GitHub issues automatically
4. Quarterly drill report generated

## Safety Guidelines

1. **Never run drills on production without isolation**
2. **Use dedicated DR namespace for full tests**
3. **Have rollback plan for each drill**
4. **Monitor cluster health during drills**
5. **Stop drill if cluster stability impacted**
6. **Document all findings**

## Integration with Monitoring

- Prometheus alerts for drill detection
- Grafana dashboard for drill status
- Loki logs for drill execution traces
- Tempo traces for service behavior during drills

## Schedule

| Drill | Schedule | Automation |
|-------|----------|------------|
| Component Failure | Monthly 1st 4 AM | GitHub Actions |
| Security Drills | Monthly 15th 4 AM | GitHub Actions |
| Data Protection | Weekly Sun 6 AM | Systemd timer |
| Full DR Test | Monthly 1st 2 AM | GitHub Actions |
| Capacity Alerts | Weekly Mon 6 AM | GitHub Actions |
| Service Failover | On-demand | Manual/Ansible |