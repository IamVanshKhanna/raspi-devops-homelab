#!/usr/bin/env python3
"""
Capacity Planning Automation for Homelab
Queries Prometheus for metrics and runs forecasting predictions
"""

import os
import sys
import json
import requests
import argparse
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

# Configuration
PROMETHEUS_URL = os.environ.get("PROMETHEUS_URL", "http://prometheus.monitoring.svc.cluster.local:9090")
OUTPUT_DIR = os.environ.get("OUTPUT_DIR", "/home/vansh/homelab-prod/capacity-reports")

# PromQL Queries for capacity planning
QUERIES = {
    "disk_usage": {
        "query": 'node_filesystem_avail_bytes{mountpoint="/mnt/data"}',
        "unit": "GB",
        "description": "Available disk space on /mnt/data"
    },
    "disk_total": {
        "query": 'node_filesystem_size_bytes{mountpoint="/mnt/data"}',
        "unit": "GB",
        "description": "Total disk space on /mnt/data"
    },
    "disk_usage_pct": {
        "query": '(1 - (node_filesystem_avail_bytes{mountpoint="/mnt/data"} / node_filesystem_size_bytes{mountpoint="/mnt/data"})) * 100',
        "unit": "%",
        "description": "Disk usage percentage"
    },
    "disk_growth_rate": {
        "query": 'rate(node_filesystem_size_bytes{mountpoint="/mnt/data"} - node_filesystem_avail_bytes{mountpoint="/mnt/data"}[30d])',
        "unit": "GB/day",
        "description": "Disk growth rate per day"
    },
    "memory_usage_pct": {
        "query": '(1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)) * 100',
        "unit": "%",
        "description": "Memory usage percentage"
    },
    "memory_total": {
        "query": 'node_memory_MemTotal_bytes',
        "unit": "GB",
        "description": "Total system memory"
    },
    "memory_available": {
        "query": 'node_memory_MemAvailable_bytes',
        "unit": "GB",
        "description": "Available memory"
    },
    "cpu_usage_pct": {
        "query": 'avg by (instance) (irate(node_cpu_seconds_total{mode!="idle"}[5m])) * 100',
        "unit": "%",
        "description": "CPU usage percentage"
    },
    "cpu_cores": {
        "query": 'count(node_cpu_seconds_total{mode="idle"}) by (instance)',
        "unit": "cores",
        "description": "CPU cores per instance"
    },
    "network_receive_rate": {
        "query": 'rate(node_network_receive_bytes_total[5m])',
        "unit": "MB/s",
        "description": "Network receive rate"
    },
    "network_transmit_rate": {
        "query": 'rate(node_network_transmit_bytes_total[5m])',
        "unit": "MB/s",
        "description": "Network transmit rate"
    },
    "pod_count": {
        "query": 'count(kube_pod_info)',
        "unit": "pods",
        "description": "Total pod count"
    },
    "pvc_usage": {
        "query": 'kubelet_volume_stats_used_bytes',
        "unit": "GB",
        "description": "PVC usage per volume"
    },
    "pvc_capacity": {
        "query": 'kubelet_volume_stats_capacity_bytes',
        "unit": "GB",
        "description": "PVC capacity per volume"
    }
}

# Prediction queries (using predict_linear)
PREDICTION_QUERIES = {
    "disk_exhaustion_30d": {
        "query": 'predict_linear(node_filesystem_avail_bytes{mountpoint="/mnt/data"}[30d], 30*24*3600)',
        "unit": "GB",
        "description": "Predicted available disk in 30 days"
    },
    "disk_exhaustion_60d": {
        "query": 'predict_linear(node_filesystem_avail_bytes{mountpoint="/mnt/data"}[30d], 60*24*3600)',
        "unit": "GB",
        "description": "Predicted available disk in 60 days"
    },
    "disk_exhaustion_90d": {
        "query": 'predict_linear(node_filesystem_avail_bytes{mountpoint="/mnt/data"}[30d], 90*24*3600)',
        "unit": "GB",
        "description": "Predicted available disk in 90 days"
    },
    "memory_exhaustion_30d": {
        "query": 'predict_linear((1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)) * 100[30d], 30*24*3600)',
        "unit": "%",
        "description": "Predicted memory usage % in 30 days"
    },
    "pod_growth_30d": {
        "query": 'predict_linear(count(kube_pod_info)[30d], 30*24*3600)',
        "unit": "pods",
        "description": "Predicted pod count in 30 days"
    }
}

THRESHOLDS = {
    "disk_warning_pct": 80,
    "disk_critical_pct": 90,
    "memory_warning_pct": 85,
    "memory_critical_pct": 95,
    "cpu_warning_pct": 80,
    "cpu_critical_pct": 90
}

def query_prometheus(query: str, time: Optional[str] = None) -> Dict[str, Any]:
    """Query Prometheus API"""
    params = {"query": query}
    if time:
        params["time"] = time
    
    response = requests.get(f"{PROMETHEUS_URL}/api/v1/query", params=params, timeout=30)
    response.raise_for_status()
    return response.json()

def query_prometheus_range(query: str, start: str, end: str, step: str = "1h") -> Dict[str, Any]:
    """Query Prometheus range API"""
    params = {
        "query": query,
        "start": start,
        "end": end,
        "step": step
    }
    
    response = requests.get(f"{PROMETHEUS_URL}/api/v1/query_range", params=params, timeout=30)
    response.raise_for_status()
    return response.json()

def format_value(value: str, unit: str) -> str:
    """Format value based on unit"""
    try:
        val = float(value)
        if unit == "GB":
            return f"{val / (1024**3):.2f} GB"
        elif unit == "MB/s":
            return f"{val / (1024**2):.2f} MB/s"
        elif unit == "%":
            return f"{val:.1f}%"
        elif unit in ["pods", "cores"]:
            return f"{val:.0f} {unit}"
        else:
            return f"{val:.2f} {unit}"
    except:
        return f"{value} {unit}"

def get_current_metrics() -> Dict[str, Any]:
    """Get all current metrics"""
    metrics = {}
    for key, config in QUERIES.items():
        try:
            result = query_prometheus(config["query"])
            if result["data"]["result"]:
                # Take first result for single-value queries, or average for multi-instance
                values = [float(r["value"][1]) for r in result["data"]["result"]]
                if len(values) == 1:
                    metrics[key] = {
                        "value": values[0],
                        "formatted": format_value(str(values[0]), config["unit"]),
                        "unit": config["unit"],
                        "description": config["description"]
                    }
                else:
                    avg_val = sum(values) / len(values)
                    metrics[key] = {
                        "value": avg_val,
                        "formatted": format_value(str(avg_val), config["unit"]),
                        "unit": config["unit"],
                        "description": config["description"],
                        "instances": len(values)
                    }
            else:
                metrics[key] = {"error": "No data returned"}
        except Exception as e:
            metrics[key] = {"error": str(e)}
    return metrics

def get_predictions() -> Dict[str, Any]:
    """Get all prediction metrics"""
    predictions = {}
    for key, config in PREDICTION_QUERIES.items():
        try:
            result = query_prometheus(config["query"])
            if result["data"]["result"]:
                values = [float(r["value"][1]) for r in result["data"]["result"]]
                avg_val = sum(values) / len(values)
                predictions[key] = {
                    "value": avg_val,
                    "formatted": format_value(str(avg_val), config["unit"]),
                    "unit": config["unit"],
                    "description": config["description"]
                }
            else:
                predictions[key] = {"error": "No data returned"}
        except Exception as e:
            predictions[key] = {"error": str(e)}
    return predictions

def get_historical_data(query: str, days: int = 30) -> List[Dict[str, Any]]:
    """Get historical data for trend analysis"""
    end = datetime.utcnow()
    start = end - timedelta(days=days)
    
    try:
        result = query_prometheus_range(
            query,
            start.isoformat() + "Z",
            end.isoformat() + "Z",
            "1h"
        )
        
        if result["data"]["result"]:
            series = result["data"]["result"][0]  # First series
            return [
                {"timestamp": point[0], "value": float(point[1])}
                for point in series["values"]
            ]
    except Exception as e:
        print(f"Error getting historical data: {e}", file=sys.stderr)
    
    return []

def calculate_disk_exhaustion_date(current_avail_gb: float, growth_gb_per_day: float) -> Optional[str]:
    """Calculate when disk will be exhausted"""
    if growth_gb_per_day <= 0:
        return None
    
    days_remaining = current_avail_gb / growth_gb_per_day
    exhaustion_date = datetime.utcnow() + timedelta(days=days_remaining)
    return exhaustion_date.isoformat()

def check_thresholds(metrics: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Check metrics against thresholds"""
    alerts = []
    
    # Disk usage
    if "disk_usage_pct" in metrics and "value" in metrics["disk_usage_pct"]:
        val = metrics["disk_usage_pct"]["value"]
        if val >= THRESHOLDS["disk_critical_pct"]:
            alerts.append({"level": "critical", "metric": "disk_usage_pct", "value": val, "threshold": THRESHOLDS["disk_critical_pct"]})
        elif val >= THRESHOLDS["disk_warning_pct"]:
            alerts.append({"level": "warning", "metric": "disk_usage_pct", "value": val, "threshold": THRESHOLDS["disk_warning_pct"]})
    
    # Memory usage
    if "memory_usage_pct" in metrics and "value" in metrics["memory_usage_pct"]:
        val = metrics["memory_usage_pct"]["value"]
        if val >= THRESHOLDS["memory_critical_pct"]:
            alerts.append({"level": "critical", "metric": "memory_usage_pct", "value": val, "threshold": THRESHOLDS["memory_critical_pct"]})
        elif val >= THRESHOLDS["memory_warning_pct"]:
            alerts.append({"level": "warning", "metric": "memory_usage_pct", "value": val, "threshold": THRESHOLDS["memory_warning_pct"]})
    
    # CPU usage
    if "cpu_usage_pct" in metrics and "value" in metrics["cpu_usage_pct"]:
        val = metrics["cpu_usage_pct"]["value"]
        if val >= THRESHOLDS["cpu_critical_pct"]:
            alerts.append({"level": "critical", "metric": "cpu_usage_pct", "value": val, "threshold": THRESHOLDS["cpu_critical_pct"]})
        elif val >= THRESHOLDS["cpu_warning_pct"]:
            alerts.append({"level": "warning", "metric": "cpu_usage_pct", "value": val, "threshold": THRESHOLDS["cpu_warning_pct"]})
    
    return alerts

def generate_report() -> Dict[str, Any]:
    """Generate full capacity report"""
    print("Fetching current metrics...")
    metrics = get_current_metrics()
    
    print("Fetching predictions...")
    predictions = get_predictions()
    
    print("Checking thresholds...")
    alerts = check_thresholds(metrics)
    
    # Calculate disk exhaustion
    disk_exhaustion = None
    if "disk_usage" in metrics and "disk_growth_rate" in metrics:
        disk_avail = metrics["disk_usage"].get("value", 0) / (1024**3)  # Convert to GB
        growth_rate = metrics["disk_growth_rate"].get("value", 0) / (1024**3) * 86400  # GB/day
        if growth_rate > 0:
            disk_exhaustion = calculate_disk_exhaustion_date(disk_avail, growth_rate)
    
    report = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "prometheus_url": PROMETHEUS_URL,
        "current_metrics": metrics,
        "predictions": predictions,
        "disk_exhaustion_estimate": disk_exhaustion,
        "alerts": alerts,
        "thresholds": THRESHOLDS
    }
    
    return report

def save_report(report: Dict[str, Any], output_dir: str) -> str:
    """Save report to file"""
    os.makedirs(output_dir, exist_ok=True)
    
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    filename = f"capacity_report_{timestamp}.json"
    filepath = os.path.join(output_dir, filename)
    
    with open(filepath, "w") as f:
        json.dump(report, f, indent=2)
    
    # Also save as latest
    latest_path = os.path.join(output_dir, "capacity_report_latest.json")
    with open(latest_path, "w") as f:
        json.dump(report, f, indent=2)
    
    return filepath

def print_summary(report: Dict[str, Any]):
    """Print human-readable summary"""
    print("\n" + "="*60)
    print("CAPACITY PLANNING REPORT")
    print("="*60)
    print(f"Generated: {report['timestamp']}")
    print(f"Prometheus: {report['prometheus_url']}")
    
    print("\n--- CURRENT METRICS ---")
    for key, data in report["current_metrics"].items():
        if "formatted" in data:
            print(f"  {data['description']}: {data['formatted']}")
        elif "error" in data:
            print(f"  {key}: ERROR - {data['error']}")
    
    print("\n--- PREDICTIONS (30-90 days) ---")
    for key, data in report["predictions"].items():
        if "formatted" in data:
            print(f"  {data['description']}: {data['formatted']}")
        elif "error" in data:
            print(f"  {key}: ERROR - {data['error']}")
    
    print("\n--- DISK EXHAUSTION ESTIMATE ---")
    if report["disk_exhaustion_estimate"]:
        print(f"  Estimated exhaustion: {report['disk_exhaustion_estimate']}")
    else:
        print("  Unable to calculate (no growth or no data)")
    
    print("\n--- ALERTS ---")
    if report["alerts"]:
        for alert in report["alerts"]:
            print(f"  [{alert['level'].upper()}] {alert['metric']}: {alert['value']:.1f} (threshold: {alert['threshold']})")
    else:
        print("  No threshold violations")
    
    print("\n" + "="*60)

def main():
    parser = argparse.ArgumentParser(description="Capacity Planning Automation")
    parser.add_argument("--prometheus-url", default=PROMETHEUS_URL, help="Prometheus URL")
    parser.add_argument("--output-dir", default=OUTPUT_DIR, help="Output directory")
    parser.add_argument("--json", action="store_true", help="Output JSON only")
    parser.add_argument("--no-save", action="store_true", help="Don't save report to file")
    args = parser.parse_args()
    
    global PROMETHEUS_URL, OUTPUT_DIR
    PROMETHEUS_URL = args.prometheus_url
    OUTPUT_DIR = args.output_dir
    
    try:
        report = generate_report()
        
        if not args.no_save:
            filepath = save_report(report, OUTPUT_DIR)
            print(f"Report saved to: {filepath}")
        
        if args.json:
            print(json.dumps(report, indent=2))
        else:
            print_summary(report)
        
        # Exit with error code if critical alerts
        critical_alerts = [a for a in report["alerts"] if a["level"] == "critical"]
        if critical_alerts:
            sys.exit(1)
        elif report["alerts"]:
            sys.exit(2)  # Warning
        else:
            sys.exit(0)
            
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(3)

if __name__ == "__main__":
    main()