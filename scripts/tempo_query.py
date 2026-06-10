#!/usr/bin/env python3
"""
Tempo Trace Query Helper
Usage: python3 tempo_query.py --service ollama --operation generate --since 1h
"""

import argparse
import requests
import json
import sys
from datetime import datetime, timedelta

DEFAULT_TEMPO_URL = "http://localhost:3200"

def query_traces(url: str, service: str = None, operation: str = None, since: str = "1h", limit: int = 50) -> dict:
    """Query Tempo for traces."""
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
    
    end = datetime.now().isoformat() + "Z"
    
    tags = []
    if service:
        tags.append(f'service.name="{service}"')
    if operation:
        tags.append(f'operation=~"{operation}.*"')
    
    tag_query = " && ".join(tags) if tags else ""
    
    params = {
        "tags": tag_query,
        "start": start,
        "end": end,
        "limit": limit
    }
    
    response = requests.get(f"{url}/api/traces", params=params)
    response.raise_for_status()
    return response.json()

def get_trace(url: str, trace_id: str) -> dict:
    """Get full trace details."""
    response = requests.get(f"{url}/api/traces/{trace_id}")
    response.raise_for_status()
    return response.json()

def search_traces(url: str, service: str, min_duration: str = None, since: str = "1h") -> dict:
    """Search for slow traces."""
    unit = since[-1]
    value = int(since[:-1])
    if unit == 'h':
        start = (datetime.now() - timedelta(hours=value)).isoformat() + "Z"
    elif unit == 'm':
        start = (datetime.now() - timedelta(minutes=value)).isoformat() + "Z"
    else:
        start = (datetime.now() - timedelta(seconds=value)).isoformat() + "Z"
    
    end = datetime.now().isoformat() + "Z"
    
    query = f'service.name="{service}"'
    if min_duration:
        query += f' && duration > {min_duration}'
    
    params = {
        "tags": f'service.name="{service}"',
        "start": (datetime.now() - timedelta(hours=1)).isoformat() + "Z",
        "end": datetime.now().isoformat() + "Z",
        "limit": 50
    }
    
    response = requests.get(f"{url}/api/traces", params=params)
    response.raise_for_status()
    return response.json()

def main():
    parser = argparse.ArgumentParser(description="Query Tempo traces")
    parser.add_argument("--url", default="http://localhost:3200", help="Tempo URL")
    parser.add_argument("--service", help="Service name filter")
    parser.add_argument("--operation", help="Operation name filter")
    parser.add_argument("--since", default="1h", help="Time range (e.g., 1h, 30m)")
    parser.add_argument("--limit", type=int, default=20, help="Max traces")
    parser.add_argument("--trace-id", help="Get full trace by ID")
    parser.add_argument("--format", choices=["json", "summary"], default="summary")
    
    args = parser.parse_args()
    
    try:
        if args.trace_id:
            result = get_trace(args.url, args.trace_id)
            print(json.dumps(result, indent=2))
            return
        
        result = query_traces(args.url, args.service, args.operation, args.since, args.limit)
        
        if args.format == "json":
            print(json.dumps(result, indent=2))
        else:
            traces = result.get("traces", [])
            print(f"Found {len(traces)} traces")
            for trace in traces:
                trace_id = trace.get("traceID", "unknown")
                root_span = trace.get("spans", [{}])[0] if trace.get("spans") else {}
                service_name = root_span.get("serviceName", "unknown")
                operation = root_span.get("name", "unknown")
                duration_ms = root_span.get("duration", 0) / 1e6
                start_time = root_span.get("startTime", "")
                
                print(f"\nTrace: {trace_id}")
                print(f"  Service: {service_name}")
                print(f"  Operation: {operation}")
                print(f"  Duration: {duration_ms:.2f}ms")
                print(f"  Start: {start_time}")
                
    except requests.exceptions.RequestException as e:
        print(f"Error querying Tempo: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()