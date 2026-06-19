# Resource Quotas and Limits Configuration
# Applied per namespace based on service criticality tier

## Overview
This directory contains ResourceQuota and LimitRange manifests for all namespaces.
Quotas are tiered based on service criticality:
- **P0 Critical** (RTO 4h): Higher limits, guaranteed resources
- **P1 Important** (RTO 12h): Moderate limits
- **P2 Standard** (RTO 24h): Standard limits
- **P3 Optional** (RTO 72h): Minimal limits

## Namespace Tier Mapping

| Tier | Namespaces | CPU Limit | Memory Limit | Storage Limit | Pod Limit |
|------|------------|-----------|--------------|---------------|-----------|
| P0 | apps, databases, secrets, auth, monitoring | 4 cores | 8 GiB | 100 GiB | 50 |
| P1 | smarthome, logging, tracing, security, uptime | 2 cores | 4 GiB | 50 GiB | 30 |
| P2 | logging, tracing (additional), secrets (additional) | 1 core | 2 GiB | 20 GiB | 20 |
| P3 | litmus, ai (optional), chaos | 500m | 1 GiB | 10 GiB | 10 |

## Default Resource Requests (per container)
- P0: cpu: 250m, memory: 512Mi
- P1: cpu: 100m, memory: 256Mi
- P2: cpu: 50m, memory: 128Mi
- P3: cpu: 25m, memory: 64Mi