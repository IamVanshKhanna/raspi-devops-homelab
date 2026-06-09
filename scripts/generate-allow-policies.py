#!/usr/bin/env python3
"""
Generate allow NetworkPolicies for specific traffic flows
"""

# Allow Traefik ingress to all services
ALLOW_TRAEFIK = """
# Allow Traefik ingress to monitoring
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-traefik-ingress
  namespace: monitoring
spec:
  podSelector: {}
  policyTypes:
    - Ingress
  ingress:
    - from:
        - namespaceSelector:
            matchLabels:
              name: traefik
      ports:
        - protocol: TCP
          port: 9090   # Prometheus
        - protocol: TCP
          port: 3100   # Loki
        - protocol: TCP
          port: 9093   # Alertmanager
        - protocol: TCP
          port: 3200   # Tempo

---
# Allow Traefik ingress to apps
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-traefik-ingress
  namespace: apps
spec:
  podSelector: {}
  policyTypes:
    - Ingress
  ingress:
    - from:
        - namespaceSelector:
            matchLabels:
              name: traefik
      ports:
        - protocol: TCP
          port: 80
        - protocol: TCP
          port: 443

---
# Allow Traefik ingress to uptime
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-traefik-ingress
  namespace: uptime
spec:
  podSelector: {}
  policyTypes:
    - Ingress
  ingress:
    - from:
        - namespaceSelector:
            matchLabels:
              name: traefik
      ports:
        - protocol: TCP
          port: 3001

---
# Allow Traefik ingress to smarthome
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-traefik-ingress
  namespace: smarthome
spec:
  podSelector: {}
  policyTypes:
    - Ingress
  ingress:
    - from:
        - namespaceSelector:
            matchLabels:
              name: traefik
      ports:
        - protocol: TCP
          port: 8123
"""

ALLOW_PROMETHEUS = """
# Allow Prometheus to scrape metrics
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-prometheus-scrape
  namespace: monitoring
spec:
  podSelector: {}
  policyTypes:
    - Ingress
  ingress:
    - from:
        - namespaceSelector:
            matchLabels:
              name: monitoring
      ports:
        - protocol: TCP
          port: 9090
"""

ALLOW_LOKI = """
# Allow Loki to receive logs from Promtail
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-loki-ingress
  namespace: logging
spec:
  podSelector: {}
  policyTypes:
    - Ingress
  ingress:
    - from:
        - namespaceSelector:
            matchLabels:
              name: logging
      ports:
        - protocol: TCP
          port: 3100
    - from:
        - namespaceSelector:
            matchLabels:
              name: monitoring
      ports:
        - protocol: TCP
          port: 3100
"""

ALLOW_TEMPO = """
# Allow Tempo to receive traces from OTEL Collector
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-tempo-ingress
  namespace: tracing
spec:
  podSelector: {}
  policyTypes:
    - Ingress
  ingress:
    - from:
        - namespaceSelector:
            matchLabels:
              name: tracing
      ports:
        - protocol: TCP
          port: 3200
        - protocol: TCP
          port: 4317
        - protocol: TCP
          port: 4318
"""

ALLOW_AUTHELIA = """
# Allow Authelia to communicate with Traefik (ForwardAuth)
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-authelia-traefik
  namespace: auth
spec:
  podSelector: {}
  policyTypes:
    - Ingress
  ingress:
    - from:
        - namespaceSelector:
            matchLabels:
              name: traefik
      ports:
        - protocol: TCP
          port: 9091
"""

ALLOW_CROWDSEC = """
# Allow CrowdSec to read logs
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-crowdsec-logs
  namespace: security
spec:
  podSelector: {}
  policyTypes:
    - Ingress
  ingress:
    - from:
        - namespaceSelector:
            matchLabels:
              name: logging
      ports:
        - protocol: TCP
          port: 3100
"""

ALLOW_DATABASES = """
# Allow database access from applications
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-db-from-apps
  namespace: databases
spec:
  podSelector: {}
  policyTypes:
    - Ingress
  ingress:
    - from:
        - namespaceSelector:
            matchLabels:
              name: apps
      ports:
        - protocol: TCP
          port: 5432  # PostgreSQL
        - protocol: TCP
          port: 6379  # Redis
        - protocol: TCP
          port: 3306  # MariaDB/MySQL
    - from:
        - namespaceSelector:
            matchLabels:
              name: auth
      ports:
        - protocol: TCP
          port: 5432
        - protocol: TCP
          port: 6379
    - from:
        - namespaceSelector:
            matchLabels:
              name: secrets
      ports:
        - protocol: TCP
          port: 5432
        - protocol: TCP
          port: 6379
    - from:
        - namespaceSelector:
            matchLabels:
              name: monitoring
      ports:
        - protocol: TCP
          port: 5432
        - protocol: TCP
          port: 6379
"""

ALLOW_LONGHORN = """
# Allow Longhorn CSI driver
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-longhorn-csi
  namespace: longhorn-system
spec:
  podSelector: {}
  policyTypes:
    - Ingress
  ingress:
    - from:
        - namespaceSelector:
            matchLabels:
              name: kube-system
      ports:
        - protocol: TCP
          port: 9500
"""

ALLOW_CERT_MANAGER = """
# Allow Cert-Manager ACME HTTP-01
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-cert-manager-acme
  namespace: cert-manager
spec:
  podSelector: {}
  policyTypes:
    - Ingress
  ingress:
    - from:
        - namespaceSelector:
            matchLabels:
              name: traefik
      ports:
        - protocol: TCP
          port: 8080
        - protocol: TCP
          port: 8081
"""

ALLOW_EXTERNAL_DNS = """
# Allow External-DNS to update Cloudflare
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-external-dns-egress
  namespace: external-dns
spec:
  podSelector: {}
  policyTypes:
    - Egress
  egress:
    - to:
        - namespaceSelector:
            matchLabels:
              name: cert-manager
      ports:
        - protocol: TCP
          port: 443
    - to: []  # External (Cloudflare API)
      ports:
        - protocol: TCP
          port: 443
"""

ALLOW_ARGOCD = """
# Allow ArgoCD to sync with Git repo
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-argocd-egress
  namespace: argocd
spec:
  podSelector: {}
  policyTypes:
    - Egress
  egress:
    - to:
        - namespaceSelector:
            matchLabels:
              name: cert-manager
      ports:
        - protocol: TCP
          port: 443
    - to: []  # GitHub API
      ports:
        - protocol: TCP
          port: 443
    - to: []  # Docker registry
      ports:
        - protocol: TCP
          port: 443
        - protocol: TCP
          port: 5000
    - to:
        - namespaceSelector: {}
      ports:
        - protocol: UDP
          port: 53
        - protocol: TCP
          port: 53
"""

# Write all policies
policies = {
    "allow-traefik-ingress.yaml": ALLOW_TRAEFIK,
    "allow-prometheus-scrape.yaml": ALLOW_PROMETHEUS,
    "allow-loki-ingress.yaml": ALLOW_LOKI,
    "allow-tempo-ingress.yaml": ALLOW_TEMPO,
    "allow-authelia-traefik.yaml": ALLOW_AUTHELIA,
    "allow-crowdsec-logs.yaml": ALLOW_CROWDSEC,
    "allow-db-from-apps.yaml": ALLOW_DATABASES,
    "allow-longhorn-csi.yaml": ALLOW_LONGHORN,
    "allow-cert-manager-acme.yaml": ALLOW_CERT_MANAGER,
    "allow-external-dns-egress.yaml": ALLOW_EXTERNAL_DNS,
    "allow-argocd-egress.yaml": ALLOW_ARGOCD,
}

for filename, content in policies.items():
    with open(f"/home/ubuntu_wsl/raspi-devops-homelab/config/network-policies/allow/{filename}", "w") as f:
        f.write(content.strip() + "\n")

print(f"Generated {len(policies)} allow policies")