# Submariner Cross-Cluster Service Discovery

## Overview
Submariner provides cross-cluster service discovery and connectivity for Kubernetes clusters.
It enables services in one cluster to be accessible in another cluster seamlessly.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        SUBMARINER ARCHITECTURE                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────────┐                    ┌──────────────────┐              │
│  │   Cluster 1      │                    │   Cluster 2      │              │
│  │  (Pi 4B)         │                    │  (Pi 5)          │              │
│  │                  │                    │                  │              │
│  │ ┌──────────────┐ │                    │ ┌──────────────┐ │              │
│  │ │ Submariner   │ │◀── Cable/IPsec ──▶│ │ Submariner   │ │              │
│  │ │ Gateway      │ │   (VXLAN/GENEVE)   │ │ Gateway      │ │              │
│  │ │ (Gateway)    │ │                    │ │ (Gateway)    │ │              │
│  │ └──────────────┘ │                    │ └──────────────┘ │              │
│  │        │         │                    │        │         │              │
│  │        ▼         │                    │        ▼         │              │
│  │ ┌──────────────┐ │                    │ ┌──────────────┐ │              │
│  │ │ Service      │ │                    │ │ Service      │ │              │
│  │ │ Discovery    │ │                    │ │ Discovery    │ │              │
│  │ │ (Lighthouse) │ │◀── DNS sync ──────▶│ │ (Lighthouse) │ │              │
│  │ └──────────────┘ │                    │ └──────────────┘ │              │
│  │        │         │                    │        │         │              │
│  │        ▼         │                    │        ▼         │              │
│  │ ┌──────────────┐ │                    │ ┌──────────────┐ │              │
│  │ │ Services     │ │                    │ │ Services     │ │              │
│  │ │ (Nextcloud,  │ │                    │ │ (PostgreSQL, │ │              │
│  │ │  Vaultwarden)│ │                    │ │  Redis)      │ │              │
│  │ └──────────────┘ │                    │ └──────────────┘ │              │
│  └──────────────────┘                    └──────────────────┘              │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Components

1. **Submariner Gateway** - Establishes tunnels between clusters
2. **Submariner Route Agent** - Populates route tables
3. **Lighthouse (Service Discovery)** - DNS-based cross-cluster service discovery
4. **Globalnet** - Handles overlapping CIDRs

## Prerequisites

- Kubernetes v1.21+ on all clusters
- Network connectivity between cluster gateways (direct or via VPN)
- Non-overlapping pod/service CIDRs (or use Globalnet)
- Cluster admin access on all clusters

## Installation

### 1. Install Submariner on Cluster 1 (Pi 4B)
```bash
# Add helm repo
helm repo add submariner-latest https://submariner-io.github.io/submariner-helm
helm repo update

# Install Submariner operator
helm install submariner-operator submariner-latest/submariner-operator \
  --namespace submariner-operator --create-namespace \
  --version 0.16.0

# Create Submariner resource
kubectl apply -f - <<EOF
apiVersion: submariner.io/v1alpha1
kind: Submariner
metadata:
  name: submariner
  namespace: submariner-operator
spec:
  brokerK8sSecret: submariner-broker
  credentialsSecret: submariner-credentials
  cni: "calico"
  natEnabled: true
  globalnetEnabled: true
  serviceDiscoveryEnabled: true
  clusterid: homelab-pi4
  clusterCidr: 192.168.0.0/16
  serviceCidr: 10.96.0.0/12
  globalCidr: 242.0.0.0/8
  globalnet:
    enabled: true
    clusterSize: 256
  connectionTimeout: 30s
  reconnectTimeout: 10s
  debug: false
EOF
```

### 2. Install Submariner on Cluster 2 (Pi 5)
```bash
# Same as above but with different clusterid
kubectl apply -f - <<EOF
apiVersion: submariner.io/v1alpha1
kind: Submariner
metadata:
  name: submariner
  namespace: submariner-operator
spec:
  brokerK8sSecret: submariner-broker
  credentialsSecret: submariner-credentials
  cni: "calico"
  natEnabled: true
  globalnetEnabled: true
  serviceDiscoveryEnabled: true
  clusterid: homelab-pi5
  clusterCidr: 192.168.0.0/16
  serviceCidr: 10.96.0.0/12
  globalCidr: 242.0.0.0/8
  globalnet:
    enabled: true
    clusterSize: 256
  connectionTimeout: 30s
  reconnectTimeout: 10s
  debug: false
EOF
```

### 3. Configure Broker (Management Cluster)
```bash
# On management cluster, create broker
kubectl apply -f - <<EOF
apiVersion: submariner.io/v1alpha1
kind: Broker
metadata:
  name: submariner-broker
  namespace: submariner-operator
spec:
  globalnetEnabled: true
EOF
```

## Cross-Cluster Service Export/Import

### Export Service from Cluster 1 (Pi 4B)
```yaml
# On Cluster 1 - export Nextcloud
apiVersion: submariner.io/v1alpha1
kind: ServiceExport
metadata:
  name: nextcloud
  namespace: apps
```

### Import Service on Cluster 2 (Pi 5)
```yaml
# Automatic via Lighthouse - creates ServiceImport
# Result: nextcloud.apps.svc.clusterset.local
```

### Access Cross-Cluster Service
```bash
# From any pod in Cluster 2, access Nextcloud in Cluster 1
curl http://nextcloud.apps.svc.clusterset.local

# Or use short name if in same namespace
curl http://nextcloud.apps
```

## Lighthouse Service Discovery

### Enable Lighthouse (installed with Submariner)
```bash
# Lighthouse is automatically installed with Submariner
# It creates DNS records for cross-cluster services

# Check Lighthouse deployment
kubectl get deployment lighthouse-agent -n submariner-operator
kubectl get deployment lighthouse-dns -n submariner-operator
```

### DNS Resolution
```bash
# Services are available as:
# <service>.<namespace>.svc.clusterset.local
# <service>.<namespace>.svc.<cluster>.clusterset.local

# Example:
# nextcloud.apps.svc.clusterset.local
# nextcloud.apps.svc.homelab-pi4.clusterset.local
# prometheus.monitoring.svc.clusterset.local
```

## Cross-Cluster Service Examples

### Database Access
```yaml
# Cluster 1 exports PostgreSQL
apiVersion: submariner.io/v1alpha1
kind: ServiceExport
metadata:
  name: postgresql
  namespace: databases

# Cluster 2 can now access:
# postgresql.databases.svc.clusterset.local:5432
```

### Redis Access
```yaml
# Cluster 1 exports Redis
apiVersion: submariner.io/v1alpha1
kind: ServiceExport
metadata:
  name: redis
  namespace: databases

# Cluster 2 can access:
# redis.databases.svc.clusterset.local:6379
```

### Monitoring Stack
```yaml
# Export Prometheus for cross-cluster metrics
apiVersion: submariner.io/v1alpha1
kind: ServiceExport
metadata:
  name: prometheus
  namespace: monitoring

# Export Grafana for unified dashboards
apiVersion: submariner.io/v1alpha1
kind: ServiceExport
metadata:
  name: grafana
  namespace: monitoring

# Export Alertmanager
apiVersion: submariner.io/v1alpha1
kind: ServiceExport
metadata:
  name: alertmanager
  namespace: monitoring
```

## Globalnet (Overlapping CIDR Handling)

```yaml
# If clusters have overlapping CIDRs, enable Globalnet
globalnet:
  enabled: true
  clusterSize: 256  # Max pods per node
```

Globalnet assigns global IPs from 242.0.0.0/8 to pods, avoiding conflicts.

## Network Policies for Cross-Cluster

```yaml
# Allow cross-cluster traffic
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-submariner
  namespace: apps
spec:
  podSelector: {}
  policyTypes:
    - Ingress
    - Egress
  ingress:
    - from:
        - namespaceSelector:
            matchLabels:
              submariner.io/gateway: "true"
      ports:
        - protocol: TCP
          port: 80
        - protocol: TCP
          port: 443
  egress:
    - to:
        - namespaceSelector:
            matchLabels:
              submariner.io/gateway: "true"
      ports:
        - protocol: TCP
        - protocol: UDP
```

## Troubleshooting

### Check Gateway Status
```bash
kubectl get gateway -n submariner-operator
kubectl describe gateway -n submariner-operator
```

### Check Connection Status
```bash
kubectl get connection -n submariner-operator
kubectl describe connection -n submariner-operator
```

### Check Service Discovery
```bash
kubectl get serviceexport -A
kubectl get serviceimport -A
```

### Debug Gateway Logs
```bash
kubectl logs -n submariner-operator -l app=submariner-gateway -c submariner-gateway
kubectl logs -n submariner-operator -l app=submariner-routeagent -c route-agent
```

### Debug Lighthouse
```bash
kubectl logs -n submariner-operator -l app=lighthouse-agent
kubectl logs -n submariner-operator -l app=lighthouse-dns
```

## Monitoring

### Prometheus Metrics
```promql
# Submariner gateway status
submariner_gateway_status{cluster="homelab-pi4"}

# Connection status
submariner_connection_status{cluster="homelab-pi4"}

# Service export/import counts
submariner_serviceexport_total
submariner_serviceimport_total

# Gateway throughput
rate(submariner_gateway_bytes_sent_total[5m])
```

### Alerts
```yaml
groups:
- name: submariner
  rules:
  - alert: SubmarinerGatewayDown
    expr: submariner_gateway_status{status="down"} == 1
    for: 5m
    labels:
      severity: critical
    annotations:
      summary: "Submariner gateway down for {{ $labels.cluster }}"
      
  - alert: SubmarinerConnectionDown
    expr: submariner_connection_status{status="down"} == 1
    for: 5m
    labels:
      severity: critical
    annotations:
      summary: "Submariner connection down between clusters"
```