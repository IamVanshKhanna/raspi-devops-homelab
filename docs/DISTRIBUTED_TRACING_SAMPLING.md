# Distributed Tracing Sampling Policy

## Overview
This document defines the distributed tracing sampling strategy for homelab-prod v2.3+.
The goal is to balance observability completeness with resource constraints on Pi 4B hardware.

## Sampling Strategy

### Head-Based Sampling (At Ingestion)
Configured at the OpenTelemetry Collector level to reduce volume at the source.

| Service Type | Sample Rate | Rationale |
|--------------|-------------|-----------|
| **High-Value (Ollama, Nextcloud API)** | 100% | Critical for debugging user-facing issues |
| **Auth (Authelia)** | 100% | Security audit trail requires full trace coverage |
| **Edge (Traefik, Authelia)** | 50% | High volume, sufficient for latency analysis |
| **Internal (DB, Redis, Internal APIs)** | 10% | High volume, lower business impact |
| **Background Jobs (Backup, Sync)** | 5% | Low priority, periodic sampling sufficient |

### Tail-Based Sampling (At Storage)
Configured in Tempo to selectively retain traces based on outcome.

| Condition | Retention |
|-----------|-----------|
| **Error spans (status=error)** | 100% retain |
| **High latency (p99 > threshold)** | 100% retain |
| **Specific services (Ollama, Authelia)** | 100% retain |
| **Normal requests** | Per head-based rate |

## Configuration

### OTEL Collector Sampling Configuration
```yaml
# config/otel/otel-collector-config.yaml
processors:
  tail_sampling:
    decision_wait: 30s
    expected_new_traces_per_sec: 100
    policies:
      - name: errors
        type: string_attribute
        string_attribute:
          key: "span.status_code"
          values: ["ERROR"]
      - name: high_latency
        type: numeric_attribute
        numeric_attribute:
          key: "duration_ms"
          min_value: 5000  # 5 seconds
      - name: ollama_traces
        type: string_attribute
        string_attribute:
          key: "service.name"
          values: ["ollama"]
      - name: authelia_traces
        type: string_attribute
        string_attribute:
          key: "service.name"
          values: ["authelia"]
      - name: normal_traffic
        type: probabilistic
        probabilistic:
          sampling_percentage: 10
```

### Tempo Compactor Configuration
```yaml
# Tempo compactor with trace retention
compactor:
  compaction:
    block_retention: 72h  # Match Loki retention
    compacted_block_retention: 1h
  traces_to_metrics:
    enabled: true
```

## Correlation ID Propagation

### Standard Headers
All services MUST propagate these headers:

| Header | Format | Required |
|--------|--------|----------|
| `X-Correlation-ID` | UUID v4 | **Yes** |
| `X-Request-ID` | UUID v4 (per request) | Yes |
| `traceparent` | W3C trace-context | Yes (for OTEL) |
| `tracestate` | Vendor-specific | Optional |

### Propagation Rules

#### Ingress (Traefik)
```yaml
# Traefik middleware to extract/inject correlation IDs
middlewares:
  correlation-id:
    plugin:
      correlation-id:
        headerName: "X-Correlation-ID"
        generator: "uuid"
        allowEmpty: false
```

#### Application Services (All)
- **Extract** `X-Correlation-ID` from incoming request headers
- **Generate** new UUID if not present
- **Inject** into all outgoing HTTP/gRPC calls
- **Log** correlation ID with every structured log entry

#### Correlation ID in Logs
```json
{
  "timestamp": "2026-06-09T15:30:00.123Z",
  "level": "info",
  "service": "nextcloud",
  "correlation_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "request_id": "req-12345",
  "trace_id": "4bf92f3577b34da6a3ce929d0e0e4736",
  "span_id": "00f067aa0ba902b7",
  "message": "File upload started"
}
```

## Service-Specific Implementation

### Go Services
```go
// correlation/middleware.go
func CorrelationIDMiddleware(next http.Handler) http.Handler {
    return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
        cid := r.Header.Get("X-Correlation-ID")
        if cid == "" {
            cid = uuid.New().String()
        }
        w.Header().Set("X-Correlation-ID", cid)
        ctx := context.WithValue(r.Context(), CorrelationIDKey, cid)
        next.ServeHTTP(w, r.WithContext(ctx))
    }
}
```

### Python Services
```python
# correlation_id.py
class CorrelationIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        correlation_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))
        correlation_id_var.set(correlation_id)
        response = await call_next(request)
        response.headers["X-Correlation-ID"] = correlation_id
        return response
```

### Logrus/Zap/Structlog Integration
```go
// golang
log.WithField("correlation_id", GetCorrelationID(ctx)).Info("Request processed")

// python
logger.info("Request processed", extra={"correlation_id": get_correlation_id()})
```

## Verification

### Automated Checks
```bash
# Check correlation ID in logs
./scripts/loki_query.py --query '{job=~".*"} |~ `correlation_id`' --since 1h

# Check trace propagation
./scripts/tempo_query.py --service ollama --since 1h

# Check sampling rates
./scripts/promql_query.py --query 'rate(traces_received_total[5m])' --format table
```

### Dashboard
Grafana dashboard: **Correlation ID Debugging** (UID: `homelab-correlation-id-debugging`)

## Sampling Rate Monitoring

### Key Metrics
| Metric | Target | Alert Threshold |
|--------|--------|-----------------|
| Trace ingestion rate | < 1000 spans/sec | > 2000 spans/sec |
| Error trace retention | 100% | < 99% |
| High-latency trace retention | 100% | < 95% |
| Correlation ID coverage | 100% | < 99% |

### Alert Rules
```yaml
- alert: TracingSamplingRateHigh
  expr: rate(tempo_distributor_spans_received_total[5m]) > 2000
  for: 5m
  labels:
    severity: warning
  annotations:
    summary: "Tracing sampling rate exceeded threshold"
    description: "Current rate: {{ $value }} spans/sec"

- alert: CorrelationIDMissing
  expr: sum(rate(logs_without_correlation_id_total[5m])) > 0.01
  for: 1m
  labels:
    severity: warning
  annotations:
    summary: "Correlation ID missing in logs"
```

## Capacity Planning

### Estimated Trace Volume
| Environment | Services | Requests/day | Traces/day (at 10%) | Storage/day |
|-------------|----------|--------------|---------------------|-------------|
| Production | 15 | 500K | 50K | ~500MB |
| Staging | 15 | 50K | 5K | ~50MB |

### Storage Requirements
- **Tempo block storage**: 10Gi (72h retention)
- **Compactor**: Runs every 1h, retains 72h
- **Index**: Stored in object storage (Longhorn/S3)

## Migration Checklist (v2.3)
- [ ] Configure OTEL Collector tail sampling processor
- [ ] Update Tempo compactor config
- [ ] Deploy correlation ID middleware to all services
- [ ] Update logging format to include correlation_id
- [ ] Add correlation ID extraction to Loki/Promtail pipeline
- [ ] Create Grafana dashboards for sampling monitoring
- [ ] Add sampling rate alerts
- [ ] Document correlation ID usage for on-call
- [ ] Test correlation ID propagation end-to-end
- [ ] Verify tail sampling retains all error traces