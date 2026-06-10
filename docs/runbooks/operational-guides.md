# Runbook: Resource Quota Management

## Overview
Resource quotas enforce namespace-level resource limits across 4 tiers (P0-P3) in 12 namespaces.

## Quota Tiers

| Tier | Namespaces | CPU Limit | Memory Limit | Storage | Pods |
|------|------------|-----------|--------------|---------|------|
| P0 Critical | apps, databases, secrets, auth, monitoring | 4 cores | 8 GiB | 100 GiB | 50 |
| P1 Important | smarthome, logging, tracing, security, uptime | 2 cores | 4 GiB | 50 GiB | 30 |
| P2 Standard | tracing, security | 1 core | 2 GiB | 20 GiB | 20 |
| P3 Optional | ai, litmus | 500m | 1 GiB | 10 GiB | 10 |

## Operations

### Check Quota Usage
```bash
# View quota usage for a namespace
kubectl describe resourcequota -n <namespace>

# View all quotas
kubectl get resourcequota -A
```

### Increase Quota (Emergency)
```bash
# Edit quota (emergency only - requires approval)
kubectl edit resourcequota <quota-name> -n <namespace>

# Or patch
kubectl patch resourcequota <quota-name> -n <namespace> \
  --patch '{"spec":{"hard":{"limits.cpu":"8"}}}'
```

### Verify LimitRange
```bash
kubectl describe limitrange -n <namespace>
```

## Troubleshooting

### Pod Stuck in Pending (Quota Exceeded)
```bash
# Check events
kubectl describe pod <pod-name> -n <namespace>

# Check quota usage
kubectl get resourcequota <quota-name> -n <namespace> -o yaml

# Check LimitRange
kubectl get limitrange -n <namespace> -o yaml
```

### Quota Exhausted - Resolution
1. Identify resource consuming quota
2. Right-size workloads (see rightsizing runbook)
3. Delete unused resources (see unused detection runbook)
4. Request quota increase with justification

## Alerting

| Alert | Condition | Severity |
|-------|-----------|----------|
| QuotaExhausted | Resource usage > 90% of quota | Warning |
| QuotaExhaustedCritical | Resource usage > 95% of quota | Critical |

---

# Runbook: Spot Instance Management (DR Cluster)

## Overview
DR cluster uses EKS Spot instances (t3.medium) with 70% cost savings.

## Architecture
- **Node Group**: spot-workers (t3.medium, capacity-optimized)
- **Labels**: `lifecycle=spot`, `workload=spot-tolerant`
- **Taints**: `dedicated=spot:NoSchedule`
- **Spot-Tolerant Workloads**: Vaultwarden, Grafana, Loki, Tempo, Prometheus, Home Assistant

## Operations

### Check Spot Node Status
```bash
# List spot nodes
kubectl get nodes -l lifecycle=spot -o wide

# Check spot termination notices
kubectl logs -n kube-system -l app=spot-termination-handler
```

### Handle Spot Termination
```bash
# 1. Spot termination handler automatically cordons node
# 2. Pods rescheduled to other nodes (via PDB minAvailable)
# 3. Verify pod rescheduling
kubectl get pods -A -o wide | grep spot

# 4. Check PDB status
kubectl get pdb -A
```

### Manual Spot Node Replacement
```bash
# If spot node doesn't recover automatically
kubectl cordon <spot-node-name>
kubectl drain <spot-node-name> --ignore-daemonsets --delete-emptydir-data
# ASG will launch replacement
```

### PDB Configuration
```yaml
# PDB for spot workloads (allow controlled disruption)
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: spot-workloads-pdb
  namespace: apps
spec:
  maxUnavailable: 50%
  selector:
    matchLabels:
      lifecycle: spot
```

## Monitoring & Alerts

| Alert | Condition | Severity |
|-------|-----------|----------|
| SpotInstanceTerminated | `increase(spot_termination_notice_total[5m]) > 0` | Warning |
| SpotCapacityLow | `count(kube_node_info{label_lifecycle="spot"}) < 2` | Warning |
| SpotWorkloadsPending | `kube_pod_status_phase{phase="Pending", label_lifecycle="spot"} > 5` | Warning |

---

# Runbook: Right-Sizing Recommendations

## Overview
Weekly automated analysis of container resource usage vs requests/limits via Prometheus + VPA.

## Components
- **Script**: `scripts/rightsizing-analyzer.py`
- **Workflow**: `.github/workflows/rightsizing-analysis.yml`
- **Schedule**: Weekly Monday 6 AM

## Operations

### Run Manual Analysis
```bash
python3 scripts/rightsizing-analyzer.py \
  --prometheus-url http://prometheus.monitoring.svc.cluster.local:9090 \
  --output rightsizing-report.md \
  --format markdown \
  --min-savings 10
```

### Review Recommendations
```bash
# View report
cat rightsizing-report.md

# Or view JSON
cat rightsizing-report.json | jq '.[] | select(.cpu_savings_percent > 20)'
```

### Apply Recommendation
```bash
# Example: Update deployment resources
kubectl patch deployment nextcloud -n apps \
  --patch '{"spec":{"template":{"spec":{"containers":[{"name":"nextcloud","resources":{"requests":{"cpu":"250m","memory":"512Mi"},"limits":{"cpu":"500m","memory":"1Gi"}}}}]}}'

# Or use VPA CR
kubectl apply -f - <<EOF
apiVersion: autoscaling.k8s.io/v1
kind: VerticalPodAutoscaler
metadata:
  name: nextcloud-vpa
  namespace: apps
spec:
  targetRef:
    apiVersion: "apps/v1"
    kind: Deployment
    name: nextcloud
  updatePolicy:
    updateMode: "Auto"
EOF
```

### Verify Changes
```bash
# Wait for rollout
kubectl rollout status deployment/nextcloud -n apps

# Verify new resources
kubectl describe pod -n apps -l app.kubernetes.io/name=nextcloud | grep -A5 "Resources:"
```

## Interpretation

| Savings | Action |
|---------|--------|
| >30% | High priority — apply immediately |
| 10-30% | Medium priority — schedule in next sprint |
| <10% | Low priority — monitor |

---

# Runbook: Unused Resource Detection

## Overview
Weekly scan for 8 categories of unused resources with PR creation for cleanup.

## Detection Categories

| Category | Check | Age Threshold |
|----------|-------|---------------|
| PVCs | Bound but unmounted | 7 days |
| Secrets | Not referenced by any pod | 7 days |
| ConfigMaps | Not referenced by any pod | 7 days |
| Services | Selector with no endpoints | 3 days |
| Ingresses | No backend rules | 3 days |
| NetworkPolicies | No matching pods | 7 days |
| HPAs | No target or no metrics | 7 days |
| RoleBindings | Reference missing role | 7 days |
| LoadBalancers | No endpoints (idle LB) | 1 day |

## Operations

### Run Manual Scan
```bash
python3 scripts/unused-resource-detector.py \
  --prometheus-url http://prometheus.monitoring.svc.cluster.local:9090 \
  --output unused-resources-report.md \
  --format markdown \
  --min-age 1
```

### Review & Cleanup

#### PVC Cleanup
```bash
# List unused PVCs
kubectl get pvc -A --field-selector=status.phase=Bound

# Delete unused PVC (after backup verification)
kubectl delete pvc <name> -n <namespace>
```

#### Secret/ConfigMap Cleanup
```bash
# Delete unused secret
kubectl delete secret <name> -n <namespace>

# Delete unused configmap
kubectl delete configmap <name> -n <namespace>
```

#### Service Cleanup
```bash
# Delete unused service
kubectl delete svc <name> -n <namespace>
```

#### LoadBalancer Cleanup
```bash
# Check for idle LBs
kubectl get svc -A -o wide | grep LoadBalancer

# Delete idle LB service
kubectl delete svc <name> -n <namespace>
```

### PR Review Checklist
- [ ] Verify resource is truly unused (check logs, metrics)
- [ ] Confirm no external dependencies
- [ ] Backup data if PVC
- [ ] Merge PR after approval

---

# Runbook: Cost Allocation & Chargeback

## Overview
Weekly cost allocation by namespace, team, and service via Prometheus metrics.

## Operations

### Generate Report
```bash
python3 scripts/cost-allocation.py \
  --prometheus-url http://prometheus.monitoring.svc.cluster.local:9090 \
  --output cost-allocation-report.md \
  --format markdown \
  --cpu-rate 30.0 \
  --memory-rate 4.0 \
  --storage-rate 0.10 \
  --lb-rate 22.0
```

### Cost Rates (Monthly)
| Resource | Rate | Unit |
|----------|------|------|
| CPU Core | $30.00 | /month |
| Memory | $4.00 | /GiB/month |
| Storage | $0.10 | /GiB/month |
| LoadBalancer | $22.00 | /month |
| Electricity (Pi) | $0.15/kWh | Local |

### Review Report
```bash
cat cost-allocation-report.md

# Or JSON for programmatic access
cat cost-allocation-report.json | jq '.by_team'
```

### Team Mapping
| Namespace | Team | Services |
|-----------|------|----------|
| apps | platform | nextcloud, vaultwarden, ollama |
| databases | data | postgresql, redis |
| secrets | security | infisical |
| auth | security | authelia |
| monitoring | platform | prometheus, grafana, alertmanager |
| logging | platform | loki, promtail |
| tracing | platform | tempo, otel |
| security | security | crowdsec, kyverno |
| smarthome | iot | homeassistant |
| uptime | platform | uptime-kuma |
| ai | ml | ollama |

---

# Runbook: Power Optimization (Pi Hardware)

## Overview
Automated Pi power optimization via systemd timer + GitHub Actions monitoring.

## Components
- **Script**: `scripts/pi-power-optimize.sh`
- **Service**: `scripts/pi-power-optimize.service`
- **Timer**: `scripts/pi-power-optimize.timer` (hourly)
- **Monitoring**: `config/grafana/provisioning/dashboards/pi-power-monitoring.json`
- **Alerts**: `config/prometheus/rules/pi-power-alerts.yaml`

## Operations

### Manual Run
```bash
sudo /usr/local/bin/pi-power-optimize.sh
```

### Check Status
```bash
# Service status
systemctl status pi-power-optimize.service

# Timer status
systemctl status pi-power-optimize.timer

# View logs
journalctl -u pi-power-optimize.service -f
```

### Verify Optimizations
```bash
# Check CPU governor
cat /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor

# Check CPU frequencies
cat /sys/devices/system/cpu/cpu*/cpufreq/scaling_max_freq
cat /sys/devices/system/cpu/cpu*/cpufreq/scaling_cur_freq

# Check ZRAM
zramctl

# Check temperature
cat /sys/class/thermal/thermal_zone0/temp
```

### Power Metrics (if INA219 connected)
```bash
# Run exporter
python3 scripts/pi-power-exporter.py --port 9090

# Query Prometheus
curl -s http://localhost:9090/metrics | grep node_power_watts
```

### Power Alerts

| Alert | Condition | Severity |
|-------|-----------|----------|
| PiHighPowerConsumption | `node_power_watts > 15` (15m) | Warning |
| PiCriticalPowerConsumption | `node_power_watts > 20` (5m) | Critical |
| PiHighTemperature | `pi_cpu_temp_C > 75` (10m) | Warning |
| PiCriticalTemperature | `pi_cpu_temp_C > 80` (5m) | Critical |
| PiHighPowerCost | `sum(node_power_watts) * 24 * 30 * 0.15 / 1000 > 50` | Warning |

---

# Runbook: Right-Sizing Analysis

## Overview
Weekly automated analysis of container resource usage vs requests/limits via Prometheus + VPA.

## Components
- **Script**: `scripts/rightsizing-analyzer.py`
- **Workflow**: `.github/workflows/rightsizing-analysis.yml`
- **Schedule**: Weekly Monday 6 AM

## Operations

### Run Manual Analysis
```bash
python3 scripts/rightsizing-analyzer.py \
  --prometheus-url http://prometheus.monitoring.svc.cluster.local:9090 \
  --output rightsizing-report.md \
  --format markdown \
  --min-savings 10
```

### Review Recommendations
```bash
# View report
cat rightsizing-report.md

# Or view JSON
cat rightsizing-report.json | jq '.[] | select(.cpu_savings_percent > 20)'
```

### Apply Recommendation
```bash
# Example: Update deployment resources
kubectl patch deployment nextcloud -n apps \
  --patch '{"spec":{"template":{"spec":{"containers":[{"name":"nextcloud","resources":{"requests":{"cpu":"250m","memory":"512Mi"},"limits":{"cpu":"500m","memory":"1Gi"}}}}]}}'

# Or use VPA CR
kubectl apply -f - <<EOF
apiVersion: autoscaling.k8s.io/v1
kind: VerticalPodAutoscaler
metadata:
  name: nextcloud-vpa
  namespace: apps
spec:
  targetRef:
    apiVersion: "apps/v1"
    kind: Deployment
    name: nextcloud
  updatePolicy:
    updateMode: "Auto"
EOF
```

### Verify Changes
```bash
# Wait for rollout
kubectl rollout status deployment/nextcloud -n apps

# Verify new resources
kubectl describe pod -n apps -l app.kubernetes.io/name=nextcloud | grep -A5 "Resources:"
```

## Interpretation

| Savings | Action |
|---------|--------|
| >30% | High priority — apply immediately |
| 10-30% | Medium priority — schedule in next sprint |
| <10% | Low priority — monitor |

---

# Runbook: Unused Resource Detection

## Overview
Weekly scan for 8 categories of unused resources with PR creation for cleanup.

## Detection Categories

| Category | Check | Age Threshold |
|----------|-------|---------------|
| PVCs | Bound but unmounted | 7 days |
| Secrets | Not referenced by any pod | 7 days |
| ConfigMaps | Not referenced by any pod | 7 days |
| Services | Selector with no endpoints | 3 days |
| Ingresses | No backend rules | 3 days |
| NetworkPolicies | No matching pods | 7 days |
| HPAs | No target or no metrics | 7 days |
| RoleBindings | Reference missing role | 7 days |
| LoadBalancers | No endpoints (idle LB) | 1 day |

## Operations

### Run Manual Scan
```bash
python3 scripts/unused-resource-detector.py \
  --prometheus-url http://prometheus.monitoring.svc.cluster.local:9090 \
  --output unused-resources-report.md \
  --format markdown \
  --min-age 1
```

### Review & Cleanup

#### PVC Cleanup
```bash
# List unused PVCs
kubectl get pvc -A --field-selector=status.phase=Bound

# Delete unused PVC (after backup verification)
kubectl delete pvc <name> -n <namespace>
```

#### Secret/ConfigMap Cleanup
```bash
# Delete unused secret
kubectl delete secret <name> -n <namespace>

# Delete unused configmap
kubectl delete configmap <name> -n <namespace>
```

#### Service Cleanup
```bash
# Delete unused service
kubectl delete svc <name> -n <namespace>
```

#### LoadBalancer Cleanup
```bash
# Check for idle LBs
kubectl get svc -A -o wide | grep LoadBalancer

# Delete idle LB service
kubectl delete svc <name> -n <namespace>
```

### PR Review Checklist
- [ ] Verify resource is truly unused (check logs, metrics)
- [ ] Confirm no external dependencies
- [ ] Backup data if PVC
- [ ] Merge PR after approval

---

# Runbook: Cost Allocation & Chargeback

## Overview
Weekly cost allocation by namespace, team, and service via Prometheus metrics.

## Operations

### Generate Report
```bash
python3 scripts/cost-allocation.py \
  --prometheus-url http://prometheus.monitoring.svc.cluster.local:9090 \
  --output cost-allocation-report.md \
  --format markdown \
  --cpu-rate 30.0 \
  --memory-rate 4.0 \
  --storage-rate 0.10 \
  --lb-rate 22.0
```

### Cost Rates (Monthly)
| Resource | Rate | Unit |
|----------|------|------|
| CPU Core | $30.00 | /month |
| Memory | $4.00 | /GiB/month |
| Storage | $0.10 | /GiB/month |
| LoadBalancer | $22.00 | /month |
| Electricity (Pi) | $0.15/kWh | Local |

### Review Report
```bash
cat cost-allocation-report.md

# Or JSON for programmatic access
cat cost-allocation-report.json | jq '.by_team'
```

### Team Mapping
| Namespace | Team | Services |
|-----------|------|----------|
| apps | platform | nextcloud, vaultwarden, ollama |
| databases | data | postgresql, redis |
| secrets | security | infisical |
| auth | security | authelia |
| monitoring | platform | prometheus, grafana, alertmanager |
| logging | platform | loki, promtail |
| tracing | platform | tempo, otel |
| security | security | crowdsec, kyverno |
| smarthome | iot | homeassistant |
| uptime | platform | uptime-kuma |
| ai | ml | ollama |

---

# Runbook: Power Optimization (Pi Hardware)

## Overview
Automated Pi power optimization via systemd timer + GitHub Actions monitoring.

## Components
- **Script**: `scripts/pi-power-optimize.sh`
- **Service**: `scripts/pi-power-optimize.service`
- **Timer**: `scripts/pi-power-optimize.timer` (hourly)
- **Monitoring**: `config/grafana/provisioning/dashboards/pi-power-monitoring.json`
- **Alerts**: `config/prometheus/rules/pi-power-alerts.yaml`

## Operations

### Manual Run
```bash
sudo /usr/local/bin/pi-power-optimize.sh
```

### Check Status
```bash
# Service status
systemctl status pi-power-optimize.service

# Timer status
systemctl status pi-power-optimize.timer

# View logs
journalctl -u pi-power-optimize.service -f
```

### Verify Optimizations
```bash
# Check CPU governor
cat /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor

# Check CPU frequencies
cat /sys/devices/system/cpu/cpu*/cpufreq/scaling_max_freq
cat /sys/devices/system/cpu/cpu*/cpufreq/scaling_cur_freq

# Check ZRAM
zramctl

# Check temperature
cat /sys/class/thermal/thermal_zone0/temp
```

### Power Metrics (if INA219 connected)
```bash
# Run exporter
python3 scripts/pi-power-exporter.py --port 9090

# Query Prometheus
curl -s http://localhost:9090/metrics | grep node_power_watts
```

### Power Alerts

| Alert | Condition | Severity |
|-------|-----------|----------|
| PiHighPowerConsumption | `node_power_watts > 15` (15m) | Warning |
| PiCriticalPowerConsumption | `node_power_watts > 20` (5m) | Critical |
| PiHighTemperature | `pi_cpu_temp_C > 75` (10m) | Warning |
| PiCriticalTemperature | `pi_cpu_temp_C > 80` (5m) | Critical |
| PiHighPowerCost | `sum(node_power_watts) * 24 * 30 * 0.15 / 1000 > 50` | Warning |