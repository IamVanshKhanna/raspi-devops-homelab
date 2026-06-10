# Loki Multi-Tenancy for Federated Logging

## Overview
Loki multi-tenancy enables centralized log aggregation across multiple clusters with tenant isolation.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      LOKI MULTI-TENANCY                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐      │
│  │  Cluster 1   │    │  Cluster 2   │    │  Cluster N   │      │
│  │  (Pi 4B)     │    │  (Pi 5)      │    │  (DR/Cloud)  │      │
│  │              │    │              │    │              │      │
│  │ Promtail ──▶ │    │ Promtail ──▶ │    │ Promtail ──▶ │      │
│  │ Tenant: pi4  │    │ Tenant: pi5  │    │ Tenant: dr   │      │
│  └──────────────┘    └──────────────┘    └──────────────┘      │
│         │                   │                   │                │
│         │ Loki Push API     │ Loki Push API     │ Loki Push API  │
│         ▼                   ▼                   ▼                │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                    LOKI (Centralized)                    │    │
│  │  ┌─────────────────────────────────────────────────────┐  │    │
│  │  │              Tenant Isolation                        │  │    │
│  │  │  pi4  │  pi5  │  dr  │  ...                         │  │    │
│  │  └─────────────────────────────────────────────────────┘  │    │
│  │  ┌─────────────────────────────────────────────────────┐  │    │
│  │  │              Object Storage (S3/B2)                  │  │    │
│  │  └─────────────────────────────────────────────────────┘  │    │
│  └─────────────────────────────────────────────────────────┘    │
│                           │                                      │
│                           ▼                                      │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                    GRAFANA                                │    │
│  │  Queries Loki with tenant header                         │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Configuration

### Central Loki (Management Cluster)

```yaml
# loki-stack values for multi-tenancy
loki:
  auth_enabled: true
  multi_tenant: true
  
  limits:
    ingestion_rate_mb: 10
    ingestion_burst_size_mb: 20
    per_stream_rate_limit: 3MB
    per_stream_rate_limit_burst: 10MB
    max_entries_per_query: 50000
    max_global_streams_per_user: 10000
    reject_old_samples: true
    reject_old_samples_max_age: 168h
    creation_grace_period: 10m
    max_line_size: 256KB
```

### Per-Cluster Promtail

```yaml
# Promtail configuration per cluster
promtail:
  config:
    clients:
      - url: http://loki.monitoring:3100/loki/api/v1/push
        tenant_id: "pi4"  # or pi5, dr, etc.
        basic_auth:
          username: "loki-writer"
          password: "${LOKI_PASSWORD}"
```

## Implementation

### 1. Central Loki (Management Cluster)

```bash
helm install loki grafana/loki-stack \
  --namespace logging \
  --set loki.auth_enabled=true \
  --set loki.multi_tenant=true \
  --set loki.limits.ingestion_rate_mb=10 \
  --set loki.limits.ingestion_burst_size_mb=20 \
  --version 5.0.0
```

### 2. Per-Cluster Promtail

```yaml
# promtail-values-pi4.yaml
promtail:
  config:
    clients:
      - url: http://loki.monitoring:3100/loki/api/v1/push
        tenant_id: "homelab-pi4"
        basic_auth:
          username: "loki-writer"
          password: "${LOKI_PASSWORD}"
    positions:
      directory: /var/log/positions
    scrape_configs:
      - job_name: kubernetes-pods
        kubernetes_sd_configs:
        - role: pod
```

### 3. Grafana Data Source

```yaml
# Grafana Loki datasource with tenant support
apiVersion: 1
datasources:
  - name: Loki
    type: loki
    url: http://loki.logging:3100
    access: proxy
    jsonData:
      derivedFields:
        - name: TraceID
          matcherRegex: "trace[=:]([a-f0-9]+)"
          url: http://tempo.tracing:3200/tempo/traces/${__value.raw}
      maxLines: 1000
      timeout: 60s
```

## Tenant Management

### Create Tenant
```bash
# Create tenant with limits
curl -X POST http://loki.logging:3100/api/admin/tenant \
  -H "Content-Type: application/json" \
  -d '{"tenant_id": "homelab-pi4", "limits": {"ingestion_rate_mb": 10, "retention_period": "30d"}}'
```

### List Tenants
```bash
curl http://loki.logging:3100/api/admin/tenants
```

### Delete Tenant
```bash
curl -X DELETE http://loki.logging:3100/api/admin/tenant/homelab-pi4
```

## Queries

### Per-Tenant Queries (Grafana)
```logql
# Query logs for specific tenant
{tenant="homelab-pi4"} |= "error"

# Cross-tenant query (admin only)
| tenant | cluster | namespace | pod | message |
```

### Multi-Tenant Alerting
```yaml
groups:
- name: loki-multi-tenant
  rules:
  - alert: HighErrorRate
    expr: |
      sum by (tenant, cluster) (rate({tenant=~"homelab-.*"} |= "error" [5m])) > 10
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "High error rate in {{ $labels.tenant }}/{{ $labels.cluster }}"
```

## Network Policies

```yaml
# Allow Promtail from workload clusters to Loki
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-promtail-to-loki
  namespace: logging
spec:
  podSelector:
    matchLabels:
      app: loki
  policyTypes:
    - Ingress
  ingress:
    - from:
        - namespaceSelector:
            matchLabels:
              kubernetes.io/metadata.name: monitoring
      ports:
        - protocol: TCP
          port: 3100
    - from:
        - podSelector:
            matchLabels:
              app: promtail
      ports:
        - protocol: TCP
          port: 3100
```

## Retention per Tenant

```yaml
# loki-config.yaml
limits_config:
  # Global retention
  retention_period: 30d
  
  # Per-tenant overrides via Loki API
  # curl -X POST http://loki:3100/api/admin/tenant/homelab-pi4/limits \
  #   -d '{"retention_period": "90d"}'
```

## Integration with Thanos

```promql
# Correlate logs with metrics
# In Grafana: Use Loki for logs, Thanos for metrics
# Shared correlation ID: trace_id, span_id
```

## Backup Strategy

```bash
# Backup Loki configuration
kubectl get configmap loki -n logging -o yaml > loki-config-backup.yaml

# Backup tenant configs
curl http://loki:3100/api/admin/tenants > tenants-backup.json
```