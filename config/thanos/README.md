# Thanos Federated Prometheus for Multi-Cluster Observability

## Overview
Thanos provides global querying, deduplication, and long-term storage for Prometheus metrics across multiple clusters.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           THANOS FEDERATION                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐                  │
│  │  Cluster 1   │    │  Cluster 2   │    │  Cluster N   │                  │
│  │  (Pi 4B)     │    │  (Pi 5)      │    │  (DR/Cloud)  │                  │
│  │              │    │              │    │              │                  │
│  │ Prometheus   │    │ Prometheus   │    │ Prometheus   │                  │
│  │ + Sidecar    │    │ + Sidecar    │    │ + Sidecar    │                  │
│  └──────┬───────┘    └──────┬───────┘    └──────┬───────┘                  │
│         │                   │                   │                           │
│         │ remote-write      │ remote-write      │ remote-write             │
│         ▼                   ▼                   ▼                           │
│  ┌─────────────────────────────────────────────────────────────────┐       │
│  │                     THANOS QUERY (Global)                        │       │
│  │  Deduplicates + merges metrics from all sidecars                │       │
│  └─────────────────────────────────────────────────────────────────┘       │
│         │                                                                    │
│         │                    ┌──────────────────┐                          │
│         ├─── Obj Store ─────▶│  S3/B2/GCS       │                          │
│         │                    │  Long-term store │                          │
│         │                    └──────────────────┘                          │
│         │                                                                    │
│         ▼                                                                    │
│  ┌─────────────────────────────────────────────────────────────────┐       │
│  │                    GRAFANA (Single Pane)                         │       │
│  │  Queries Thanos Query for global metrics                         │       │
│  └─────────────────────────────────────────────────────────────────┘       │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Components

1. **Thanos Sidecar** (per cluster) - Uploads blocks to object storage, serves StoreAPI
2. **Thanos Query** (global) - Queries all sidecars + object store
3. **Thanos Store Gateway** - Serves StoreAPI for historical data
4. **Thanos Compactor** - Downsampling and compaction
5. **Thanos Ruler** - Global alerting and recording rules

## Installation

### Per Workload Cluster (Sidecar)
```bash
# Add Thanos to existing Prometheus
helm repo add bitnami https://charts.bitnami.com/bitnami
helm install thanos-sidecar bitnami/thanos-sidecar \
  --namespace monitoring \
  --prometheus-url=http://prometheus:9090 \
  --objstore.config='{"type":"S3","config":{"bucket":"homelab-thanos","endpoint":"s3.us-east-1.amazonaws.com","access_key":"...","secret_key":"..."}}'
```

### Management Cluster (Global Components)
```bash
helm install thanos-query bitnami/thanos-query \
  --namespace monitoring \
  --replicaCount=2 \
  --stores="thanos-sidecar.monitoring:10901,thanos-store-gateway.monitoring:10901"

helm install thanos-store-gateway bitnami/thanos-store-gateway \
  --namespace monitoring \
  --objstore.config='{"type":"S3","config":{"bucket":"homelab-thanos","endpoint":"s3.us-east-1.amazonaws.com","access_key":"...","secret_key":"..."}}'

helm install thanos-compactor bitnami/thanos-compactor \
  --namespace monitoring \
  --objstore.config='{"type":"S3","config":{"bucket":"homelab-thanos","endpoint":"s3.us-east-1.amazonaws.com","access_key":"...","secret_key":"..."}}' \
  --retention.resolution-raw=30d \
  --retention.resolution-5m=180d \
  --retention.resolution-1h=0d

helm install thanos-ruler bitnami/thanos-ruler \
  --namespace monitoring \
  --replicaCount=2 \
  --objstore.config='{"type":"S3","config":{"bucket":"homelab-thanos","endpoint":"s3.us-east-1.amazonaws.com","access_key":"...","secret_key":"..."}}' \
  --alertmanagers.url="http://alertmanager.monitoring:9093"
```

## Object Store Configuration (Backblaze B2)

```yaml
# thanos-objstore-secret.yaml
apiVersion: v1
kind: Secret
metadata:
  name: thanos-objstore-config
  namespace: monitoring
type: Opaque
stringData:
  objstore.yml: |
    type: S3
    config:
      bucket: homelab-thanos
      endpoint: s3.us-east-005.backblazeb2.com
      access_key: ${B2_KEY_ID}
      secret_key: ${B2_APP_KEY}
      insecure: false
      signature_version2: false
      part_size: 134217728
      sse_type: ""
      sse_kms_key_id: ""
      sse_kms_encryption_context: ""
      http_config:
        idle_conn_timeout: 90s
        response_header_timeout: 2m
        insecure_skip_verify: false
```

## Prometheus Configuration for Thanos Sidecar

```yaml
# prometheus-thanos-config.yaml
apiVersion: monitoring.coreos.com/v1
kind: Prometheus
metadata:
  name: homelab-prometheus
  namespace: monitoring
spec:
  # Enable remote write to Thanos
  remoteWrite:
    - url: http://thanos-receive.monitoring:19291/api/v1/receive
      queueConfig:
        maxSamplesPerSend: 1000
        maxShards: 200
        capacity: 2500
  
  # External labels for cluster identification
  externalLabels:
    cluster: homelab-pi4
    environment: production
    region: local
```

## Deployment via Helmfile

```yaml
# helmfile.yaml additions
releases:
  # Per-cluster sidecar (deploy to each workload cluster)
  - name: thanos-sidecar
    namespace: monitoring
    chart: bitnami/thanos-sidecar
    version: "1.0.0"
    values:
      - helmfile/values/thanos-sidecar.yaml

  # Global components (deploy to management cluster)
  - name: thanos-query
    namespace: monitoring
    chart: bitnami/thanos-query
    version: "1.0.0"
    values:
      - helmfile/values/thanos-query.yaml
      
  - name: thanos-store-gateway
    namespace: monitoring
    chart: bitnami/thanos-store-gateway
    version: "1.0.0"
    values:
      - helmfile/values/thanos-store-gateway.yaml

  - name: thanos-compactor
    namespace: monitoring
    chart: bitnami/thanos-compactor
    version: "1.0.0"
    values:
      - helmfile/values/thanos-compactor.yaml

  - name: thanos-ruler
    namespace: monitoring
    chart: bitnami/thanos-ruler
    version: "1.0.0"
    values:
      - helmfile/values/thanos-ruler.yaml
```

## Queries

### Global Cluster Health
```promql
# All clusters up
up{job="prometheus"} == 1

# Cluster count
count(up{job="prometheus"}) 

# Per-cluster resource usage
sum by (cluster) (rate(container_cpu_usage_seconds_total[5m]))
sum by (cluster) (container_memory_usage_bytes)
```

### Cross-Cluster Comparisons
```promql
# CPU usage across clusters
sum by (cluster) (rate(container_cpu_usage_seconds_total{namespace!="kube-system"}[5m]))

# Memory pressure
sum by (cluster) (container_memory_working_set_bytes / container_spec_memory_limit_bytes)

# Pod count per cluster
count by (cluster) (kube_pod_info)
```

### Deduplication
```promql
# Thanos automatically deduplicates identical metrics from HA pairs
# Use cluster label to distinguish
sum by (cluster, instance) (rate(node_cpu_seconds_total{mode="idle"}[5m]))
```

## Grafana Setup

### Data Source
```yaml
# Grafana datasource for Thanos Query
apiVersion: 1
datasources:
  - name: Thanos
    type: prometheus
    url: http://thanos-query.monitoring:10902
    access: proxy
    isDefault: true
    jsonData:
      timeInterval: "30s"
      queryTimeout: "60s"
```

### Dashboards
- **Cluster Fleet Overview** - All clusters health/status
- **Resource Comparison** - CPU/Memory/Network across clusters
- **Cost Allocation** - Per-cluster resource consumption
- **Global Alerting** - Unified alert view

## Network Policies

```yaml
# Allow Thanos sidecar to query Prometheus
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-thanos-sidecar
  namespace: monitoring
spec:
  podSelector:
    matchLabels:
      app: prometheus
  policyTypes:
    - Ingress
  ingress:
    - from:
        - podSelector:
            matchLabels:
              app: thanos-sidecar
      ports:
        - protocol: TCP
          port: 9090

# Allow Thanos Query to connect to sidecars across clusters
# (Requires cross-cluster networking via Submariner/VPN)
```

## Thanos Receive (Alternative to Sidecar)

```yaml
# For clusters without direct object store access
apiVersion: v1
kind: Service
metadata:
  name: thanos-receive
  namespace: monitoring
spec:
  ports:
    - name: grpc
      port: 10901
    - name: http
      port: 19291
  selector:
    app: thanos-receive

---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: thanos-receive
  namespace: monitoring
spec:
  replicas: 2
  selector:
    matchLabels:
      app: thanos-receive
  template:
    spec:
      containers:
      - name: thanos
        image: quay.io/thanos/thanos:v0.34.0
        args:
        - receive
        - --tsdb.path=/data
        - --remote-write.address=0.0.0.0:19291
        - --grpc-address=0.0.0.0:10901
        - --http-address=0.0.0.0:10902
        - --objstore.config-file=/etc/thanos/objstore.yml
        - --receive.default-tenant-id=homelab
        - --receive.hashrings-file=/etc/thanos/hashrings.json
        ports:
        - containerPort: 10901
        - containerPort: 19291
        - containerPort: 10902
        volumeMounts:
        - name: config
          mountPath: /etc/thanos
        - name: data
          mountPath: /data
      volumes:
      - name: config
        secret:
          secretName: thanos-objstore-config
      - name: data
        emptyDir: {}
```

## Alerting Rules (Global)

```yaml
# config/prometheus/rules/thanus-global-alerts.yaml
groups:
- name: thanos-global
  rules:
  - alert: ClusterDown
    expr: up{job="prometheus"} == 0
    for: 5m
    labels:
      severity: critical
    annotations:
      summary: "Cluster {{ $labels.cluster }} is down"
      
  - alert: ClusterHighCPU
    expr: |
      (sum by (cluster) (rate(container_cpu_usage_seconds_total[5m])) / sum by (cluster) (kube_node_status_capacity_cpu_cores)) > 0.85
    for: 15m
    labels:
      severity: warning
    annotations:
      summary: "Cluster {{ $labels.cluster }} high CPU usage"
      
  - alert: ThanosStoreGatewayDown
    expr: up{job="thanos-store-gateway"} == 0
    for: 5m
    labels:
      severity: critical
    annotations:
      summary: "Thanos Store Gateway down"
```