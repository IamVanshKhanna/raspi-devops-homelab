# Runbook: Resource Quota Exceeded

## Detection
- Pod stuck in `Pending` with events: `Warning FailedScheduling quota exceeded`
- `kubectl get events -A` shows quota warnings
- Grafana dashboard "Resource Quotas" shows 100% usage
- `make verify-v1` fails with quota errors

## Diagnosis
```bash
# Check which namespace hit quota
kubectl get resourcequota -A -o custom-columns="NS:.metadata.namespace,NAME:.metadata.name,USED:.status.used,HARD:.status.hard"

# Check quota details for specific namespace
kubectl describe resourcequota <quota-name> -n <namespace>

# Check which resource type is exhausted (cpu, memory, pods, services, etc.)
kubectl get resourcequota <quota-name> -n <namespace> -o jsonpath='{.status.used}'
```

## Quota Tiers (v2.10)
| Tier | Namespaces | Purpose |
|------|------------|---------|
| P0-Critical | monitoring, auth, databases, secrets, apps | Core platform |
| P1-Important | logging, uptime, tracing, smarthome | Key services |
| P2-Standard | (user workloads) | Standard apps |
| P3-Optional | litmus, ai | Experimental |

## Common Causes & Fixes

### 1. Legitimate Growth (Scale up quota)
```bash
# Check current limits
kubectl get resourcequota -n <namespace> -o yaml

# Edit quota (requires cluster admin)
kubectl edit resourcequota <quota-name> -n <namespace>
# Increase: requests.cpu, requests.memory, limits.cpu, limits.memory, pods, services
```

### 2. Resource Leak (Pods not cleaning up)
```bash
# Find completed/failed pods consuming quota
kubectl get pods -n <namespace> --field-selector=status.phase!=Running

# Clean up completed jobs
kubectl delete pods -n <namespace> --field-selector=status.phase=Succeeded
kubectl delete pods -n <namespace> --field-selector=status.phase=Failed

# Check for orphaned PVCs
kubectl get pvc -n <namespace>
```

### 3. Misconfigured Requests/Limits
```bash
# Check pod resource requests vs actual usage
./scripts/cost_optimizer.py --namespace <namespace>

# Right-size using VPA recommendations
./scripts/rightsizing-analyzer.py --namespace <namespace>
```

## Recovery Steps
1. Identify exhausted resource via `kubectl get resourcequota -A`
2. Determine cause: growth vs leak vs misconfig
3. Apply fix: scale quota, clean up, or right-size
4. Verify: `kubectl get resourcequota -n <namespace>` shows usage < hard limit
5. Restart affected deployments: `kubectl rollout restart deployment -n <namespace>`

## Prevention
- Weekly: `./scripts/cost_optimizer.py --all-namespaces`
- Enable VPA for automated recommendations
- Set up Grafana alert: `resource_quota_usage_percent > 80`

## Escalation
- If P0 namespace quota exceeded: Immediate action required
- If recurring: Create GitHub issue with quota audit

## Related
- Quota manifests: `config/cost-optimization/quotas/`
- Cost optimizer: `scripts/cost_optimizer.py`
- Rightsizing: `scripts/rightsizing-analyzer.py`