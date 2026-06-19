# Cluster API (CAPI) Configuration for Homelab Multi-Cluster
# Provides declarative cluster lifecycle management

## Overview
Cluster API (CAPI) enables Kubernetes-style declarative APIs for cluster creation, scaling, and upgrading.
This directory contains configurations for managing multiple homelab clusters.

## Architecture

Management Cluster
  - Cluster API Controllers
  - Kubeadm Bootstrap Provider
  - Infrastructure Provider (Docker/Cloud/Metal3)

Workload Clusters managed by CAPI:
  - Cluster 1 (Pi 4B)
  - Cluster 2 (Pi 5)
  - Cluster N (Cloud/AWS for DR)

## Prerequisites

Management Cluster (Pi 4B - Primary):
- Kubernetes v1.27+
- kubectl access
- Helm 3.10+

Infrastructure Provider Options:
1. Docker (for local/dev clusters)
2. Metal3 (for bare metal Pi clusters)
3. Cloud providers (AWS, GCP, Azure for DR regions)

## Installation

### 1. Install clusterctl
curl -L https://github.com/kubernetes-sigs/cluster-api/releases/download/v1.6.0/clusterctl-linux-amd64 -o clusterctl
chmod +x clusterctl
sudo mv clusterctl /usr/local/bin/
clusterctl version

### 2. Initialize Management Cluster
# Using Docker infrastructure provider (simplest)
clusterctl init --infrastructure docker

# Or with Metal3 for bare metal
clusterctl init --infrastructure metal3 --bootstrap kubeadm --control-plane kubeadm

### 3. Create Workload Cluster
clusterctl generate cluster homelab-workload-1 \
  --infrastructure docker \
  --kubernetes-version v1.28.5 \
  --control-plane-machine-count 1 \
  --worker-machine-count 2 \
  > homelab-workload-1.yaml

kubectl apply -f homelab-workload-1.yaml