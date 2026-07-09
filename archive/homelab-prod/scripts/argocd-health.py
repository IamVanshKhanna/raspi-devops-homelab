#!/usr/bin/env python3
"""
ArgoCD Health Check and Sync Script
Checks ArgoCD application health and triggers sync if needed
Usage: python3 argocd-health.py [--app <app-name>] [--sync] [--output text|json]
"""

import argparse
import subprocess
import json
import sys
from datetime import datetime

def run_cmd(cmd: list) -> tuple:
    """Run command and return (exit_code, stdout, stderr)."""
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode, result.stdout.strip(), result.stderr.strip()

def get_apps() -> list:
    """Get all ArgoCD applications."""
    code, stdout, stderr = run_cmd(["argocd", "app", "list", "-o", "json"])
    if code != 0:
        print(f"Error: {stderr}", file=sys.stderr)
        return []
    return json.loads(stdout)

def get_app_details(app_name: str) -> dict:
    """Get detailed info for a specific app."""
    code, stdout, stderr = run_cmd(["argocd", "app", "get", app_name, "-o", "json"])
    if code != 0:
        return {}
    return json.loads(stdout)

def sync_app(app_name: str) -> bool:
    """Sync a specific app."""
    code, stdout, stderr = run_cmd(["argocd", "app", "sync", app_name])
    return code == 0

def check_health(apps: list) -> dict:
    """Check health of all applications."""
    results = {
        "healthy": [],
        "degraded": [],
        "missing": [],
        "out_of_sync": [],
        "unknown": []
    }
    
    for app in apps:
        name = app.get("name", "")
        health = app.get("health", {})
        sync = app.get("sync", {})
        
        health_status = health.get("status", "Unknown")
        sync_status = sync.get("status", "Unknown")
        
        if health_status == "Healthy" and sync_status == "Synced":
            results["healthy"].append(name)
        elif health_status in ["Degraded", "Progressing"]:
            results["degraded"].append(name)
        elif sync_status == "OutOfSync":
            results["out_of_sync"].append(name)
        elif health_status == "Missing":
            results["missing"].append(name)
        else:
            results["unknown"].append(name)
    
    return results

def main():
    parser = argparse.ArgumentParser(description="ArgoCD Health Check and Sync")
    parser.add_argument("--app", help="Specific app to check/sync")
    parser.add_argument("--sync", action="store_true", help="Sync out-of-sync apps")
    parser.add_argument("--output", choices=["text", "json"], default="text", help="Output format")
    args = parser.parse_args()
    
    apps = get_apps()
    
    if not apps:
        print("No applications found or argocd not configured")
        sys.exit(1)
    
    if args.app:
        apps = [a for a in apps if a.get("name") == args.app]
        if not apps:
            print(f"App '{args.app}' not found")
            sys.exit(1)
    
    health_results = check_health(apps)
    
    if args.output == "json":
        print(json.dumps({
            "timestamp": datetime.now().isoformat(),
            "total": len(apps),
            "results": health_results
        }, indent=2))
        return
    
    # Text output
    print("=" * 60)
    print(f"ArgoCD Health Check - {datetime.now().isoformat()}")
    print("=" * 60)
    print(f"Total Apps: {len(apps)}")
    print(f"Healthy:      {len(health_results['healthy'])}")
    print(f"Degraded:     {len(health_results['degraded'])}")
    print(f"Out of Sync:  {len(health_results['out_of_sync'])}")
    print(f"Missing:      {len(health_results['missing'])}")
    print(f"Unknown:      {len(health_results['unknown'])}")
    print()
    
    if health_results["out_of_sync"]:
        print("OUT OF SYNC APPS:")
        for name in health_results["out_of_sync"]:
            print(f"  - {name}")
            if args.sync:
                print(f"    Syncing {name}...")
                if sync_app(name):
                    print(f"    ✓ Synced")
                else:
                    print(f"    ✗ Failed")
        print()
    
    if health_results["degraded"]:
        print("DEGRADED APPS:")
        for name in health_results["degraded"]:
            print(f"  - {name}")
        print()
    
    if health_results["missing"]:
        print("MISSING APPS:")
        for name in health_results["missing"]:
            print(f"  - {name}")
        print()
    
    if health_results["healthy"] and args.output == "text":
        print("HEALTHY APPS:")
        for name in health_results["healthy"]:
            print(f"  ✓ {name}")

if __name__ == "__main__":
    main()