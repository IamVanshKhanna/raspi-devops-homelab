# ADR-007: GPU Scheduling for AI/ML Workloads

## Status
Proposed

## Context
v3.0 introduces AI/ML platform capabilities requiring GPU scheduling on heterogeneous hardware:
- **Jetson Orin 16GB** (ARM64, NVIDIA GPU, 16GB shared memory)
- **Cloud GPU burst** (AWS p3/p4, GCP A100/H100, x86_64)
- **Pi 5** (no GPU, CPU inference only)

Current v2.x cluster uses K3s with standard kube-scheduler. No GPU awareness, no device plugin, no resource management for GPU workloads.

### Requirements
1. **GPU resource advertising** — Nodes report `nvidia.com/gpu` capacity
2. **Workload scheduling** — Pods request `nvidia.com/gpu: 1`, scheduled to GPU nodes
3. **Multi-arch support** — ARM64 (Jetson) + x86_64 (Cloud) GPU nodes
4. **Resource isolation** — GPU memory/containers via NVIDIA Container Toolkit
5. **Cloud burst** — Spot GPU nodes with tolerations/PDBs

---

## Decision
Adopt **NVIDIA GPU Operator** + **k8s-device-plugin** for GPU lifecycle management, with custom scheduling for heterogeneous GPU fleet.

### Components
| Component | Version | Purpose |
|-----------|---------|---------|
| NVIDIA Device Plugin | v0.14+ | Advertise `nvidia.com/gpu` to kube-scheduler |
| NVIDIA GPU Operator | v24.6+ | Driver, toolkit, DCGM, MIG manager |
| k8s-device-plugin (legacy) | v0.14+ | Fallback for simple GPU advertising |
| Custom scheduler (optional) | — | GPU topology-aware scheduling |

### Node Configuration
```yaml
# Jetson Orin (ARM64, integrated GPU)
# Labels: nvidia.com/gpu.present=true, gpu-type=orin, arch=arm64
# Taints: gpu-workload=true:NoSchedule

# Cloud GPU Spot (x86_64, discrete GPU)
# Labels: nvidia.com/gpu.present=true, gpu-type=a100/h100, lifecycle=spot, arch=amd64
# Taints: gpu-workload=true:NoSchedule, dedicated=spot:NoSchedule
```

### Workload Specification
```yaml
# Ollama inference pod
resources:
  limits:
    nvidia.com/gpu: 1
    memory: 16Gi
  requests:
    nvidia.com/gpu: 1
    memory: 8Gi
tolerations:
  - key: "gpu-workload"
    operator: "Equal"
    value: "true"
    effect: "NoSchedule"
  - key: "dedicated"
    operator: "Equal"
    value: "spot"
    effect: "NoSchedule"
nodeSelector:
  nvidia.com/gpu.present: "true"
```

### Cloud Burst Strategy
- **EKS/GKE Spot GPU node groups** with capacity-optimized allocation
- **Cluster Autoscaler** with GPU-aware scale-up
- **PDB** for spot workloads: `maxUnavailable: 50%`
- **NVIDIA GPU Operator** on cloud nodes (driver version pinned)

---

## Consequences

### Positive
- ✅ Native Kubernetes GPU scheduling
- ✅ Heterogeneous GPU fleet (ARM64 + x86_64)
- ✅ Cloud burst for cost optimization
- ✅ Standard NVIDIA tooling (DCGM, MIG)
- ✅ Integrates with existing K3s + ArgoCD

### Negative
- ❌ Added complexity (Operator, drivers, toolkit)
- ❌ ARM64 GPU support less mature than x86_64
- ❌ Cloud GPU spot eviction handling required
- ❌ Driver version pinning across fleet

### Neutral
- ⚠️ MIG not needed (single GPU per node)
- ⚠️ vGPU not required (workload isolation via containers)

---

## Alternatives Considered

| Alternative | Pros | Cons | Decision |
|-------------|------|------|----------|
| **k8s-device-plugin only** | Simple, lightweight | No driver mgmt, no DCGM, no MIG | Rejected |
| **Custom scheduler** | Full control | High maintenance, reinvent wheel | Deferred |
| **KubeRay/Kubeflow** | ML-native | Overkill for inference-first | Deferred to v3.1 |
| **Run:AI / Volcano** | Advanced scheduling | Licensing, complexity | Rejected |

---

## Implementation Plan (v3.0 Sprint 1-2)

1. **Week 1**: Install NVIDIA Device Plugin on Jetson, validate `nvidia.com/gpu` advertised
2. **Week 1**: Deploy NVIDIA GPU Operator on Jetson (driver, toolkit, DCGM)
3. **Week 2**: Add Jetson GPU node to cluster with taints/labels
4. **Week 2**: Deploy Ollama with GPU resource requests
4. **Week 2**: Test inference workload scheduling
5. **Week 3**: Configure EKS Spot GPU node group + GPU Operator
6. **Week 3**: Test cloud burst with spot GPU pod

---

## Validation Criteria

- [ ] `kubectl get nodes -l nvidia.com/gpu.present=true` shows Jetson
- [ ] `kubectl describe node jetson` shows `nvidia.com/gpu: 1` allocatable
- [ ] Ollama pod scheduled to GPU node, `nvidia-smi` works inside container
- [ ] Cloud spot GPU node joins, workloads schedule with tolerations
- [ ] GPU memory isolation verified (2 pods requesting 1 GPU each → only 1 scheduled)

---

## Related ADRs
- ADR-001: Orchestration Platform Selection
- ADR-008: v2.0 Breaking Migration — Docker Compose to K3s

---

## References
- [NVIDIA GPU Operator](https://github.com/NVIDIA/gpu-operator)
- [NVIDIA Device Plugin](https://github.com/NVIDIA/k8s-device-plugin)
- [Kubernetes GPU Scheduling](https://kubernetes.io/docs/tasks/manage-gpus/scheduling-gpus/)
- [Jetson Orin Kubernetes](https://github.com/dusty-nv/jetson-containers)