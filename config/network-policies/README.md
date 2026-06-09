# Network Policies - homelab-prod v2.x

## Overview
Zero-trust network segmentation using Kubernetes NetworkPolicies.
Default deny-all with explicit allow rules for required traffic flows.

## Structure
```
config/network-policies/
├── 00-default-deny-ingress.yaml          # Default namespace deny
├── 01-default-deny-all-namespaces.yaml   # All namespaces default deny
├── deny/                                 # Individual namespace deny policies
│   ├── kube-system.yaml
│   ├── monitoring.yaml
│   ├── logging.yaml
│   └── ...
├── allow/                                # Explicit allow rules
│   ├── allow-traefik-ingress.yaml
│   ├── allow-prometheus-scrape.yaml
│   ├── allow-loki-ingress.yaml
│   ├── allow-tempo-ingress.yaml
│   ├── allow-authelia-traefik.yaml
│   ├── allow-crowdsec-logs.yaml
│   ├── allow-db-from-apps.yaml
│   ├── allow-longhorn-csi.yaml
│   ├── allow-cert-manager-acme.yaml
│   ├── allow-external-dns-egress.yaml
│   └── allow-argocd-egress.yaml
└── scripts/
    ├── generate-deny-policies.py
    ├── generate-allow-policies.py
```

## Traffic Flow Matrix

| From | To | Ports | Protocol |
|------|-----|-------|----------|
| traefik | monitoring | 9090, 3100, 9093, 3200 | TCP |
| traefik | apps | 80, 443 | TCP |
| traefik | uptime | 3001 | TCP |
| traefik | smarthome | 8123 | TCP |
| monitoring | all (scrape) | 9090 | TCP |
| logging | loki | 3100 | TCP |
| tracing | tempo | 3200, 4317, 4318 | TCP |
| traefik | auth (authelia) | 9091 | TCP |
| logging | crowdsec | 3100 | TCP |
| apps/auth/secrets/monitoring | databases | 5432, 6379, 3306 | TCP |
| kube-system | longhorn | 9500 | TCP |
| traefik | cert-manager | 8080, 8081 | TCP |
| external-dns | cloudflare (external) | 443 | TCP |
| argocd | github/registries (external) | 443 | TCP |
| all | DNS | 53 | UDP/TCP |

## Default Policies
- **Default Deny Ingress**: All namespaces deny all ingress by default
- **Default Deny Egress**: All namespaces deny all egress except DNS (53/UDP, 53/TCP)

## Application
```bash
# Apply all policies
kubectl apply -k config/network-policies/

# Or apply individually
kubectl apply -f config/network-policies/00-default-deny-ingress.yaml
kubectl apply -f config/network-policies/01-default-deny-all-namespaces.yaml
kubectl apply -k config/network-policies/
```

## Verification
```bash
# Check policies applied
kubectl get networkpolicies -A

# Test connectivity
kubectl exec -n apps <pod> -- curl -I http://traefik.monitoring.svc.cluster.local:9090
```