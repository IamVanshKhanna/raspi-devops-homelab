# Runbook: Backup Failure

## Detection
- Telegram alert from `backup-alert.sh`
- `make verify-backup` fails
- Cron log shows exit code != 0

## Diagnosis
```bash
# Check backup logs
cat /mnt/backup/logs/backup-$(date +%Y%m%d)*.log

# Check restic repository
restic -r $RESTIC_REPOSITORY snapshots

# Check B2 connectivity
curl -I https://api.backblazeb2.com/b2api/v2/b2_list_file_names

# Check disk space
df -h /mnt/backup /mnt/data
```

## Common Causes & Fixes

### B2 Authentication Failed
```bash
# Verify credentials in .env
grep B2_ .env

# Test B2 API
curl -u "$B2_ACCOUNT_ID:$B2_ACCOUNT_KEY" \
  https://api.backblazeb2.com/b2api/v2/b2_authorize_account
```

### Repository Locked
```bash
# Check for stale lock
restic -r $RESTIC_REPOSITORY unlock
```

### Disk Full
```bash
# Check disk space
df -h /mnt/backup /mnt/data

# Clean old backups
restic -r $RESTIC_REPOSITORY forget --keep-daily 7 --keep-weekly 4 --keep-monthly 6 --prune
```

### Network Timeout
```bash
# Check connectivity
ping -c 3 api.backblazeb2.com

# Retry backup
./scripts/backup-wrapper.sh
```

## Recovery Steps
1. Identify cause from logs
2. Apply fix
3. Re-run backup: `./scripts/backup-wrapper.sh`
4. Verify: `make verify-backup`
5. Check Telegram for success alert

## Escalation
- If B2 quota exceeded: Upgrade B2 plan or increase retention cleanup
- If repository corrupted: `restic check --repair` (backup first!)
- If persistent >2 failures: Create GitHub issue, manual backup to local disk