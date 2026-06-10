# Trace Sampling Configuration — homelab-prod

## Current Configuration (config/otel/otel-collector-config.yaml)

### Sampling Status: **No explicit sampling** (100% trace ingestion)
- All traces sent to Tempo
- No probabilistic sampling configured
- Memory limiter at 500 MiB protects OOM

### Impact
| Metric | Value |
|--------|-------|
| Ingestion rate | ~100% of traces |
| Storage growth | Linear with request volume |
| Query performance | Good for current scale |
| Cost | Higher storage/network |

---

## Recommended Sampling for v2.12+

### Option 1: Tail-Based Sampling (Recommended)
```yaml
processors:
  # Add to processors section
  tail_sampling:
    # Sample 100% of errors, 10% of slow traces, 1% of normal
    decision_wait: 30s
    num_traces: 50000
    expected_new_traces_per_sec: 100
    policy:
      - name: errors-policy
        type: string_attribute
        string_attribute:
          key: status
          values: ["error", "5xx"]
      - name: slow-traces-policy
        type: latency
        latency:
          threshold_ms: 5000
      - name: correlation-id-policy
        type: string_attribute
        string_attribute:
          key: correlation_id
          values: ["*"]  # Always sample traces with correlation IDs
      - name: probabilistic-policy
        type: probabilistic
        probabilistic:
          sampling_percentage: 10
```

### Option 2: Head-Based Probabilistic (Simpler)
```yaml
processors:
  probabilistic_sampler:
    hash_seed: 22
    sampling_percentage: 25  # 25% of traces
```

### Option 3: Rate-Limited Sampling
```yaml
processors:
  # Limit to 100 traces/second max
  span_processor:
    export_rate_limit: 100
```

---

## Implementation Plan for v2.12

### Phase 1: Add Tail Sampling (Week 2)
- [ ] Add `tail_sampling` processor to `config/otel/otel-collector-config.yaml`
- [ ] Configure policies: errors (100%), slow >5s (100%), correlation IDs (100%), rest 10%
- [ ] Test in staging, verify error traces captured

### Phase 2: Add Metrics for Sampling Effectiveness (Week 3)
- [ ] Add Prometheus metrics: `otelcol_processor_tail_sampling_spans_dropped`
- [ ] Dashboard panel: "Trace Sampling Rate by Policy"
- [ ] Alert: `trace_sampling_dropped_percentage > 50` (warning)

### Phase 3: Cost Validation (Week 3)
- [ ] Compare Tempo storage before/after
- [ ] Verify < 5% observability gap (no critical traces missed)
- [ ] Document sampling ratios per service

---

## Validation Commands

```bash
# Check current trace ingestion rate
curl -s tempo:3100/metrics | grep tempo_trace_ingester_spans_received_total

# Check sampling processor metrics
curl -s otel-collector:8888/metrics | grep tail_sampling

# Verify error traces not dropped
# Search for known error traces in Tempo
```

---

## Target Sampling Ratios (Post-v2.12)

| Policy | Sampling % | Rationale |
|--------|------------|-----------|
| Errors (5xx, exceptions) | 100% | Zero observability gap for failures |
| Slow traces (>5s) | 100% | Performance debugging critical |
| Correlation ID present | 100% | End-to-end debugging value |
| High-value services (Ollama, Authelia) | 25% | Debugging priority |
| Standard services | 10% | Cost control |
| Health checks / readiness | 0% (drop) | Zero value, high volume |

---

## References
- [OpenTelemetry Tail Sampling](https://github.com/open-telemetry/opentelemetry-collector-contrib/tree/main/processor/tailsamplingprocessor)
- [Google SRE: Distributed Tracing Sampling](https://sre.google/sre-book/distributed-tracing/)
- [Tempo Sampling Guide](https://grafana.com/docs/tempo/latest/configuration/sampling/)