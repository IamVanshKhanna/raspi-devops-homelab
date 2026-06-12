# Runbook: Cost Allocation / Chargeback Anomalies

## Detection
- Weekly GitHub Actions "Cost Allocation Report" shows unexpected spikes
- Grafana dashboard "Cost Allocation by Namespace/Team/Service" anomalies
- `./scripts/cost-allocation.py` output deviates >20% from baseline
- Team leads report budget discrepancies

## Diagnosis
```bash
# Run cost allocation manually
./scripts/cost-allocation.py --period weekly --output json > cost.json

# View by namespace
cat cost.json | jq '.by_namespace | to_entries[] | .key + ": " + (.value | tostring)'

# View by team
cat cost.json | jq '.by_team'

# View by service
cat cost.json | jq '.by_service'

# Check rate config
cat config/cost-optimization/rates.yaml
```

## v2.10 Cost Allocation Setup
| Component | Configuration |
|-----------|---------------|
| Script | `scripts/cost-allocation.py` |
| Schedule | Weekly (Monday 00:00 UTC) |
| Rates | `config/cost-optimization/rates.yaml` (CPU/hr, Mem/GB-hr, Storage/GB-mo, Network/GB) |
| Output | GitHub Actions summary + artifact |
| Granularity | Namespace → Team → Service |

## Common Causes & Fixes

### 1. Rate Misconfiguration
```bash
# Check current rates
cat config/cost-optimization/rates.yaml

# Example rates (adjust to your cloud provider):
# cpu_per_hour_usd: 0.031611  # t3.medium equivalent
# memory_per_gb_hour_usd: 0.004237
# storage_per_gb_month_usd: 0.10
# network_per_gb_usd: 0.09

# Fix: Update rates.yaml, commit, workflow auto-picks up
```

### 2. Namespace → Team Mapping Drift
```bash
# Check team annotations on namespaces
kubectl get ns -o custom-columns="NAME:.metadata.name,TEAM:.metadata.annotations.cost\.homelab/team"

# Fix: Add/update annotation
kubectl annotate ns <namespace> cost.homelab/team=<team-name> --overwrite
```

### 3. Unattributed Resources (No namespace/team)
```bash
# Find resources without cost tracking labels
kubectl get pods -A --show-labels | grep -v "cost.homelab/"

# Fix: Enforce labels via Kyverno policy or admission webhook
```

### 4. Spot/On-Demand Mix Not Reflected
```bash
# Check node labels
kubectl get nodes --show-labels | grep -E "node.kubernetes.io/instance-type|topology.kubernetes.io/zone"

# Fix: Update rates.yaml with spot discount factor
# spot_cpu_discount: 0.7  # 70% savings
```

## Recovery Steps
1. Identify anomaly source: namespace, team, or service
2. Check rate config vs actual cloud bill
3. Verify namespace/team annotations
4. Re-run allocation: `./scripts/cost-allocation.py --recalculate`
5. Update rates/annotations as needed
6. Regenerate report

## Prevention
- Monthly: Compare allocation report vs actual cloud invoice
- CI: Validate all namespaces have `cost.homelab/team` annotation
- Quarterly: Review and update rates.yaml with current pricing
- Alert: `cost_allocation_variance_percent > 20`

## Escalation
- If variance >50% vs cloud bill: Immediate audit
- If team disputes charges: Provide per-service breakdown from report
- Persistent misattribution: Implement automated label enforcement

## Related
- Allocator: `scripts/cost-allocation.py`
- Rates config: `config/cost-optimization/rates.yaml`
- Weekly workflow: `.github/workflows/cost-allocation.yml`
- Grafana dashboard: `config/grafana/provisioning/dashboards/cost-allocation.json`