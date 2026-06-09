#!/usr/bin/env bash
# k3s-cluster-setup.sh - Bootstrap K3s multi-node cluster
# Run on control plane node (node-1)

set -euo pipefail

# Configuration
CLUSTER_NAME="homelab-cluster"
CONTROL_PLANE_IP="192.168.1.50"
NODE_IPS=("192.168.1.50" "192.168.1.51")  # Add more worker IPs as needed
K3S_VERSION="v1.28.5+k3s1"
CLUSTER_CIDR="10.42.0.0/16"
SERVICE_CIDR="10.43.0.0/16"

# Colors
GREEN='\033[0;32m'; RED='\033[0;31m'; YELLOW='\033[1;33m'; NC='\033[0m'

log() { echo -e "${GREEN}[K3S-SETUP]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
fail() { echo -e "${RED}[FAIL]${NC} $1"; exit 1; }

# Check if running as root
[[ $EUID -eq 0 ]] || fail "Run as root: sudo ./k3s-cluster-setup.sh"

log "Starting K3s cluster setup for $CLUSTER_NAME"

# Install K3s on control plane
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

# Save kubeconfig for user
mkdir -p /home/vansh/.kube
cp /etc/rancher/k3s/k3s.yaml /home/vansh/.kube/config
chown -R vansh:vansh /home/vansh/.kube
sed -i "s/127.0.0.1/$CONTROL_PLANE_IP/" /home/vansh/.kube/config

# Install k3sup for worker joins
log "Installing k3sup..."
curl -sLS https://get.k3sup.dev | sh
mv k3sup /usr/local/bin/

# Join worker nodes
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

# Label nodes
log "Labeling nodes..."
kubectl label node node-1 node-role.kubernetes.io/control-plane=true --overwrite
for i in "${!NODE_IPS[@]}"; do
  if [[ $i -gt 0 ]]; then
    kubectl label node "node-$((i+1))" node-role.kubernetes.io/worker=true --overwrite
  fi
done

# Install Helm
log "Installing Helm..."
curl -fsSL https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash

# Add Helm repos
log "Adding Helm repositories..."
helm repo add longhorn https://charts.longhorn.io
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo add grafana https://grafana.github.io/helm-charts
helm repo add jetstack https://charts.jetstack.io
helm repo add external-dns https://kubernetes-sigs.github.io/external-dns/
helm repo add zalando https://charts.zalando.io
helm repo update

# Install Longhorn
log "Installing Longhorn..."
helm install longhorn longhorn/longhorn \
  --namespace longhorn-system --create-namespace \
  --set defaultSettings.backupTarget=s3://homelab-backups@us-east-1 \
  --set defaultSettings.backupTargetCredentialSecret=longhorn-backup-credentials \
  --set defaultSettings.defaultReplicaCount=2 \
  --set defaultSettings.replicaSoftAntiAffinity=false

# Wait for Longhorn
kubectl wait --for=condition=Available deployment/longhorn-driver-deployer -n longhorn-system --timeout=300s

# Install Cert-Manager
log "Installing Cert-Manager..."
helm install cert-manager jetstack/cert-manager \
  --namespace cert-manager --create-namespace \
  --version v1.13.0 \
  --set installCRDs=true

# Wait for Cert-Manager
kubectl wait --for=condition=Ready deployment/cert-manager -n cert-manager --timeout=120s

# Create ClusterIssuer for Let's Encrypt
log "Creating ClusterIssuer for Let's Encrypt..."
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

# Create Cloudflare credentials secret
read -rsp "Enter Cloudflare API Token: " CF_TOKEN
echo
kubectl create secret generic cloudflare-credentials \
  --namespace cert-manager \
  --from-literal=api-token="$CF_TOKEN" \
  --dry-run=client -o yaml | kubectl apply -f -

# Install Prometheus Stack
log "Installing Prometheus Stack..."
helm install prometheus prometheus-community/kube-prometheus-stack \
  --namespace monitoring --create-namespace \
  --set prometheus.prometheusSpec.retention=30d \
  --set prometheus.prometheusSpec.storageSpec.volumeClaimTemplate.spec.storageClassName=longhorn \
  --set prometheus.prometheusSpec.storageSpec.volumeClaimTemplate.spec.resources.requests.storage=10Gi \
  --set grafana.persistence.enabled=true \
  --set grafana.persistence.storageClassName=longhorn \
  --set grafana.persistence.size=5Gi

# Install Loki Stack
log "Installing Loki Stack..."
helm install loki grafana/loki-stack \
  --namespace logging --create-namespace \
  --set loki.persistence.enabled=true \
  --set loki.persistence.storageClassName=longhorn \
  --set loki.persistence.size=10Gi

# Install Tempo
log "Installing Tempo..."
helm install tempo grafana/tempo \
  --namespace tracing --create-namespace \
  --set persistence.enabled=true \
  --set persistence.storageClassName=longhorn

# Install External-DNS
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

# Install Postgres Operator
log "Installing Postgres Operator (Patroni)..."
helm install postgres-operator zalando/postgres-operator \
  --namespace postgres-system --create-namespace

# Create namespace for databases
kubectl create namespace databases --dry-run=client -o yaml | kubectl apply -f -

# Create Postgres cluster
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

# Install Redis Operator
log "Installing Redis Operator..."
kubectl apply -f https://github.com/spotahome/redis-operator/releases/download/v1.1.0/redis-operator.yaml

# Wait for operators
kubectl wait --for=condition=Ready deployment/postgres-operator -n postgres-system --timeout=120s

# Create Redis cluster
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

# Verify cluster
log "Verifying cluster..."
kubectl get nodes -o wide
kubectl get pods -A
kubectl get pv,pvc -A

# Install secrets-rotation script and systemd timer
log "Installing secrets-rotation script and systemd timer..."
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cp "$SCRIPT_DIR/secrets-rotation.sh" /usr/local/bin/secrets-rotation.sh
chmod +x /usr/local/bin/secrets-rotation.sh

cp "$SCRIPT_DIR/homelab-secrets-rotation.service" /etc/systemd/system/
cp "$SCRIPT_DIR/homelab-secrets-rotation.timer" /etc/systemd/system/

systemctl daemon-reload
systemctl enable homelab-secrets-rotation.timer
systemctl start homelab-secrets-rotation.timer
log "Secrets rotation timer installed and started"

log "✅ K3s cluster setup complete!"
log ""
log "Next steps:"
log "1. Deploy applications via Helm/ArgoCD"
log "2. Configure Longhorn backup to B2"
log "2. Set up ArgoCD for GitOps"
log "3. Configure Grafana dashboards"
log "4. Test failover scenarios"