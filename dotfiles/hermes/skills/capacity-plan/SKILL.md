---
name: capacity-plan
description: Resource forecasting and capacity planning for homelab
version: 1.0.0
category: homelab
---

## Triggers
- "capacity forecast"
- "disk forecast"
- "ram forecast"
- "when will disk be full"
- "resource trends"

## Allowed Commands (read-only, no confirmation)
- `df -h /mnt/data /mnt/backup`
- `free -h`
- `vcgencmd measure_temp`
- `promtool query instant 'node_filesystem_size_bytes{mountpoint="/mnt/data"}'`
- `promtool query instant 'node_filesystem_avail_bytes{mountpoint="/mnt/data"}'`
- `promtool query instant '(1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)) * 100'`

## Allowed Actions (require confirmation)
- **Generate capacity report**: Run promql queries and format as markdown
- **Project disk exhaustion**: `promtool query instant 'predict_linear(node_filesystem_avail_bytes{mountpoint="/mnt/data"}[30d], 30d)'`
- **Project RAM exhaustion**: `promtool query instant 'predict_linear(1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)[30d], 30d)'`
- **Set alert threshold**: Update Prometheus rules (requires PR)

## Forbidden
- Modifying Prometheus rules directly (requires PR)
- Changing disk partitions
- Modifying ZRAM configuration

## PromQL Queries for Forecasting

### Disk Exhaustion (30-day linear projection)
```promql
predict_linear(node_filesystem_avail_bytes{mountpoint="/mnt/data"}[30d], 30d) < 0
```

### Disk Days Remaining
```promql
node_filesystem_avail_bytes{mountpoint="/mnt/data"} / (node_filesystem_size_bytes{mountpoint="/mnt/data"} - node_filesystem_avail_bytes{mountpoint="/mnt/data"}) * 30
```

### RAM Growth Rate
```promql
rate(container_memory_usage_bytes[30d])
```

## Context Variables
- `DATA_DIR` (/mnt/data)
- `BACKUP_DIR` (/mnt/backup)
- Prometheus endpoint: `http://localhost:9090`

## Alert Thresholds (current)
- Disk warning: 80%
- Disk critical: 90%
- RAM warning: 85%
- RAM critical: 95%

## Example Usage
> "When will /mnt/data run out of space?"
> "Show me 30-day RAM usage trend"
> "Generate capacity planning report"
> "What's the disk growth rate per day?"