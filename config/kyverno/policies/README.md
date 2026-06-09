# Kyverno Policies for Homelab Admission Control

This directory contains Kyverno ClusterPolicy and Policy resources for enforcing security and compliance standards.

## Structure

```
config/kyverno/policies/
├── 00-require-digest-pinning.yaml      # Require @sha256 digest for all images
├── 01-disallow-latest-tag.yaml         # Block :latest tags
├── 02-require-resource-limits.yaml     # Require CPU/memory limits
├── 03-disallow-privileged.yaml         # Block privileged containers
├── 04-require-non-root.yaml            # Require non-root user
├── 05-require-readonly-rootfs.yaml     # Require read-only root filesystem
├── 06-disallow-host-namespace.yaml     # Block hostNetwork/hostPID/hostIPC
├── 07-require-labels.yaml              # Require standard labels
├── 08-restrict-capabilities.yaml       # Drop ALL caps, add only required
├── 09-require-network-policy.yaml      # Require NetworkPolicy per namespace
├── 10-validate-prometheus-rules.yaml   # Validate PrometheusRule syntax
├── 11-restrict-external-secrets.yaml   # Validate ExternalSecret references
└── 12-require-pod-disruption-budget.yaml # Require PDB for stateful workloads
```

## Installation

```bash
# Install Kyverno
helm repo add kyverno https://kyverno.github.io/kyverno/
helm repo update
helm install kyverno kyverno/kyverno --namespace kyverno --create-namespace

# Apply policies
kubectl apply -f config/kyverno/policies/
```

## Policy Categories

### Supply Chain Security
- `00-require-digest-pinning.yaml` - Enforce digest pinning
- `01-disallow-latest-tag.yaml` - Block :latest tags

### Pod Security Standards (Restricted)
- `02-require-resource-limits.yaml` - Resource quotas
- `03-disallow-privileged.yaml` - No privileged containers
- `04-require-non-root.yaml` - Run as non-root
- `05-require-readonly-rootfs.yaml` - Read-only rootfs
- `06-disallow-host-namespace.yaml` - No host namespaces
- `08-restrict-capabilities.yaml` - Minimal capabilities

### Operational Standards
- `07-require-labels.yaml` - Standard metadata
- `09-require-network-policy.yaml` - Zero-trust networking
- `10-validate-prometheus-rules.yaml` - Monitoring validity
- `11-restrict-external-secrets.yaml` - Secrets management
- `12-require-pod-disruption-budget.yaml` - HA guarantees

## Exceptions

Exceptions are handled via `kyverno.io/exclude` annotations or separate PolicyException resources (Kyverno v1.11+).