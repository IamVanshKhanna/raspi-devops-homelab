# LitmusChaos for Homelab

LitmusChaos provides cloud-native chaos engineering for Kubernetes. This directory contains chaos experiments, workflows, and RBAC configurations for the homelab cluster.

## Overview

LitmusChaos enables:
- **Pod-level failures**: Kill, CPU/memory stress, network latency/loss
- **Node-level failures**: Drain, reboot, taint
- **Infrastructure failures**: Disk fill, DNS failure, time skew
- **Application-level failures**: HTTP error codes, latency injection
- **Scheduled chaos**: Automated experiments via Argo Workflows
- **Observability**: Prometheus metrics, Grafana dashboards

## Installation

```bash
# Install via Helmfile
helmfile -l name=litmus sync

# Or manually
kubectl create namespace litmus
kubectl apply -f config/litmus/rbac*.yaml
kubectl apply -f config/litmus/chaos-experiments/
```

## Chaos Experiments

### Available Experiments

| Experiment | Description | Target | Duration |
|------------|-------------|--------|----------|
| `pod-delete` | Random pod termination | Apps (nextcloud, vaultwarden, etc.) | 30s |
| `pod-cpu-hog` | CPU stress (1 core) | Apps | 60s |
| `pod-memory-hog` | Memory stress (500Mi) | Apps | 60s |
| `pod-network-latency` | 1000ms latency + 100ms jitter | Apps | 60s |
| `pod-network-loss` | 50% packet loss | Apps | 60s |
| `node-drain` | Drain worker node | node-2 | 120s |
| `disk-fill` | Fill 80% of ephemeral storage | Apps | 60s |

### Running Experiments Manually

```bash
# Run pod-delete experiment
kubectl apply -f config/litmus/chaos-experiments/pod-delete.yaml

# Watch chaos engine
kubectl get chaosengine -n litmus -w

# Check results
kubectl get chaosresult -n litmus

# View experiment logs
kubectl logs -n litmus -l chaosengine=pod-delete-engine -c chaos
```

### Running via Argo Workflows

```bash
# Submit scheduled chaos workflow
argo submit -n argocd config/litmus/chaos-workflows/scheduled-chaos.yaml

# Or use ArgoCD UI to sync the 'litmus' application
```

## Configuration

### Targeting Different Applications

Edit the `applabel` in experiment files:

```yaml
appinfo:
  appns: "apps"
  applabel: "app.kubernetes.io/name=vaultwarden"
```

### Adjusting Intensity

Modify experiment parameters:

```yaml
components:
  env:
    - name: PODS_AFFECTED_PERC
      value: "100"  # Affect all pods (default: 50%)
    - name: TOTAL_CHAOS_DURATION
      value: "120"  # Longer duration
```

## Safety Guidelines

1. **Always run in staging first** - Test experiments in non-production namespaces
2. **Start small** - Begin with `PODS_AFFECTED_PERC: 25%` or lower
3. **Monitor closely** - Watch Grafana dashboards and alerts during experiments
4. **Have rollback ready** - Ensure ArgoCD auto-sync can recover workloads
5. **Run during maintenance windows** - Avoid peak usage times
6. **Document findings** - Record expected vs actual behavior

## Observability

### Prometheus Metrics

```promql
# Experiment status
litmus_experiment_status{experiment="pod-delete"}

# Pod kill count
increase(litmus_pod_kill_total[5m])

# CPU hog active
litmus_cpu_hog_active{namespace="apps"}

# Network latency injected
litmus_network_latency_ms{experiment="pod-network-latency"}
```

### Grafana Dashboard

Import dashboard from: `config/litmus/dashboards/litmus-chaos.json`

Key panels:
- Experiment success/failure rate
- Affected pods over time
- Resource consumption during chaos
- Recovery time measurements

## Scheduled Chaos

The `scheduled-chaos.yaml` workflow runs:
1. Pod delete (daily)
2. CPU hog (weekly)
3. Memory hog (weekly)
4. Network latency (monthly)
5. Node drain (quarterly - manual approval)

### CronJob Alternative

```yaml
# config/litmus/cronjob.yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: weekly-chaos
  namespace: litmus
spec:
  schedule: "0 2 * * 0"  # Weekly Sunday 2 AM
  jobTemplate:
    spec:
      template:
        spec:
          serviceAccountName: litmus-admin
          containers:
          - name: chaos-runner
            image: litmuschaos/litmus-checker:latest
            command: ["kubectl", "apply", "-f", "/experiments/"]
            volumeMounts:
            - name: experiments
              mountPath: /experiments
          volumes:
          - name: experiments
            configMap:
              name: litmus-experiments
          restartPolicy: OnFailure
```

## Troubleshooting

| Issue | Check | Resolution |
|-------|-------|------------|
| Experiment stuck | `kubectl describe chaosengine` | Check RBAC, pod scheduling |
| No chaos pods | `kubectl get pods -n litmus` | Verify operator running |
| Metrics missing | `kubectl get servicemonitor -n monitoring` | Check Prometheus config |
| Argo workflow fails | `argo logs -n argocd <workflow>` | Check service account perms |

## Useful Commands

```bash
# List all chaos experiments
kubectl get chaosexperiments -n litmus

# List chaos engines
kubectl get chaosengine -n litmus

# Get detailed result
kubectl get chaosresult -n litmus -o yaml

# Clean up completed experiments
kubectl delete chaosengine --all -n litmus

# View Argo workflow
argo get -n argocd @latest
```

## References

- [LitmusChaos Docs](https://litmuschaos.io/docs/)
- [Chaos Experiments Catalog](https://hub.litmuschaos.io/)
- [Argo Workflows](https://argoproj.github.io/argo-workflows/)
- [Homelab Runbooks](../runbooks/)