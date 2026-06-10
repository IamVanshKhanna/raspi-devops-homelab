# Runbook: Error Budget Exhausted

## Detection
- Prometheus alert: `ErrorBudgetExhausted` (budget < 0)
- Prometheus alert: `ErrorBudgetCritical` (< 5% remaining)
- Grafana SLO dashboard shows negative budget
- `make verify-v1` fails on SLO checks

## Diagnosis
```bash
# Check which service/SLO exhausted
# From alert labels: service, slo

# View error budget remaining (30d window)
# Example for Traefik:
PROMQL='(1 - 0.999) - (1 - (sum(rate(traefik_entrypoint_requests_total{code=~"2..|3.."}[30d])) / sum(rate(traefik_entrypoint_requests_total[30d])))'

# View % budget consumed
PROMQL='(1 - (sum(rate(traefik_entrypoint_requests_total{code=~"2..|3.."}[30d])) / sum(rate(traefik_entrypoint_requests_total[30d]))) / (1 - 0.999)) * 100

# Check burn rate (are we still burning?)
PROMQL='(1 - (sum(rate(traefik_entrypoint_requests_total{code=~"2..|3.."}[1h])) / sum(rate(traefik_entrypoint_requests_total[1h]))) / (1 - 0.999)) * 100
```

## SLO Error Budget Reference

| Service | Target | Total Budget (30d) | 5% Remaining | Exhausted |
|---------|--------|-------------------|--------------|-----------|
| Traefik | 99.9% | 43.8 min | 2.19 min | < 0 min |
| Authelia | 99.95% | 21.9 min | 1.1 min | < 0 min |
| Nextcloud | 99.5% | 3.65 h | 11 min | < 0 min |
| Vaultwarden | 99.9% | 43.8 min | 2.19 min | < 0 min |
| Ollama | 99% | 7.3 h | 22 min | < 0 min |
| HomeAssistant | 99.9% | 43.8 min | 2.19 min | < 0 min |

## Recovery Steps

### 1. Immediate: Stop the Bleeding
```bash
# Check if still burning
# If burn rate > 0: Find root cause FIRST

# If deployment caused it: ROLLBACK
kubectl rollout undo deployment/<name> -n <namespace>

# If resource exhaustion: Scale up or increase limits
kubectl scale deployment <name> -n <namespace> --replicas=5
kubectl set resources deployment <name> -n <namespace> --limits=cpu=2000m,memory=4Gi
```

### 2. Short-term: Error Budget Payback
- **Feature freeze** on affected service until budget positive
- **No new deployments** except hotfixes
- **Increase monitoring**: 1m scrape interval for affected metrics
- **Communicate**: Update status page, notify stakeholders

### 3. Medium-term: Pay Back Debt
- Budget pays back at rate: `(1 - target) * requests_per_period`
- Example: Traefik 99.9% target, 1M req/day → 1000 errors/day budget
- At 0 errors/day → ~44 days to recover 43.8 min at 99.9%

### 4. Long-term: Prevent Recurrence
- Root cause analysis (RCA) within 5 business days
- Update SLO targets if unrealistic
- Add circuit breakers, retries, timeouts
- Improve observability (more granular SLIs)

## Escalation

| Budget Level | Action |
|--------------|--------|
| < 5% remaining | On-call investigates, feature freeze, GitHub issue |
| Exhausted (< 0%) | **Page on-call**, war room if multi-service, status page update |
| Multi-service exhausted | **Incident commander** appointed, executive notification |

## Related
- SLO definitions: `config/prometheus/rules/slo-definitions.yaml`
- Burn rate alerts: `config/prometheus/rules/burn-rate-alerts.yaml`
- Dashboard: Grafana → SLO & Error Budget Overview (`homelab-slo-overview`)
- SLO violation runbook: `docs/runbooks/slo-violation.md`
- Error budget theory: Google SRE Book Ch. 4