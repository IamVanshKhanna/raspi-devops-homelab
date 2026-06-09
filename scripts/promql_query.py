#!/usr/bin/env python3
"""
PromQL Query Helper for homelab-prod
Usage: python3 promql_query.py --query 'up == 0' --since 5m
"""

import argparse
import requests
import json
import sys
from datetime import datetime, timedelta

DEFAULT_PROM_URL = "http://localhost:9090"

def query_prometheus(url: str, query: str, since: str = "5m") -> dict:
    """Execute PromQL query."""
    unit = since[-1]
    value = int(since[:-1])
    if unit == 'h':
        start = int((datetime.now() - timedelta(hours=value)).timestamp())
    elif unit == 'm':
        start = int((datetime.now() - timedelta(minutes=value)).timestamp())
    elif unit == 's':
        start = int((datetime.now() - timedelta(seconds=value)).timestamp())
    else:
        raise ValueError("Duration must end with h, m, or s")
    
    end = int(datetime.now().timestamp())
    
    params = {
        "query": query,
        "start": start,
        "end": end,
        "step": "15s"
    }
    
    response = requests.get(f"{url}/api/v1/query_range", params=params)
    response.raise_for_status()
    return response.json()

def instant_query(url: str, query: str) -> dict:
    """Instant query."""
    params = {"query": query, "time": int(datetime.now().timestamp())}
    response = requests.get(f"{url}/api/v1/query", params=params)
    response.raise_for_status()
    return response.json()

def query_series(url: str) -> list:
    """Get all metric names."""
    params = {"match[]": "{__name__=~\".+\"}"}
    response = requests.get(f"{url}/api/v1/series", params=params)
    response.raise_for_status()
    return response.json().get("data", [])

def query_label_values(url: str, label: str) -> list:
    """Get values for a specific label."""
    response = requests.get(f"{url}/api/v1/label/{label}/values")
    response.raise_for_status()
    return response.json().get("data", [])

def main():
    parser = argparse.ArgumentParser(description="Query Prometheus metrics")
    parser.add_argument("--url", default="http://localhost:9090", help="Prometheus URL")
    parser.add_argument("--query", help="PromQL query")
    parser.add_argument("--since", default="5m", help="Time range (e.g., 5m, 1h, 6h)")
    parser.add_argument("--instant", action="store_true", help="Instant query instead of range")
    parser.add_argument("--series", action="store_true", help="List all series")
    parser.add_argument("--labels", action="store_true", help="List all label names")
    parser.add_argument("--label-values", help="Get values for a label")
    parser.add_argument("--format", choices=["json", "table", "csv"], default="table")
    
    args = parser.parse_args()
    
    try:
        if args.series:
            series = query_series(args.url)
            print(f"Total series: {len(series)}")
            for s in series[:50]:
                print(s)
            if len(series) > 50:
                print(f"... and {len(series) - 50} more")
            return
        
        if args.labels:
            series = query_series(args.url)
            labels = set()
            for s in series:
                for k in s.keys():
                    labels.add(k)
            print("Available labels:", sorted(labels))
            return
        
        if args.label_values:
            values = query_label_values(args.url, args.label_values)
            print(json.dumps(values, indent=2))
            return
        
        if not args.query:
            parser.error("--query is required unless using --series, --labels, or --label-values")
        
        if args.instant:
            result = instant_query(args.url, args.query)
        else:
            result = query_prometheus(args.url, args.query, args.since)
        
        data = result.get("data", {})
        result_type = data.get("resultType", "")
        
        if args.format == "json":
            print(json.dumps(result, indent=2))
        elif args.format == "csv":
            if result_type == "matrix":
                for series in data.get("result", []):
                    metric = series.get("metric", {})
                    for value in series.get("values", []):
                        ts, val = value
                        metric_str = ",".join(f'{k}="{v}"' for k, v in metric.items())
                        print(f"{ts},{val},{metric_str}")
        else:
            if result_type == "matrix":
                for series in data.get("result", []):
                    metric = series.get("metric", {})
                    print(f"\nSeries: {metric}")
                    for value in series.get("values", [])[:10]:
                        ts, val = value
                        dt = datetime.datetime.fromtimestamp(int(ts)).isoformat()
                        print(f"  {dt}: {val}")
                    if len(series.get("values", [])) > 10:
                        print(f"  ... and {len(series['values']) - 10} more points")
            elif result_type == "vector":
                for series in data.get("result", []):
                    metric = series.get("metric", {})
                    value = series.get("value", [0, "0"])[1]
                    print(f"{metric}: {value}")
            else:
                print(f"Result type: {result_type}")
                print(json.dumps(result, indent=2))
                
    except requests.exceptions.RequestException as e:
        print(f"Error querying Prometheus: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    import datetime
    main()