# Disaster Recovery for Secondary Region

## Overview
This document describes the disaster recovery strategy for the homelab to a secondary region (cloud provider or remote site).

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        DISASTER RECOVERY ARCHITECTURE                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  PRIMARY REGION (Home Lab - Pi 4B/5)                                        │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  Clusters: homelab-pi4, homelab-pi5                                 │   │
│  │  Services: Nextcloud, Vaultwarden, Home Assistant, DBs, Monitoring  │   │
│  │  Backup: Restic → Backblaze B2 (Daily, 30d retention)               │   │
│  │  DR Sync: Velero → B2 (Every 6 hours)                               │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                        │
│                                    │ Cross-region replication               │
│                                    ▼                                        │
│  SECONDARY REGION (AWS/GCP/Azure or Remote Pi)                            │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  Cluster: dr-cloud (EKS/GKE/AKS or k3s on remote Pi)                │   │
│  │  State: Warm standby (control plane only) or Cold (cluster on-demand)│  │
│  │  Restore: Automated via Velero + ArgoCD ApplicationSet               │   │
│  │  RTO: < 4 hours (warm) / < 24 hours (cold)                          │   │
│  │  RPO: < 6 hours (Velero sync) / < 24 hours (Restic)                 │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  BACKUP STORES                                                       │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                  │   │
│  │  │ Backblaze B2│  │ AWS S3      │  │ Local/Remote│                  │   │
│  │  │ (Restic)    │  │ (Velero)    │  │ (Restic)    │                  │   │
│  │  │ Primary     │  │ Secondary   │  │ Tertiary    │                  │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘                  │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## RTO/RPO Targets

| Tier | Services | RTO | RPO | Strategy |
|------|----------|-----|-----|----------|
| **Critical** | Nextcloud, Vaultwarden, Databases | 4 hours | 6 hours | Warm standby + Velero |
| **Important** | Home Assistant, Auth, Secrets | 12 hours | 12 hours | Velero + ArgoCD |
| **Standard** | Monitoring, Logging, Tracing | 24 hours | 24 hours | Velero |
| **Optional** | Chaos, Benchmarks | 72 hours | 72 hours | Scheduled restore test |

## Backup Strategy

### 1. Restic (Primary - Daily)
```bash
# Daily backup to Backblaze B2
restic backup /mnt/data /etc/kubernetes /home/vansh/homelab-prod \
  --tag "daily-{{date}}" \
  --repo s3:homelab-backups@us-east-1
```

### 2. Velero (Cluster State - Every 6 Hours)
```yaml
# Velero schedule for cluster resources
apiVersion: velero.io/v1
kind: Schedule
metadata:
  name: daily-cluster-backup
  namespace: velero
spec:
  schedule: "0 */6 * * *"
  template:
    ttl: 72h
    includedNamespaces:
      - "*"
    excludedResources:
      - events
      - events.events.k8s.io
      - pods
      - replicasets
    storageLocation: secondary-region-s3
```

### 3. Velero DR Sync (Cross-Region)
```bash
# Install Velero on both primary and DR clusters
velero install \
  --provider aws \
  --plugins velero/velero-plugin-for-aws:v1.9.0 \
  --bucket homelab-velero \
  --backup-location-config region=us-east-1 \
  --snapshot-location-config region=us-east-1 \
  --secret-file ./credentials-velero

# Create cross-region schedule
velero schedule create dr-sync-6h \
  --schedule "0 */6 * * *" \
  --include-namespaces '*' \
  --storage-location dr-region \
  --ttl 72h
```

## DR Cluster Setup (Secondary Region)

### Option A: Cloud (AWS EKS - Recommended)
```bash
# Create EKS cluster for DR
eksctl create cluster \
  --name dr-cloud \
  --region us-east-1 \
  --nodegroup-name dr-workers \
  --node-type t3.medium \
  --nodes 1 \
  --nodes-min 1 \
  --nodes-max 3 \
  --managed

# Install ArgoCD agent for DR
helm repo add argocd https://argoproj.github.io/argo-helm
helm install argocd-agent argocd/argocd-agent \
  --namespace argocd-agent --create-namespace \
  --set mode=agent \
  --set principal.address=argocd-server.argocd:8080

# Register DR cluster with ArgoCD
argocd cluster add dr-cloud --name dr-cloud --label homelab.io/cluster=dr-cloud --label homelab.io/role=dr --label homelab.io/environment=dr
```

### Option B: Remote Pi (k3s)
```bash
# On remote Pi, install k3s
curl -sfL https://get.k3s.io | INSTALL_K3S_VERSION="v1.28.5+k3s1" sh -s - server \
  --cluster-init \
  --disable traefik \
  --disable servicelb \
  --disable local-storage

# Join as worker to management cluster via Submariner
# (Follow Submariner setup for cross-cluster connectivity)
```

### Option C: On-Demand (Cluster API)
```bash
# Use CAPI to create DR cluster on-demand
clusterctl generate cluster dr-on-demand \
  --infrastructure aws \
  --kubernetes-version v1.28.5 \
  --control-plane-machine-count 1 \
  --worker-machine-count 2 \
  > dr-on-demand.yaml

# Apply when DR needed
kubectl apply -f dr-on-demand.yaml
```

## Velero Configuration

### Install Velero on Primary Cluster
```bash
velero install \
  --provider aws \
  --plugins velero/velero-plugin-for-aws:v1.9.0 \
  --bucket homelab-velero-primary \
  --backup-location-config region=us-east-1 \
  --snapshot-location-config region=us-east-1 \
  --secret-file ./credentials-velero \
  --default-volumes-to-fs-backup
```

### Install Velero on DR Cluster
```bash
velero install \
  --provider aws \
  --plugins velero/velero-plugin-for-aws:v1.9.0 \
  --bucket homelab-velero-dr \
  --backup-location-config region=us-west-2 \
  --snapshot-location-config region=us-west-2 \
  --secret-file ./credentials-velero-dr
```

### Cross-Region Backup Sync
```yaml
# Primary cluster: backup to primary bucket
apiVersion: velero.io/v1
kind: BackupStorageLocation
metadata:
  name: primary
  namespace: velero
spec:
  provider: aws
  objectStorage:
    bucket: homelab-velero-primary
    prefix: backups
  config:
    region: us-east-1
  credential:
    name: cloud-credentials
    key: cloud
---
# Primary to DR replication
apiVersion: velero.io/v1
kind: BackupStorageLocation
metadata:
  name: dr-region
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
```

## DR Test Plan

### Monthly DR Test
```bash
#!/bin/bash
# dr-test-monthly.sh

# 1. Create test namespace
kubectl create namespace dr-test --dry-run=client -o yaml | kubectl apply -f -

# 2. Restore critical services from latest backup
velero restore create --from-backup $(velero backup get -o json | jq -r '.[0].metadata.name') \
  --namespace-mappings '*:dr-test' \
  --include-namespaces 'apps,databases,secrets,auth,monitoring' \
  --wait

# 3. Verify restored services
kubectl wait --for=condition=Ready pod -l app.kubernetes.io/name=nextcloud -n dr-test --timeout=300s
kubectl wait --for=condition=Ready pod -l app.kubernetes.io/name=vaultwarden -n dr-test --timeout=300s
kubectl wait --for=condition=Ready pod -l app.kubernetes.io/name=postgresql -n dr-test --timeout=300s

# 4. Run smoke tests
# (Add application-specific health checks)

# 5. Cleanup
kubectl delete namespace dr-test

# 6. Report
echo "DR test completed at $(date)"
```

### Quarterly Full DR Test
```bash
#!/bin/bash
# dr-test-quarterly.sh

# Full DR failover test
# 1. Simulate primary region outage
# 2. Promote DR cluster (update DNS, promote Velero backups)
# 3. Run full application test suite
# 4. Document RTO/RPO actuals
# 5. Failback to primary
# 6. Update runbooks based on findings
```

## DNS Failover

### Cloudflare Failover
```yaml
# Cloudflare load balancer with failover
apiVersion: v1
kind: ConfigMap
metadata:
  name: cloudflare-failover
  namespace: external-dns
data:
  failover-config.json: |
    {
      "pools": [
        {
          "name": "primary",
          "origins": [
            {"name": "pi4", "address": "192.168.1.50", "enabled": true}
          ],
          "minimum_origins": 1
        },
        {
          "name": "dr",
          "origins": [
            {"name": "dr-cloud", "address": "dr.homelab.local", "enabled": false}
          ],
          "minimum_origins": 1
        }
      ],
      "fallback_pool": "dr"
    }
```

### Manual DNS Failover Script
```bash
#!/bin/bash
# dns-failover.sh

FAILOVER_TO="${1:-dr}"  # dr or primary

case $FAILOVER_TO in
  dr)
    # Update Cloudflare DNS to point to DR
    curl -X PUT "https://api.cloudflare.com/client/v4/zones/$ZONE_ID/dns_records/$RECORD_ID" \
      -H "Authorization: Bearer $CF_TOKEN" \
      -H "Content-Type: application/json" \
      --data "{\"type\":\"A\",\"name\":\"homelab\",\"content\":\"$DR_IP\",\"ttl\":60,\"proxied\":true}"
    ;;
  primary)
    # Update Cloudflare DNS to point back to primary
    curl -X PUT "https://api.cloudflare.com/client/v4/zones/$ZONE_ID/dns_records/$RECORD_ID" \
      -H "Authorization: Bearer $CF_TOKEN" \
      -H "Content-Type: application/json" \
      --data "{\"type\":\"A\",\"name\":\"homelab\",\"content\":\"$PRIMARY_IP\",\"ttl\":60,\"proxied\":true}"
    ;;
esac

# Notify team
curl -X POST "https://api.telegram.org/bot$TELEGRAM_TOKEN/sendMessage" \
  -d chat_id="$TELEGRAM_CHAT_ID" \
  -d text="🚨 DNS failover to $FAILOVER_TO completed at $(date)"
```

## DR Documentation

### Runbook: Primary Region Outage
```markdown
# RUNBOOK: Primary Region Outage

## Detection
- Alert: Primary cluster unreachable
- Alert: Multiple services down
- External monitoring (Uptime Kuma) shows primary down

## Triage (5 min)
1. Confirm primary region outage (not network partition)
2. Check Uptime Kuma, Cloudflare, Tailscale
3. Confirm with on-site if possible

## Decision (5 min)
- If outage > 15 min AND confirmed: Initiate DR failover
- If outage < 15 min: Monitor, don't failover

## Failover (15 min)
1. Execute `./dns-failover.sh dr`
2. Verify DR cluster services coming up
2. Check Velero restores on DR cluster
3. Verify critical services: Nextcloud, Vaultwarden, DBs

## Validation (10 min)
1. Test Nextcloud login/sync
2. Test Vaultwarden access
3. Test Home Assistant devices
4. Check monitoring/alerting on DR

## Communication (5 min)
1. Send Telegram/email to team
2. Update status page
3. Log incident in tracker

## Resolution
- When primary restored: Execute `./dns-failover.sh primary`
- Run `./dr-test-monthly.sh` to verify primary
- Post-incident review within 48 hours
```

## Automation

### GitHub Actions for DR Test
```yaml
# .github/workflows/dr-test.yml
name: Monthly DR Test

on:
  schedule:
    - cron: '0 3 1 * *'  # Monthly 1st at 3 AM
  workflow_dispatch:

permissions:
  contents: read
  id-token: write

jobs:
  dr-test:
    runs-on: ubuntu-latest
    timeout-minutes: 60
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup kubectl
        uses: azure/k8s-set-context@v4
        with:
          kubeconfig: ${{ secrets.KUBECONFIG_DR }}
      
      - name: Run DR test
        run: |
          chmod +x scripts/dr-test-monthly.sh
          ./scripts/dr-test-monthly.sh
      
      - name: Upload test results
        uses: actions/upload-artifact@v4
        with:
          name: dr-test-results
          path: /tmp/dr-test-*.log
      
      - name: Send Telegram notification
        if: always()
        run: |
          STATUS="${{ job.status }}"
          curl -X POST "https://api.telegram.org/bot${{ secrets.TELEGRAM_BOT_TOKEN }}/sendMessage" \
            -d chat_id="${{ secrets.TELEGRAM_CHAT_ID }}" \
            -d text="🧪 DR Test ${STATUS} at $(date)"
```

## Cost Estimation (AWS DR)

| Component | Monthly Cost | Notes |
|-----------|--------------|-------|
| EKS Control Plane | $73/mo | $0.10/hr |
| Worker Nodes (t3.medium x2) | ~$60/mo | Spot instances: ~$18/mo |
| Velero S3 Storage | ~$5/mo | 100GB |
| EBS Snapshots | ~$10/mo | 500GB |
| Data Transfer | ~$5/mo | Cross-region |
| **Total (On-Demand)** | **~$150/mo** | |
| **Total (Spot + On-Demand)** | **~$100/mo** | |

## Testing Schedule

| Test | Frequency | Automation |
|------|-----------|------------|
| Velero backup verification | Daily | Automated |
| DR test (critical services) | Monthly | GitHub Actions |
| Full DR failover test | Quarterly | Manual + Automation |
| Failback test | Quarterly | Manual |
| Runbook review | Semi-annual | Manual |

## Contacts

| Role | Primary | Secondary |
|------|---------|-----------|
| DR Lead | Vansh | - |
| Cloud Admin | Vansh | - |
| On-call | Vansh | - |
| Communication | Vansh | - |