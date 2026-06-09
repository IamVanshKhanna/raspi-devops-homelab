# Incident Runbooks Index

> Quick reference for homelab incident response.

---

## Runbook Catalog

| Runbook | Trigger | Severity | Target Resolution |
|---------|---------|----------|-------------------|
| [Service Down](service-down.md) | Health check fail, container down | High | < 30 min |
| [Backup Failure](backup-failure.md) | Backup alert, verify fail | High | < 1 hour |
| [Security Incident](security-incident.md) | CrowdSec alert, CVE, unauthorized access | Variable | Per severity |

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
|--------|---------|------------------|
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