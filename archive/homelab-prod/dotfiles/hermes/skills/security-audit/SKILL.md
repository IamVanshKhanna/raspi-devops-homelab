---
name: security-audit
description: Security scanning and CVE triage using Trivy, Grype, and policy checks
version: 1.0.0
category: homelab
---

## Triggers
- "security scan"
- "trivy scan"
- "cve report"
- "vulnerability summary"
- "check image vulnerabilities"

## Allowed Commands (read-only, no confirmation)
- `trivy image --severity CRITICAL,HIGH <image>`
- `trivy image --severity CRITICAL,HIGH --format json <image>`
- `grype <image> --only-fixed --fail-on high`
- `docker images --format "{{.Repository}}:{{.Tag}}" | xargs -I {} trivy image --severity CRITICAL,HIGH {}`
- `kubectl get pods -A -o jsonpath="{..image}" | tr ' ' '\n' | sort -u | xargs -I {} trivy image --severity CRITICAL,HIGH {}`

## Allowed Actions (require confirmation)
- **Generate Trivy SARIF for GitHub**: `trivy image --severity CRITICAL,HIGH --format sarif --output trivy.sarif <image>`
- **Update vulnerability database**: `trivy image --download-db-only`
- **Enforce policy in CI**: Add Trivy gate to GitHub Actions

## Forbidden
- Modifying running containers
- Installing packages in running containers
- Any `docker exec` with privileged commands

## Context Variables
- `TRIVY_DB_REPOSITORY` (default: ghcr.io/aquasecurity/trivy-db:2)
- `TRIVY_JAVA_DB_REPOSITORY` (default: ghcr.io/aquasecurity/trivy-java-db:1)

## Integration
- **GitHub Actions**: `.github/workflows/trivy-scan.yml` (weekly + push)
- **PR Gate**: Trivy SARIF upload to GitHub Security tab
- **Alerting**: Critical/High CVEs → Telegram via Alertmanager

## Example Usage
> "Scan the nextcloud image for critical vulnerabilities"
> "Generate a CVE report for all deployed images"
> "Check if any deployed images have unfixed high-severity CVEs"