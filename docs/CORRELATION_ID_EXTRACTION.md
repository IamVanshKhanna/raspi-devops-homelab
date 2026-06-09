# Correlation ID Extraction for Loki/Promtail

## Promtail Pipeline Configuration

Add to `config/promtail/promtail.yml` under the pipeline stages:

```yaml
scrape_configs:
  - job_name: containers
    static_configs:
      - targets:
          - localhost
        labels:
          job: containerlogs
          __path__: /var/log/pods/*/*.log
    pipeline_stages:
      # Parse Docker JSON log format
      - json:
          expressions:
            stream: stream
            log: log
            container: kubernetes.container_name
            namespace: kubernetes.namespace_name
            pod: kubernetes.pod_name
            pod_uid: kubernetes.pod_uid

      # Extract correlation ID from log message
      - regex:
          expression: '(?P<correlation_id>[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})'
          source: log

      # Extract request ID
      - regex:
          expression: '(?P<request_id>req-[a-zA-Z0-9-]+)'
          source: log

      # Extract trace/span IDs from W3C traceparent
      - regex:
          expression: 'traceparent: (?P<trace_id>[a-f0-9]{32})-(?P<span_id>[a-f0-9]{16})'
          source: log

      # Add labels for Loki
      - labels:
          correlation_id:
          request_id:
          trace_id:
          span_id:
          container:
          namespace:
          pod:

      # Output structured log
      - output:
          source: log
```

## Loki Query Examples

### Find logs by correlation ID
```logql
{job="containerlogs"} | correlation_id="a1b2c3d4-e5f6-7890-abcd-ef1234567890"
```

### Find all logs with correlation IDs in last hour
```logql
{job="containerlogs"} |~ `correlation_id` | json | line_format "{{.correlation_id}} | {{.service}} | {{.message}}"
```

### Count logs with/without correlation IDs
```logql
# With correlation ID
count_over_time({job="containerlogs"} |~ `correlation_id` [5m])

# Without correlation ID
count_over_time({job="containerlogs"} |~ `correlation_id` [5m] != 0)
```

### Correlation ID distribution by service
```logql
sum by (service) (count_over_time({job="containerlogs"} |~ `correlation_id` [5m]))
```

### Trace correlation ID across services
```logql
# Find all logs for a specific trace
{job="containerlogs"} | trace_id="4bf92f3577b34da6a3ce929d0e0e4736"
```

## Grafana Dashboard Queries

### Correlation ID Distribution
```logql
sum by (service) (count_over_time({job="containerlogs"} |~ `correlation_id` [5m]))
```

### Logs with Correlation ID (last 5m)
```logql
count_over_time({job="containerlogs"} |~ `correlation_id` [5m])
```

### Missing Correlation ID Alert
```logql
# Alert if > 1% of logs missing correlation ID
(
  count_over_time({job="containerlogs"} | line_format "{{.log}}" |~ `(?![a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})` [5m])
  /
  count_over_time({job="containerlogs"} [5m])
) > 0.01
```

## Promtail Config Update

Apply the updated promtail config:
```bash
kubectl apply -f config/promtail/promtail.yml -n logging
```

## Verification

```bash
# Check promtail is running
kubectl get pods -n logging -l app=promtail

# Check Loki receiving logs
curl -s http://loki:3100/ready

# Test query
curl -G -s "http://loki:3100/loki/api/v1/query_range" \
  --data-urlencode 'query={job="containerlogs"} |~ `correlation_id`' \
  --data-urlencode 'limit=10'
```