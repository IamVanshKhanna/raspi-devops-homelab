# Kyverno Policy Definitions

## Overview
This document contains Kyverno policies for admission control in the homelab-prod cluster.
Policies enforce security best practices, resource limits, and compliance standards.

## Policy Categories

### 1. Pod Security Standards (Restricted)
```yaml
# config/kyverno/policies/pod-security-restricted.yaml
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: pod-security-restricted
  annotations:
    policies.kyverno.io/title: "Restricted Pod Security"
    policies.kyverno.io/category: "Pod Security Standards"
    policies.kyverno.io/severity: "high"
spec:
  validationFailureAction: Enforce
  background: true
  rules:
    - name: restrict-privileged-containers
      match:
        any:
        - resources:
            kinds:
              - Pod
      validate:
        message: "Privileged containers are not allowed"
        pattern:
          spec:
            containers:
              - securityContext:
                  privileged: "false"
                  
    - name: restrict-host-namespaces
      match:
        any:
        - resources:
            kinds:
              - Pod
      validate:
        message: "Host namespaces are not allowed"
        pattern:
          spec:
            hostNetwork: "false"
            hostPID: "false"
            hostIPC: "false"
            
    - name: require-non-root-user
      match:
        any:
        - resources:
            kinds:
              - Pod
      validate:
        message: "Containers must run as non-root user"
        pattern:
          spec:
            securityContext:
              runAsNonRoot: "true"
              runAsUser: "> 1000"
            containers:
              - securityContext:
                  runAsNonRoot: "true"
                  runAsUser: "> 1000"
                  
    - name: drop-all-capabilities
      match:
        any:
        - resources:
            kinds:
              - Pod
      validate:
        message: "All capabilities must be dropped"
        pattern:
          spec:
            containers:
              - securityContext:
                  capabilities:
                    drop: ["ALL"]
                    
    - name: require-read-only-root-fs
      match:
        any:
        - resources:
            kinds:
              - Pod
      validate:
        message: "Root filesystem must be read-only"
        pattern:
          spec:
            containers:
              - securityContext:
                  readOnlyRootFilesystem: "true"
                  
    - name: restrict-seccomp
      match:
        any:
        - resources:
            kinds:
              - Pod
      validate:
        message: "Seccomp profile must be RuntimeDefault or Localhost"
        pattern:
          spec:
            containers:
              - securityContext:
                  seccompProfile:
                    type: "RuntimeDefault|Localhost"
```

### 2. Resource Requirements
```yaml
# config/kyverno/policies/resource-requirements.yaml
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: require-resource-limits
  annotations:
    policies.kyverno.io/title: "Require Resource Limits"
    policies.kyverno.io/category: "Resource Management"
spec:
  validationFailureAction: Enforce
  background: true
  rules:
    - name: require-limits-and-requests
      match:
        any:
        - resources:
            kinds:
              - Pod
      validate:
        message: "All containers must have CPU and memory limits and requests"
        pattern:
          spec:
            containers:
              - resources:
                  limits:
                    cpu: "?*"
                    memory: "?*"
                  requests:
                    cpu: "?*"
                    memory: "?*"
                    
    - name: limit-max-resources
      match:
        any:
        - resources:
            kinds:
              - Pod
      validate:
        message: "CPU limit must not exceed 4 cores, memory limit must not exceed 8Gi"
        deny:
          conditions:
            all:
            - key: "{{ sum(request.object.spec.containers[*].resources.limits.cpu) }}"
              operator: GreaterThan
              value: "4"
            - key: "{{ sum(request.object.spec.containers[*].resources.limits.memory) }}"
              operator: GreaterThan
              value: "8Gi"
```

### 3. Image Security
```yaml
# config/kyverno/policies/image-security.yaml
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: image-security
  annotations:
    policies.kyverno.io/title: "Image Security Requirements"
    policies.kyverno.io/category: "Supply Chain Security"
spec:
  validationFailureAction: Enforce
  background: true
  rules:
    - name: require-digest-pinning
      match:
        any:
        - resources:
            kinds:
              - Pod
              - Deployment
              - StatefulSet
              - DaemonSet
              - Job
              - CronJob
      validate:
        message: "Images must be pinned by digest (@sha256:)"
        pattern:
          spec:
            containers:
              - image: "*@sha256:*"
              
    - name: disallow-latest-tag
      match:
        any:
        - resources:
            kinds:
              - Pod
              - Deployment
              - StatefulSet
              - DaemonSet
              - Job
              - CronJob
      validate:
        message: "Image tag 'latest' is not allowed"
        deny:
          conditions:
            any:
            - key: "{{ request.object.spec.containers[*].image }}"
              operator: Matches
              value: ".*:latest$"
              
    - name: require-trusted-registry
      match:
        any:
        - resources:
            kinds:
              - Pod
      validate:
        message: "Images must come from trusted registries"
        deny:
          conditions:
            all:
            - key: "{{ request.object.spec.containers[*].image }}"
              operator: NotMatches
              value: "^(registry\\.example\\.com|docker\\.io/library|ghcr\\.io/your-org)/.*"
              
    - name: verify-cosign-signature
      match:
        any:
        - resources:
            kinds:
              - Pod
              - Deployment
              - StatefulSet
              - DaemonSet
      verifyImages:
        - imageReferences:
            - "*"
          attesters:
            - entries:
              - keys:
                  publicKeys: |-
                    -----BEGIN PUBLIC KEY-----
                    ...
                    -----END PUBLIC KEY-----
```

### 4. Secret Management
```yaml
# config/kyverno/policies/secret-management.yaml
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: secret-management
  annotations:
    policies.kyverno.io/title: "Secret Management"
    policies.kyverno.io/category: "Secrets Management"
spec:
  validationFailureAction: Enforce
  background: true
  rules:
    - name: no-plain-secrets-in-configmaps
      match:
        any:
        - resources:
            kinds:
              - ConfigMap
      validate:
        message: "ConfigMaps must not contain sensitive data"
        deny:
          conditions:
            any:
            - key: "{{ request.object.data }}"
              operator: Matches
              value: "(?i)(password|secret|token|key|credential)"
              
    - name: secrets-must-have-labels
      match:
        any:
        - resources:
            kinds:
              - Secret
      validate:
        message: "Secrets must have required labels"
        pattern:
          metadata:
            labels:
              app.kubernetes.io/name: "?*"
              app.kubernetes.io/managed-by: "?*"
              
    - name: secrets-type-validation
      match:
        any:
        - resources:
            kinds:
              - Secret
      validate:
        message: "Secrets must have type specified"
        pattern:
          type: "Opaque|kubernetes.io/tls|kubernetes.io/dockerconfigjson"
```

### 5. Network Policy Enforcement
```yaml
# config/kyverno/policies/network-policy.yaml
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: network-policy-existence
  annotations:
    policies.kyverno.io/title: "Require Network Policies"
    policies.kyverno.io/category: "Network Security"
spec:
  validationFailureAction: Audit
  background: true
  rules:
    - name: require-network-policy
      match:
        any:
        - resources:
            kinds:
              - Namespace
      validate:
        message: "Namespaces must have at least one NetworkPolicy"
        deny:
          conditions:
            all:
            - key: "{{ request.object.metadata.name }}"
              operator: NotIn
              value: ["kube-system", "kube-public", "kube-node-lease"]
            - key: "{{ networkpolicies[request.object.metadata.name].length }}"
              operator: Equals
              value: 0
```

### 6. Helm Release Validation
```yaml
# config/kyverno/policies/helm-release.yaml
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: helm-release-validation
  annotations:
    policies.kyverno.io/title: "Helm Release Validation"
    policies.kyverno.io/category: "Deployment Safety"
spec:
  validationFailureAction: Enforce
  background: true
  rules:
    - name: require-helm-release-annotations
      match:
        any:
        - resources:
            kinds:
              - HelmRelease
      validate:
        message: "HelmReleases must have required metadata"
        pattern:
          metadata:
            annotations:
              meta.helm.sh/release-name: "?*"
              meta.helm.sh/release-namespace: "?*"
```

## Installation

### 1. Install Kyverno
```bash
helm repo add kyverno https://kyverno.github.io/kyverno/
helm repo update

helm install kyverno kyverno/kyverno \
  --namespace kyverno --create-namespace \
  --set installCRDs=true \
  --set replicaCount=2 \
  --set resources.limits.cpu=500m \
  --set resources.limits.memory=512Mi
```

### 2. Apply Policies
```bash
# Apply all policies
kubectl apply -k config/kyverno/policies/

# Or apply individually
kubectl apply -f config/kyverno/policies/pod-security-restricted.yaml
kubectl apply -f config/kyverno/policies/resource-requirements.yaml
kubectl apply -f config/kyverno/policies/image-security.yaml
kubectl apply -f config/kyverno/policies/secret-management.yaml
kubectl apply -f config/kyverno/policies/network-policy.yaml
kubectl apply -f config/kyverno/policies/helm-release.yaml
```

### 3. Verify Policies
```bash
# Check policies
kubectl get clusterpolicies

# Check policy status
kubectl get clusterpolicy pod-security-restricted -o yaml

# Check policy reports
kubectl get policyreports -A
```

### 3. Reporting
```bash
# Generate compliance report
kyverno report generate --format=json > compliance-report.json

# Check violations
kubectl get policyreports -A -o json | jq '.items[] | select(.results[] | .result == "fail")'
```

## Testing Policies

### Dry Run Test
```bash
# Test policy against resource
kubectl apply --dry-run=server -f test-resource.yaml
```

### Policy Testing with Kuttl
```yaml
# test/kuttl-test.yaml
apiVersion: kuttl.dev/v1beta1
kind: TestSuite
testDirs:
  - test/cases
startKubernetes: true
```

## Policy Exceptions

### Namespace Exclusions
```yaml
# config/kyverno/exceptions.yaml
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: policy-exceptions
spec:
  validationFailureAction: Enforce
  background: true
  rules:
    - name: exclude-system-namespaces
      match:
        any:
        - resources:
            kinds:
              - Pod
          namespaces:
            - kube-system
            - kube-public
            - kube-node-lease
            - kyverno
            - argocd
            - cert-manager
            - monitoring
            - logging
            - tracing
```

## Monitoring Policy Violations

### Prometheus Metrics
```promql
# Kyverno policy violations
kyverno_policy_violations_total{policy="pod-security-restricted"}

# Policy evaluation duration
kyverno_policy_evaluation_duration_seconds_bucket{policy="image-security"}

# Policy count
kyverno_policies_total{validation_action="enforce"}
```

### Alert Rules
```yaml
- alert: KyvernoPolicyViolations
  expr: increase(kyverno_policy_violations_total[5m]) > 0
  for: 1m
  labels:
    severity: warning
  annotations:
    summary: "Kyverno policy violations detected"
    description: "{{ $value }} violations in the last 5 minutes"
```

## Gradual Enforcement

### Phased Rollout
1. **Week 1**: Audit mode (`validationFailureAction: Audit`)
2. **Week 2**: Enforce on non-critical namespaces
3. **Week 3**: Enforce on all namespaces
4. **Week 4**: Add to CI/CD pipeline

### Exemption Process
1. Create PolicyException resource
2. Document justification
3. Set expiration date
3. Review monthly