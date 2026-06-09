# Multi-Cluster ArgoCD ApplicationSet

## Overview
ArgoCD ApplicationSet enables managing applications across multiple clusters from a single ArgoCD instance.
It uses generators to create Applications dynamically based on cluster labels, Git repositories, or matrices.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        ARGOCD APPLICATIONSET                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                        ARGOCD (Management Cluster)                  │    │
│  │                                                                      │    │
│  │  ┌──────────────────┐    ┌──────────────────┐    ┌──────────────┐  │    │
│  │  │ ApplicationSet   │    │  Cluster         │    │  Application │  │    │
│  │  │ Controller       │───▶│  Generator       │───▶│  Controller  │  │    │
│  │  └──────────────────┘    └──────────────────┘    └──────────────┘  │    │
│  │         │                       │                     │             │    │
│  │         ▼                       ▼                     ▼             │    │
│  │  ┌──────────────────────────────────────────────────────────────┐  │    │
│  │  │                    GENERATED APPLICATIONS                     │  │    │
│  │  │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐           │  │    │
│  │  │  │ Nextcloud │ │ Vaultwarden│ │ Postgres │ │ Redis    │ ...  │  │    │
│  │  │  │  (Pi 4B)  │ │  (Pi 4B) │ │ (Pi 5)  │ │ (Pi 5)  │      │  │    │
│  │  │  └─────────┘ └─────────┘ └─────────┘ └─────────┘           │  │    │
│  │  └──────────────────────────────────────────────────────────────┘  │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│           │                    │                                            │
│           ▼                    ▼                                            │
│  ┌──────────────────┐  ┌──────────────────┐                                │
│  │   Cluster 1      │  │   Cluster 2      │                                │
│  │   (Pi 4B)        │  │   (Pi 5)         │                                │
│  │                  │  │                  │                                │
│  │ ArgoCD Agent     │  │ ArgoCD Agent     │                                │
│  │ (argocd-agent)   │  │ (argocd-agent)   │                                │
│  └──────────────────┘  └──────────────────┘                                │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## ApplicationSet Generators

### 1. Cluster Generator (Deploy to all clusters)
```yaml
apiVersion: argoproj.io/v1alpha1
kind: ApplicationSet
metadata:
  name: cluster-addons
  namespace: argocd
spec:
  generators:
    - clusters:
        selector:
          matchLabels:
            homelab.io/managed-by: argocd
  template:
    metadata:
      name: '{{name}}-{{metadata.labels.homelab\.io/cluster}}'
    spec:
      project: homelab
      source:
        repoURL: https://github.com/IamVanshKhanna/homelab-prod.git
        targetRevision: HEAD
        path: config/argocd/clusters/{{name}}
      destination:
        server: '{{server}}'
        namespace: '{{name}}'
      syncPolicy:
        automated:
          prune: true
          selfHeal: true
```

### 2. Matrix Generator (Service x Cluster combinations)
```yaml
apiVersion: argoproj.io/v1alpha1
kind: ApplicationSet
metadata:
  name: services-matrix
  namespace: argocd
spec:
  generators:
    - matrix:
        generators:
          - clusters:
              selector:
                matchLabels:
                  homelab.io/environment: production
          - git:
              repoURL: https://github.com/IamVanshKhanna/homelab-prod.git
              revision: HEAD
              directories:
                - path: config/argocd/services/*
  template:
    metadata:
      name: '{{path.basename}}-{{name}}'
    spec:
      project: homelab
      source:
        repoURL: https://github.com/IamVanshKhanna/homelab-prod.git
        targetRevision: HEAD
        path: '{{path}}'
      destination:
        server: '{{server}}'
      syncPolicy:
        automated:
          prune: true
          selfHeal: true
```

### 3. Git Generator (Monorepo services)
```yaml
apiVersion: argoproj.io/v1alpha1
kind: ApplicationSet
metadata:
  name: git-services
  namespace: argocd
spec:
  generators:
    - git:
        repoURL: https://github.com/IamVanshKhanna/homelab-prod.git
        revision: HEAD
        directories:
          - path: config/argocd/services/*
  template:
    metadata:
      name: '{{path.basename}}'
    spec:
      project: homelab
      source:
        repoURL: https://github.com/IamVanshKhanna/homelab-prod.git
        targetRevision: HEAD
        path: '{{path}}'
      destination:
        server: https://kubernetes.default.svc
        namespace: '{{path.basename}}'
      syncPolicy:
        automated:
          prune: true
          selfHeal: true
```

## Cluster Registration

### Register Cluster with ArgoCD
```bash
# On management cluster, add workload clusters
argocd cluster add homelab-pi4 --name homelab-pi4 --label homelab.io/cluster=homelab-pi4 --label homelab.io/hardware=pi4 --label homelab.io/region=local

argocd cluster add homelab-pi5 --name homelab-pi5 --label homelab.io/cluster=homelab-pi5 --label homelab.io/hardware=pi5 --label homelab.io/region=local

# List clusters
argocd cluster list
```

### Cluster Secret (Auto-created by `argocd cluster add`)
```yaml
apiVersion: v1
kind: Secret
metadata:
  name: homelab-pi4
  namespace: argocd
  labels:
    argocd.argoproj.io/secret-type: cluster
type: Opaque
stringData:
  name: homelab-pi4
  server: https://192.168.1.50:6443
  config: |
    {"tlsClientConfig":{"insecure":false}}
```

## ApplicationSet Examples

### Core Services (Deploy to appropriate clusters)
```yaml
apiVersion: argoproj.io/v1alpha1
kind: ApplicationSet
metadata:
  name: core-services
  namespace: argocd
spec:
  generators:
    - git:
        repoURL: https://github.com/IamVanshKhanna/homelab-prod.git
        revision: HEAD
        directories:
          - path: config/argocd/services/core/*
  template:
    metadata:
      name: 'core-{{path.basename}}'
      labels:
        homelab.io/tier: core
    spec:
      project: homelab
      source:
        repoURL: https://github.com/IamVanshKhanna/homelab-prod.git
        targetRevision: HEAD
        path: '{{path}}'
      destination:
        server: '{{server}}'
        namespace: '{{path.basename}}'
      syncPolicy:
        automated:
          prune: true
          selfHeal: true
        syncOptions:
          - CreateNamespace=true
          - PruneLast=true
```

### Monitoring Stack (Deploy to monitoring cluster)
```yaml
apiVersion: argoproj.io/v1alpha1
kind: ApplicationSet
metadata:
  name: monitoring-stack
  namespace: argocd
spec:
  generators:
    - clusters:
        selector:
          matchLabels:
            homelab.io/role: monitoring
    - git:
        repoURL: https://github.com/IamVanshKhanna/homelab-prod.git
        revision: HEAD
        directories:
          - path: config/argocd/services/monitoring/*
  template:
    metadata:
      name: 'monitoring-{{path.basename}}-{{name}}'
    spec:
      project: homelab
      source:
        repoURL: https://github.com/IamVanshKhanna/homelab-prod.git
        targetRevision: HEAD
        path: '{{path}}'
      destination:
        server: '{{server}}'
        namespace: '{{path.basename}}'
      syncPolicy:
        automated:
          prune: true
          selfHeal: true
```

### Database Services (Deploy to database cluster)
```yaml
apiVersion: argoproj.io/v1alpha1
kind: ApplicationSet
metadata:
  name: database-services
  namespace: argocd
spec:
  generators:
    - matrix:
        generators:
          - clusters:
              selector:
                matchLabels:
                  homelab.io/role: database
          - git:
              repoURL: https://github.com/IamVanshKhanna/homelab-prod.git
              revision: HEAD
              directories:
                - path: config/argocd/services/database/*
  template:
    metadata:
      name: 'database-{{path.basename}}-{{name}}'
    spec:
      project: homelab
      source:
        repoURL: https://github.com/IamVanshKhanna/homelab-prod.git
        targetRevision: HEAD
        path: '{{path}}'
      destination:
        server: '{{server}}'
        namespace: databases
      syncPolicy:
        automated:
          prune: true
          selfHeal: true
```

## ArgoCD Agent (For managed clusters)

### Install Agent on Workload Clusters
```bash
# Install argocd-agent on each workload cluster
helm repo add argocd https://argoproj.github.io/argo-helm
helm install argocd-agent argocd/argocd-agent \
  --namespace argocd-agent --create-namespace \
  --set mode=agent \
  --set principal.address=argocd-server.argocd:8080 \
  --set principal.tls.secret=argocd-agent-tls
```

### Agent Registration
```yaml
# Agent registration (auto-created)
apiVersion: argoproj.io/v1alpha1
kind: Agent
metadata:
  name: homelab-pi4-agent
  namespace: argocd
spec:
  mode: agent
  principal:
    address: argocd-server.argocd:8080
```

## Sync Windows and Waves

### Sync Windows (Maintenance Windows)
```yaml
apiVersion: argoproj.io/v1alpha1
kind: ApplicationSet
metadata:
  name: production-services
  namespace: argocd
spec:
  generators:
    - git:
        repoURL: https://github.com/IamVanshKhanna/homelab-prod.git
        revision: HEAD
        directories:
          - path: config/argocd/services/production/*
  template:
    metadata:
      name: 'prod-{{path.basename}}'
      annotations:
        argocd.argoproj.io/sync-wave: "10"
    spec:
      project: homelab
      syncPolicy:
        automated:
          prune: true
          selfHeal: true
          allowEmpty: false
        syncOptions:
          - CreateNamespace=true
          - PruneLast=true
        retry:
          limit: 5
          backoff:
            duration: 5s
            factor: 2
            maxDuration: 3m
      syncWindows:
        - kind: schedule
          schedule: '0 2 * * 0'  # Weekly Sunday 2 AM
          duration: 4h
          namespaces:
            - '*'
```

### Sync Waves (Dependency Ordering)
```yaml
# In each Application, use sync-wave annotation
metadata:
  annotations:
    argocd.argoproj.io/sync-wave: "10"  # Databases first
---
metadata:
  annotations:
    argocd.argoproj.io/sync-wave: "20"  # Then Redis
---
metadata:
  annotations:
    argocd.argoproj.io/sync-wave: "30"  # Then Apps
---
metadata:
  annotations:
    argocd.argoproj.io/sync-wave: "40"  # Then Ingress
```

## Multi-Cluster Project Structure

```
config/argocd/
├── applicationsets/
│   ├── cluster-addons.yaml
│   ├── core-services.yaml
│   ├── monitoring-stack.yaml
│   ├── database-services.yaml
│   ├── production-services.yaml
│   └── services-matrix.yaml
├── clusters/
│   ├── homelab-pi4/
│   │   ├── argocd-agent.yaml
│   │   └── cluster-secret.yaml
│   ├── homelab-pi5/
│   │   ├── argocd-agent.yaml
│   │   └── cluster-secret.yaml
│   └── dr-cloud/
│       ├── argocd-agent.yaml
│       └── cluster-secret.yaml
├── projects/
│   └── homelab-project.yaml
└── services/
    ├── core/
    │   ├── traefik/
    │   ├── cert-manager/
    │   └── external-dns/
    ├── monitoring/
    │   ├── prometheus/
    │   ├── grafana/
    │   ├── loki/
    │   └── tempo/
    ├── database/
    │   ├── postgres/
    │   └── redis/
    ├── apps/
    │   ├── nextcloud/
    │   ├── vaultwarden/
    │   └── homeassistant/
    └── security/
        ├── authelia/
        ├── kyverno/
        └── kyverno-policies/
```