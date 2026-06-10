# Runbook: Unused Resource Accumulation

## Detection
- Weekly GitHub Actions workflow "Unused Resource Detection" creates issue/PR
- `./scripts/unused-resource-detector.py` outputs findings
- Grafana dashboard "Unused Resources" shows accumulating items
- Manual check reveals stale PVCs, Secrets, Services, etc.

## Diagnosis
```bash
# Run detector manually (8 categories)
./scripts/unused-resource-detector.py --all-categories --output json > unused.json

# View results
cat unused.json | jq '.[] | {category, count, resources}'

# Individual category checks:
# PVCs not bound to pods
kubectl get pvc -A -o custom-columns="NS:.metadata.namespace,NAME:.metadata.name,STATUS:.status.phase,BOUND:.spec.volumeName" | grep -v Bound

# Secrets not referenced by pods/SA
kubectl get secrets -A --field-selector=type!=kubernetes.io/service-account-token

# Services without endpoints
kubectl get svc -A -o custom-columns="NS:.metadata.namespace,NAME:.metadata.name,ENDPOINTS:.status.loadBalancer.ingress" | grep '<none>'

# Ingresses without backend services
kubectl get ingress -A

# NetworkPolicies not selecting pods
kubectl get networkpolicy -A -o yaml | grep -A 5 podSelector

# HPAs not targeting existing deployments
kubectl get hpa -A -o custom-columns="NS:.metadata.namespace,NAME:.metadata.name,TARGET:.spec.scaleTargetRef.name"

# Roles/RoleBindings without subjects
kubectl get role,rolebinding -A
```

## v2.10 Unused Detection (8 Categories)
| Category | Check | Cleanup Action |
|----------|-------|----------------|
| PVCs | Unbound > 7 days | Delete if no backup needed |
| Secrets | Unreferenced > 30 days | Delete (verify not in external-secrets) |
| Services | No endpoints > 7 days | Delete |
| Ingresses | No backend service | Delete |
| NetworkPolicies | No matching pods | Delete |
| HPAs | Target missing | Delete |
| Roles | No bindings | Delete |
| LBs | No backing service | Delete |

## Common Causes & Fixes

### 1. Stale PVCs (Post-delete of StatefulSet)
```bash
# Find PVCs with no matching pod
for pvc in $(kubectl get pvc -A -o jsonpath='{range .items[*]}{.metadata.namespace}/{.metadata.name} {.spec.volumeName}{"\n"}{end}'); do
  ns=$(echo $pvc | cut -d' ' -f1 | cut -d/ -f1)
  name=$(echo $pvc | cut -d' ' -f1 | cut -d/ -f2)
  if ! kubectl get pv $(echo $pvc | cut -d' ' -f2) -o jsonpath='{.spec.claimRef.name}' 2>/dev/null | grep -q $name; then
    echo "Orphaned: $ns/$name"
  fi
done

# Fix: Delete if confirmed unused
kubectl delete pvc <name> -n <namespace>
```

### 2. Orphaned Secrets (ExternalSecrets / rotated)
```bash
# Find secrets not mounted by any pod
./scripts/unused-resource-detector.py --category secrets --dry-run

# Fix: Delete after confirming not in ExternalSecret store
kubectl delete secret <name> -n <namespace>
```

### 3. Accumulated NetworkPolicies
```bash
# Find policies selecting non-existent pods
kubectl get networkpolicy -A -o json | jq -r '.items[] | select(.spec.podSelector.matchLabels | length > 0) | "\(.metadata.namespace)/\(.metadata.name) \(.spec.podSelector.matchLabels | tostring)"' | while read ns name labels; do
  if ! kubectl get pods -n $ns -l "$labels" --no-headers 2>/dev/null | grep -q .; then
    echo "Unused NetworkPolicy: $ns/$name"
  fi
done
```

## Recovery Steps
1. Run detector: `./scripts/unused-resource-detector.py --all-categories`
2. Review output / weekly GitHub issue
3. For each resource:
   - Confirm truly unused (check logs, backups, external refs)
   - Delete: `kubectl delete <type> <name> -n <ns>`
   - Document in PR/issue
4. Verify no regressions: `make verify-v1`

## Prevention
- Weekly automated scan (GitHub Actions)
- TTL labels on resources: `cleanup.homelab/ttl: "7d"`
- ArgoCD prune: Enable `prune: true` in ApplicationSet
- CI gate: Fail if new resources created without ownerReferences

## Escalation
- If detector reports 50+ unused items: Schedule cleanup sprint
- If critical resource deleted by mistake: Restore from Velero backup
- Persistent accumulation: Audit resource creation workflows

## Related
- Detector: `scripts/unused-resource-detector.py`
- GitHub workflow: `.github/workflows/unused-resource-detection.yml`
- Velero backup: `make backup` / `./scripts/replicate-restic.sh`