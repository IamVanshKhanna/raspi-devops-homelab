# Runbook: Spot Instance Node Termination / Issues

## Detection
- Nodes with `node.kubernetes.io/instance-type=spot` label go NotReady
- Pods on spot nodes evicted (check `kubectl get events -A | grep -i spot`)
- Spot termination notice in node logs: `aws-node-termination-handler` alerts
- PDB violations: `kubectl get pdb -A` shows `MIN AVAILABLE` not met

## Diagnosis
```bash
# Spot node status
kubectl get nodes -l node.kubernetes.io/instance-type=spot -o wide

# Check spot termination handler logs
kubectl logs -n kube-system -l app=aws-node-termination-handler --tail 50

# Check PDBs
kubectl get pdb -A -o custom-columns="NS:.metadata.namespace,NAME:.metadata.name,MIN:.spec.minAvailable,CURRENT:.status.currentHealthy,DESIRED:.status.desiredHealthy"

# Check which pods were evicted
kubectl get pods -A -o wide | grep -E "Evicted|Terminating"
```

## v2.10 Spot Setup
| Component | Configuration |
|-----------|---------------|
| Node Group | EKS Spot (t3.medium, capacity-optimized) |
| Savings | ~70% vs on-demand |
| PDBs | Applied to all critical workloads |
| Termination Handler | `aws-node-termination-handler` (2-min notice) |
| Tolerations | Spot patches in `config/spot-patches/` |

## Common Causes & Fixes

### 1. Spot Node Terminated (Expected)
```bash
# Verify workloads rescheduled
kubectl get pods -A -o wide | grep -v spot-node-name

# Check PDB protected workloads
kubectl get pdb -A --no-headers | awk '$4 < $5 {print $0}'

# If pods stuck pending: check node capacity
kubectl describe nodes | grep -A 5 "Allocated resources"
```

### 2. PDB Violation (Workloads not protected)
```bash
# Check which workloads lack PDBs
for ns in $(kubectl get ns -o name | cut -d/ -f2); do
  for deploy in $(kubectl get deploy -n $ns -o name); do
    if ! kubectl get pdb -n $ns --selector=app=$(echo $deploy | cut -d/ -f2) &>/dev/null; then
      echo "Missing PDB: $ns/$deploy"
    fi
  done
done

# Fix: Apply PDB or spot tolerations
kubectl apply -f config/spot-patches/<workload>-patch.yaml
```

### 3. Termination Handler Not Working
```bash
# Check handler status
kubectl get pods -n kube-system -l app=aws-node-termination-handler

# Check handler logs for errors
kubectl logs -n kube-system -l app=aws-node-termination-handler | grep -i error

# Restart if needed
kubectl rollout restart daemonset/aws-node-termination-handler -n kube-system
```

## Recovery Steps
1. Verify spot termination notice received (2-min warning)
2. Confirm handler cordons node and drains pods
3. Check PDBs: critical workloads should have `MIN AVAILABLE` met
4. Verify new spot node joins cluster (ASG replacement)
5. Confirm pods rescheduled to new/on-demand nodes
6. Run: `make verify-v1` or `./scripts/cluster-health.sh`

## Prevention
- Weekly DR test includes spot node failure simulation
- `./scripts/cost_optimizer.py` reports spot vs on-demand ratio
- Monitor: `aws_ec2_spot_instance_interruption_warning` metric
- Quarterly: Review spot capacity optimization

## Escalation
- If >2 spot nodes lost simultaneously and PDBs violated: Failover to on-demand
- If handler down >5 min: Manual cordon/drain affected nodes
- Persistent spot capacity issues: Adjust ASG max/desired, increase on-demand base

## Related
- Spot patches: `config/spot-patches/` (7 workload patches)
- Cost optimizer: `scripts/cost_optimizer.py --spot-analysis`
- Cluster health: `scripts/cluster-health.sh`
- DR test: `scripts/disaster-recovery-test.sh --scenario spot-failure`