# Spot/Preemptible Node Integration for Cloud DR

## Overview
This document describes the configuration for using spot/preemptible instances in the cloud DR cluster to reduce costs by up to 90% compared to on-demand pricing.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        SPOT INSTANCE ARCHITECTURE                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  DR CLUSTER (AWS EKS / GCP GKE / Azure AKS)                                 │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  MANAGED NODE GROUP (On-Demand)                                     │   │
│  │  ┌─────────┐  ┌─────────┐  ┌─────────┐                              │   │
│  │  │ System  │  │ System  │  │ System  │  ← Critical: control plane,  │   │
│  │  │ Pods    │  │ Pods    │  │ Pods    │     databases, auth          │   │
│  │  └─────────┘  └─────────┘  └─────────┘                              │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                        │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  SPOT NODE GROUP (Preemptible)                                     │   │
│  │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐              │   │
│  │  │ App     │  │ App     │  │ App     │  │ Batch   │  ← Fault-tolerant│   │
│  │  │ Pods    │  │ Pods    │  │ Pods    │  │ Jobs    │    workloads     │   │
│  │  └─────────┘  └─────────┘  └─────────┘  └─────────┘                │   │
│  │  Labels: lifecycle=spot                                            │   │
│  │  Taints: dedicated=spot:NoSchedule                                 │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  POD DISTRIBUTION:                                                          │
│  ┌─────────────────┐         ┌─────────────────┐                          │
│  │ Critical Pods   │         │ Spot-Tolerant   │                          │
│  │ (preferred      │         │ Pods            │                          │
│  │  on-demand)     │◀───────▶│ (required       │                          │
│  │                 │         │  spot)          │                          │
│  └─────────────────┘         └─────────────────┘                          │
│         │                          │                                       │
│         ▼                          ▼                                       │
│  tolerations: []            tolerations:                                   │
│                              - key: "dedicated"                            │
│                                operator: "Equal"                           │
│                                value: "spot"                               │
│                                effect: "NoSchedule"                        │
│                              nodeSelector:                                 │
│                                lifecycle: "spot"                           │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## AWS EKS Spot Configuration

### 1. Create Spot Node Group
```bash
# Create spot node group with mixed instances policy
eksctl create nodegroup --cluster dr-cloud \
  --name spot-workers \
  --node-type t3.medium \
  --nodes 3 \
  --nodes-min 1 \
  --nodes-max 10 \
  --managed \
  --spot \
  --instance-types t3.medium,t3.large,t2.medium,t2.large \
  --asg-access \
  --labels lifecycle=spot,workload=spot-tolerant \
  --taints dedicated=spot:NoSchedule
```

### 2. Mixed Instances Policy (EKS)
```yaml
# spot-nodegroup.yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: dr-cloud
  region: us-west-2
nodeGroups:
  - name: spot-workers
    instanceType: t3.medium
    desiredCapacity: 3
    minSize: 1
    maxSize: 10
    instancesDistribution:
      instanceTypes:
        - t3.medium
        - t3.large
        - t2.medium
        - t2.large
        - t3a.medium
        - t3a.large
      onDemandBaseCapacity: 0
      onDemandPercentageAboveBaseCapacity: 0
      spotAllocationStrategy: "capacity-optimized"
    labels:
      lifecycle: spot
      workload: spot-tolerant
    taints:
      dedicated: "spot:NoSchedule"
    iam:
      withAddonPolicies:
        autoScaler: true
        cloudWatch: true
        ebs: true
        efs: true
```

### 3. Pod Configuration for Spot
```yaml
# Spot-tolerant pod example (Nextcloud, Vaultwarden, etc.)
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nextcloud
  namespace: apps
spec:
  replicas: 3
  template:
    spec:
      # Schedule on spot nodes
      nodeSelector:
        lifecycle: spot
      # Tolerate spot taint
      tolerations:
      - key: "dedicated"
        operator: "Equal"
        value: "spot"
        effect: "NoSchedule"
      # Prefer spot but allow fallback
      affinity:
        nodeAffinity:
          preferredDuringSchedulingIgnoredDuringExecution:
          - weight: 100
            preference:
              matchExpressions:
              - key: lifecycle
                operator: In
                values:
                - spot
      containers:
      - name: nextcloud
        image: nextcloud:latest
        resources:
          requests:
            cpu: "250m"
            memory: "512Mi"
          limits:
            cpu: "500m"
            memory: "1Gi"
```

### 3. Spot Instance Termination Handler
```yaml
# spot-termination-handler.yaml
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: spot-termination-handler
  namespace: kube-system
spec:
  selector:
    matchLabels:
      app: spot-termination-handler
  template:
    metadata:
      labels:
        app: spot-termination-handler
    spec:
      hostNetwork: true
      containers:
      - name: spot-termination-handler
        image: quay.io/kubernetes-spot-termination-handler:v1.0.0
        env:
        - name: NODE_NAME
          valueFrom:
            fieldRef:
              fieldPath: spec.nodeName
        - name: POD_NAMESPACE
          valueFrom:
            fieldRef:
              fieldPath: metadata.namespace
        resources:
          requests:
            cpu: 10m
            memory: 20Mi
```

## GCP GKE Spot Configuration

### Preemptible Node Pool
```bash
gcloud container node-pools create spot-pool \
  --cluster=dr-cloud \
  --zone=us-central1-a \
  --machine-type=e2-medium \
  --num-nodes=3 \
  --enable-autoscaling --min-nodes=1 --max-nodes=10 \
  --preemptible \
  --node-labels=lifecycle=spot,workload=spot-tolerant \
  --node-taints=dedicated=spot:NoSchedule \
  --scopes=cloud-platform
```

### Spot Pod Configuration (GKE)
```yaml
# GKE uses preemptible node selector
apiVersion: apps/v1
kind: Deployment
metadata:
  name: spot-workload
spec:
  template:
    spec:
      nodeSelector:
        cloud.google.com/gke-preemptible: "true"
      tolerations:
      - key: "cloud.google.com/gke-preemptible"
        operator: "Equal"
        value: "true"
        effect: "NoSchedule"
```

## Azure AKS Spot Configuration

### Spot Node Pool
```bash
az aks nodepool add \
  --resource-group dr-rg \
  --cluster-name dr-cloud \
  --name spotpool \
  --node-count 3 \
  --min-count 1 \
  --max-count 10 \
  --enable-cluster-autoscaler \
  --spot-max-price -1 \
  --eviction-policy Delete \
  --labels lifecycle=spot workload=spot-tolerant \
  --node-taints dedicated=spot:NoSchedule \
  --node-vm-size Standard_B2s \
  --enable-cluster-autoscaler
```

## Workload Classification for Spot

### Spot-Suitable Workloads (Required spot)
```yaml
# These workloads CAN run on spot
spot_suitable_workloads:
  - nextcloud (stateless web)
  - vaultwarden (stateless API)
  - grafana (stateless dashboards)
  - loki (stateless log query)
  - tempo (stateless trace query)
  - prometheus (remote write to TSDB)
  - loki promotes (stateless)
  - batch jobs / cronjobs
  - CI/CD runners
  - development environments
```

### On-Demand Required Workloads (Never spot)
```yaml
# These MUST run on on-demand
on_demand_only_workloads:
  - postgresql (stateful, data loss risk)
  - redis (stateful, persistence risk)
  - authelia (auth critical)
  - infisical (secrets critical)
  - authelia redis (auth sessions)
  - etcd (cluster state)
  - kube-apiserver (control plane)
  - kube-controller-manager
  - kube-scheduler
  - coredns
  - cert-manager (cert renewal)
  - external-dns
  - ingress controllers (traefik)
  - submariner gateway
  - argocd (GitOps controller)
  - velero (backup/restore)
```

## Pod Disruption Budgets for Spot

```yaml
# PDB for spot workloads - allow controlled disruption
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: nextcloud-pdb
  namespace: apps
spec:
  minAvailable: 1  # At least 1 replica available during disruption
  selector:
    matchLabels:
      app.kubernetes.io/name: nextcloud
---
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: spot-workloads-pdb
  namespace: apps
spec:
  maxUnavailable: 50%  # Allow up to 50% of spot pods to be disrupted
  selector:
    matchLabels:
      lifecycle: spot
```

## Spot Termination Graceful Shutdown

```yaml
# PreStop hook for graceful shutdown
apiVersion: apps/v1
kind: Deployment
spec:
  template:
    spec:
      containers:
      - name: app
        lifecycle:
          preStop:
            exec:
              command:
              - /bin/sh
              - -c
              - |
                # Signal application to stop accepting traffic
                kill -SIGTERM 1
                # Wait for connections to drain
                sleep 10
        terminationGracePeriodSeconds: 30
```

## Cost Savings Analysis

| Instance Type | On-Demand Price | Spot Price | Savings |
|---------------|-----------------|------------|---------|
| t3.medium (2 vCPU, 4 GiB) | $0.0416/hr | ~$0.012/hr | **71%** |
| t3.large (2 vCPU, 8 GiB) | $0.0832/hr | ~$0.025/hr | **70%** |
| t3.xlarge (4 vCPU, 16 GiB) | $0.1664/hr | ~$0.05/hr | **70%** |
| e2-medium (2 vCPU, 4 GiB) | $0.0316/hr | ~$0.007/hr | **78%** |

### Monthly Savings Estimate (4 spot nodes)
| Configuration | On-Demand Monthly | Spot Monthly | Annual Savings |
|---------------|-------------------|--------------|----------------|
| 4x t3.medium | ~$120 | ~$35 | **$1,020/year** |
| 6x t3.medium | ~$180 | ~$52 | **$1,536/year** |
| 10x t3.medium | ~$300 | ~$87 | **$2,556/year** |

## Implementation Checklist

- [ ] Create spot node group in DR cluster
- [ ] Label spot nodes: `lifecycle=spot`
- [ ] Taint spot nodes: `dedicated=spot:NoSchedule`
- [ ] Deploy spot termination handler DaemonSet
- [ ] Update spot-suitable deployments with nodeSelector + tolerations
- [ ] Add PDBs for spot workloads
- [ ] Update terminationGracePeriodSeconds to 30s
- [ ] Test spot termination simulation
- [ ] Monitor spot interruption metrics
- [ ] Document runbook for spot interruption handling

## Monitoring Spot Instances

```promql
# Spot instance count
count(kube_node_info{label_lifecycle="spot"})

# Spot interruption rate
rate(spot_termination_notice_total[5m])

# Spot capacity
sum(kube_node_status_capacity_cpu_cores{label_lifecycle="spot"})
```

## Alerting Rules

```yaml
groups:
- name: spot-instances
  rules:
  - alert: SpotInstanceTerminated
    expr: increase(spot_termination_notice_total[5m]) > 0
    for: 0m
    labels:
      severity: warning
    annotations:
      summary: "Spot instance termination detected"
      description: "Spot instance {{ $labels.instance }} received termination notice"
      
  - alert: SpotCapacityLow
    expr: |
      count(kube_node_info{label_lifecycle="spot"}) < 2
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "Less than 2 spot instances available"
      
  - alert: SpotWorkloadPodsPending
    expr: |
      sum(kube_pod_status_phase{phase="Pending", label_lifecycle="spot"}) > 5
    for: 10m
    labels:
      severity: warning
    annotations:
      summary: "More than 5 spot workload pods pending"
```