# Runbook: Rightsizing Recommendations / Resource Waste

## Detection
- Weekly GitHub Actions workflow "Right-Sizing Analysis" creates PR with recommendations
- Grafana dashboard "Container Rightsizing" shows savings potential >10%
- `./scripts/rightsizing-analyzer.py` outputs high-confidence recommendations
- Cost allocation report shows namespaces with low utilization

## Diagnosis
```bash
# Run rightsizing analysis manually
./scripts/rightsizing-analyzer.py --all-namespaces --output json > rightsizing.json

# View recommendations
cat rightsizing.json | jq '.[] | select(.confidence=="High")'

# Check VPA recommendations (if VPA installed)
kubectl get vpa -A -o custom-columns="NS:.metadata.namespace,NAME:.metadata.name,TARGET:.spec.targetRef.name,REC:.status.recommendation"

# Check actual vs requested resources
./scripts/cost_optimizer.py --namespace <namespace> --detail
```

## v2.10 Rightsizing Setup
| Component | Configuration |
|-----------|---------------|
| Analyzer | `scripts/rightsizing-analyzer.py` (Prometheus + VPA) |
| Schedule | Weekly (GitHub Actions: `rightsizing-analysis.yml`) |
| Output | PR to repo with patch files |
| Confidence Levels | High (>30 days data), Medium (7-30 days), Low (<7 days) |
| Threshold | PR created only if savings >10% |

## Common Causes & Fixes

### 1. Over-provisioned Requests (Most Common)
```bash
# Typical pattern: requests >> actual usage
# Fix: Apply VPA recommendations or manually adjust

# Example: deployment with 500m CPU request, actual 50m
kubectl set resources deployment <name> -n <ns> --requests=cpu=100m,memory=128Mi
```

### 2. Missing Limits (OOM Risk)
```bash
# Containers without limits can starve others
# Fix: Set limits = requests * 1.5-2x (QoS: Burstable)
kubectl set resources deployment <name> -n <ns> --limits=cpu=200m,memory=256Mi
```

### 3. VPA Not Installed/Configured
```bash
# Check VPA status
kubectl get crd verticalpodautoscalers.autoscaling.k8s.io

# Install VPA (if missing)
kubectl apply -f https://github.com/kubernetes/autoscaler/releases/download/vertical-pod-autoscaler-<version>/vpa-release.yaml

# Configure VPA for namespace
cat <<EOF | kubectl apply -f -
apiVersion: autoscaling.k8s.io/v1
kind: VerticalPodAutoscaler
metadata:
  name: <workload>-vpa
  namespace: <namespace>
spec:
  targetRef:
    apiVersion: "apps/v1"
    kind: Deployment
    name: <workload>
  updatePolicy:
    updateMode: "Auto"
EOF
```

## Recovery Steps
1. Review weekly PR: `rightsizing-recommendations-<date>`
2. For each High confidence recommendation:
   - Verify workload can tolerate restart
   - Apply patch: `git apply rightsizing-patch-<workload>.patch`
   - Deploy: `kubectl apply -k config/cost-optimization/quotas/`
3. Monitor for 1 week post-change
4. If issues: Revert via GitHub PR revert

## Prevention
- Enable VPA in "Auto" mode for stateless workloads
- Set default requests/limits via namespace quota
- Quarterly review: `./scripts/rightsizing-analyzer.py --history 90d`
- CI gate: Block deployments with requests > 3x P99 usage (policy)

## Escalation
- If rightsizing causes OOM/performance regression: Immediate revert
- If VPA stuck: Check `kubectl describe vpa` for conditions
- Persistent recommendations ignored: Add to technical debt backlog

## Related
- Analyzer: `scripts/rightsizing-analyzer.py`
- Cost optimizer: `scripts/cost_optimizer.py`
- Quota configs: `config/cost-optimization/quotas/`
- Workflow: `.github/workflows/rightsizing-analysis.yml`