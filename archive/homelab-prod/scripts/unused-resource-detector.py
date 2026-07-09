#!/usr/bin/env python3
"""
Unused Resource Detection
Detects and reports unused Kubernetes resources to optimize costs.
"""

import json
import subprocess
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from collections import defaultdict

@dataclass
class UnusedResource:
    resource_type: str
    name: str
    namespace: str
    reason: str
    age_days: int
    estimated_monthly_cost: float
    recommendation: str

class UnusedResourceDetector:
    def __init__(self, prometheus_url: str = "http://prometheus.monitoring.svc.cluster.local:9090"):
        self.prometheus_url = prometheus_url
    
    def run_kubectl(self, args: List[str]) -> Dict:
        """Run kubectl command and return JSON"""
        cmd = ["kubectl"] + args
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if result.returncode != 0:
            raise Exception(f"kubectl failed: {result.stderr}")
        return json.loads(result.stdout)
    
    def query_prometheus(self, query: str) -> Dict:
        """Query Prometheus API"""
        response = requests.get(
            f"{self.prometheus_url}/api/v1/query",
            params={"query": query},
            timeout=30
        )
        response.raise_for_status()
        return response.json()
    
    def get_unused_pvcs(self) -> List[UnusedResource]:
        """Detect unused PersistentVolumeClaims"""
        unused = []
        
        # Get all PVCs
        pvcs = self.run_kubectl(["get", "pvc", "-A", "-o", "json"])
        
        # Get pods and their PVC usage
        pods = self.run_kubectl(["get", "pods", "-A", "-o", "json"])
        
        # Build PVC usage map
        pvc_usage = set()
        for pod in pods.get("items", []):
            ns = pod["metadata"]["namespace"]
            for volume in pod["spec"].get("volumes", []):
                if "persistentVolumeClaim" in volume:
                    claim_name = volume["persistentVolumeClaim"]["claimName"]
                    pvc_usage.add(f"{ns}/{claim_name}")
        
        for pvc in pvcs.get("items", []):
            ns = pvc["metadata"]["namespace"]
            name = pvc["metadata"]["name"]
            key = f"{ns}/{name}"
            
            # Check if PVC is bound
            phase = pvc["status"].get("phase", "")
            
            if phase != "Bound":
                age_days = self._calculate_age(pvc["metadata"].get("creationTimestamp", ""))
                unused.append(UnusedResource(
                    resource_type="PersistentVolumeClaim",
                    name=name,
                    namespace=ns,
                    reason=f"PVC not bound (phase: {phase})",
                    age_days=age_days,
                    estimated_monthly_cost=self._estimate_pvc_cost(pvc),
                    recommendation="Delete if not needed, or fix binding issue"
                ))
            elif key not in pvc_usage:
                # PVC is bound but not mounted by any pod
                age_days = self._calculate_age(pvc["metadata"].get("creationTimestamp", ""))
                unused.append(UnusedResource(
                    resource_type="PersistentVolumeClaim",
                    name=name,
                    namespace=ns,
                    reason="PVC bound but not mounted by any pod",
                    age_days=age_days,
                    estimated_monthly_cost=self._estimate_pvc_cost(pvc),
                    recommendation="Delete PVC and PV if data not needed, or attach to workload"
                ))
        
        return unused
    
    def get_unused_secrets_configmaps(self) -> List[UnusedResource]:
        """Detect unused Secrets and ConfigMaps"""
        unused = []
        
        # Get pods to find referenced secrets/configmaps
        pods = self.run_kubectl(["get", "pods", "-A", "-o", "json"])
        
        used_secrets = set()
        used_configmaps = set()
        
        for pod in pods.get("items", []):
            ns = pod["metadata"]["namespace"]
            
            # Check volumes
            for volume in pod["spec"].get("volumes", []):
                if "secret" in volume:
                    used_secrets.add(f"{ns}/{volume['secret']['secretName']}")
                if "configMap" in volume:
                    used_configmaps.add(f"{ns}/{volume['configMap']['name']}")
            
            # Check envFrom
            for container in pod["spec"].get("containers", []):
                for env_from in container.get("envFrom", []):
                    if "secretRef" in env_from:
                        used_secrets.add(f"{ns}/{env_from['secretRef']['name']}")
                    if "configMapRef" in env_from:
                        used_configmaps.add(f"{ns}/{env_from['configMapRef']['name']}")
        
        # Check Secrets
        secrets = self.run_kubectl(["get", "secrets", "-A", "-o", "json"])
        for secret in secrets.get("items", []):
            ns = secret["metadata"]["namespace"]
            name = secret["metadata"]["name"]
            key = f"{ns}/{name}"
            
            # Skip system secrets
            if secret["type"] in ["kubernetes.io/service-account-token", "kubernetes.io/dockercfg"]:
                continue
            
            if key not in used_secrets and secret["type"] != "kubernetes.io/tls":
                age_days = self._calculate_age(secret["metadata"].get("creationTimestamp", ""))
                if age_days > 7:  # Only report if older than 7 days
                    unused.append(UnusedResource(
                        resource_type="Secret",
                        name=name,
                        namespace=ns,
                        reason=f"Secret not referenced by any pod (type: {secret['type']})",
                        age_days=age_days,
                        estimated_monthly_cost=0.01,  # Negligible
                        recommendation="Delete if not needed, or verify if referenced externally"
                    ))
        
        # Check ConfigMaps
        configmaps = self.run_kubectl(["get", "configmaps", "-A", "-o", "json"])
        for cm in configmaps.get("items", []):
            ns = cm["metadata"]["namespace"]
            name = cm["metadata"]["name"]
            key = f"{ns}/{name}"
            
            # Skip system configmaps
            if name.startswith("kube-root-ca.crt") or name.startswith("kubeadmin-"):
                continue
            
            if key not in used_configmaps:
                age_days = self._calculate_age(cm["metadata"].get("creationTimestamp", ""))
                if age_days > 7:
                    unused.append(UnusedResource(
                        resource_type="ConfigMap",
                        name=name,
                        namespace=ns,
                        reason="ConfigMap not referenced by any pod",
                        age_days=age_days,
                        estimated_monthly_cost=0.01,
                        recommendation="Delete if not needed, or verify external references"
                    ))
        
        return unused
    
    def get_unused_services(self) -> List[UnusedResource]:
        """Detect unused Services"""
        unused = []
        
        # Get all services
        services = self.run_kubectl(["get", "svc", "-A", "-o", "json"])
        
        # Get endpoints
        endpoints = self.run_kubectl(["get", "endpoints", "-A", "-o", "json"])
        
        # Build endpoint map
        endpoint_map = {}
        for ep in endpoints.get("items", []):
            ns = ep["metadata"]["namespace"]
            name = ep["metadata"]["name"]
            has_endpoints = len(ep.get("subsets", [])) > 0 and any(s.get("addresses", []) for s in ep.get("subsets", []))
            if has_endpoints:
                endpoint_map[f"{ns}/{name}"] = True
        
        for svc in services.get("items", []):
            ns = svc["metadata"]["namespace"]
            name = svc["metadata"]["name"]
            key = f"{ns}/{name}"
            
            # Skip system services
            if name == "kubernetes" or ns == "kube-system":
                continue
            
            # Check if headless service (no clusterIP)
            if svc["spec"].get("clusterIP") == "None":
                # Headless services don't have endpoints in the same way
                continue
            
            # Check if service has selector
            selector = svc["spec"].get("selector", {})
            if not selector:
                # ExternalName or manual service
                continue
            
            # Check if service has endpoints
            if key not in endpoint_map:
                age_days = self._calculate_age(svc["metadata"].get("creationTimestamp", ""))
                if age_days > 3:
                    unused.append(UnusedResource(
                        resource_type="Service",
                        name=name,
                        namespace=ns,
                        reason="Service has selector but no matching pods (no endpoints)",
                        age_days=age_days,
                        estimated_monthly_cost=0.05,  # Negligible
                        recommendation="Check if selector matches any pods, or delete service"
                    ))
        
        return unused
    
    def get_unused_ingresses(self) -> List[UnusedResource]:
        """Detect unused Ingresses"""
        unused = []
        
        ingresses = self.run_kubectl(["get", "ingress", "-A", "-o", "json"])
        
        for ing in ingresses.get("items", []):
            ns = ing["metadata"]["namespace"]
            name = ing["metadata"]["name"]
            
            # Check if ingress has rules and backend services
            has_backend = False
            for rule in ing["spec"].get("rules", []):
                if "http" in rule:
                    for path in rule["http"].get("paths", []):
                        if "backend" in path:
                            has_backend = True
                            break
            
            if not has_backend:
                age_days = self._calculate_age(ing["metadata"].get("creationTimestamp", ""))
                if age_days > 3:
                    unused.append(UnusedResource(
                        resource_type="Ingress",
                        name=name,
                        namespace=ns,
                        reason="Ingress has no backend rules defined",
                        age_days=age_days,
                        estimated_monthly_cost=0.02,
                        recommendation="Add backend rules or delete Ingress"
                    ))
        
        return unused
    
    def get_unused_networkpolicies(self) -> List[UnusedResource]:
        """Detect unused NetworkPolicies"""
        unused = []
        
        networkpolicies = self.run_kubectl(["get", "networkpolicies", "-A", "-o", "json"])
        
        # Get all pods and their labels
        pods = self.run_kubectl(["get", "pods", "-A", "-o", "json"])
        
        # Build pod label map per namespace
        ns_pod_labels = defaultdict(set)
        for pod in pods.get("items", []):
            ns = pod["metadata"]["namespace"]
            labels = pod["metadata"].get("labels", {})
            for k, v in labels.items():
                ns_pod_labels[ns].add(f"{k}={v}")
        
        for np in networkpolicies.get("items", []):
            ns = np["metadata"]["namespace"]
            name = np["metadata"]["name"]
            
            # Check if policy selects any pods
            pod_selector = np["spec"].get("podSelector", {})
            match_labels = pod_selector.get("matchLabels", {})
            match_expressions = pod_selector.get("matchExpressions", [])
            
            # Check if any pod matches
            has_matching_pods = False
            if not match_labels and not match_expressions:
                # Empty selector matches all pods in namespace
                has_matching_pods = len(ns_pod_labels[ns]) > 0
            else:
                for pod_labels in ns_pod_labels[ns]:
                    # Simplified match check
                    if all(pod_labels.get(k) == v for k, v in match_labels.items()):
                        has_matching_pods = True
                        break
            
            if not has_matching_pods:
                age_days = self._calculate_age(np["metadata"].get("creationTimestamp", ""))
                if age_days > 7:
                    unused.append(UnusedResource(
                        resource_type="NetworkPolicy",
                        name=name,
                        namespace=ns,
                        reason="NetworkPolicy selects no pods (no matching labels)",
                        age_days=age_days,
                        estimated_monthly_cost=0.01,
                        recommendation="Update podSelector to match existing pods, or delete policy"
                    ))
        
        return unused
    
    def get_unused_hpa(self) -> List[UnusedResource]:
        """Detect unused/ineffective HPAs"""
        unused = []
        
        hpas = self.run_kubectl(["get", "hpa", "-A", "-o", "json"])
        
        for hpa in hpas.get("items", []):
            ns = hpa["metadata"]["namespace"]
            name = hpa["metadata"]["name"]
            
            # Check if target exists
            target_ref = hpa["spec"].get("scaleTargetRef", {})
            target_kind = target_ref.get("kind", "")
            target_name = target_ref.get("name", "")
            
            # Check if target exists
            target_exists = False
            try:
                if target_kind == "Deployment":
                    self.run_kubectl(["get", "deployment", target_name, "-n", ns])
                    target_exists = True
                elif target_kind == "StatefulSet":
                    self.run_kubectl(["get", "statefulset", target_name, "-n", ns])
                    target_exists = True
            except:
                pass
            
            if not target_exists:
                unused.append(UnusedResource(
                    resource_type="HorizontalPodAutoscaler",
                    name=name,
                    namespace=ns,
                    reason=f"HPA target {target_kind}/{target_name} does not exist",
                    age_days=self._calculate_age(hpa["metadata"].get("creationTimestamp", "")),
                    estimated_monthly_cost=0.0,
                    recommendation="Delete HPA or create target resource"
                ))
                continue
            
            # Check if HPA has metrics configured
            metrics = hpa["spec"].get("metrics", [])
            if not metrics:
                unused.append(UnusedResource(
                    resource_type="HorizontalPodAutoscaler",
                    name=name,
                    namespace=ns,
                    reason="HPA has no metrics configured",
                    age_days=self._calculate_age(hpa["metadata"].get("creationTimestamp", "")),
                    estimated_monthly_cost=0.0,
                    recommendation="Add metrics or delete HPA"
                ))
        
        return unused
    
    def get_unused_roles_bindings(self) -> List[UnusedResource]:
        """Detect unused Roles/RoleBindings and ClusterRoles/ClusterRoleBindings"""
        unused = []
        
        # Check RoleBindings
        rolebindings = self.run_kubectl(["get", "rolebindings", "-A", "-o", "json"])
        
        # Get all subjects referenced
        for rb in rolebindings.get("items", []):
            ns = rb["metadata"]["namespace"]
            name = rb["metadata"]["name"]
            
            # Check if role exists
            role_ref = rb.get("roleRef", {})
            role_kind = role_ref.get("kind", "")
            role_name = role_ref.get("name", "")
            
            role_exists = False
            try:
                if role_kind == "Role":
                    self.run_kubectl(["get", "role", role_name, "-n", ns])
                    role_exists = True
                elif role_kind == "ClusterRole":
                    self.run_kubectl(["get", "clusterrole", role_name])
                    role_exists = True
            except:
                pass
            
            if not role_exists:
                unused.append(UnusedResource(
                    resource_type="RoleBinding",
                    name=name,
                    namespace=ns,
                    reason=f"References non-existent {role_kind}: {role_name}",
                    age_days=self._calculate_age(rb["metadata"].get("creationTimestamp", "")),
                    estimated_monthly_cost=0.0,
                    recommendation="Delete RoleBinding or create referenced Role/ClusterRole"
                ))
        
        # Check ClusterRoleBindings
        clusterrolebindings = self.run_kubectl(["get", "clusterrolebindings", "-o", "json"])
        
        for crb in clusterrolebindings.get("items", []):
            name = crb["metadata"]["name"]
            role_ref = crb.get("roleRef", {})
            role_name = role_ref.get("name", "")
            
            role_exists = False
            try:
                self.run_kubectl(["get", "clusterrole", role_name])
                role_exists = True
            except:
                pass
            
            if not role_exists:
                unused.append(UnusedResource(
                    resource_type="ClusterRoleBinding",
                    name=name,
                    namespace="cluster",
                    reason=f"References non-existent ClusterRole: {role_name}",
                    age_days=self._calculate_age(crb["metadata"].get("creationTimestamp", "")),
                    estimated_monthly_cost=0.0,
                    recommendation="Delete ClusterRoleBinding or create referenced ClusterRole"
                ))
        
        return unused
    
    def get_idle_loadbalancers(self) -> List[UnusedResource]:
        """Detect idle LoadBalancer services (cloud cost)"""
        unused = []
        
        services = self.run_kubectl(["get", "svc", "-A", "-o", "json"])
        
        for svc in services.get("items", []):
            if svc["spec"].get("type") == "LoadBalancer":
                ns = svc["metadata"]["namespace"]
                name = svc["metadata"]["name"]
                
                # Check if LB has active endpoints
                endpoints = self.run_kubectl(["get", "endpoints", name, "-n", ns, "-o", "json"])
                
                has_endpoints = False
                for subset in endpoints.get("subsets", []):
                    if subset.get("addresses"):
                        has_endpoints = True
                        break
                
                if not has_endpoints:
                    age_days = self._calculate_age(svc["metadata"].get("creationTimestamp", ""))
                    if age_days > 1:
                        # Estimate LB cost (~$20-25/month on AWS/GCP)
                        unused.append(UnusedResource(
                            resource_type="Service (LoadBalancer)",
                            name=name,
                            namespace=ns,
                            reason="LoadBalancer service has no endpoints (idle)",
                            age_days=age_days,
                            estimated_monthly_cost=22.0,  # ~$22/month for AWS NLB
                            recommendation="Delete service or ensure target pods are running"
                        ))
        
        return unused
    
    def _calculate_age(self, timestamp: str) -> int:
        """Calculate age in days from timestamp"""
        if not timestamp:
            return 0
        try:
            created = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            return (datetime.now(created.tzinfo) - created).days
        except:
            return 0
    
    def _estimate_pvc_cost(self, pvc: Dict) -> float:
        """Estimate monthly cost of PVC"""
        storage = pvc["spec"].get("resources", {}).get("requests", {}).get("storage", "0")
        # Parse storage
        try:
            if storage.endswith("Gi"):
                gib = float(storage[:-2])
            elif storage.endswith("Ti"):
                gib = float(storage[:-2]) * 1024
            else:
                gib = 0
            # Estimate: $0.10/GB/month for standard storage
            return gib * 0.10
        except:
            return 0.05
    
    def run_all_checks(self) -> Dict[str, List[UnusedResource]]:
        """Run all unused resource checks"""
        print("Running unused resource detection...")
        
        all_unused = {}
        
        checks = [
            ("unused_pvcs", self.get_unused_pvcs),
            ("unused_secrets_configmaps", self.get_unused_secrets_configmaps),
            ("unused_services", self.get_unused_services),
            ("unused_ingresses", self.get_unused_ingresses),
            ("unused_networkpolicies", self.get_unused_networkpolicies),
            ("unused_hpa", self.get_unused_hpa),
            ("unused_roles_bindings", self.get_unused_roles_bindings),
            ("idle_loadbalancers", self.get_idle_loadbalancers),
        ]
        
        total_unused = 0
        total_cost = 0.0
        
        for check_name, check_func in checks:
            try:
                print(f"Running {check_name}...")
                results = check_func()
                all_unused[check_name] = results
                total_unused += len(results)
                total_cost += sum(r.estimated_monthly_cost for r in results)
                print(f"  Found {len(results)} unused resources")
            except Exception as e:
                print(f"  Error in {check_name}: {e}")
        
        print(f"\nTotal unused resources: {total_unused}")
        print(f"Estimated monthly cost savings: ${total_cost:.2f}")
        
        return all_unused

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Unused Resource Detection")
    parser.add_argument("--prometheus-url", default="http://prometheus.monitoring.svc.cluster.local:9090")
    parser.add_argument("--output", default="unused-resources-report.json")
    parser.add_argument("--format", choices=["json", "csv", "markdown"], default="json")
    parser.add_argument("--min-age", type=int, default=1, help="Minimum age in days to report")
    args = parser.parse_args()
    
    detector = UnusedResourceDetector(prometheus_url=args.prometheus_url)
    all_unused = detector.run_all_checks()
    
    # Filter by minimum age
    for key, resources in all_unused.items():
        all_unused[key] = [r for r in resources if r.age_days >= args.min_age]
    
    # Output
    if args.format == "json":
        output = {k: [asdict(r) for r in v] for k, v in all_unused.items()}
        with open(args.output, "w") as f:
            json.dump(output, f, indent=2)
    elif args.format == "csv":
        import csv
        with open(args.output, "w") as f:
            writer = csv.writer(f)
            writer.writerow(["Type", "Name", "Namespace", "Reason", "Age (days)", "Est. Monthly Cost", "Recommendation"])
            for resources in all_unused.values():
                for r in resources:
                    writer.writerow([r.resource_type, r.name, r.namespace, r.reason, r.age_days, r.estimated_monthly_cost, r.recommendation])
    elif args.format == "markdown":
        with open(args.output, "w") as f:
            f.write("# Unused Resources Report\n\n")
            f.write(f"Generated: {datetime.utcnow().isoformat()}Z\n\n")
            
            total_cost = 0.0
            total_count = 0
            
            for check_name, resources in all_unused.items():
                if not resources:
                    continue
                
                f.write(f"## {check_name.replace('_', ' ').title()} ({len(resources)})\n\n")
                f.write("| Type | Name | Namespace | Reason | Age (days) | Est. Monthly Cost | Recommendation |\n")
                f.write("|------|------|-----------|--------|------------|------------------|----------------|\n")
                for r in resources:
                    f.write(f"| {r.resource_type} | {r.name} | {r.namespace} | {r.reason} | {r.age_days} | ${r.estimated_monthly_cost:.2f} | {r.recommendation} |\n")
                    total_cost += r.estimated_monthly_cost
                    total_count += 1
                f.write("\n")
            
            f.write(f"\n**Summary:** {total_count} unused resources, estimated ${total_cost:.2f}/month savings\n")
    
    print(f"Report saved to {args.output}")

if __name__ == "__main__":
    main()