#!/usr/bin/env python3
"""
Generate default deny NetworkPolicy for all namespaces
"""

NAMESPACES = [
    "kube-system",
    "monitoring",
    "logging",
    "tracing",
    "auth",
    "secrets",
    "apps",
    "smarthome",
    "uptime",
    "security",
    "ai",
    "databases",
    "longhorn-system",
    "cert-manager",
    "external-dns",
    "postgres-system",
    "argocd",
    "traefik",
]

for ns in NAMESPACES:
    content = f"""# Default Deny Ingress - {ns}
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-ingress
  namespace: {ns}
spec:
  podSelector: {{}}
  policyTypes:
    - Ingress
"""
    with open(f"/home/ubuntu_wsl/raspi-devops-homelab/config/network-policies/deny/{ns}.yaml", "w") as f:
        f.write(content)

print(f"Generated {len(NAMESPACES)} deny policies")