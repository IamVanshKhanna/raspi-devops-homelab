# mTLS Implementation with Linkerd

## Overview
This document describes the implementation of mutual TLS (mTLS) across all services in the homelab-prod cluster using Linkerd service mesh.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Linkerd Control Plane                      │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │   Proxy     │  │   Identity  │  │   Destination / Tap     │  │
│  │  Injector   │  │   Service   │  │   Profile Services      │  │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
          ┌───────────────────┼───────────────────┐
          ▼                   ▼                   ▼
    ┌──────────┐        ┌──────────┐        ┌──────────┐
    │ Traefik  │        │  Apps    │        │   Auth   │
    │ (Ingress)│        │          │        │ (Authelia)│
    └──────────┘        └──────────┘        └──────────┘
```

## Installation

### 1. Install Linkerd CLI
```bash
curl --proto '=https' --tlsv1.2 -sSfL https://run.linkerd.io/install | sh
export PATH=$PATH:$HOME/.linkerd2/bin
```

### 2. Pre-install Checks
```bash
linkerd check --pre
```

### 3. Install Linkerd Control Plane
```bash
linkerd install \
  --ha \
  --set proxy.logging=info \
  --set proxy.cpu.request=100m \
  --set proxy.memory.request=64Mi \
  --set proxy.cpu.limit=500m \
  --set proxy.memory.limit=128Mi \
  --set-file identityTrustAnchorsPEM=ca.crt \
  --set identityTrustDomain=homelab.local \
  | kubectl apply -f -
```

### 4. Verify Installation
```bash
linkerd check
```

### 5. Install Viz Extension (Dashboard)
```bash
linkerd viz install | kubectl apply -f -
linkerd viz check
```

## Configuration

### 1. Automatic mTLS
Linkerd automatically enables mTLS for all meshed pods:
- Service-to-service: mTLS enforced
- Ingress (Traefik): mTLS from edge
- Egress: mTLS to external services (where supported)

### 2. Service Profiles
Create service profiles for better observability and traffic splitting:

```yaml
# config/linkerd/service-profiles.yaml
apiVersion: linkerd.io/v1alpha2
kind: ServiceProfile
metadata:
  name: nextcloud.apps.svc.cluster.local
  namespace: apps
spec:
  retryBudget:
    retryRatio: 0.2
    minRetriesPerSecond: 10
    ttl: 10s
  routes:
  - name: "WebDAV"
    condition:
      method: "PROPFIND"
      pathRegex: "/remote.php/dav/.*"
    isRetryable: true
    timeout: 30s
  - name: "API"
    condition:
      pathRegex: "/ocs/v2.php/.*"
    isRetryable: true
    timeout: 10s
```

### 3. Traffic Splitting (Canary Deployments)
```yaml
# config/linkerd/traffic-split.yaml
apiVersion: split.smi-spec.io/v1alpha2
kind: TrafficSplit
metadata:
  name: nextcloud-canary
  namespace: apps
spec:
  service: nextcloud
  backends:
  - service: nextcloud
    weight: 900m
  - service: nextcloud-canary
    weight: 100m
```

### 4. Network Policies with Linkerd
Update network policies to allow Linkerd sidecar communication:

```yaml
# config/network-policies/allow/linkerd-sidecar.yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-linkerd-sidecar
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
              linkerd.io/control-plane-ns: "true"
  egress:
    - to:
        - namespaceSelector:
            matchLabels:
              linkerd.io/control-plane-ns: "true"
```

### 5. External Traffic (TLS Termination)
Configure Traefik to work with Linkerd mTLS:

```yaml
# config/traefik/traefik-linkerd.yaml
apiVersion: traefik.io/v1alpha1
kind: IngressRoute
metadata:
  name: traefik-internal
  namespace: traefik
spec:
  entryPoints:
    - websecure
  routes:
  - match: Host(`internal.homelab.local`)
    kind: Rule
    services:
    - name: linkerd-proxy
      port: 4143
      scheme: h2c
    middlewares:
    - name: linkerd-auth
```

## mTLS Verification

### Check mTLS Status
```bash
# Check all meshed pods
linkerd stat deployments -n apps

# Check mTLS status for specific deployment
linkerd routes deployment/nextcloud -n apps

# Check tap for live traffic
linkerd tap deployment/nextcloud -n apps
```

### Verify mTLS in Prometheus
```promql
# Check mTLS success rate
sum(rate(linkerd_server_tls_handshake_total{result="success"}[5m])) 
/ sum(rate(linkerd_server_tls_handshake_total[5m]))

# Check mTLS handshake errors
rate(linkerd_server_tls_handshake_total{result!="success"}[5m])
```

## Certificate Management

### Automatic Rotation
Linkerd automatically rotates certificates every 24 hours by default.

### Custom CA (Optional)
```bash
# Generate custom CA
openssl req -x509 -newkey rsa:4096 -keyout ca.key -out ca.crt \
  -days 365 -nodes -subj "/CN=homelab.local"

# Install with custom CA
linkerd install \
  --identity-trust-anchors-file ca.crt \
  --identity-trust-domain homelab.local \
  | kubectl apply -f -
```

## Monitoring

### Grafana Dashboards
Linkerd Viz provides pre-built dashboards:
- Service health overview
- Request rate, error rate, latency (RED metrics)
- mTLS handshake metrics
- Traffic split visualization

### Alerts
```yaml
# config/prometheus/rules/linkerd-alerts.yaml
groups:
- name: linkerd
  rules:
  - alert: LinkerdControlPlaneDown
    expr: up{job="linkerd-controller"} == 0
    for: 1m
    labels:
      severity: critical
    annotations:
      summary: "Linkerd control plane down"
      
  - alert: LinkerdHighFailedHandshakes
    expr: rate(linkerd_server_tls_handshake_total{result!="success"}[5m]) > 0.01
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "High mTLS handshake failure rate"
```

## Troubleshooting

| Issue | Check | Resolution |
|-------|-------|------------|
| Pod not meshed | `linkerd check --proxy` | Check proxy injector, annotations |
| mTLS handshake failures | `linkerd check --proxy` | Check identity, trust anchors |
| High latency | `linkerd routes` | Check service profiles, timeouts |
| Sidecar crash | `kubectl logs -c linkerd-proxy` | Check resources, config |

## Upgrading Linkerd
```bash
# Upgrade CLI
curl --proto '=https' --tlsv1.2 -sSfL https://run.linkerd.io/install | sh

# Upgrade control plane
linkerd upgrade | kubectl apply -f -

# Verify
linkerd check
```

## Uninstalling
```bash
linkerd uninstall | kubectl apply -f -
linkerd viz uninstall | kubectl apply -f -
```