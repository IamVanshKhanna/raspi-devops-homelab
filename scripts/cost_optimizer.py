#!/usr/bin/env python3
"""
Cost Optimization Analyzer for homelab-prod
Analyzes resource usage and provides cost optimization recommendations
"""

import argparse
import json
import subprocess
import sys
from datetime import datetime, timedelta

def run_kubectl(cmd: list) -> str:
    """Run kubectl and return output."""
    result = subprocess.run(["kubectl"] + cmd, capture_output=True, text=True)
    if result.returncode != 0:
        return ""
    return result.stdout.strip()

def get_node_resources() -> dict:
    """Get node resource capacity and allocatable."""
    nodes = {}
    output = run_kubectl(["get", "nodes", "-o", "json"])
    if not output:
        return nodes
    
    data = json.loads(output)
    for node in data["items"]:
        name = node["metadata"]["name"]
        capacity = node["status"]["capacity"]
        allocatable = node["status"]["allocatable"]
        nodes[name] = {
            "cpu_capacity": capacity.get("cpu", "0"),
            "mem_capacity": capacity.get("memory", "0"),
            "cpu_allocatable": allocatable.get("cpu", "0"),
            "mem_allocatable": allocatable.get("memory", "0"),
        }
    return nodes

def get_pod_resources() -> list:
    """Get pod resource requests/limits."""
    output = run_kubectl(["get", "pods", "--all-namespaces", "-o", "json"])
    if not output:
        return []
    
    data = json.loads(output)
    pods = []
    for pod in data["items"]:
        ns = pod["metadata"]["namespace"]
        name = pod["metadata"]["name"]
        phase = pod["status"]["phase"]
        
        total_requests_cpu = 0
        total_requests_mem = 0
        total_limits_cpu = 0
        total_limits_mem = 0
        
        for container in pod["spec"].get("containers", []):
            resources = container.get("resources", {})
            req = resources.get("requests", {})
            lim = resources.get("limits", {})
            
            for k, v in req.items():
                if k == "cpu":
                    total_requests_cpu += parse_cpu(v)
                elif k == "memory":
                    total_requests_mem += parse_memory(v)
            for k, v in lim.items():
                if k == "cpu":
                    total_limits_cpu += parse_cpu(v)
                elif k == "memory":
                    total_limits_mem += parse_memory(v)
        
        if total_requests_cpu > 0 or total_requests_mem > 0:
            pods.append({
                "namespace": ns,
                "name": name,
                "phase": phase,
                "requests_cpu": total_requests_cpu,
                "requests_mem": total_requests_mem,
                "limits_cpu": total_limits_cpu,
                "limits_mem": total_limits_mem,
            })
    return pods

def parse_cpu(v: str) -> float:
    """Parse CPU string to cores."""
    if v.endswith("m"):
        return float(v[:-1]) / 1000
    return float(v)

def parse_memory(v: str) -> int:
    """Parse memory string to bytes."""
    units = {"Ki": 1024, "Mi": 1024**2, "Gi": 1024**3, "Ti": 1024**4,
             "K": 1000, "M": 1000**2, "G": 1000**3, "T": 1000**4}
    for unit, mult in units.items():
        if v.endswith(unit):
            return int(v[:-len(unit)]) * mult
    return int(v)

def format_bytes(b: int) -> str:
    """Format bytes to human readable."""
    for unit in ["B", "KiB", "MiB", "GiB", "TiB"]:
        if b < 1024:
            return f"{b:.1f} {unit}"
        b /= 1024
    return f"{b:.1f} PiB"

def main():
    parser = argparse.ArgumentParser(description="Analyze cluster resource usage for cost optimization")
    parser.add_argument("--threshold-cpu", type=float, default=0.1, help="CPU utilization threshold (fraction)")
    parser.add_argument("--threshold-mem", type=float, default=0.1, help="Memory utilization threshold (fraction)")
    parser.add_argument("--output", choices=["text", "json"], default="text")
    args = parser.parse_args()
    
    nodes = get_node_resources()
    pods = get_pod_resources()
    
    # Aggregate by namespace
    ns_usage = {}
    for pod in pods:
        ns = pod["namespace"]
        if ns not in ns_usage:
            ns_usage[ns] = {"cpu_req": 0, "mem_req": 0, "cpu_lim": 0, "mem_lim": 0, "pods": 0}
        ns_usage[ns]["cpu_req"] += pod["requests_cpu"]
        ns_usage[ns]["mem_req"] += pod["requests_mem"]
        ns_usage[ns]["cpu_lim"] += pod["limits_cpu"]
        ns_usage[ns]["mem_lim"] += pod["limits_mem"]
        ns_usage[ns]["pods"] += 1
    
    # Node totals
    total_cpu_alloc = sum(parse_cpu(n["cpu_allocatable"]) for n in nodes.values())
    total_mem_alloc = sum(parse_memory(n["mem_allocatable"]) for n in nodes.values())
    
    total_cpu_req = sum(ns["cpu_req"] for ns in ns_usage.values())
    total_mem_req = sum(ns["mem_req"] for ns in ns_usage.values())
    total_cpu_lim = sum(ns["cpu_lim"] for ns in ns_usage.values())
    total_mem_lim = sum(ns["mem_lim"] for ns in ns_usage.values())
    
    cpu_util = total_cpu_req / total_cpu_alloc if total_cpu_alloc > 0 else 0
    mem_util = total_mem_req / total_mem_alloc if total_mem_alloc > 0 else 0
    
    if args.output == "json":
        result = {
            "nodes": len(nodes),
            "total_cpu_allocatable": total_cpu_alloc,
            "total_mem_allocatable": total_mem_alloc,
            "total_cpu_requests": total_cpu_req,
            "total_mem_requests": total_mem_req,
            "total_cpu_limits": total_cpu_lim,
            "total_mem_limits": total_mem_lim,
            "cpu_utilization": cpu_util,
            "mem_utilization": mem_util,
            "namespaces": ns_usage,
        }
        print(json.dumps(result, indent=2))
        return
    
    # Text output
    print("=" * 60)
    print("HOMELAB COST OPTIMIZATION ANALYSIS")
    print("=" * 60)
    print(f"Nodes: {len(nodes)}")
    print(f"Total Allocatable: {total_cpu_alloc:.2f} CPU, {format_bytes(total_mem_alloc)} RAM")
    print(f"Total Requests:    {total_cpu_req:.2f} CPU, {format_bytes(total_mem_req)} RAM")
    print(f"Total Limits:      {total_cpu_lim:.2f} CPU, {format_bytes(total_mem_lim)} RAM")
    print(f"Utilization:       CPU {cpu_util*100:.1f}%, RAM {mem_util*100:.1f}%")
    print()
    
    print("PER NAMESPACE:")
    print("-" * 60)
    for ns, usage in sorted(ns_usage.items(), key=lambda x: x[1]["cpu_req"], reverse=True):
        if usage["cpu_req"] > 0 or usage["mem_req"] > 0:
            print(f"  {ns:20s} | CPU: {usage['cpu_req']:.2f}/{usage['cpu_lim']:.2f} cores | RAM: {format_bytes(usage['mem_req']):>8s}/{format_bytes(usage['mem_lim']):>8s} | Pods: {usage['pods']}")
    
    print()
    print("RECOMMENDATIONS:")
    print("-" * 60)
    
    if cpu_util < args.threshold_cpu:
        print(f"  ⚠️  LOW CPU UTILIZATION ({cpu_util*100:.1f}%): Consider reducing node count or instance size")
    
    if mem_util < args.threshold_mem:
        print(f"  ⚠️  LOW MEMORY UTILIZATION ({mem_util*100:.1f}%): Consider reducing node RAM")
    
    # Over-provisioned namespaces
    for ns, usage in ns_usage.items():
        if usage["limits_cpu"] > 0 and usage["cpu_req"] / usage["limits_cpu"] < 0.3:
            print(f"  💡 {ns}: CPU requests only {usage['cpu_req']/usage['limits_cpu']*100:.0f}% of limits - consider reducing limits")
        if usage["limits_mem"] > 0 and usage["mem_req"] / usage["limits_mem"] < 0.3:
            print(f"  💡 {ns}: RAM requests only {usage['mem_req']/usage['limits_mem']*100:.0f}% of limits - consider reducing limits")
    
    # Idle pods
    for ns, usage in ns_usage.items():
        if usage["pods"] > 0 and usage["cpu_req"] == 0 and usage["mem_req"] == 0:
            print(f"  🔍 {ns}: {usage['pods']} pods with no resource requests - add requests/limits")

if __name__ == "__main__":
    main()