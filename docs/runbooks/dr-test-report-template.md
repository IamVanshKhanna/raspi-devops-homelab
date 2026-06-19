# Disaster Recovery Test Report Template

> Template for documenting DR test results
> Run monthly as part of backup verification

---

## Test Metadata

| Field | Value |
|-------|-------|
| **Test Date** | YYYY-MM-DD |
| **Test ID** | DR-YYYYMMDD-XXX |
| **Tester** | Name/Handle |
| **Environment** | Production / Staging |
| **Backup Snapshot** | Snapshot ID / Timestamp |
| **Restic Repository** | b2:bucket:path |

---

## Test Scope

| Component | Tested | RTO Target | RPO Target | Result |
|-----------|--------|------------|------------|--------|
| Nextcloud DB | ☐ Yes / ☐ No | 30 min | 1 hour | |
| Nextcloud Files | ☐ Yes / ☐ No | 2 hours | 4 hours | |
| Vaultwarden DB | ☐ Yes / ☐ No | 15 min | 30 min | |
| Home Assistant Config | ☐ Yes / ☐ No | 30 min | 1 hour | |
| Grafana Dashboards | ☐ Yes / ☐ No | 10 min | 1 hour | |
| Prometheus Data | ☐ Yes / ☐ No | 1 hour | 1 hour | |
| Loki Logs | ☐ Yes / ☐ No | 2 hours | 4 hours | |
| Tempo Traces | ☐ Yes / ☐ No | 2 hours | 4 hours | |
| Infisical Secrets | ☐ Yes / ☐ No | 15 min | 1 hour | |
| Authelia DB | ☐ Yes / ☐ No | 15 min | 30 min | |

---

## Test Procedure

### 1. Pre-Test Checks
- [ ] Verify restic repository accessible: `restic -r $RESTIC_REPOSITORY snapshots`
- [ ] Verify B2 connectivity: `curl -I https://api.backblazeb2.com`
- [ ] Check available disk space on restore target: `df -h /mnt/restore-test`
- [ ] Verify restic password available in environment

### 2. Restore Test Execution

```bash
# 1. List available snapshots
restic -r $RESTIC_REPOSITORY snapshots --latest 5

# 2. Select snapshot to restore
SNAPSHOT_ID=<snapshot-id>

# 3. Restore to test directory
restic -r $RESTIC_REPOSITORY restore $SNAPSHOT_ID \
  --target /mnt/restore-test \
  --include "*.sql" \
  --include "*.yaml" \
  --include "*.conf"

# 4. Verify critical files
ls -la /mnt/restore-test/
```

### 3. Component Validation

#### Nextcloud Database
- [ ] SQL dump restores without errors
- [ ] Table count matches expected
- [ ] Sample queries return data
- [ ] Admin user exists

#### Vaultwarden
- [ ] Database schema intact
- [ ] User records present
- [ ] Cipher records decryptable

#### Home Assistant
- [ ] Configuration.yaml valid YAML
- [ ] Automations load without error
- [ ] Integrations have valid tokens

#### Grafana
- [ ] Dashboards load without error
- [ ] Data sources connect
- [ ] Alerts evaluate correctly

### 4. Performance Metrics

| Metric | Target | Actual | Pass/Fail |
|--------|--------|--------|-----------|
| **Restore Time (DB)** | < 30 min | ___ min | ☐ Pass / ☐ Fail |
| **Restore Time (Files)** | < 2 hours | ___ min | ☐ Pass / ☐ Fail |
| **Data Integrity** | 100% | ___% | ☐ Pass / ☐ Fail |
| **Restic Verify** | 0 errors | ___ errors | ☐ Pass / ☐ Fail |

### 5. Post-Test Cleanup

```bash
# Clean up test restore
rm -rf /mnt/restore-test

# Verify cleanup
ls -la /mnt/restore-test 2>/dev/null || echo "Cleaned up"
```

---

## Results Summary

| Overall Result | ☐ PASS | ☐ FAIL |
|----------------|--------|--------|

### Issues Found

| Issue | Severity | Component | Action Required |
|-------|----------|-----------|-----------------|
| | | | |

### Recommendations

| Recommendation | Priority | Owner | Due Date |
|----------------|----------|-------|----------|
| | | | |

---

## Sign-off

| Role | Name | Signature | Date |
|------|------|-----------|------|
| Tester | | | |
| Reviewer | | | |
| Approver | | | |

---

*Template Version: 1.0 | homelab-prod DR Test*
*Next Review: Monthly*