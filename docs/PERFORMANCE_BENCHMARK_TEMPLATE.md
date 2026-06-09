# Performance Benchmark Report Template

> Template for documenting performance benchmarks
> Run quarterly or after major changes

---

## Test Metadata

| Field | Value |
|-------|-------|
| **Test Date** | YYYY-MM-DD |
| **Test ID** | PERF-YYYYMMDD-XXX |
| **Tester** | Name/Handle |
| **Environment** | Production / Staging |
| **Hardware** | Pi 4B 4GB / Pi 5 8GB / K3s Cluster |
| **Software** | homelab-prod vX.Y.Z |
| **Kubernetes** | v1.XX.X / Docker Compose vX.Y.Z |

---

## Test Environment

### Hardware
| Node | CPU | RAM | Storage | Network |
|------|-----|-----|---------|---------|
| Node-1 | Pi 4B 4C | 8GB | 2TB SSD | 1Gbps |
| Node-2 | Pi 4B 4C | 8GB | 2TB SSD | 1Gbps |

### Software Versions
| Component | Version |
|-----------|---------|
| Kubernetes | v1.28.x |
| Traefik | v3.0.x |
| Prometheus | v2.54.x |
| Grafana | v11.1.x |
| Loki | v2.9.x |
| Tempo | v2.4.x |
| Ollama | v0.3.x |

---

## Benchmark Categories

### 1. API Latency Benchmarks

| Endpoint | Method | Target p50 | Target p95 | Target p99 | Actual p50 | Actual p95 | Actual p99 | Pass/Fail |
|----------|--------|------------|------------|------------|------------|------------|------------|-----------|
| Traefik /health | GET | <10ms | <50ms | <100ms | | | | |
| Nextcloud /status.php | GET | <100ms | <500ms | <1s | | | | |
| Vaultwarden /alive | GET | <50ms | <200ms | <500ms | | | | |
| Grafana /api/health | GET | <50ms | <200ms | <500ms | | | | |
| Prometheus /-/ready | GET | <20ms | <100ms | <200ms | | | | |
| Ollama /api/tags | GET | <200ms | <1s | <2s | | | | |
| Home Assistant /api/ | GET | <100ms | <500ms | <1s | | | | |
| Authelia /api/healthz | GET | <50ms | <200ms | <500ms | | | | |

### 2. Ollama Inference Benchmarks

| Model | Prompt Tokens | Max Tokens | Target Tokens/s | Actual Tokens/s | GPU Used | Pass/Fail |
|-------|--------------|------------|-----------------|-----------------|----------|-----------|
| gemma:2b | 100 | 200 | >15 | | | |
| llama3:8b | 100 | 200 | >10 | | | |
| codellama:7b | 200 | 500 | >8 | | | |
| mixtral:8x7b | 200 | 500 | >5 | | | |

**Test Prompt**: "Explain quantum computing in simple terms"

### 3. Database Performance

| Operation | Target | Actual | Pass/Fail |
|-----------|--------|--------|-----------|
| Nextcloud: SELECT 1000 files | <500ms | | |
| Nextcloud: INSERT 100 files | <2s | | |
| Vaultwarden: GET 100 items | <200ms | | |
| Nextcloud DB: Connection pool | <10ms | | |
| Redis: SET/GET 1000 ops | <50ms | | |

### 4. Storage I/O

| Operation | Target | Actual | Pass/Fail |
|-----------|--------|--------|-----------|
| Sequential Read (SSD) | >400 MB/s | | |
| Sequential Write (SSD) | >300 MB/s | | |
| Random Read 4K (SSD) | >50 MB/s | | |
| Random Write 4K (SSD) | >40 MB/s | | |
| Longhorn Replica Write | >50 MB/s | | |
| Longhorn Replica Read | >100 MB/s | | |
| Restic Backup (100GB) | <2 hours | | |
| Restic Restore (100GB) | <4 hours | | |

### 5. Network

| Test | Target | Actual | Pass/Fail |
|------|--------|--------|-----------|
| Inter-node latency | <1ms | | |
| Inter-node bandwidth | >900 Mbps | | |
| External DNS resolution | <50ms | | |
| TLS handshake | <100ms | | |
| Tailscale connection | <5s | | |

### 6. Resource Utilization (Under Load)

| Resource | Target Max | Actual Peak | Pass/Fail |
|----------|------------|-------------|----------|
| CPU (per node) | <80% | | |
| RAM (per node) | <85% | | |
| Disk I/O wait | <10% | | |
| Network saturation | <70% | | |
| Temperature | <70°C | | |

### 7. Ollama Cluster Scaling

| Metric | 1 Replica | 2 Replicas | 3 Replicas | 6 Replicas |
|--------|-----------|------------|------------|------------|
| Concurrent Requests | 2 | 4 | 6 | 12 |
| Avg Latency (p95) | | | | |
| Error Rate | | | | |
| Scale-up Time | N/A | | | |
| Scale-down Time | N/A | | | |

---

## Test Results Summary

| Category | Tests Run | Passed | Failed | Pass Rate |
|----------|-----------|--------|--------|-----------|
| API Latency | 8 | | | |
| Ollama Inference | 4 | | | |
| Database | 5 | | | |
| Storage I/O | 6 | | | |
| Network | 5 | | | |
| Resource Utilization | 5 | | | |
| **Total** | **33** | | | |

---

## Issues Found

| Issue | Severity | Component | Impact | Recommendation |
|-------|----------|-----------|--------|----------------|
| | | | | |

---

## Recommendations

| Recommendation | Priority | Effort | Expected Improvement |
|----------------|----------|--------|---------------------|
| | | | |

---

## Test Artifacts

| Artifact | Location |
|----------|----------|
| Raw Benchmark Data | `/mnt/benchmark-results/YYYYMMDD/` |
| Grafana Dashboard Snapshot | `/mnt/benchmark-results/YYYYMMDD/grafana-snapshot.json` |
| Prometheus Query Export | `/mnt/benchmark-results/YYYYMMDD/prometheus-export.json` |
| Ollama Benchmark Logs | `/mnt/benchmark-results/YYYYMMDD/ollama-benchmark.log` |

---

## Tools Used

| Tool | Version | Purpose |
|------|---------|---------|
| `hey` / `wrk` / `ab` | Latest | HTTP load testing |
| `ollama` CLI | 0.3.x | LLM inference testing |
| `sysbench` | Latest | CPU/Memory/IO benchmarks |
| `iperf3` | Latest | Network bandwidth |
| `fio` | Latest | Storage I/O |
| `promtool` | 2.54.x | Prometheus query testing |
| `hey` / `wrk` | Latest | HTTP benchmarking |

---

## Historical Comparison

| Metric | Previous (v1.6) | Current (v1.7) | Change |
|--------|-----------------|----------------|--------|
| Avg API Latency (p95) | | | |
| Ollama Tokens/s (gemma:2b) | | | |
| Backup Time (100GB) | | | |
| Restore Time (100GB) | | | |
| CPU Idle % | | | |
| RAM Usage % | | | |

---

## Sign-off

| Role | Name | Signature | Date |
|------|------|-----------|------|
| Tester | | | |
| Reviewer | | | |
| Approver | | | |

---

*Template Version: 1.0 | homelab-prod Performance Benchmark*
*Frequency: Quarterly or after major changes*
*Next Review: Quarterly*