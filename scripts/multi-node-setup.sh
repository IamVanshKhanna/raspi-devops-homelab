#!/usr/bin/env bash
# multi-node-setup.sh - Automated K3s multi-node cluster setup for homelab
# Run on control plane node (node-1)
# Usage: sudo ./scripts/multi-node-setup.sh

set -euo pipefail

# Configuration
CLUSTER_NAME="homelab-cluster"
K3S_VERSION="v1.28.5+k3s1"
CONTROL_PLANE_IP="192.168.1.50"
NODE_IPS=("192.168.1.50" "192.168.1.51" "192.168.1.52")
CLUSTER_CIDR="10.42.0.0/16"
SERVICE_CIDR="10.43.0.0/16"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

log() { echo -e "${GREEN}[MULTI-NODE]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
fail() { echo -e "${RED}[FAIL]${NC} $1"; exit 1; }

# Check if running as root
[[ $EUID -eq 0 ]] || fail "Run as root: sudo ./scripts/multi-node-setup.sh"

log "Starting K3s multi-node cluster setup for $CLUSTER_NAME"
log "Control plane: $CONTROL_PLANE_IP"
log "Nodes: ${NODE_IPS[*]}"

# 1. Install K3s on control plane with cluster-init
log "Installing K3s on control plane ($CONTROL_PLANE_IP)..."
curl -sfL https://get.k3s.io | INSTALL_K3S_VERSION="$K3S_VERSION" sh -s - server \
  --cluster-init \
  --tls-san "$CONTROL_PLANE_IP" \
  --tls-san "homelab.local" \
  --tls-san "k3s.homelab.local" \
  --cluster-cidr "$CLUSTER_CIDR" \
  --service-cidr "$SERVICE_CIDR" \
  --disable traefik \
  --disable servicelb \
  --disable local-storage \
  --write-kubeconfig-mode 644 \
  --kubelet-arg="max-pods=110" \
  --kubelet-arg="eviction-hard=memory.available<500Mi,nodefs.available<10%"

# Wait for k3s to be ready
log "Waiting for K3s control plane to be ready..."
while ! kubectl get nodes 2>/dev/null | grep -q "Ready"; do
  sleep 5
done

# Get node token for workers
NODE_TOKEN=$(cat /var/lib/rancher/k3s/server/node-token)
log "Node token: $NODE_TOKEN"

# 2. Install k3sup for worker joins
log "Installing k3sup..."
curl -sLS https://get.k3sup.dev | sh
mv k3sup /usr/local/bin/

# 3. Join worker nodes
for i in "${!NODE_IPS[@]}"; do
  if [[ $i -eq 0 ]]; then continue; fi  # Skip control plane
  WORKER_IP="${NODE_IPS[$i]}"
  log "Joining worker node $WORKER_IP..."
  k3sup join \
    --ip "$WORKER_IP" \
    --user vansh \
    --server-ip "$CONTROL_PLANE_IP" \
    --server-user vansh \
    --k3s-version "$K3S_VERSION" \
    --k3s-extra-args "--kubelet-arg=max-pods=110 --kubelet-arg=eviction-hard=memory.available<500Mi,nodefs.available<10%"
done

# Wait for all nodes
log "Waiting for all nodes to join..."
kubectl wait --for=condition=Ready nodes --all --timeout=300s

# 4. Label nodes
log "Labeling nodes..."
kubectl label node node-1 node-role.kubernetes.io/control-plane=true --overwrite
for i in "${!NODE_IPS[@]}"; do
  if [[ $i -gt 0 ]]; then
    kubectl label node "node-$((i+1))" node-role.kubernetes.io/worker=true --overwrite
  fi
done

# 5. Install Helm
log "Installing Helm..."
curl -fsSL https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash

# 6. Add Helm repos
log "Adding Helm repositories..."
helm repo add longhorn https://charts.longhorn.io
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo add grafana https://grafana.github.io/helm-charts
helm repo add jetstack https://charts.jetstack.io
helm repo add external-dns https://kubernetes-sigs.github.io/external-dns/
helm repo add zalando https://charts.zalando.io
helm repo update

# 7. Install Longhorn (distributed block storage)
log "Installing Longhorn..."
helm install longhorn longhorn/longhorn \
  --namespace longhorn-system --create-namespace \
  --set defaultSettings.backupTarget=s3://homelab-backups@us-east-1 \
  --set defaultSettings.backupTargetCredentialSecret=longhorn-backup-credentials \
  --set defaultSettings.defaultReplicaCount=2 \
  --set defaultSettings.replicaSoftAntiAffinity=false

# Wait for Longhorn
kubectl wait --for=condition=Available deployment/longhorn-driver-deployer -n longhorn-system --timeout=300s

# 8. Install Cert-Manager
log "Installing Cert-Manager..."
helm install cert-manager jetstack/cert-manager \
  --namespace cert-manager --create-namespace \
  --version v1.13.0 \
  --set installCRDs=true

# Wait for Cert-Manager
kubectl wait --for=condition=Ready deployment/cert-manager -n cert-manager --timeout=120s

# 9. Create Cloudflare credentials secret for DNS-01
log "Creating Cloudflare credentials secret..."
read -rsp "Enter Cloudflare API Token: " CF_TOKEN
echo
kubectl create secret generic cloudflare-credentials \
  --namespace cert-manager \
  --from-literal=api-token="$CF_TOKEN" \
  --dry-run=client -o yaml | kubectl apply -f -

# 10. Create ClusterIssuer for Let's Encrypt
log "Creating ClusterIssuer for Let's Encrypt..."
read -rp "Enter ACME email: " ACME_EMAIL
kubectl apply -f - <<EOF
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-prod
spec:
  acme:
    server: https://acme-v02.api.letsencrypt.org/directory
    email: ${ACME_EMAIL}
    privateKeySecretRef:
      name: letsencrypt-prod-key
    solvers:
    - dns01:
        cloudflare:
          apiTokenSecretRef:
            name: cloudflare-credentials
            key: api-token
EOF

# 11. Install Prometheus Stack
log "Installing Prometheus Stack..."
helm install prometheus prometheus-community/kube-prometheus-stack \
  --namespace monitoring --create-namespace \
  --set prometheus.prometheusSpec.retention=30d \
  --set prometheus.prometheusSpec.storageSpec.volumeClaimTemplate.spec.storageClassName=longhorn \
  --set prometheus.prometheusSpec.storageSpec.volumeClaimTemplate.spec.resources.requests.storage=10Gi \
  --set grafana.persistence.enabled=true \
  --set grafana.persistence.storageClassName=longhorn \
  --set grafana.persistence.size=5Gi

# 12. Install Loki Stack
log "Installing Loki Stack..."
helm install loki grafana/loki-stack \
  --namespace logging --create-namespace \
  --set loki.persistence.enabled=true \
  --set loki.persistence.storageClassName=longhorn \
  --set loki.persistence.size=10Gi

# 12b. Apply Loki retention policy
kubectl apply -f config/loki/retention-policy.yaml -n logging

# 13. Install Tempo (distributed tracing)
log "Installing Tempo..."
helm install tempo grafana/tempo \
  --namespace tracing --create-namespace \
  --set persistence.enabled=true \
  --set persistence.storageClassName=longhorn

# 14. Install External-DNS
log "Installing External-DNS..."
kubectl create secret generic cloudflare-credentials \
  --namespace external-dns \
  --from-literal=api-token="$CF_TOKEN" \
  --dry-run=client -o yaml | kubectl apply -f -

helm install external-dns external-dns/external-dns \
  --namespace external-dns --create-namespace \
  --set provider=cloudflare \
  --set env[0].name=CF_API_TOKEN \
  --set env[0].valueFrom.secretKeyRef.name=cloudflare-credentials \
  --set env[0].valueFrom.secretKeyRef.key=api-token

# 15. Install Postgres Operator (Patroni for HA PostgreSQL)
log "Installing Postgres Operator (Patroni)..."
helm install postgres-operator zalando/postgres-operator \
  --namespace postgres-system --create-namespace

# Create namespace for databases
kubectl create namespace databases --dry-run=client -o yaml | kubectl apply -f -

# 16. Create Postgres cluster
log "Creating PostgreSQL cluster (Patroni)..."
kubectl apply -f - <<EOF
apiVersion: "acid.zalan.do/v1"
kind: postgresql
metadata:
  name: homelab-postgres
  namespace: databases
spec:
  teamId: homelab
  volume:
    size: 20Gi
    storageClass: longhorn
  numberOfInstances: 3
  postgresql:
    version: "15"
  users:
    admin:
      - superuser
      - createdb
  databases:
    nextcloud: admin
    vaultwarden: admin
    authelia: admin
  resources:
    requests:
      cpu: 500m
      memory: 1Gi
    limits:
      cpu: 2000m
      memory: 4Gi
EOF

# 17. Install Redis Operator
log "Installing Redis Operator..."
kubectl apply -f https://github.com/spotahome/redis-operator/releases/download/v1.1.0/redis-operator.yaml

# Wait for operators
kubectl wait --for=condition=Ready deployment/postgres-operator -n postgres-system --timeout=120s

# 18. Create Redis cluster
log "Creating Redis cluster..."
kubectl apply -f - <<EOF
apiVersion: databases.spotahome.com/v1
kind: Redis
metadata:
  name: homelab-redis
  namespace: databases
spec:
  replicas: 3
  image: redis:7-alpine
  storageClassName: longhorn
  storageSize: 1Gi
  resources:
    requests:
      cpu: 100m
      memory: 128Mi
    limits:
      cpu: 500m
      memory: 512Mi
EOF

# 18b. Wait for Postgres and Redis
kubectl wait --for=condition=Ready postgresql/homelab-postgres -n databases --timeout=300s
kubectl wait --for=condition=Ready redis/homelab-redis -n databases --timeout=120s

# 19. Verify cluster
log "Verifying cluster..."
kubectl get nodes -o wide
kubectl get pods -A
kubectl get pv,pvc -A
kubectl get postgresql -n databases
kubectl get redis -n databases

# 20. Create Longhorn backup credentials
log "Creating Longhorn backup credentials..."
read -rp "Enter B2 Account ID: " B2_ACCOUNT_ID
read -rp "Enter B2 Application Key: " B2_ACCOUNT_KEY
kubectl create secret generic longhorn-backup-credentials \
  --namespace longhorn-system \
  --from-literal=AWS_ACCESS_KEY_ID="$B2_ACCOUNT_ID" \
  --from-literal=AWS_SECRET_ACCESS_KEY="$B2_ACCOUNT_KEY" \
  --from-literal=AWS_ENDPOINT="https://s3.us-east-005.backblazeb2.com" \
  --from-literal=AWS_REGION="us-east-005" \
  --dry-run=client -o yaml | kubectl apply -f -

# 21. Configure Longhorn backup target
log "Configuring Longhorn backup target..."
kubectl patch settings -n longhorn-system backup-target \
  -p '{"value": "s3://homelab-backups@us-east-1"}' --type=merge
kubectl patch settings -n longhorn-system backup-target-credential-secret \
  -p '{"value": "longhorn-backup-credentials"}' --type=merge

log "✅ Multi-node K3s cluster setup complete!"
log ""
log "Next steps:"
log "1. Deploy applications via ArgoCD/Helm"
log "2. Configure Longhorn backup schedule"
log "3. Set up Grafana dashboards"
log "4. Configure SLO dashboards"
log "5. Test failover scenarios"