# v3.0 AI/ML Platform — Migration Plan & Architecture

> **Status**: Planning Phase | **Target**: 6+ months | **Prerequisites**: v2.11 documentation complete, GPU hardware procurement

---

## Executive Summary

v3.0 transforms homelab-prod into a **production-grade AI/ML platform** with multi-node GPU inference, RAG pipelines, fine-tuning capabilities, and OpenAI-compatible inference APIs. Built on the v2.x multi-cluster foundation (CAPI, Submariner, ArgoCD, Thanos, Loki, Tempo, Linkerd, Kyverno, cost optimization).

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           v3.0 AI/ML Platform Architecture                       │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  ┌────────────────────────────────────────────────────────────────────────────┐ │
│  │                        MANAGEMENT CLUSTER                                    │ │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────────────────┐ │ │
│  │  │   ArgoCD    │  │   CAPI      │  │     Thanos Query / Loki / Tempo       │
│  │  │ ApplicationSet│  │ Metal3/Docker│  │     (Federated Observability)       │
│  │  └─────────────┘  └─────────────┘  └─────────────────────────────────────┘ │ │
│  └────────────────┬──────────────────────┬──────────────────────────────────┘ │
│                   │                      │                                      │
│        ┌──────────┴──────────┐ ┌────────┴──────────┐                         │
        ▼                      ▼        ▼                                  │
┌───────────────┐      ┌───────────────┐  ┌───────────────┐                 │
│  Primary Site │      │  Cloud DR     │  │  AI/ML Cloud  │                 │
│  (Pi 4B/5)    │      │  (EKS/GKE)    │  │  (GPU Burst)  │                 │
│               │      │               │  │               │                 │
│ ┌───────────┐ │      │ ┌───────────┐ │  │ ┌───────────┐ │                 │
│ │ Ollama    │ │      │ │ Ollama    │ │  │ │ vLLM/TGI  │ │                 │
│ │ (CPU)     │ │      │ │ (CPU)     │ │  │ │ (GPU)     │ │                 │
│ └───────────┘ │      │ └───────────┘ │  │ └───────────┘ │                 │
│ ┌───────────┐ │      │ ┌───────────┐ │  │ ┌───────────┐ │                 │
│ │ Qdrant    │ │      │ │ Qdrant    │ │  │ │ Qdrant    │ │                 │
│ │ (Vector)  │ │      │ │ (Vector)  │ │  │ │ (Vector)  │ │                 │
│ └───────────┘ │      │ └───────────┘ │  │ └───────────┘ │                 │
└───────────────┘      └───────────────┘  └───────────────┘                 │
                                                                   ▼        │
                                                    ┌──────────────────────┐ │
                                                    │   Submariner +       │ │
                                                    │   Lighthouse         │ │
                                                    │   (Cross-cluster)    │ │
                                                    └──────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Milestone Breakdown

### M1: Ollama Multi-Node GPU Cluster (Months 1-2)

#### Objectives
- Deploy 3+ node Ollama cluster with GPU offload (Pi 5 + Jetson Orin / Cloud GPU)
- Model registry with versioning, metadata, health checks
- Auto-scaling based on queue depth / GPU utilization
- Health checks, model pre-pulling, rolling updates

#### Architecture
```
┌─────────────────────────────────────────────────────────────┐
│                   Ollama Cluster (3+ nodes)                  │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐   │
│  │ Node 1       │    │ Node 2       │    │ Node 3       │   │
│  │ (Pi 5 +      │    │ (Jetson      │    │ (Cloud GPU   │   │
│  │  VideoCore)  │    │  Orin 16GB)  │    │  A10G/T4)    │   │
│  │              │    │              │    │              │   │
│  │ ollama serve │    │ ollama serve │    │ vLLM serve   │   │
│  │ :11434       │    │ :11434       │    │ :8000        │   │
│  └──────┬───────┘    └──────┬───────┘    └──────┬───────┘   │
│         │                   │                   │            │
│         └───────────────────┼───────────────────┘            │
│                             ▼                                │
│                    ┌──────────────────┐                      │
│                    │  Model Registry  │                      │
│                    │  (ConfigMap +    │                      │
│                    │   PVC storage)   │                      │
│                    │  Versions +      │                      │
│                    │  Health + Metrics│                      │
│                    └──────────────────┘                      │
└─────────────────────────────────────────────────────────────┘
```

#### Components
| Component | Technology | Configuration |
|-----------|------------|---------------|
| **Inference** | vLLM (GPU) / Ollama (CPU) | vLLM for GPU nodes, Ollama for CPU |
| **Model Registry** | ConfigMap + PVC | Versioned, metadata, health |
| **Load Balancing** | Traefik + Submariner | Round-robin, session affinity |
| **Auto-scaling** | KEDA + Prometheus | GPU util > 70% → scale up |
| **Health** | `/health` + model ready | Liveness/readiness probes |

#### Deliverables
- [ ] 3+ node Ollama cluster (Pi 5 + Jetson + Cloud GPU)
- [ ] Model registry with versioning, metadata, health
- [ ] Auto-scaling based on GPU util / queue depth
- [ ] Rolling updates with zero-downtime
- [ ] Health checks + model pre-pulling
- [ ] ArgoCD ApplicationSet for multi-cluster deploy

---

### M2: RAG Pipeline (Months 2-3)

#### Objectives
- Vector database (Qdrant) with multi-tenancy
- Embedding service (BGE-M3, local, multi-lingual)
- Retrieval API with hybrid search (vector + keyword)
- Reranking (cross-encoder) for quality
- Document ingestion pipeline (PDF, MD, HTML, code)

#### Architecture
```
┌─────────────────────────────────────────────────────────────┐
│                      RAG Pipeline                            │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐   │
│  │  Ingestion   │    │  Embedding   │    │   Vector DB  │   │
│  │  Service     │───▶│  Service     │───▶│   (Qdrant)   │   │
│  │  (PDF/MD/    │    │  (BGE-M3,    │    │  (Multi-     │   │
│  │  HTML, Code) │    │  local GPU)  │    │   tenant)    │   │
│  └──────────────┘    └──────────────┘    └──────┬───────┘   │
│                                                  │          │
│                    ┌─────────────────────────────┘          │
                    ▼                                          │
         ┌─────────────────────────────────────────────────┐   │
         │              Retrieval API                       │   │
         │  ┌────────────┐  ┌────────────┐  ┌───────────┐  │   │
         │  │   Vector   │  │  Keyword   │  │  Hybrid   │  │   │
         │  │  Search    │  │  Search    │  │  (RRF)    │  │   │
         │  └────────────┘  └────────────┘  └───────────┘  │   │
         │                    │                             │   │
         │                    ▼                             │   │
         │         ┌──────────────────┐                     │   │
         │         │  Reranker        │                     │   │
         │         │  (Cross-encoder) │                     │   │
         │         └──────────────────┘                     │   │
         │                    │                             │   │
         └────────────────────┼─────────────────────────────┘   │
                              ▼
                    ┌──────────────────┐
                    │  LLM Generator   │
                    │  (Ollama/vLLM)   │
                    └──────────────────┘
```

#### Components
| Component | Technology | Configuration |
|-----------|------------|---------------|
| **Vector DB** | Qdrant | Multi-tenant, HNSW, persistent |
| **Embeddings** | BGE-M3 (1024-dim) | GPU batch, 512 token chunks |
| **Retrieval** | Hybrid (vector + BM25) | RRF fusion, top-k=20 |
| **Reranker** | Cross-encoder (bge-reranker-v2) | Top-20 → top-5 |
| **Generation** | Ollama / vLLM | Streaming, citation support |
| **Ingestion** | Apache Tika + custom | PDF, MD, HTML, code |

#### Deliverables
- [ ] Qdrant cluster with multi-tenancy
- [ ] Embedding service (BGE-M3, GPU batch)
- [ ] Retrieval API (hybrid search + reranking)
- [ ] Document ingestion pipeline (PDF, MD, HTML, code)
- [ ] RAG API with streaming, citations, metrics
- [ ] Evaluation framework (RAGAS, custom)

---

### M3: Fine-Tuning Pipeline (Months 3-4)

#### Objectives
- LoRA/QLoRA fine-tuning pipeline
- Dataset versioning & preprocessing
- Model registry with versioning, evaluation
- Training job orchestration (Kueue + KubeRay/TorchRun)

#### Architecture
```
┌─────────────────────────────────────────────────────────────┐
│                   Fine-Tuning Pipeline                       │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐   │
│  │   Dataset    │    │  Training    │    │   Model      │   │
│  │  Registry    │───▶│  Job (LoRA)  │───▶│  Registry    │   │
│  │  (DVC +      │    │  (Kueue +    │    │  (Versioned, │   │
│  │  Git LFS)    │    │  KubeRay)    │    │  Evaluated)  │   │
│  └──────────────┘    └──────────────┘    └──────┬───────┘   │
│                                                   │         │
│                    ┌─────────────────────────────┘         │
                    ▼                                          │
         ┌─────────────────────────────────────────────────┐   │
         │              Evaluation Pipeline                 │   │
         │  ┌────────────┐  ┌────────────┐  ┌───────────┐  │   │
         │  │  Perplexity│  │  Benchmark │  │  Human    │  │   │
         │  │  / Loss    │  │  (MMLU,    │  │  Eval     │  │   │
         │  │            │  │  GSM8K)    │  │           │  │   │
         │  └────────────┘  └────────────┘  └───────────┘  │   │
         └─────────────────────────────────────────────────┘   │
```

#### Components
| Component | Technology | Configuration |
|-----------|------------|---------------|
| **Dataset Registry** | DVC + Git LFS | Versioned, deduplicated |
| **Training** | LoRA/QLoRA (4-bit) | Kueue + KubeRay, 4-bit quantization |
| **Model Registry** | MLflow + PVC | Versioned, evaluated, promoted |
| **Evaluation** | Perplexity, MMLU, GSM8K | Automated + human review |
| **Orchestration** | Kueue + KubeRay | Queue-based, priority, preemption |

#### Deliverables
- [ ] Dataset registry with versioning (DVC + Git LFS)
- [ ] LoRA/QLoRA training jobs (4-bit, Kueue + KubeRay)
- [ ] Model registry (MLflow + PVC) with versioning, evaluation
- [ ] Evaluation pipeline (perplexity, MMLU, GSM8K, human)
- [ ] Promotion pipeline (dev → staging → prod)

---

### M4: Inference API (Months 4-5)

#### Objectives
- OpenAI-compatible API (`/v1/chat/completions`, `/v1/embeddings`)
- Streaming responses, function calling, structured output
- Rate limiting, authentication, caching, metrics
- Model routing (small/large), fallback chains

#### Architecture
```
┌─────────────────────────────────────────────────────────────┐
│                    Inference API Gateway                      │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │              API Gateway (Traefik/Envoy)              │   │
│  │  Auth (Authelia OIDC) │ Rate Limit │ Request Router  │   │
│  └─────────────────────┬─────────────────────────────────┘   │
│                        │                                      │
│         ┌──────────────┼──────────────┐                      │
│         ▼              ▼              ▼                       │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐             │
│  │  Small     │  │  Medium    │  │  Large     │             │
│  │  (Ollama   │  │  (vLLM     │  │  (vLLM     │             │
│  │  CPU)      │  │  GPU)      │  │  GPU)      │             │
│  │  gemma:2b  │  │  llama3:8b │  │  mixtral   │             │
│  └────────────┘  └────────────┘  └────────────┘             │
```

#### API Endpoints
| Endpoint | Description | Features |
|----------|-------------|----------|
| `POST /v1/chat/completions` | Chat completion | Streaming, functions, structured output |
| `POST /v1/completions` | Text completion | Legacy support |
| `POST /v1/embeddings` | Embeddings | Batch, truncate, dimensions |
| `GET /v1/models` | List models | Capabilities, metadata |
| `GET /health` | Health check | Readiness, liveness |

#### Features
| Feature | Implementation |
|---------|----------------|
| **Auth** | Authelia OIDC, API keys, JWT |
| **Rate Limiting** | Token bucket (per key, per model) |
| **Caching** | Redis (exact + semantic) |
| **Streaming** | SSE, chunked encoding |
| **Functions** | OpenAI function calling schema |
| **Structured Output** | JSON schema, guided decoding |
| **Model Routing** | Size-based, capability-based |
| **Fallback** | Auto-failover to larger model |
| **Metrics** | Prometheus (latency, tokens, errors) |

#### Deliverables
- [ ] OpenAI-compatible API (`/v1/*`)
- [ ] Streaming, functions, structured output
- [ ] Rate limiting, auth, caching
- [ ] Model routing + fallback chains
- [ ] Metrics (latency, tokens, errors, cost)
- [ ] Load testing (k6, 1000+ concurrent)

---

### M5: MLOps Platform (Months 5-6)

#### Objectives
- MLflow for experiment tracking
- Model lineage & versioning
- CI/CD for models (training → eval → deploy)
- Automated retraining triggers
- Experiment comparison & visualization

#### Architecture
```
┌─────────────────────────────────────────────────────────────┐
│                      MLOps Platform                          │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐     │
│  │   MLflow    │    │   Model     │    │   ArgoCD    │     │
│  │  Tracking   │───▶│  Registry   │───▶│  (Deploy)   │     │
│  │  (Experi-   │    │  (MLflow +  │    │  (AppSet)   │     │
│  │  ments)     │    │   PVC)      │    │             │     │
│  └─────────────┘    └─────────────┘    └─────────────┘     │
│         │                 │                   │             │
│         ▼                 ▼                   ▼             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │  Automated  │  │   Drift     │  │  Automated  │         │
│  │  Retraining │  │  Detection  │  │  Rollback   │         │
│  │  (Schedule/ │  │  (Data/     │  │  (Canary)   │         │
│  │  Trigger)   │  │  Concept)   │  │             │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
```

#### Components
| Component | Technology | Features |
|-----------|------------|----------|
| **Experiment Tracking** | MLflow | Params, metrics, artifacts, tags |
| **Model Registry** | MLflow + PVC | Staging/Prod, aliases, lineage |
| **CI/CD** | ArgoCD AppSet | Build → test → eval → deploy |
| **Drift Detection** | Evidently / custom | Data/concept drift, alerts |
| **Auto-Retraining** | Cron + trigger | Schedule / data change / perf drop |
| **Auto-Rollback** | ArgoCD + metrics | Canary, auto-rollback on SLO breach |

#### Deliverables
- [ ] MLflow tracking server + model registry
- [ ] Model CI/CD pipeline (train → eval → deploy)
- [ ] Automated retraining triggers
- [ ] Drift detection (data/concept) + alerts
- [ ] Canary deployments + auto-rollback
- [ ] Experiment comparison dashboard (Grafana)

---

## Hardware Requirements

### On-Prem (Current)
| Node | Spec | Role |
|------|------|------|
| Pi 4B 8GB | 4C/8GB, NVMe | Control plane, CPU inference |
| Pi 5 8GB ×2 | 4C/8GB, NVMe, PCIe | Worker, GPU offload (VideoCore) |

### Cloud DR (Current)
| Component | Spec | Purpose |
|-----------|------|---------|
| EKS Spot | t3.medium ×3-10 | DR workloads (70% savings) |

### AI/ML Cloud Burst (New for v3.0)
| Instance | Spec | Qty | Est. Cost/mo | Use Case |
|----------|------|-----|--------------|----------|
| **g5.xlarge** | 4 vCPU, 16GB, 1×A10G | 2 | ~$500 | LLM inference (vLLM) |
| **g5.2xlarge** | 8 vCPU, 32GB, 1×A10G | 1 | ~$1000 | Fine-tuning (LoRA) |
| **p4d.24xlarge** | 96 vCPU, 8×A100 | 1 (spot) | ~$3000 | Large fine-tuning |
| **Qdrant Cloud** | Managed | 1 | ~$200 | Vector DB (prod) |

**Estimated Monthly (Steady State)**: ~$700-1500 depending on usage

---

## Data Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      Data Architecture                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │   Raw Data   │───▶│  Processed   │───▶│  Vector DB   │          │
│  │  (S3/MinIO)  │    │  (Chunked)   │    │  (Qdrant)    │          │
│  └──────────────┘    └──────────────┘    └──────────────┘          │
│           │                   │                   │                │
│           ▼                   ▼                   ▼                │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐        │
│  │  DVC +       │    │  Embedding   │    │  Qdrant      │        │
│  │  Git LFS     │    │  (BGE-M3)    │    │  (HNSW,      │        │
│  │  (Versioned) │    │  (GPU)       │    │   Multi-tenant)       │
│  └──────────────┘    └──────────────┘    └──────────────┘        │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                    MLflow + MLflow Model Registry          │   │
│  │  Experiments │ Models │ Versions │ Lineage │ Artifacts    │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │  DVC +       │  │  Training    │  │  Prometheus  │         │
│  │  Git LFS     │    │  (Kueue +  │  │  + Grafana   │         │
│  │  (Datasets)  │    │   KubeRay) │  │  (Metrics)   │         │
│  └──────────────┘    └──────────────┘    └──────────────┘      │
└─────────────────────────────────────────────────────────────────┘
```

---

## Security & Compliance (v3.0)

| Control | Implementation |
|---------|----------------|
| **Model Access** | Authelia OIDC + API keys, per-model RBAC |
| **Data Privacy** | Local embeddings, no external API calls |
| **Model Integrity** | Cosign signing, SBOM, signature verification |
| **Audit Trail** | MLflow + Audit log (who trained/deployed what) |
| **Model Scanning** | Trivy + custom (pickle safety, license check) |
| **Data Isolation** | Qdrant multi-tenancy, network policies |

---

## Rollout Strategy

| Phase | Scope | Validation | Rollback |
|-------|-------|------------|----------|
| **Canary (10%)** | Internal traffic | Automated health + metrics | Auto-rollback on error rate > 1% |
| **Staging (50%)** | Internal + beta users | Synthetic + real traffic | Manual approval |
| **Production (100%)** | All traffic | Full metric suite | Instant rollback |

---

## Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| GPU cloud cost overrun | Medium | High | Budget alerts, spot instances, auto-shutdown |
| Model hallucination | High | High | RAG grounding, citations, eval pipeline |
| Data privacy leakage | Low | Critical | Local embeddings, no external APIs |
| GPU driver/kernel issues | Medium | High | Tested AMIs, node taints, PDBs |
| Model drift undetected | Medium | High | Automated drift detection + retraining |
| Cost overrun | Medium | High | Budget alerts, quotas, auto-shutdown |

---

## Success Metrics (v3.0 GA)

| Metric | Target |
|--------|--------|
| **Inference Latency (p95)** | <500ms (streaming first token <200ms) |
| **Throughput** | >50 tok/s (GPU), >15 tok/s (CPU) |
| **Availability** | 99.9% (inference API) |
| **RAG Accuracy** | >85% (custom eval set) |
| **Fine-tune Time** | <4h (LoRA, 7B, 1 GPU) |
| **Cost/1M tokens** | <$0.50 (self-hosted) |
| **Power Efficiency** | <20W avg (Pi cluster) |

---

## Dependencies (v3.0 Prerequisites)

| Dependency | Status | Notes |
|------------|--------|-------|
| **v2.11 Docs Complete** | Pending | Blocking |
| **Jetson Orin 16GB ×1** | Planned | GPU worker |
| **Cloud GPU Credits** | Pending | AWS/GCP credits application |
| **Qdrant License** | Evaluating | Cloud vs self-hosted |
| **vLLM Compatibility** | Tested | ARM64 support (Pi) vs x86_64 (cloud) |
| **Team Capacity** | TBC | 1-2 engineers for 6 months |

---

## Decision Log (v3.0)

| Date | Decision | Rationale |
|------|----------|-----------|
| 2024-06 | Qdrant over Milvus/Weaviate | Rust, fast, single-binary, multi-tenant |
| 2024-06 | BGE-M3 embeddings | Multi-lingual, 1024-dim, strong retrieval |
| 2024-06 | vLLM for GPU inference | PagedAttention, continuous batching |
| 2024-06 | LoRA/QLoRA (4-bit) | Memory efficient, fast training |
| 2024-06 | MLflow + ArgoCD for MLOps | Native K8s, GitOps native |

---

## Next Steps

1. **Complete v2.11 documentation** (this document set)
2. **Procure Jetson Orin 16GB** (GPU worker)
3. **Apply for AWS/GCP credits** ($5k-10k for 6 months)
4. **POC: Qdrant vs Milvus** (2 weeks)
5. **POC: Ollama Cluster on Pi 5 + Jetson** (2 weeks)
6. **v3.0 Kickoff Sprint Planning** (sprint 1: Ollama cluster)

---

*Document Version: 1.0*  
*Last Updated: 2024-06-09*  
*Owner: Platform Team*