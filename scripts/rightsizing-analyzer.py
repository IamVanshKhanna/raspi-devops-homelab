#!/usr/bin/env python3
"""
Right-Sizing Recommendations Automation
Analyzes Prometheus metrics and VPA recommendations to generate
container resource right-sizing suggestions.
"""

import os
import json
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
import subprocess

@dataclass
class ResourceRecommendation:
    namespace: str
    workload: str
    workload_type: str  # Deployment, StatefulSet, DaemonSet
    container: str
    current_request_cpu: str
    current_request_memory: str
    current_limit_cpu: str
    current_limit_memory: str
    recommended_request_cpu: str
    recommended_request_memory: str
    recommended_limit_cpu: str
    recommended_limit_memory: str
    cpu_savings_percent: float
    memory_savings_percent: float
    confidence: str  # High, Medium, Low
    reason: str

class RightSizingAnalyzer:
    def __init__(self, prometheus_url: str = "http://prometheus.monitoring.svc.cluster.local:9090"):
        self.prometheus_url = prometheus_url
        self.vpa_enabled = self._check_vpa()
        
    def _check_vpa(self) -> bool:
        """Check if VPA is installed and has recommendations"""
        try:
            result = subprocess.run(
                ["kubectl", "get", "crd", "verticalpodautoscalers.autoscaling.k8s.io"],
                capture_output=True, text=True, timeout=10
            )
            return result.returncode == 0
        except:
            return False
    
    def query_prometheus(self, query: str, time: Optional[str] = None) -> Dict:
        """Query Prometheus API"""
        params = {"query": query}
        if time:
            params["time"] = time
        
        response = requests.get(
            f"{self.prometheus_url}/api/v1/query",
            params=params,
            timeout=30
        )
        response.raise_for_status()
        return response.json()
    
    def query_prometheus_range(self, query: str, start: str, end: str, step: str = "1h") -> Dict:
        """Query Prometheus range API"""
        params = {"query": query, "start": start, "end": end, "step": step}
        response = requests.get(
            f"{self.prometheus_url}/api/v1/query_range",
            params=params,
            timeout=30
        )
        response.raise_for_status()
        return response.json()
    
    def get_workloads(self) -> List[Dict]:
        """Get all workloads with their containers"""
        workloads = []
        
        # Deployments
        result = subprocess.run([
            "kubectl", "get", "deployments", "-A", "-o", "json"
        ], capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            data = json.loads(result.stdout)
            for item in data.get("items", []):
                ns = item["metadata"]["namespace"]
                name = item["metadata"]["name"]
                for container in item["spec"]["template"]["spec"]["containers"]:
                    workloads.append({
                        "namespace": ns,
                        "name": name,
                        "type": "Deployment",
                        "container": container["name"],
                        "current_requests": container.get("resources", {}).get("requests", {}),
                        "current_limits": container.get("resources", {}).get("limits", {})
                    })
        
        # StatefulSets
        result = subprocess.run([
            "kubectl", "get", "statefulsets", "-A", "-o", "json"
        ], capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            data = json.loads(result.stdout)
            for item in data.get("items", []):
                ns = item["metadata"]["namespace"]
                name = item["metadata"]["name"]
                for container in item["spec"]["template"]["spec"]["containers"]:
                    workloads.append({
                        "namespace": ns,
                        "name": name,
                        "type": "StatefulSet",
                        "container": container["name"],
                        "current_requests": container.get("resources", {}).get("requests", {}),
                        "current_limits": container.get("resources", {}).get("limits", {})
                    })
        
        # DaemonSets
        result = subprocess.run([
            "kubectl", "get", "daemonsets", "-A", "-o", "json"
        ], capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            data = json.loads(result.stdout)
            for item in data.get("items", []):
                ns = item["metadata"]["namespace"]
                name = item["metadata"]["name"]
                for container in item["spec"]["template"]["spec"]["containers"]:
                    workloads.append({
                        "namespace": ns,
                        "name": name,
                        "type": "DaemonSet",
                        "container": container["name"],
                        "current_requests": container.get("resources", {}).get("requests", {}),
                        "current_limits": container.get("resources", {}).get("limits", {})
                    })
        
        return workloads
    
    def get_vpa_recommendations(self) -> Dict[str, Dict]:
        """Get VPA recommendations if VPA is enabled"""
        recommendations = {}
        
        if not self.vpa_enabled:
            return recommendations
        
        try:
            result = subprocess.run([
                "kubectl", "get", "vpa", "-A", "-o", "json"
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                data = json.loads(result.stdout)
                for item in data.get("items", []):
                    ns = item["metadata"]["namespace"]
                    name = item["metadata"]["name"]
                    target = item["spec"]["targetRef"]["name"]
                    
                    # Get recommendation
                    rec = item.get("status", {}).get("recommendation", {})
                    container_recs = rec.get("containerRecommendations", [])
                    
                    for crec in container_recs:
                        key = f"{crec['containerName']}.{target}.{ns}"
                        recommendations[key] = {
                            "target_cpu": crec.get("target", {}).get("cpu"),
                            "target_memory": crec.get("target", {}).get("memory"),
                            "lower_cpu": crec.get("lowerBound", {}).get("cpu"),
                            "lower_memory": crec.get("lowerBound", {}).get("memory"),
                            "upper_cpu": crec.get("upperBound", {}).get("cpu"),
                            "upper_memory": crec.get("upperBound", {}).get("memory"),
                            "uncapped_cpu": crec.get("uncappedTarget", {}).get("cpu"),
                            "uncapped_memory": crec.get("uncappedTarget", {}).get("memory"),
                        }
        except Exception as e:
            print(f"Error getting VPA recommendations: {e}")
        
        return recommendations
    
    def get_prometheus_metrics(self, workload: Dict) -> Dict[str, Any]:
        """Get actual usage metrics from Prometheus"""
        ns = workload["namespace"]
        workload_name = workload["name"]
        container = workload["container"]
        workload_type = workload["type"]
        
        metrics = {}
        
        # CPU usage (95th percentile over 30 days)
        cpu_query = f'''
        histogram_quantile(0.95, 
          sum by (namespace, workload, container, le) (
            rate(container_cpu_usage_seconds_total{{
              namespace="{ns}",
              pod=~"{workload_name}.*",
              container="{container}"
            }}[5m])
          )
        )'''
        
        # Memory usage (95th percentile over 30 days)
        mem_query = f'''
        histogram_quantile(0.95,
          sum by (namespace, workload, container, le) (
            rate(container_memory_usage_bytes{{
              namespace="{ns}",
              pod=~"{workload_name}.*",
              container="{container}"
            }}[5m])
          )
        )'''
        
        # Request vs actual
        cpu_req_query = f'''
        sum by (namespace, workload, container) (
          kube_pod_container_resource_requests_cpu_cores{{
            namespace="{ns}",
            pod=~"{workload_name}.*",
            container="{container}"
          }}
        )'''
        
        mem_req_query = f'''
        sum by (namespace, workload, container) (
          kube_pod_container_resource_requests_memory_bytes{{
            namespace="{ns}",
            pod=~"{workload_name}.*",
            container="{container}"
          }}
        )'''
        
        try:
            # CPU usage
            cpu_result = self.query_prometheus(cpu_query)
            if cpu_result["data"]["result"]:
                metrics["cpu_usage_95th"] = float(cpu_result["data"]["result"][0]["value"][1])
            
            # Memory usage
            mem_result = self.query_prometheus(mem_query)
            if mem_result["data"]["result"]:
                metrics["memory_usage_95th"] = float(mem_result["data"]["result"][0]["value"][1])
            
            # CPU request
            cpu_req_result = self.query_prometheus(cpu_req_query)
            if cpu_req_result["data"]["result"]:
                metrics["cpu_request"] = float(cpu_req_result["data"]["result"][0]["value"][1])
            
            # Memory request
            mem_req_result = self.query_prometheus(mem_req_query)
            if mem_req_result["data"]["result"]:
                metrics["memory_request"] = float(mem_req_result["data"]["result"][0]["value"][1])
                
        except Exception as e:
            print(f"Error getting metrics for {workload}: {e}")
        
        return metrics
    
    def calculate_recommendations(self, workload: Dict, metrics: Dict, vpa_rec: Optional[Dict]) -> Optional[ResourceRecommendation]:
        """Calculate right-sizing recommendation"""
        
        current_cpu_req = self._parse_cpu(workload["current_requests"].get("cpu", "0"))
        current_mem_req = self._parse_memory(workload["current_requests"].get("memory", "0"))
        current_cpu_limit = self._parse_cpu(workload["current_limits"].get("cpu", "0"))
        current_mem_limit = self._parse_memory(workload["current_limits"].get("memory", "0"))
        
        cpu_usage = metrics.get("cpu_usage_95th", 0)
        mem_usage = metrics.get("memory_usage_95th", 0)
        cpu_request = metrics.get("cpu_request", current_cpu_req)
        mem_request = metrics.get("memory_request", current_mem_req)
        
        # Skip if no usage data
        if cpu_usage == 0 and mem_usage == 0:
            return None
        
        # Calculate recommended values (add 20% buffer for requests, 50% for limits)
        rec_cpu_req = max(cpu_usage * 1.2, 0.01)  # Minimum 10m
        rec_mem_req = max(mem_usage * 1.2, 32 * 1024 * 1024)  # Minimum 32Mi
        rec_cpu_limit = max(rec_cpu_req * 1.5, 0.02)  # Minimum 20m
        rec_mem_limit = max(rec_mem_req * 1.5, 64 * 1024 * 1024)  # Minimum 64Mi
        
        # Use VPA if available and higher confidence
        if vpa_rec:
            vpa_cpu = self._parse_cpu(vpa_rec.get("target_cpu", "0"))
            vpa_mem = self._parse_memory(vpa_rec.get("target_memory", "0"))
            if vpa_cpu > 0:
                rec_cpu_req = vpa_cpu
            if vpa_mem > 0:
                rec_mem_req = vpa_mem
            rec_cpu_limit = rec_cpu_req * 1.5
            rec_mem_limit = rec_mem_req * 1.5
            confidence = "High"
        else:
            confidence = "Medium" if cpu_usage > 0 and mem_usage > 0 else "Low"
        
        # Calculate savings
        cpu_savings = 0
        mem_savings = 0
        if cpu_request > 0:
            cpu_savings = ((cpu_request - rec_cpu_req) / cpu_request) * 100
        if mem_request > 0:
            mem_savings = ((mem_request - rec_mem_req) / mem_request) * 100
        
        # Only recommend if savings > 10% or significant over-provisioning
        if cpu_savings < 10 and mem_savings < 10:
            return None
        
        # Format values
        def format_cpu(cpu):
            if cpu >= 1:
                return f"{cpu:.1f}"
            else:
                return f"{int(cpu * 1000)}m"
        
        def format_mem(mem):
            if mem >= 1024**3:
                return f"{mem / 1024**3:.1f}Gi"
            elif mem >= 1024**2:
                return f"{mem / 1024**2:.0f}Mi"
            elif mem >= 1024:
                return f"{mem / 1024:.0f}Ki"
            else:
                return f"{mem:.0f}"
        
        reason = f"95th percentile CPU: {cpu_usage:.3f} cores, Memory: {mem_usage / 1024**2:.0f} MiB. "
        reason += f"Current requests: {format_cpu(cpu_request)} CPU, {format_mem(mem_request)} memory. "
        if vpa_rec:
            reason += "Based on VPA recommendation. "
        else:
            reason += "Based on Prometheus metrics (95th percentile + 20% buffer). "
        
        return ResourceRecommendation(
            namespace=workload["namespace"],
            workload=workload["name"],
            workload_type=workload["type"],
            container=workload["container"],
            current_request_cpu=format_cpu(cpu_request),
            current_request_memory=format_mem(mem_request),
            current_limit_cpu=format_cpu(current_cpu_limit),
            current_limit_memory=format_mem(current_mem_limit),
            recommended_request_cpu=format_cpu(rec_cpu_req),
            recommended_request_memory=format_mem(rec_mem_req),
            recommended_limit_cpu=format_cpu(rec_cpu_limit),
            recommended_limit_memory=format_mem(rec_mem_limit),
            cpu_savings_percent=round(cpu_savings, 1),
            memory_savings_percent=round(mem_savings, 1),
            confidence=confidence,
            reason=reason
        )
    
    def _parse_cpu(self, cpu_str: str) -> float:
        """Parse CPU string to cores"""
        if not cpu_str:
            return 0.0
        cpu_str = str(cpu_str).strip()
        if cpu_str.endswith("m"):
            return float(cpu_str[:-1]) / 1000
        elif cpu_str.endswith("n"):
            return float(cpu_str[:-1]) / 1e9
        else:
            return float(cpu_str)
    
    def _parse_memory(self, mem_str: str) -> float:
        """Parse memory string to bytes"""
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
    
    def format_cpu(self, cpu: float) -> str:
        if cpu >= 1:
            return f"{cpu:.1f}"
        else:
            return f"{int(cpu * 1000)}m"
    
    def format_mem(self, mem: float) -> str:
        if mem >= 1024**3:
            return f"{mem / 1024**3:.1f}Gi"
        elif mem >= 1024**2:
            return f"{mem / 1024**2:.0f}Mi"
        elif mem >= 1024:
            return f"{mem / 1024:.0f}Ki"
        else:
            return f"{int(mem)}"
    
    def run_analysis(self) -> List[ResourceRecommendation]:
        """Run complete right-sizing analysis"""
        print("Starting right-sizing analysis...")
        
        # Get VPA recommendations
        vpa_recs = self.get_vpa_recommendations()
        print(f"Found {len(vpa_recs)} VPA recommendations")
        
        # Get all workloads
        workloads = self.get_workloads()
        print(f"Found {len(workloads)} workloads")
        
        recommendations = []
        
        for workload in workloads:
            # Skip system namespaces
            if workload["namespace"] in ["kube-system", "kube-public", "kube-node-lease"]:
                continue
            
            # Get Prometheus metrics
            metrics = self.get_prometheus_metrics(workload)
            
            # Get VPA recommendation for this container
            vpa_key = f"{workload['container']}.{workload['name']}.{workload['namespace']}"
            vpa_rec = vpa_recs.get(vpa_key)
            
            # Calculate recommendation
            rec = self.calculate_recommendations(workload, metrics, vpa_rec)
            if rec:
                recommendations.append(rec)
        
        # Sort by total savings (CPU + Memory)
        recommendations.sort(
            key=lambda x: x.cpu_savings_percent + x.memory_savings_percent,
            reverse=True
        )
        
        return recommendations

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Right-Sizing Recommendations")
    parser.add_argument("--prometheus-url", default="http://prometheus.monitoring.svc.cluster.local:9090")
    parser.add_argument("--output", default="rightsizing-report.json")
    parser.add_argument("--format", choices=["json", "csv", "markdown"], default="json")
    parser.add_argument("--min-savings", type=float, default=10.0, help="Minimum savings % to report")
    args = parser.parse_args()
    
    analyzer = RightSizingAnalyzer(prometheus_url=args.prometheus_url)
    recommendations = analyzer.run_analysis()
    
    # Filter by minimum savings
    recommendations = [
        r for r in recommendations 
        if r.cpu_savings_percent >= args.min_savings or r.memory_savings_percent >= args.min_savings
    ]
    
    # Output
    if args.format == "json":
        output = [asdict(r) for r in recommendations]
        with open(args.output, "w") as f:
            json.dump(output, f, indent=2)
    elif args.format == "csv":
        import csv
        with open(args.output, "w") as f:
            writer = csv.DictWriter(f, fieldnames=list(asdict(recommendations[0]).keys()) if recommendations else [])
            writer.writeheader()
            for r in recommendations:
                writer.writerow(asdict(r))
    elif args.format == "markdown":
        with open(args.output, "w") as f:
            f.write("# Right-Sizing Recommendations\n\n")
            f.write(f"Generated: {datetime.utcnow().isoformat()}Z\n\n")
            f.write("| Namespace | Workload | Container | Current CPU Req | Rec CPU Req | CPU Savings | Current Mem Req | Rec Mem Req | Mem Savings | Confidence |\n")
            f.write("|-----------|----------|-----------|-----------------|-------------|-------------|-----------------|-------------|-------------|------------|\n")
            for r in recommendations:
                f.write(f"| {r.namespace} | {r.workload} | {r.container} | {r.current_request_cpu} | {r.recommended_request_cpu} | {r.cpu_savings_percent}% | {r.current_request_memory} | {r.recommended_request_memory} | {r.memory_savings_percent}% | {r.confidence} |\n")
    
    print(f"Generated {len(recommendations)} recommendations")
    print(f"Output saved to {args.output}")

if __name__ == "__main__":
    main()