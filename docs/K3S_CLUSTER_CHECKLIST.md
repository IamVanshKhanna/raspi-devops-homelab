# K3s Cluster Deployment Checklist

## Pre-requisites
- [ ] 2+ Raspberry Pi 4/5 (4GB+ RAM each)
- [ ] Raspberry Pi OS Lite 64-bit (Bookworm) on all nodes
- [ ] Static IPs configured on all nodes
- [ ] SSH keys exchanged between all nodes
- [ ] Domain with Cloudflare DNS configured
- [ ] Backblaze B2 bucket created
- [ ] Telegram bot created for alerts

## Node Preparation (Run on ALL nodes)
```bash
# On each Pi node:
sudo apt update && sudo apt upgrade -y
sudo apt install -y curl git vim htop btop
# Set hostname
sudo hostnamectl set-hostname node-1  # or node-2, node-3
# Add to /etc/hosts on all nodes
echo "192.168.1.50 node-1" | sudo tee -a /etc/hosts
echo "192.168.1.51 node-2" | sudo tee -a /etc/hosts
echo "192.168.1.52 node-3" | sudo tee -a /etc/hosts
```

## Control Plane Setup (node-1 only)
```bash
# Clone repo
git clone https://github.com/IamVanshKhanna/homelab-prod.git
cd homelab-prod

# Create .env from template
cp .env.example .env
# EDIT .env with all real values!

# Run multi-node setup
sudo ./scripts/multi-node-setup.sh
```

## Post-Install Verification
```bash
# Check all nodes ready
kubectl get nodes -o wide

# Check all pods running
kubectl get pods -A

# Check Longhorn
kubectl get pods -n longhorn-system

# Check ArgoCD
kubectl get pods -n argocd
argocd admin initial-password -n argocd
```

## Post-Install Configuration
```bash
# Configure Longhorn backup
kubectl patch settings -n longhorn-system backup-target \
  -p '{"value": "s3://homelab-backups@us-east-1"}'

# Create Longhorn backup credentials
kubectl create secret generic longhorn-backup-credentials \
  --namespace longhorn-system \
  --from-literal=AWS_ACCESS_KEY_ID=$B2_ACCOUNT_ID \
  --from-literal=AWS_SECRET_ACCESS_KEY=$B2_ACCOUNT_KEY \
  --from-literal=AWS_ENDPOINT=https://s3.us-east-005.backblazeb2.com \
  --from-literal=AWS_REGION=us-east-005
```

## ArgoCD Applications Sync
```bash
# Sync all applications
argocd app sync -l app.kubernetes.io/part-of=homelab-prod

# Or sync individually
argocd app sync traefik
argocd app sync infisical
argocd app sync authelia
argocd app sync monitoring
# ... etc
```

## Verification Commands
```bash
# Check all services healthy
./scripts/health-check.sh --strict

# Check ArgoCD health
python3 scripts/argocd-health.py

# Run disaster recovery test
./scripts/disaster-recovery-test.sh --dry-run

# Validate workflows
python3 scripts/validate-workflows.py
```

## Troubleshooting
| Issue | Check | Resolution |
|-------|-------|------------|
| Node not Ready | `kubectl describe node <node>` | Check k3s agent, container runtime |
| PVC Pending | `kubectl describe pvc <pvc>` | Check Longhorn replica availability |
| Cert not issued | `kubectl describe certificate` | Verify Cloudflare DNS, cert-manager logs |
| Longhorn degraded | `kubectl get volumes -n longhorn-system` | Wait for replica rebuild, check disk space |
| ArgoCD OOS | `argocd app get <app>` | Check for resource conflicts |