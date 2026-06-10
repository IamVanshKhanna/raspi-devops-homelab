# Runbook: Pod Disruption Budget Validation & Management

## Detection
- Kyverno policy `require-pod-disruption-budget` reports violations (Audit mode)
- `kubectl get pdb -A` shows missing PDBs
- Node drain/upgrade fails due to `Cannot evict pod` errors
- Pods not rescheduled during maintenance

## Diagnosis
```bash
# List all PDBs
kubectl get pdb -A -o wide

# Check PDB status (current/desired/available)
kubectl get pdb -A -o custom-columns="NS:.metadata.namespace,NAME:.metadata.name,MIN:.spec.minAvailable,MAX:.spec.maxUnavailable,CURRENT:.status.currentHealthy,DESIRED:.status.desiredHealthy,ALLOWED:.status.disruptionsAllowed"

# Find workloads without PDBs
for ns in $(kubectl get ns -o name | cut -d/ -f2); do
  for deploy in $(kubectl get deploy -n $ns -o name 2>/dev/null); do
    labels=$(kubectl get $deploy -n $ns -o jsonpath='{.spec.selector.matchLabels}')
    pdb_count=$(kubectl get pdb -n $ns -o json 2>/dev/null | jq --argjson labels "$labels" '[.items[] | select(.spec.selector.matchLabels == $labels)] | length')
    if [[ $pdb_count -eq 0 ]]; then
      echo "Missing PDB: $ns/$deploy (labels: $labels)"
    fi
  done
done

# Check Kyverno policy results
kubectl get clusterpolicy require-pod-disruption-budget -o jsonpath='{.status.policyResults[*].resources[*].policyReportResult}'
```

## PDB Templates (config/pdb-templates/)

| Template | Use Case | minAvailable/maxUnavailable |
|----------|----------|------------------------------|
| `01-pdb-critical-controlplane.yaml` | Control plane components | minAvailable: 50% |
| `02-pdb-stateful-workload.yaml` | StatefulSets (databases, etc.) | maxUnavailable: 1 |
| `03-pdb-standard-deployment.yaml` | Standard stateless deployments | minAvailable: 50% |
| `04-pdb-spot-tolerant.yaml` | Spot instance workloads | maxUnavailable: 100% |

## Applying PDBs

```bash
# Example: Apply standard PDB to monitoring namespace for prometheus
sed 's/NAMESPACE/monitoring/g; s/app.kubernetes.io\/component: standard/app.kubernetes.io\/name: prometheus/g' \
  config/pdb-templates/03-pdb-standard-deployment.yaml | kubectl apply -f -

# Example: Apply spot PDB for spot workloads
sed 's/NAMESPACE/apps/g' config/pdb-templates/04-pdb-spot-tolerant.yaml | kubectl apply -f -
```

## Common Issues & Fixes

### 1. PDB Matching Wrong Pods
```bash
# Check selector matches
kubectl get pods -n <ns> --show-labels | grep <label-key>

# Fix: Update PDB selector to match deployment selector exactly
kubectl edit pdb <pdb-name> -n <ns>
```

### 2. Disruptions Not Allowed (minAvailable too high)
```bash
# Check current healthy vs desired
kubectl get pdb <name> -n <ns> -o jsonpath='{.status.currentHealthy}/{.status.desiredHealthy}'

# Fix: Reduce minAvailable or scale up deployment
kubectl scale deploy <name> -n <ns> --replicas=3
# Or adjust PDB
kubectl patch pdb <name> -n <ns> -p '{"spec":{"minAvailable": "33%"}}'
```

### 3. Pod Stuck in Terminating (PDB blocking)
```bash
# Check disruptionsAllowed
kubectl get pdb <name> -n <ns> -o jsonpath='{.status.disruptionsAllowed}'

# If 0: Wait for other pods to become ready, or temporarily increase maxUnavailable
kubectl patch pdb <name> -n <ns> -p '{"spec":{"maxUnavailable": 2}}'
```

## Validation Checklist

- [ ] Every Deployment/StatefulSet in production namespaces has a PDB
- [ ] PDB selector matches workload selector exactly
- [ ] minAvailable/maxUnavailable appropriate for HA requirements
- [ ] Kyverno policy `require-pod-disruption-budget` in Enforce mode (currently Audit)
- [ ] Node drain test passes: `kubectl drain <node> --ignore-daemonsets --dry-run`
- [ ] PDBs documented in runbooks for each critical service

## Escalation
- PDB violations in Kyverno (Audit): Create GitHub issue for missing PDB
- Node drain blocked > 10 min: Temporarily patch PDB, investigate root cause
- Recurring issues: Review HA architecture, consider anti-affinity rules

## Related
- Kyverno policy: `config/kyverno/policies/12-require-pod-disruption-budget.yaml`
- Templates: `config/pdb-templates/`
- Spot workload PDBs: `config/spot-patches/` (v2.10)
- Maintenance procedures: `docs/operational-guides.md`