# Runbook: SLO Violation / Burn Rate Alert

## Detection
- Prometheus alert: `SLOBurnRateCritical` (2% budget in 1h)
- Prometheus alert: `SLOBurnRateWarning` (5% budget in 6h)
- Prometheus alert: `SLOBurnRateInfo` (10% budget in 1d)
- Grafana SLO dashboard shows consumption spike
- `make verify-v1` fails on SLO checks

## Diagnosis
```bash
# Check which service/SLO is burning
# From alert labels: service, slo

# View current error budget consumption (30d window)
# Traefik availability example:
PROMQL='(1 - (sum(rate(traefik_entrypoint_requests_total{code=~"2..|3.."}[1h])) / sum(rate(traefik_entrypoint_requests_total[1h]))) / (1 - 0.999)) * 100'

# Check error rate (5xx)
PROMQL='sum(rate(traefik_entrypoint_requests_total{code=~"5.."}[5m])) / sum(rate(traefik_entrypoint_requests_total[5m]))'

# Check latency SLO (p99)
PROMQL='histogram_quantile(0.99, sum(rate(traefik_entrypoint_request_duration_seconds_bucket[5m])) by (le))'

# View service logs for correlation
kubectl logs -n <namespace> -l app=<service> --tail 100
```

## SLO Targets (Reference)

| Service | Availability SLO | Latency SLO (p99) | Error Budget (30d) |
|---------|-----------------|-------------------|---------------------|
| Traefik | 99.9% | < 200ms | 43.8 min |
| Authelia | 99.95% | < 1s | 21.9 min |
| Nextcloud | 99.5% | < 30s (upload) | 3.65 h |
| Vaultwarden | 99.9% | < 500ms | 43.8 min |
| Ollama | 99% | < 30s (inference) | 7.3 h |
| HomeAssistant | 99.9% | < 500ms | 43.8 min |
| K8s API | 99.9% | - | 43.8 min |
| Longhorn | 99.9% (healthy vols) | - | 43.8 min |

## Burn Rate Thresholds

| Alert | Budget Consumed | Window | Rate vs Normal | Action |
|-------|----------------|--------|----------------|--------|
| Critical | 2% | 1h | 14.4x | **Immediate** - page on-call |
| Warning | 5% | 6h | 6x | Investigate within 1h |
| Info | 10% | 1d | 3x | Plan remediation |

## Common Causes & Fixes

### 1. Upstream Dependency Failure
```bash
# Check downstream service health
kubectl get pods -n <downstream-ns>
# Check Traefik upstream
kubectl logs -n traefik deployment/traefik | grep -i upstream
```

### 2. Deployment Regression
```bash
# Check recent deployments
kubectl get events -n <namespace> --sort-by='.lastTimestamp' | tail -20
# Rollback if needed
kubectl rollout undo deployment/<name> -n <namespace>
```

### 3. Resource Exhaustion (OOM, CPU throttling)
```bash
# Check container resources
kubectl top pods -n <namespace>
# Check OOM kills
kubectl get events -n <namespace> | grep -i oom
# Fix: Increase limits or rightsize
./scripts/rightsizing-analyzer.py --namespace <namespace>
```

### 4. Database/Storage Latency
```bash
# Check Longhorn
kubectl get volumes -n longhorn-system
# Check PostgreSQL
kubectl exec -n databases postgresql-0 -- pg_stat_activity
```

### 5. Network/DNS Issues
```bash
# Check CoreDNS
kubectl logs -n kube-system -l k8s-app=kube-dns
# Check Service endpoints
kubectl get endpoints -n <namespace>
```

## Recovery Steps
1. **Identify burning service/SLO** from alert labels
2. **Check error rate & latency** via Grafana SLO dashboard or PromQL
3. **Correlate with recent changes** (deployments, config changes, scaling)
4. **Apply fix**: Rollback, scale, resource increase, dependency fix
5. **Verify recovery**: Burn rate drops below threshold for 15m
6. **Post-incident**: Document in GitHub issue, update runbook if needed

## Escalation
- **Critical (2% in 1h)**: Page on-call immediately, start war room if >2 services
- **Warning (5% in 6h)**: On-call investigates within 1h, create GitHub issue
- **Info (10% in 1d)**: Create GitHub issue, plan remediation in sprint

## Related
- SLO definitions: `config/prometheus/rules/slo-definitions.yaml`
- Burn rate alerts: `config/prometheus/rules/burn-rate-alerts.yaml`
- Dashboard: Grafana → SLO & Error Budget Overview (`homelab-slo-overview`)
- Error budget runbook: `docs/runbooks/error-budget-exhausted.md`