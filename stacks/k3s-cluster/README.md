# STACK: K3S-CLUSTER — K3s Multi-Node Cluster Setup
# Lightweight Kubernetes for multi-node homelab
# For use with 2+ Raspberry Pi 4/5 nodes

version: "3.8"

# This docker-compose is for REFERENCE only
# Actual K3s installation is done via k3sup or k3s install script
# This file documents the expected cluster topology

# Network topology:
# node-1 (control plane + worker) - 192.168.1.50
# node-2 (worker) - 192.168.1.51
# node-3 (worker) - 192.168.1.52 (optional)

# Services that would run in K3s instead of Docker Compose:
# - Traefik (ingress controller)
# - Longhorn (distributed block storage)
# - Cert-Manager (TLS certificates)
# - External-DNS (DNS management)
# - Prometheus Stack (kube-prometheus-stack)
# - Loki Stack (logging)
- Tempo (tracing)
- Postgres Operator (Patroni)
- Redis Operator
- Ollama Deployment (scaled)

# K3s Install Commands (run on each node):
# 
# Node 1 (Control Plane):
# curl -sfL https://get.k3s.io | sh -s - server \
#   --cluster-init \
#   --tls-san 192.168.1.50 \
#   --tls-san homelab.local \
#   --disable traefik \
#   --disable servicelb \
#   --disable local-storage \
#   --write-kubeconfig-mode 644
#
# Node 2+ (Workers):
# curl -sfL https://get.k3s.io | K3S_URL=https://192.168.1.50:6443 \
#   K3S_TOKEN=$(cat /var/lib/rancher/k3s/server/node-token) \
#   sh -s - agent

# kubectl access from workstation:
# scp pi@192.168.1.50:/etc/rancher/k3s/k3s.yaml ~/.kube/config-homelab
# sed -i 's/127.0.0.1/192.168.1.50/' ~/.kube/config-homelab
# export KUBECONFIG=~/.kube/config-homelab

# Helm Repos to Add:
# helm repo add longhorn https://charts.longhorn.io
# helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
# helm repo add grafana https://grafana.github.io/helm-charts
# helm repo add jetstack https://charts.jetstack.io
# helm repo add external-dns https://kubernetes-sigs.github.io/external-dns/
# helm update

# Core Deployments:
# 
# # Longhorn (Distributed Storage)
# helm install longhorn longhorn/longhorn \
#   --namespace longhorn-system --create-namespace \
#   --set defaultSettings.backupTarget=s3://homelab-backups@us-east-1 \
#   --set defaultSettings.backupTargetCredentialSecret=longhorn-backup-credentials
#
# # Cert-Manager
# helm install cert-manager jetstack/cert-manager \
#   --namespace cert-manager --create-namespace \
#   --version v1.13.0 \
#   --set installCRDs=true \
#   --set ingressShim.defaultIssuerName=letsencrypt-prod \
#   --set ingressShim.defaultIssuerKind=ClusterIssuer \
#   --set ingressShim.defaultIssuerGroup=cert-manager.io
#
# # Prometheus Stack
# helm install prometheus prometheus-community/kube-prometheus-stack \
#   --namespace monitoring --create-namespace \
#   --set prometheus.prometheusSpec.retention=30d \
#   --set prometheus.prometheusSpec.storageSpec.volumeClaimTemplate.spec.storageClassName=longhorn \
#   --set prometheus.prometheusSpec.storageSpec.volumeClaimTemplate.spec.resources.requests.storage=10Gi \
#   --set grafana.persistence.enabled=true \
#   --set grafana.persistence.storageClassName=longhorn \
#   --set grafana.persistence.size=5Gi
#
# # Loki Stack
# helm install loki grafana/loki-stack \
#   --namespace logging --create-namespace \
#   --set loki.persistence.enabled=true \
#   --set loki.persistence.storageClassName=longhorn \
#   --set loki.persistence.size=10Gi
#
# # Tempo (Distributed Tracing)
# helm install tempo grafana/tempo \
#   --namespace tracing --create-namespace \
#   --set persistence.enabled=true \
#   --set persistence.storageClassName=longhorn
#
# # External-DNS
# helm install external-dns external-dns/external-dns \
#   --namespace external-dns --create-namespace \
#   --set provider=cloudflare \
#   --set env[0].name=CF_API_TOKEN \
#   --set env[0].valueFrom.secretKeyRef.name=cloudflare-credentials \
#   --set env[0].valueFrom.secretKeyRef.key=api-token
#
# # Postgres Operator (Patroni)
# helm install postgres-operator zalando/postgres-operator \
#   --namespace postgres-system --create-namespace
#
# # Then create Postgresql cluster:
# kubectl apply -f - <<EOF
# apiVersion: "acid.zalan.do/v1"
# kind: postgresql
# metadata:
#   name: homelab-postgres
#   namespace: databases
# spec:
#   teamId: homelab
#   volume:
#     size: 20Gi
#     storageClass: longhorn
#   numberOfInstances: 3
#   postgresql:
#     version: "15"
#   users:
#     admin:
#       - superuser
#       - createdb
#   databases:
#     nextcloud: admin
#     vaultwarden: admin
#     authelia: admin
#   resources:
#     requests:
#       cpu: 500m
#       memory: 1Gi
#     limits:
#       cpu: 2000m
#       memory: 4Gi
# EOF