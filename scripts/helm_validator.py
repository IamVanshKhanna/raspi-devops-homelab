#!/usr/bin/env python3
"""
Helm Release Validator
Validates all Helm releases in the cluster against expected state
Usage: python3 helm_validator.py [--namespace all] [--strict]
"""

import argparse
import subprocess
import json
import sys
from typing import Dict, List, Tuple

EXPECTED_RELEASES = {
    "traefik": {"namespace": "traefik", "expected_version": "3.0.4"},
    "portainer": {"namespace": "portainer", "expected_version": "2.21.5"},
    "infisical": {"namespace": "secrets", "expected_version": "1.7.1"},
    "authelia": {"namespace": "auth", "expected_version": "4.38.0"},
    "monitoring": {"namespace": "monitoring", "expected_version": "58.0.0"},
    "loki": {"namespace": "logging", "expected_version": "5.0.0"},
    "tempo": {"namespace": "tracing", "expected_version": "1.6.0"},
    "crowdsec": {"namespace": "security", "expected_version": "1.6.0"},
    "nextcloud": {"namespace": "apps", "expected_version": "8.0.0"},
    "vaultwarden": {"namespace": "apps", "expected_version": "1.32.6"},
    "ollama": {"namespace": "ai", "expected_version": "0.3.14"},
    "homeassistant": {"namespace": "smarthome", "expected_version": "2024.7.3"},
    "uptime-kuma": {"namespace": "uptime", "expected_version": "1.23.9"},
    "longhorn": {"namespace": "longhorn-system", "expected_version": "1.6.0"},
    "cert-manager": {"namespace": "cert-manager", "expected_version": "1.13.0"},
    "external-dns": {"namespace": "external-dns", "expected_version": "1.15.0"},
    "postgres-operator": {"namespace": "postgres-system", "expected_version": "1.13.0"},
    "redis-operator": {"namespace": "databases", "expected_version": "1.1.0"},
    "authelia-db": {"namespace": "auth", "expected_version": "15.5.0"},
    "authelia-redis": {"namespace": "auth", "expected_version": "19.0.0"},
    "crowdsec-db": {"namespace": "security", "expected_version": "15.5.0"},
    "nextcloud-db": {"namespace": "databases", "expected_version": "1.13.0"},
    "vaultwarden-db": {"namespace": "databases", "expected_version": "1.13.0"},
    "redis-ha": {"namespace": "databases", "expected_version": "1.1.0"},
    "infisical-db": {"namespace": "secrets", "expected_version": "15.5.0"},
    "infisical-redis": {"namespace": "secrets", "expected_version": "19.0.0"},
    "letsencrypt-prod": {"namespace": "cert-manager", "expected_version": "1.13.0"},
}

def run_cmd(cmd: List[str]) -> Tuple[int, str, str]:
    """Run command and return (exit_code, stdout, stderr)."""
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode, result.stdout, result.stderr

def get_helm_releases(namespace: str = "all") -> List[Dict]:
    """Get all Helm releases from the cluster."""
    cmd = ["helm", "list", "--all-namespaces", "-o", "json"]
    if namespace != "all":
        cmd = ["helm", "list", "-n", namespace, "-o", "json"]
    
    code, stdout, stderr = run_cmd(cmd)
    if code != 0:
        print(f"Error running helm list: {stderr}", file=sys.stderr)
        return []
    return json.loads(stdout)

def validate_releases(releases: List[Dict], strict: bool = False) -> Tuple[int, int]:
    """Validate releases against expected state. Returns (issues, warnings)."""
    issues = 0
    warnings = 0
    
    # Group by name
    release_map = {r["name"]: r for r in releases}
    
    for name, expected in EXPECTED_RELEASES.items():
        if name not in release_map:
            print(f"❌ MISSING: {name} (expected in {expected['namespace']}, v{expected['expected_version']})")
            issues += 1
            continue
        
        release = release_map[name]
        actual_ns = release["namespace"]
        actual_ver = release["app_version"]
        status = release["status"]
        
        # Check namespace
        if actual_ns != expected["namespace"]:
            print(f"⚠️  NAMESPACE MISMATCH: {name} in {actual_ns}, expected {expected['namespace']}")
            warnings += 1
        
        # Check version (allow patch differences)
        expected_major = ".".join(expected["expected_version"].split(".")[:2])
        actual_major = ".".join(actual_ver.split(".")[:2])
        if expected_major != actual_major:
            print(f"⚠️  VERSION MISMATCH: {name} v{actual_ver}, expected v{expected['expected_version']}")
            warnings += 1
        
        # Check status
        if status != "deployed":
            print(f"❌ STATUS: {name} status={status}, expected=deployed")
            issues += 1
        else:
            print(f"✅ {name}: v{actual_ver} in {actual_ns} ({status})")
    
    # Check for unexpected releases
    for name in release_map:
        if name not in EXPECTED_RELEASES:
            print(f"ℹ️  UNTRACKED: {name} in {release_map[name]['namespace']}")
    
    return issues, warnings

def main():
    parser = argparse.ArgumentParser(description="Validate Helm releases")
    parser.add_argument("--namespace", default="all", help="Namespace to check")
    parser.add_argument("--strict", action="store_true", help="Treat warnings as errors")
    args = parser.parse_args()
    
    releases = get_helm_releases(args.namespace)
    if not releases:
        print("No releases found or error occurred")
        sys.exit(1)
    
    print(f"Found {len(releases)} releases\n")
    issues, warnings = validate_releases(releases)
    
    print(f"\nSummary: {issues} issues, {warnings} warnings")
    
    if issues > 0 or (args.strict and warnings > 0):
        sys.exit(1)
    sys.exit(0)

if __name__ == "__main__":
    main()