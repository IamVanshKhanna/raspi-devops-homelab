# Migration Guide: v2.x → v3.0

> **Status:** Draft for v2.12 release
> **Target:** v3.0 AI/ML Platform (2028-Q2)
> **Breaking Changes:** Yes - architectural shift from K3s GitOps to AI/ML platform

---

## Overview

This guide documents the migration from **homelab-prod v2.x** (K3s + GitOps + Observability) to **v3.0** (AI/ML Platform + Edge/OT + Developer Platform).

| Aspect | v2.x | v3.0 |
|--------|------|------|
| **Core Platform** | K3s single/multi-node | K3s + GPU workers (Jetson Orin) + Cloud burst |
| **Workloads** | Apps, monitoring, smart home | + LLM inference, RAG, fine-tuning, MLOps |
| **Infrastructure** | Pi 4B, EKS Spot DR | Pi 5, Jetson Orin, Cloud GPU (AWS/GCP) |
| **Data Layer** | PostgreSQL, Redis, Longhorn | + Qdrant/Milvus vector DB, MLflow |
| **GitOps** | ArgoCD ApplicationSet | ArgoCD + Flux (multi-cluster) |
| **Observability** | Prometheus/Grafana/Loki/Tempo | + MLflow tracking, model monitoring |
| **Security** | Kyverno, CrowdSec, mTLS | + Model signing, data lineage |

---

## Breaking Changes

### 1. Hardware Requirements
| v2.x | v3.0 | Migration |
|------|------|-----------|
| Pi 4B 4GB (control) | Pi 5 8GB + Jetson Orin 16GB | Add GPU node, migrate control plane |
| 2TB SSD | 2TB SSD + NVMe for models | Add NVMe storage class |
| No GPU | NVIDIA GPU (Jetson) + Cloud GPU | Install NVIDIA device plugin |

### 2. Kubernetes Additions
```yaml
# New required components (v3.0)
- NVIDIA Device Plugin (GPU scheduling)
- NVIDIA GPU Operator (driver management)
- KubeRay / Kubeflow (optional, for distributed training)
- Qdrant / Milvus Operator (vector DB)
- MLflow Tracking Server
- Model Registry (Harbor + Cosign or dedicated)
```

### 3. Storage Changes
| v2.x | v3.0 |
|------|------|
| Longhorn (RWX) | Longhorn + NVMe LocalPV for models |
| PostgreSQL/Redis | + Qdrant (vector), MLflow artifact store (S3) |

### 4. Networking
- New: GPU node taints/tolerations
- New: Cloud burst node groups (EKS/GKE)
- New: Model serving ingress (dedicated domain)

### 5. Security
- Model signing (Cosign + Sigstore)
- Data lineage tracking
- Model access control (RBAC per model)

---

## Migration Steps

### Phase 0: Pre-requisites (v2.12 completion)
- [ ] v2.12.0 tagged and stable
- [ ] Jetson Orin 16GB procured
- [ ] Cloud GPU credits approved ($5k-10k)
- [ ] Qdrant vs Milvus POC completed
- [ ] Ollama multi-node POC completed

### Phase 1: Infrastructure (Week 1-2)
```bash
# 1. Add GPU node to cluster
./scripts/k3s-cluster-setup.sh --gpu-node jetson-01

# 2. Install NVIDIA Device Plugin
kubectl apply -f https://raw.githubusercontent.com/NVIDIA/k8s-device-plugin/v0.14.0/nvidia-device-plugin.yml

# 3. Add NVMe LocalPV StorageClass
kubectl apply -f config/storage/nvme-localpv.yaml

# 4. Install Qdrant Operator
helm repo add qdrant https://qdrant.github.io/qdrant-helm
helm install qdrant qdrant/qdrant -n vector-db --create-namespace
```

### Phase 2: AI/ML Platform (Week 3-6)
```bash
# 1. Deploy Ollama Cluster (multi-node GPU)
helm install ollama-cluster ./charts/ollama-cluster -n ai

# 2. Deploy MLflow
helm install mlflow ./charts/mlflow -n mlops --create-namespace

# 3. Deploy Model Registry (Harbor extension)
helm install model-registry ./charts/model-registry -n mlops

# 4. Deploy RAG Pipeline (Qdrant + BGE-M3 + Retriever)
helm install rag-pipeline ./charts/rag-pipeline -n ai
```

### Phase 3: Migration & Validation (Week 7-8)
```bash
# 1. Migrate v2 workloads (no changes needed)
# ArgoCD apps continue to work

# 2. Validate GPU scheduling
kubectl get nodes -l nvidia.com/gpu.present=true

# 3. Run inference smoke test
curl -X POST http://ollama.ai.homelab.local/api/generate -d '{"model":"llama3","prompt":"test"}'

# 4. Validate RAG pipeline
# Ingest test docs, query via API
```

### Phase 4: Cutover (Week 8)
- [ ] All v2 workloads healthy on v3 cluster
- [ ] AI/ML platform functional
- [ ] DR test passed (v3 config)
- [ ] Update DNS/TLS for new endpoints
- [ ] Tag v3.0.0

---

## Rollback Plan

If critical issues:

```bash
# 1. Drain GPU node
kubectl drain jetson-01 --ignore-daemonsets --delete-emptydir-data

# 2. Remove GPU workloads
kubectl delete ns ai mlops vector-db

# 3. Revert to v2.12 cluster state
git checkout main-v2
./scripts/deploy-v2.sh

# 4. Verify v2.12 functionality
make verify-v1
```

---

## v2.x Maintenance During Migration

| Version | Support | End-of-Life |
|---------|---------|-------------|
| v2.12 | Full | 6 months after v3.0 release |
| v2.11 | Security only | v3.0 release |
| v2.10 | Security only | v3.0 release |
| v1.7 | Maintenance | 12 months after v3.0 release |

---

## References

- [v3.0 Architecture](docs/v3-planning.md)
- [Qdrant vs Milvus POC Results](../poc/qdrant-vs-milvus.md)
- [Ollama Cluster Design](../poc/ollama-cluster-design.md)
- [Cloud GPU Cost Analysis](../poc/cloud-gpu-costs.md)
- [Model Signing Procedure](docs/runbooks/model-signing.md)