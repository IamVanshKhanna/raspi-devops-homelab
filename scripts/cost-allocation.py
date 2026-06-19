#!/usr/bin/env python3
"""
Cost Allocation and Chargeback Reporting
Generates detailed cost breakdown by namespace, team, and service.
"""

import json
import subprocess
import requests
import csv
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from collections import defaultdict

@dataclass
class CostAllocation:
    namespace: str
    team: str
    service: str
    cpu_cores: float
    memory_gib: float
    storage_gib: float
    load_balancer_count: int
    cpu_cost: float
    memory_cost: float
    storage_cost: float
    lb_cost: float
    total_monthly_cost: float
    cpu_percent: float
    memory_percent: float
    storage_percent: float
    lb_percent: float

class CostAllocationAnalyzer:
    def __init__(self, prometheus_url: str = "http://prometheus.monitoring.svc.cluster.local:9090"):
        self.prometheus_url = prometheus_url
        
        # Cost rates (adjust based on your cloud provider)
        self.rates = {
            "cpu_per_core_month": 30.0,      # $30 per vCPU/month
            "memory_per_gib_month": 4.0,     # $4 per GiB/month
            "storage_per_gib_month": 0.10,   # $0.10 per GiB/month
            "load_balancer_per_month": 22.0, # $22 per LB/month (AWS NLB)
        }
        
        # Team mapping by namespace (Docker Compose on single Pi)
        self.namespace_teams = {
            "apps": "platform",
            "databases": "data",
            "secrets": "security",
            "auth": "security",
            "monitoring": "platform",
            "logging": "platform",
            "tracing": "platform",
            "security": "security",
            "smarthome": "iot",
            "uptime": "platform",
            "traefik": "platform",
            "network": "platform",
        }
        
        # Service mapping by namespace (Docker Compose on single Pi)
        self.namespace_services = {
            "apps": ["nextcloud", "vaultwarden"],
            "databases": ["mariadb", "redis"],
            "secrets": ["infisical"],
            "auth": ["authelia"],
            "monitoring": ["prometheus", "grafana", "alertmanager"],
            "logging": ["loki", "promtail"],
            "tracing": ["tempo", "otel-collector"],
            "security": ["crowdsec"],
            "smarthome": ["homeassistant"],
            "uptime": ["uptime-kuma"],
            "traefik": ["traefik"],
            "network": ["pihole", "wireguard"],
        }
    
    def run_kubectl(self, args: List[str]) -> Dict:
        cmd = ["kubectl"] + args
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if result.returncode != 0:
            raise Exception(f"kubectl failed: {result.stderr}")
        return json.loads(result.stdout)
    
    def query_prometheus(self, query: str) -> Dict:
        response = requests.get(
            f"{self.prometheus_url}/api/v1/query",
            params={"query": query},
            timeout=30
        )
        response.raise_for_status()
        return response.json()
    
    def get_namespace_resources(self) -> Dict[str, Dict]:
        """Get resource usage per namespace from Prometheus"""
        namespaces = {}
        
        # CPU usage per namespace (cores)
        cpu_query = 'sum by (namespace) (rate(container_cpu_usage_seconds_total[5m]))'
        cpu_result = self.query_prometheus(cpu_query)
        
        # Memory usage per namespace (GiB)
        mem_query = 'sum by (namespace) (container_memory_working_set_bytes) / 1024 / 1024 / 1024'
        mem_result = self.query_prometheus(mem_query)
        
        # Storage per namespace (GiB) - from PVCs
        storage_query = 'sum by (namespace) (kubelet_volume_stats_used_bytes) / 1024 / 1024 / 1024'
        storage_result = self.query_prometheus(storage_query)
        
        # Load balancers per namespace
        lb_query = 'sum by (namespace) (kube_service_info{type="LoadBalancer"})'
        lb_result = self.prometheus(lb_query)
        
        # Parse CPU
        for item in cpu_result.get("data", {}).get("result", []):
            ns = item["metric"].get("namespace", "")
            value = float(item["value"][1])
            if ns not in namespaces:
                namespaces[ns] = {"cpu_cores": 0, "memory_gib": 0, "storage_gib": 0, "lb_count": 0}
            namespaces[ns]["cpu_cores"] = value
        
        # Parse Memory
        for item in mem_result.get("data", {}).get("result", []):
            ns = item["metric"].get("namespace", "")
            value = float(item["value"][1])
            if ns not in namespaces:
                namespaces[ns] = {"cpu_cores": 0, "memory_gib": 0, "storage_gib": 0, "lb_count": 0}
            namespaces[ns]["memory_gib"] = value
        
        # Parse Storage
        for item in storage_result.get("data", {}).get("result", []):
            ns = item["metric"].get("namespace", "")
            value = float(item["value"][1])
            if ns not in namespaces:
                namespaces[ns] = {"cpu_cores": 0, "memory_gib": 0, "storage_gib": 0, "lb_count": 0}
            namespaces[ns]["storage_gib"] = value
        
        # Parse Load Balancers
        for item in lb_result.get("data", {}).get("result", []):
            ns = item["metric"].get("namespace", "")
            value = float(item["value"][1])
            if ns not in namespaces:
                namespaces[ns] = {"cpu_cores": 0, "memory_gib": 0, "storage_gib": 0, "lb_count": 0}
            namespaces[ns]["lb_count"] = int(value)
        
        # Filter out system namespaces
        system_ns = ["kube-system", "kube-public", "kube-node-lease"]
        for ns in list(namespaces.keys()):
            if ns in system_ns:
                del namespaces[ns]
        
        return namespaces
    
    def get_pod_resources(self) -> Dict[str, Dict]:
        """Get detailed resource allocation per pod"""
        pods = subprocess.run(
            ["kubectl", "get", "pods", "-A", "-o", "json"],
            capture_output=True, text=True, timeout=60
        )
        data = json.loads(pods.stdout)
        
        pod_resources = defaultdict(lambda: {"cpu_req": 0, "mem_req": 0, "cpu_lim": 0, "mem_lim": 0, "containers": 0})
        
        for pod in data.get("items", []):
            ns = pod["metadata"]["namespace"]
            pod_name = pod["metadata"]["name"]
            
            for container in pod["spec"].get("containers", []):
                resources = container.get("resources", {})
                requests = resources.get("requests", {})
                limits = resources.get("limits", {})
                
                cpu_req = self._parse_cpu(requests.get("cpu", "0"))
                mem_req = self._parse_memory(requests.get("memory", "0"))
                cpu_lim = self._parse_cpu(limits.get("cpu", "0"))
                mem_lim = self._parse_memory(limits.get("memory", "0"))
                
                pod_resources[ns]["cpu_req"] += cpu_req
                pod_resources[ns]["mem_req"] += mem_req / (1024**3)  # GiB
                pod_resources[ns]["cpu_lim"] += cpu_lim
                pod_resources[ns]["mem_lim"] += mem_lim / (1024**3)  # GiB
                pod_resources[ns]["containers"] += 1
        
        return dict(pod_resources)
    
    def _parse_cpu(self, cpu_str: str) -> float:
        if not cpu_str:
            return 0.0
        cpu_str = str(cpu_str).strip()
        if cpu_str.endswith("m"):
            return float(cpu_str[:-1]) / 1000
        elif cpu_str.endswith("n"):
            return float(cpu_str[:-1]) / 1e9
        return float(cpu_str)
    
    def _parse_memory(self, mem_str: str) -> float:
        if not mem_str:
            return 0.0
        mem_str = str(mem_str).strip().upper()
        multipliers = {
            "KI": 1024, "MI": 1024**2, "GI": 1024**3, "TI": 1024**4,
            "K": 1000, "M": 1000**2, "G": 1000**3, "T": 1000**4
        }
        for suffix, mult in multipliers.items():
            if mem_str.endswith(suffix):
                return float(mem_str[:-len(suffix)]) * mult
        return float(mem_str)
    
    def get_load_balancers(self) -> Dict[str, int]:
        """Get LoadBalancer service count per namespace"""
        services = subprocess.run(
            ["kubectl", "get", "svc", "-A", "-o", "json"],
            capture_output=True, text=True, timeout=30
        )
        data = json.loads(services.stdout)
        
        lb_counts = defaultdict(int)
        for svc in data.get("items", []):
            if svc["spec"].get("type") == "LoadBalancer":
                ns = svc["metadata"]["namespace"]
                lb_counts[ns] += 1
        return dict(lb_counts)
    
    def calculate_costs(self) -> List[CostAllocation]:
        """Calculate cost allocation by namespace"""
        namespaces = self.get_namespace_resources()
        lb_counts = self.get_load_balancers()
        
        allocations = []
        total_cpu = sum(ns["cpu_cores"] for ns in namespaces.values())
        total_mem = sum(ns["memory_gib"] for ns in namespaces.values())
        total_storage = sum(ns["storage_gib"] for ns in namespaces.values())
        total_lbs = sum(lb_counts.values())
        
        for ns, resources in namespaces.items():
            cpu_cores = resources["cpu_cores"]
            memory_gib = resources["memory_gib"]
            storage_gib = resources["storage_gib"]
            lb_count = lb_counts.get(ns, 0)
            
            cpu_cost = cpu_cores * self.rates["cpu_per_core_month"]
            memory_cost = memory_gib * self.rates["memory_per_gib_month"]
            storage_cost = storage_gib * self.rates["storage_per_gib_month"]
            lb_cost = lb_count * self.rates["load_balancer_per_month"]
            
            total_cost = cpu_cost + memory_cost + storage_cost + lb_cost
            
            # Calculate percentages
            cpu_pct = (cpu_cores / total_cpu * 100) if total_cpu > 0 else 0
            mem_pct = (memory_gib / total_mem * 100) if total_mem > 0 else 0
            storage_pct = (storage_gib / total_storage * 100) if total_storage > 0 else 0
            lb_pct = (lb_count / total_lbs * 100) if total_lbs > 0 else 0
            
            # Determine team and service
            team = self.namespace_teams.get(ns, "unknown")
            services = self.namespace_services.get(ns, ["unknown"])
            
            # Create allocation for each service in namespace
            if len(services) == 1:
                service_list = [services[0]]
            else:
                # Distribute costs equally among services in namespace
                service_list = services
            
            for service in service_list:
                num_services = len(service_list)
                allocations.append(CostAllocation(
                    namespace=ns,
                    team=team,
                    service=service,
                    cpu_cores=round(cpu_cores / num_services, 2),
                    memory_gib=round(memory_gib / num_services, 2),
                    storage_gib=round(storage_gib / num_services, 2),
                    load_balancer_count=lb_count,
                    cpu_cost=round(cpu_cost / num_services, 2),
                    memory_cost=round(memory_cost / num_services, 2),
                    storage_cost=round(storage_cost / num_services, 2),
                    lb_cost=round(lb_cost / num_services, 2),
                    total_monthly_cost=round(total_cost / num_services, 2),
                    cpu_percent=round(cpu_pct, 1),
                    memory_percent=round(mem_pct, 1),
                    storage_percent=round(storage_pct, 1),
                    lb_percent=round(lb_pct, 1)
                ))
        
        return allocations
    
    def generate_report(self, allocations: List[CostAllocation]) -> Dict:
        """Generate comprehensive cost allocation report"""
        
        # Summary by team
        team_costs = defaultdict(float)
        for a in allocations:
            team_costs[a.team] += a.total_monthly_cost
        
        # Summary by namespace
        ns_costs = defaultdict(float)
        for a in allocations:
            ns_costs[a.namespace] += a.total_monthly_cost
        
        # Summary by service
        svc_costs = defaultdict(float)
        for a in allocations:
            svc_costs[a.service] += a.total_monthly_cost
        
        total_monthly = sum(a.total_monthly_cost for a in allocations)
        
        report = {
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "summary": {
                "total_monthly_cost": round(total_monthly, 2),
                "total_namespaces": len(set(a.namespace for a in allocations)),
                "total_services": len(set(a.service for a in allocations)),
                "total_teams": len(set(a.team for a in allocations)),
            },
            "by_team": {
                team: round(cost, 2) 
                for team, cost in sorted(team_costs.items(), key=lambda x: x[1], reverse=True)
            },
            "by_namespace": {
                ns: round(cost, 2) 
                for ns, cost in sorted(ns_costs.items(), key=lambda x: x[1], reverse=True)
            },
            "by_service": {
                svc: round(cost, 2) 
                for svc, cost in sorted(svc_costs.items(), key=lambda x: x[1], reverse=True)
            },
            "detailed_allocations": [asdict(a) for a in allocations],
        }
        
        return report

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Cost Allocation and Chargeback Reporting")
    parser.add_argument("--prometheus-url", default="http://prometheus.monitoring.svc.cluster.local:9090")
    parser.add_argument("--output", default="cost-allocation-report.json")
    parser.add_argument("--format", choices=["json", "csv", "markdown"], default="json")
    parser.add_argument("--cpu-rate", type=float, default=30.0, help="Cost per CPU core per month")
    parser.add_argument("--memory-rate", type=float, default=4.0, help="Cost per GiB memory per month")
    parser.add_argument("--storage-rate", type=float, default=0.10, help="Cost per GiB storage per month")
    parser.add_argument("--lb-rate", type=float, default=22.0, help="Cost per LoadBalancer per month")
    args = parser.parse_args()
    
    analyzer = CostAllocationAnalyzer(prometheus_url=args.prometheus_url)
    analyzer.rates = {
        "cpu_per_core_month": args.cpu_rate,
        "memory_per_gib_month": args.memory_rate,
        "storage_per_gib_month": args.storage_rate,
        "load_balancer_per_month": args.lb_rate,
    }
    
    print("Collecting namespace resource usage...")
    allocations = analyzer.calculate_costs()
    
    print(f"Calculated allocations for {len(allocations)} service entries")
    
    report = analyzer.generate_report(allocations)
    
    # Output
    if args.format == "json":
        with open(args.output, "w") as f:
            json.dump(report, f, indent=2)
    elif args.format == "csv":
        with open(args.output, "w") as f:
            writer = csv.DictWriter(f, fieldnames=list(asdict(allocations[0]).keys()) if allocations else [])
            if allocations:
                writer.writeheader()
                for a in allocations:
                    writer.writerow(asdict(a))
    elif args.format == "markdown":
        with open(args.output, "w") as f:
            f.write("# Cost Allocation Report\n\n")
            f.write(f"Generated: {datetime.utcnow().isoformat()}Z\n\n")
            
            f.write("## Summary\n\n")
            f.write(f"- **Total Monthly Cost:** ${report['summary']['total_monthly_cost']:.2f}\n")
            f.write(f"- **Namespaces:** {report['summary']['total_namespaces']}\n")
            f.write(f"- **Services:** {report['summary']['total_services']}\n")
            f.write(f"- **Teams:** {report['summary']['total_teams']}\n\n")
            
            f.write("## Cost by Team\n\n")
            f.write("| Team | Monthly Cost | % of Total |\n")
            f.write("|------|-------------|------------|\n")
            total = report['summary']['total_monthly_cost']
            for team, cost in report["by_team"].items():
                pct = (cost / total * 100) if total > 0 else 0
                f.write(f"| {team} | ${cost:.2f} | {pct:.1f}% |\n")
            f.write("\n")
            
            f.write("## Cost by Namespace\n\n")
            f.write("| Namespace | Monthly Cost | % of Total |\n")
            f.write("|-----------|-------------|------------|\n")
            for ns, cost in report["by_namespace"].items():
                pct = (cost / total * 100) if total > 0 else 0
                f.write(f"| {ns} | ${cost:.2f} | {pct:.1f}% |\n")
            f.write("\n")
            
            f.write("## Cost by Service\n\n")
            f.write("| Service | Monthly Cost | % of Total |\n")
            f.write("|---------|-------------|------------|\n")
            for svc, cost in report["by_service"].items():
                pct = (cost / total * 100) if total > 0 else 0
                f.write(f"| {svc} | ${cost:.2f} | {pct:.1f}% |\n")
            f.write("\n")
            
            f.write("## Detailed Allocations\n\n")
            f.write("| Namespace | Team | Service | CPU (cores) | Memory (GiB) | Storage (GiB) | LBs | CPU Cost | Mem Cost | Storage Cost | LB Cost | Total Cost |\n")
            f.write("|-----------|------|---------|-------------|--------------|---------------|-----|----------|----------|--------------|---------|------------|\n")
            for a in sorted(allocations, key=lambda x: x.total_monthly_cost, reverse=True):
                f.write(f"| {a.namespace} | {a.team} | {a.service} | {a.cpu_cores} | {a.memory_gib} | {a.storage_gib} | {a.load_balancer_count} | ${a.cpu_cost:.2f} | ${a.memory_cost:.2f} | ${a.storage_cost:.2f} | ${a.lb_cost:.2f} | ${a.total_monthly_cost:.2f} |\n")
    
    print(f"Report saved to {args.output}")
    
    # Print summary
    print(f"\nTotal Monthly Cost: ${report['summary']['total_monthly_cost']:.2f}")
    print(f"Namespaces: {report['summary']['total_namespaces']}")
    print(f"Services: {report['summary']['total_services']}")
    print(f"Teams: {report['summary']['total_teams']}")

if __name__ == "__main__":
    main()