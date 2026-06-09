#!/usr/bin/env python3
"""
Loki Query Helper for homelab-prod
Usage: python3 loki_query.py --query '{job="ollama"}' --since 1h
"""

import argparse
import requests
import json
import sys
from datetime import datetime, timedelta

DEFAULT_LOKI_URL = "http://localhost:3100"

def query_loki(url: str, query: str, since: str = "1h", limit: int = 100) -> dict:
    """Query Loki log API."""
    # Parse time duration
    now = datetime.now()
    unit = since[-1]
    value = int(since[:-1])
    if unit == 'h':
        start = (now - timedelta(hours=value)).isoformat() + "Z"
    elif unit == 'm':
        start = (now - timedelta(minutes=value)).isoformat() + "Z"
    elif unit == 's':
        start = (now - timedelta(seconds=value)).isoformat() + "Z"
    else:
        raise ValueError("Duration must end with h, m, or s")
    
    end = now.isoformat() + "Z"
    
    params = {
        "query": query,
        "start": start,
        "end": end,
        "limit": limit,
        "direction": "BACKWARD"
    }
    
    response = requests.get(f"{url}/loki/api/v1/query_range", params=params)
    response.raise_for_status()
    return response.json()

def query_instant(url: str, query: str) -> dict:
    """Instant query (single point)."""
    params = {"query": query}
    response = requests.get(f"{url}/loki/api/v1/query", params={"query": query})
    response.raise_for_status()
    return response.json()

def get_labels(url: str) -> list:
    """Get all available label names."""
    response = requests.get(f"{url}/loki/api/v1/label")
    response.raise_for_status()
    return response.json().get("data", [])

def get_label_values(url: str, label: str) -> list:
    """Get values for a specific label."""
    response = requests.get(f"{url}/loki/api/v1/label/{label}/values")
    response.raise_for_status()
    return response.json().get("data", [])

def main():
    parser = argparse.ArgumentParser(description="Query Loki logs")
    parser.add_argument("--url", default=DEFAULT_LOKI_URL, help="Loki URL")
    parser.add_argument("--query", required=True, help="LogQL query")
    parser.add_argument("--since", default="1h", help="Time range (e.g., 1h, 30m, 5m)")
    parser.add_argument("--limit", type=int, default=100, help="Max results")
    parser.add_argument("--format", choices=["json", "text", "raw"], default="text")
    parser.add_argument("--labels", action="store_true", help="List available labels")
    parser.add_argument("--label-values", help="Get values for a label")
    
    args = parser.parse_args()
    
    try:
        if args.labels:
            labels = get_labels(args.url)
            print(json.dumps(labels, indent=2))
            return
        
        if args.label_values:
            values = get_label_values(args.url, args.label_values)
            print(json.dumps(values, indent=2))
            return
        
        result = query_loki(args.url, args.query, args.since, args.limit)
        
        if args.format == "json":
            print(json.dumps(result, indent=2))
        elif args.format == "raw":
            data = result.get("data", {})
            for stream in data.get("result", []):
                for entry in stream.get("values", []):
                    print(f"{entry[0]} {entry[1]}")
        else:
            data = result.get("data", {})
            streams = data.get("result", [])
            if not streams:
                print("No results found")
                return
            
            print(f"Found {len(streams)} stream(s) for query: {args.query}")
            for stream in streams:
                labels = stream["stream"]
                print(f"\n=== Stream: {labels} ===")
                for entry in stream.get("values", [])[:20]:
                    timestamp, line = entry
                    dt = datetime.fromtimestamp(float(timestamp) / 1e9)
                    print(f"  {dt.isoformat()} | {line}")
                if len(stream.get("values", [])) > 20:
                    print(f"  ... and {len(stream['values']) - 20} more entries")
                    
    except requests.exceptions.RequestException as e:
        print(f"Error querying Loki: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()