# Cross-Region Backup Replication

## Overview
This document describes the setup for replicating backups from primary region (Backblaze B2) to secondary regions (AWS S3, Google Cloud Storage) for disaster recovery.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    CROSS-REGION BACKUP REPLICATION                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  PRIMARY REGION (Home Lab)                                                   │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  Restic → Backblaze B2 (us-east-1)                                 │   │
│  │  Velero → B2 (us-east-1)                                           │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                        │
│                    ┌───────────────┼───────────────┐                        │
│                    ▼               ▼               ▼                         │
│  ┌─────────────────────────┐ ┌─────────────────────────┐ ┌─────────────┐  │
│  │ AWS S3 (us-west-2)      │ │ GCS (us-central1)       │ │ Azure Blob  │  │
│  │ homelab-backups-dr      │ │ homelab-backups-dr      │ │ (optional)  │  │
│  │ SSE-S3 / SSE-KMS        │ │ CMEK / CSEK             │ │ SSE         │  │
│  │ Versioning enabled      │ │ Versioning enabled      │ │ Versioning  │  │
│  │ Cross-region replication │ │ Dual-region bucket      │ │ LRS/ZRS/GZRS│  │
│  └─────────────────────────┘ └─────────────────────────┘ └─────────────┘  │
│                                                                              │
│  REPLICATION METHODS                                                         │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ 1. Restic: rclone sync (B2 → S3/GCS) - daily                       │   │
│  │ 2. Velero: Native BSL replication + S3 cross-region replication    │   │
│  │ 3. B2 Native: Lifecycle rules + replication (if available)         │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Method 1: Restic Cross-Region Replication (rclone)

### Prerequisites
- rclone configured with B2, S3, GCS remotes
- Service accounts with appropriate permissions

### rclone Configuration
```bash
# ~/.config/rclone/rclone.conf
[b2-primary]
type = b2
account = $B2_ACCOUNT_ID
key = $B2_ACCOUNT_KEY
endpoint = https://s3.us-east-005.backblazeb2.com

[s3-dr]
type = s3
provider = AWS
env_auth = false
access_key_id = $AWS_ACCESS_KEY_ID
secret_access_key = $AWS_SECRET_ACCESS_KEY
region = us-west-2
endpoint = s3.us-west-2.amazonaws.com
acl = private
server_side_encryption = AES256
sse_kms_key_id = arn:aws:kms:us-west-2:123456789012:key/12345678-1234-1234-1234-123456789012

[gcs-dr]
type = google cloud storage
project_number = 123456789012
service_account_file = /path/to/gcs-sa.json
location = us-central1
storage_class = NEARLINE
object_acl = private
```

### Replication Script
```bash
#!/usr/bin/env bash
# replicate-restic.sh - Cross-region Restic replication
# Schedule: 0 4 * * * (daily 4 AM)

set -euo pipefail

REPOS=("homelab-backups" "homelab-velero" "homelab-loki" "homelab-thanos")

for repo in "${REPOS[@]}"; do
    echo "Replicating $repo to AWS S3..."
    rclone sync "b2-primary:$repo" "s3-dr:$repo-dr" \
        --progress \
        --transfers 4 \
        --checkers 8 \
        --retries 3 \
        --low-level-retries 10 \
        --stats 1m \
        --stats-one-line \
        --log-file "/var/log/rclone-$repo-$(date +%Y%m%d).log" \
        --filter "+ **" \
        --bwlimit 50M
    
    echo "Replicating $repo to GCS..."
    rclone sync "b2-primary:$repo" "gcs-dr:$repo-dr" \
        --progress \
        --transfers 4 \
        --checkers 8 \
        --retries 3 \
        --log-file "/var/log/rclone-gcs-$repo-$(date +%Y%m%d).log"
done

# Verify replication
for repo in "${REPOS[@]}"; do
    echo "Verifying $repo replication..."
    B2_COUNT=$(rclone lsf "b2-primary:$repo" --files-only | wc -l)
    S3_COUNT=$(rclone lsf "s3-dr:$repo-dr" --files-only | wc -l)
    GCS_COUNT=$(rclone lsf "gcs-dr:$repo-dr" --files-only | wc -l)
    
    echo "  B2: $B2_COUNT objects"
    echo "  S3: $S3_COUNT objects"
    echo "  GCS: $GCS_COUNT objects"
    
    if [[ "$B2_COUNT" -eq "$S3_COUNT" && "$B2_COUNT" -eq "$GCS_COUNT" ]]; then
        echo "  ✅ Counts match"
    else
        echo "  ⚠️ Count mismatch detected"
    fi
done
```

### Rclone Systemd Timer
```ini
# /etc/systemd/system/rclone-replicate.service
[Unit]
Description=Restic Cross-Region Replication
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
User=vansh
Environment=B2_ACCOUNT_ID=%i B2_ACCOUNT_KEY=%i AWS_ACCESS_KEY_ID=%i AWS_SECRET_ACCESS_KEY=%i
ExecStart=/home/vansh/homelab-prod/scripts/replicate-restic.sh
TimeoutSec=3600

[Install]
WantedBy=multi-user.target

# /etc/systemd/system/rclone-replicate.timer
[Unit]
Description=Daily Restic Cross-Region Replication

[Timer]
OnCalendar=daily
Persistent=true
RandomizedDelaySec=30m

[Install]
WantedBy=timers.target
```

---

## Method 2: Velero Cross-Region Replication

### Velero BSL Configuration
```yaml
# Primary cluster - Backup to B2
apiVersion: velero.io/v1
kind: BackupStorageLocation
metadata:
  name: primary-b2
  namespace: velero
spec:
  provider: aws
  objectStorage:
    bucket: homelab-velero-primary
    prefix: backups
  config:
    region: us-east-1
    s3Url: https://s3.us-east-005.backblazeb2.com
    s3ForcePathStyle: "true"
  credential:
    name: cloud-credentials
    key: cloud
  default: true
---
# Primary to DR replication
apiVersion: velero.io/v1
kind: BackupStorageLocation
metadata:
  name: dr-region-s3
  namespace: velero
spec:
  provider: aws
  objectStorage:
    bucket: homelab-velero-dr
    prefix: backups
  config:
    region: us-west-2
  credential:
    name: cloud-credentials-dr
    key: cloud
  default: false
---
# DR cluster - Restore from DR bucket
apiVersion: velero.io/v1
kind: BackupStorageLocation
metadata:
  name: dr-primary
  namespace: velero
spec:
  provider: aws
  objectStorage:
    bucket: homelab-velero-dr
    prefix: backups
  config:
    region: us-west-2
  credential:
    name: cloud-credentials-dr
    key: cloud
  default: true
  accessMode: ReadOnly
---
# DR cluster - Write back to DR bucket
apiVersion: velero.io/v1
kind: BackupStorageLocation
metadata:
  name: dr-backup
  namespace: velero
spec:
  provider: aws
  objectStorage:
    bucket: homelab-velero-dr
    prefix: backups
  config:
    region: us-west-2
  credential:
    name: cloud-credentials-dr
    key: cloud
  default: false
```

### Cross-Region Backup Schedule
```yaml
# Primary cluster: Daily backup to B2 + replication to DR
apiVersion: velero.io/v1
kind: Schedule
metadata:
  name: daily-full-backup
  namespace: velero
spec:
  schedule: "0 2 * * *"  # 2 AM daily
  template:
    ttl: 72h
    includedNamespaces:
      - "*"
    excludedResources:
      - events
      - events.events.k8s.io
      - pods
      - replicasets
    storageLocation: primary-b2
---
# Primary cluster: Cross-region replication schedule
apiVersion: velero.io/v1
kind: Schedule
metadata:
  name: dr-replication-6h
  namespace: velero
spec:
  schedule: "0 */6 * * *"  # Every 6 hours
  template:
    ttl: 72h
    includedNamespaces:
      - "*"
    storageLocation: dr-region-s3
---
# DR cluster: Read-only restore verification
apiVersion: velero.io/v1
kind: Schedule
metadata:
  name: dr-restore-verification
  namespace: velero
spec:
  schedule: "0 5 * * 0"  # Weekly Sunday 5 AM
  template:
    ttl: 24h
    includedNamespaces:
      - apps
      - databases
      - secrets
      - auth
      - monitoring
    storageLocation: dr-primary
    restoreOnly:
      namespaces:
        - "*"
```

### S3 Cross-Region Replication (AWS)
```bash
# Enable S3 Cross-Region Replication
aws s3api put-bucket-replication --bucket homelab-velero-primary --replication-configuration '{
  "Role": "arn:aws:iam::123456789012:role/s3-replication-role",
  "Rules": [
    {
      "ID": "ReplicateToDR",
      "Priority": 1,
      "Status": "Enabled",
      "DeleteMarkerReplication": { "Status": "Enabled" },
      "Filter": { "Prefix": "backups/" },
      "Destination": {
        "Bucket": "arn:aws:s3:::homelab-velero-dr",
        "StorageClass": "STANDARD_IA",
        "EncryptionConfiguration": {
          "ReplicaKmsKeyID": "arn:aws:kms:us-west-2:123456789012:key/12345678-1234-1234-1234-123456789012"
        },
        "ReplicationTime": {
          "Status": "Enabled",
          "Time": { "Minutes": 15 }
        }
      }
    ]
  ]
}'
```

### GCS Dual-Region Bucket
```bash
# Create dual-region bucket for automatic replication
gsutil mb -b on -l US-CENTRAL1 -c NEARLINE \
  -p homelab-project \
  gs://homelab-velero-dr

# Or create turbo replication bucket
gsutil mb -b on -l US -c STANDARD \
  --replication-type=TURBO_REPLICATION \
  gs://homelab-velero-dr
```

---

## Method 3: B2 Native Replication (if available)

### B2 Lifecycle Rules
```bash
# B2 doesn't have native cross-region replication yet
# Use lifecycle rules for retention, replicate via rclone
b2 create_bucket homelab-backups-dr --bucket-type allPrivate --region us-west-002

# Lifecycle rule: delete incomplete large files after 7 days
b2 update_bucket homelab-backups-dr \
  --lifecycle-rules '[{"daysFromHidingToDeleting": 30, "daysFromUploadingToHiding": 7}]'
```

---

## Monitoring & Alerting

### Replication Health Checks
```bash
#!/usr/bin/env bash
# verify-replication.sh - Daily replication verification

check_rclone_sync() {
    local repo=$1
    local src=$2
    local dst=$3
    
    SRC_COUNT=$(rclone lsf "$src:$repo" --files-only | wc -l)
    DST_COUNT=$(rclone lsf "$dst:$repo" --files-only | wc -l)
    
    if [[ $SRC_COUNT -eq $DST_COUNT ]]; then
        echo "✅ $repo: $SRC_COUNT == $DST_COUNT"
        return 0
    else
        echo "❌ $repo: $SRC_COUNT != $DST_COUNT (diff: $((DST_COUNT - SRC_COUNT)))"
        return 1
    fi
}

check_velero_replication() {
    # Check last backup timestamp in DR bucket vs primary
    LATEST_PRIMARY=$(velero backup get -o json 2>/dev/null | jq -r '.[0].status.completionTimestamp')
    LATEST_DR=$(velero --kubeconfig=$KUBECONFIG_DR backup get -o json 2>/dev/null | jq -r '.[0].status.completionTimestamp')
    
    if [[ -n "$LATEST_PRIMARY" && -n "$LATEST_DR" ]]; then
        PRIMARY_EPOCH=$(date -d "$LATEST_PRIMARY" +%s)
        DR_EPOCH=$(date -d "$LATEST_DR" +%s)
        LAG_HOURS=$(( (PRIMARY_EPOCH - DR_EPOCH) / 3600 ))
        
        if [[ $LAG_HOURS -le 6 ]]; then
            echo "✅ Velero replication lag: ${LAG_HOURS}h"
            return 0
        else
            echo "❌ Velero replication lag: ${LAG_HOURS}h (>6h threshold)"
            return 1
        fi
    fi
}

# Run all checks
FAILED=0
for repo in homelab-backups homelab-velero homelab-loki homelab-thanos; do
    check_rclone_sync "$repo" "b2-primary" "s3-dr" || FAILED=1
    check_rclone_sync "$repo" "b2-primary" "gcs-dr" || FAILED=1
done

check_velero_replication || FAILED=1

exit $FAILED
```

### Prometheus Alerts
```yaml
# config/prometheus/rules/replication-alerts.yaml
groups:
- name: backup-replication
  rules:
  - alert: ResticReplicationLag
    expr: |
      (restic_repo_objects{repo="b2-primary"} - restic_repo_objects{repo="s3-dr"}) > 100
    for: 1h
    labels:
      severity: warning
    annotations:
      summary: "Restic replication lag detected"
      description: "More than 100 objects difference between B2 and S3"
      
  - alert: VeleroReplicationLag
    expr: |
      velero_backup_timestamp{location="primary"} - velero_backup_timestamp{location="dr"} > 21600
    for: 30m
    labels:
      severity: critical
    annotations:
      summary: "Velero cross-region replication lag > 6 hours"
      
  - alert: RcloneSyncFailed
    expr: |
      rclone_sync_exit_code != 0
    for: 0m
    labels:
      severity: critical
    annotations:
      summary: "Rclone sync job failed"
```

---

## Cost Estimation

| Component | Monthly Cost | Notes |
|-----------|--------------|-------|
| **Rclone S3 Storage (us-west-2)** | ~$23/TB/mo | Standard-IA for infrequent access |
| **Rclone GCS Storage (us-central1)** | ~$20/TB/mo | Nearline class |
| **S3 Cross-Region Replication** | ~$0.02/GB | Data transfer + replication |
| **GCS Dual-Region** | ~$26/TB/mo | Dual-region + Turbo replication |
| **Velero DR S3 Storage** | ~$23/TB/mo | Standard-IA |
| **Data Transfer (B2 → S3/GCS)** | ~$0.01/GB | B2 free egress to partners |
| **rclone Compute (GitHub Actions)** | Free | Included in GitHub Actions |
| **Total (10TB)** | **~$300-500/mo** | Depends on replication method |

---

## Implementation Checklist

- [ ] Configure rclone with B2, S3, GCS remotes
- [ ] Create DR buckets in S3 (us-west-2) and GCS (us-central1)
- [ ] Enable S3 Cross-Region Replication
- [ ] Configure GCS dual-region bucket
- [ ] Set up Velero BSLs for cross-region
- [ ] Create replication schedules (rclone daily, Velero 6h)
- [ ] Implement monitoring alerts
- [ ] Test full replication cycle
- [ ] Verify restore from DR region
- [ ] Document runbooks