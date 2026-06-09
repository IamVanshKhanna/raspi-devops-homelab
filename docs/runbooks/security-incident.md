# Runbook: Security Incident

## Detection
- CrowdSec alert via Telegram
- Authelia failed login alerts
- Prometheus alert: `InstanceDown`, `ContainerRestartLoop`
- Unusual traffic in Prometheus/Grafana
- Hermes: "security scan" shows unexpected CVEs

## Triage Levels

### Level 1: Low (Informational)
- Single failed login
- Low-severity CVE in non-critical image
- Action: Monitor, schedule update

### Level 2: Medium (Investigate)
- Multiple failed logins from same IP
- High-severity CVE in exposed service
- Unusual outbound traffic
- Action: Investigate within 1 hour, block IP if confirmed

### Level 3: High (Contain)
- Successful unauthorized access
- Critical CVE in exposed service (Traefik, Authelia)
- Data exfiltration suspected
- Action: Immediate containment, notify stakeholders

## Response Procedures

### Compromised Container
```bash
# 1. Isolate
docker compose -f stacks/<stack>.yml down <service>

# 2. Preserve evidence
docker commit <container> forensic/<service>-$(date +%s)
docker save forensic/<service>-$(date +%s) | gzip > /mnt/backup/forensic-<service>.tar.gz

# 3. Restore from clean image
docker compose -f stacks/<stack>.yml pull <service>
docker compose -f stacks/<stack>.yml up -d <service>

# 4. Verify
make verify-health
```

### Compromised Secrets
```bash
# 1. Rotate in Infisical
# 2. Update .env references (if any)
# 3. Restart affected services
make down-phaseX && make up-phaseX

# 4. Verify
make verify-secrets
```

### CrowdSec Alert (Malicious IP)
```bash
# Check decision
cscli decisions list

# Add manual ban if needed
cscli decisions add --ip <IP> --type ban --duration 24h --reason "Automated: suspicious activity"

# Verify
cscli decisions list --ip <IP>
```

### Authelia Brute Force
```bash
# Check regulation
# Config: regulation.max_retries=3, find_time=120, ban_time=300

# Manual unban if legitimate
# Edit /config/users_database.yml or use Authelia API

# Increase ban time if persistent
# Edit configuration.yml regulation section
```

## Post-Incident
1. Document timeline and actions in GitHub issue
2. Update runbook if new procedure
3. Schedule post-mortem within 48 hours
3. Update threat model (ADR-006) if new attack vector
4. Rotate any potentially compromised secrets
5. Update CrowdSec scenarios if new pattern