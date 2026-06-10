# Incident Runbooks Index

> Quick reference for homelab incident response.

---

## Runbook Catalog

| Runbook | Trigger | Severity | Target Resolution |
|---------|---------|----------|-------------------|
| [Service Down](service-down.md) | Health check fail, container down | High | < 30 min |
| [Backup Failure](backup-failure.md) | Backup alert, verify fail | High | < 1 hour |
| [Security Incident](security-incident.md) | CrowdSec alert, CVE, unauthorized access | Variable | Per severity |
| [Resource Quota Exceeded](quota-exceeded.md) | Pod Pending, quota alerts, Grafana 100% | High | < 1 hour |
| [Spot Instance Termination](spot-termination.md) | Spot node NotReady, PDB violation, eviction | Medium | < 15 min |
| [Rightsizing Recommendations](rightsizing.md) | Weekly PR, Grafana >10% savings, VPA | Low | < 1 week |
| [Unused Resource Accumulation](unused-resources.md) | Weekly issue, Grafana climbing, detector | Low | < 1 week |
| [Cost Allocation Anomalies](cost-allocation.md) | Weekly report spike, team budget dispute | Medium | < 1 day |
| [Power Optimization](power-optimization.md) | Grafana spike, Prometheus alert, cost report | Low | < 1 hour |
| [Certificate Rotation](cert-rotation.md) | Prometheus alert, expiry < 30d, NotReady | High | < 4 hours |
| [PDB Validation](pdb-validation.md) | Kyverno audit, node drain blocked, HA gaps | Medium | < 1 day |
| [SLO Violation](slo-violation.md) | Burn rate alert, error budget < 10%, latency SLO breach | Critical | < 30 min |
| [Error Budget Exhausted](error-budget-exhausted.md) | Budget < 5%, exhaustion alert | Critical | < 1 hour |

---

## Quick Reference Commands

### Health & Verification
```bash
# Full health check
make verify-v1

# Individual checks
make verify-health
make verify-loki
make verify-alertmanager
make verify-uptime
make verify-secrets
make verify-backup
```

### Backup Operations
```bash
# Manual backup
make backup

# Test restore
make restore-test

# List snapshots
restic -r $RESTIC_REPOSITORY snapshots
```

### Security
```bash
# Security scan
hermes --profile homelab "security scan"

# Check CrowdSec decisions
cscli decisions list

# Check Authelia regulation
docker logs authelia | grep regulation
```

### Container Management
```bash
# Restart service
docker compose -f stacks/<stack>.yml restart <service>

# Full stack restart
make down-phaseX && make up-phaseX

# View logs
docker logs <container> --tail 100
```

### System
```bash
# System metrics
vcgencmd measure_temp
df -h
free -h

# ZRAM status
swapon -s

# Tailscale status
tailscale status
```

---

## Escalation Contacts

| Role | Contact | When to Escalate |
|------|---------|------------------|
| Primary Admin | Vansh (self) | All incidents |
| GitHub Issues | homelab-prod/issues | Persistent issues, new procedures |

---

## Runbook Maintenance

| Task | Frequency | Owner |
|------|-----------|-------|
| Review runbooks | Quarterly | Primary Admin |
| Test restore | Weekly (automated) | CI |
| Update contacts | As needed | Primary Admin |
| Post-incident review | After each incident | Primary Admin |

---

## Related Documentation

- [ADR-006: Threat Model](../ADR-006-threat-model.md)
- [ADR-004: Secrets Management](../ADR-004-secrets.md)
- [HERMES_ON_PI.md](../HERMES_ON_PI.md)
- [SETUP_GUIDE.md](../SETUP_GUIDE.md)