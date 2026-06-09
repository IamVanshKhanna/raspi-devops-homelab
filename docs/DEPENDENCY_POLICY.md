# Dependency Policy

## Image Pinning Requirements

### Mandatory
- All images MUST be pinned by tag (no `:latest`)
- Digest pinning (`@sha256:...`) is STRONGLY RECOMMENDED for production
- Base images must be from official or trusted sources

### Acceptable Formats
```yaml
# Good - tagged
image: traefik:v3.0.4

# Best - digest pinned
image: traefik@sha256:abc123...

# Bad - will fail CI
image: traefik:latest
```

### Validation
- CI checks for `:latest` tags (fails build)
- Warning for missing digest pinning
- Renovate configured for digest updates

---

## Base Image Policy

### Approved Registries
- `docker.io` (Docker Hub official images)
- `ghcr.io` (GitHub Container Registry)
- `gcr.io` / `docker.io/gcr.io` (Google)
- `quay.io` (Red Hat / Quay)

### Prohibited
- Unofficial/user images without review
- Images from unknown registries
- Images without security scanning

---

## Update Strategy

### Renovate Configuration
- Weekly batch PRs (Monday 4 AM)
- Group: docker-images
- Auto-merge: patch/minor only after Trivy pass
- Major updates: manual review required

### Emergency Updates
- CRITICAL CVE: auto-merge if patch available
- Manual trigger: `gh workflow run supply-chain.yml`

---

## Base Image Preferences

| Service | Preferred Base | Rationale |
|---------|----------------|-----------|
| Go services | `gcr.io/distroless/static` | Minimal, no shell |
| Python | `python:3.12-slim` | Small, maintained |
| Node | `node:20-alpine` | Small, security updates |
| Database | Official `postgres:16-alpine` | Minimal, patched |
| Redis | Official `redis:7-alpine` | Minimal, patched |

---

## Vulnerability Management

### Trivy Gate (supply-chain.yml)
- Fail on CRITICAL
- SARIF upload for all severities
- Weekly full scan + daily quick scan

### Response SLAs
| Severity | Response Time |
|----------|---------------|
| CRITICAL | 24 hours |
| HIGH | 72 hours |
| MEDIUM | 2 weeks |
| LOW | Next minor release |

### Exception Process
1. Document exception in GitHub issue
2. Tag `@security-team`
3. Set expiration date (max 30 days)
4. Re-evaluate at expiration

---

## SBOM & Signing

### SBOM Generation (Syft)
- Format: SPDX-JSON
- Generated per image in supply-chain.yml
- Uploaded as artifact (30-day retention)
- Available for compliance

### Image Signing (Cosign)
- Keyless signing (OIDC)
- Runs on push to main/develop (not PRs)
- SBOMs attached as attestations
- Keyless = no key management

### Verification
```bash
# Verify signature
cosign verify <image> --certificate-identity-regexp ".*" --certificate-oidc-issuer-regexp ".*"

# Verify SBOM
cosign verify-attestation --type spdx <image>
```

---

## Prohibited Practices

- Using `:latest` tag in any compose file
- Building images without scanning
- Pushing unsigned images to registry (production)
- Disabling Trivy gate in CI
- Using unapproved base images

---

## Review Process

### PR Requirements
- All compose file changes trigger supply-chain.yml
- Trivy gate must pass (no CRITICAL)
- Dependency policy must pass
- SBOM generated for new images

### Release Checklist
- [ ] All images digest-pinned
- [ ] Trivy scan clean (no CRITICAL/HIGH)
- [ ] SBOMs generated
- [ ] Images signed (Cosign)
- [ ] SBOMs available in artifacts
- [ ] Dependency policy compliant

---

## Emergency Override

For zero-day vulnerabilities requiring immediate deployment:

1. Create hotfix PR
2. Add comment: `EMERGENCY: CVE-XXXX-XXXX`
3. Tag `@security-team`
4. Override Trivy gate with justification
5. Deploy immediately
6. Track remediation in GitHub issue

---

## Tools & Versions

| Tool | Version | Purpose |
|------|---------|---------|
| Trivy | Latest | Vulnerability scanning |
| Syft | Latest | SBOM generation |
| Cosign | Latest | Keyless signing |
| Renovate | Latest | Automated updates |
| Grype | Optional | Alternative scanner |

---

## References

- [SLSA Framework](https://slsa.dev/)
- [Supply Chain Levels for Software Artifacts](https://slsa.dev/spec/v1.0/levels)
- [Cosign Keyless Signing](https://docs.sigstore.dev/cosign/overview/)
- [Syft SBOM](https://github.com/anchore/syft)
- [Trivy](https://aquasecurity.github.io/trivy/)