# ADR-007: v2.0 Breaking Migration — Docker Compose to K3s

## Status
Accepted

## Context
v1.x used Docker Compose on a single Raspberry Pi 4B. As the homelab grows (more services, HA requirements, multi-node scaling), Docker Compose limitations become bottlenecks:

- No horizontal scaling
- No self-healing beyond restart policies
- No rolling updates
- Single point of failure (single node)
- No distributed storage (local volumes only)
- Manual secret management via `.env` files
- No rolling updates / blue-green deployments
- Limited resource management (cgroups only)

## Decision
Migrate from **Docker Compose (single-node)** to **K3s (multi-node Kubernetes)** for v2.0.

## Alternatives Considered

| Option | Pros | Cons | Decision |
|--------|------|------|----------|
| **K3s** | Lightweight (~50MB), ARM64 native, HA support, CNCF graduated | Learning curve, more complex | **Chosen** |
| **Docker Swarm** | Native Docker, simple | Deprecated, no active development, no ARM64 HA | Rejected |
| **Nomad** | Simple, flexible, HashiCorp ecosystem | Smaller community, less K8s compatibility | Rejected |
| **MicroK8s** | Canonical backed, snap install | Snap overhead, less ARM optimization | Rejected |
| **Talos** | Immutable, secure, API-driven | Steep learning curve, less community | Rejected |

## Migration Strategy

### Phased Approach
1. **v1.7** — K3s docs + Ollama K8s manifests (dual-run capability)
2. **v2.0-rc** — K3s cluster bootstrap script, dual-run validation
3. **v2.0** — Full cutover, Docker Compose deprecated

### Data Migration
- **Nextcloud**: MariaDB dump/restore + rsync data dir
- **Vaultwarden**: SQLite dump/restore
- **Home Assistant**: rsync config dir (auto-migrates)
- **Grafana**: Provisioned dashboards (no migration)
- **Prometheus/Loki/Tempo**: Fresh deploy (30d retention)

### Secret Migration
- `.env` → Infisical (complete migration before cutover)
- `.env` deprecated post-migration
- All services consume secrets via Infisical CLI at deploy time

## Breaking Changes Summary

| Component | v1.x | v2.0 | Migration |
|-----------|------|------|-----------|
| **Orchestration** | `docker compose` | `kubectl` + Helm | Rewrite manifests |
| **Secrets** | `.env` files | Infisical (only) | `scripts/migrate-to-infisical.sh` |
| **TLS** | HTTP-01 + DNS-01 | DNS-01 only | Port 80 closed |
| **Auth** | Basic + optional Authelia | Authelia mandatory | Update all ingresses |
| **Storage** | Local volumes | Longhorn (RWX) | `rsync` + PVC |
| **Networking** | Docker networks | CNI + Services/Ingress | Rewrite network config |
| **Backup** | Restic (host) | Longhorn snapshots + Restic | Update scripts |
| **Auth** | Per-service | Authelia ForwardAuth | Traefik middleware |

## Rollback Plan
1. Keep v1.7 running in parallel during validation
2. DNS switch with TTL rollback capability
3. Data sync scripts reversible
4. Infisical secrets readable by both systems during transition

## Risks & Mitigations

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Data loss during migration | Low | Critical | Pre-migration backup, verify restore |
| DNS propagation delays | Medium | Medium | Low TTL (5 min) pre-migration |
| K3s learning curve | Medium | Medium | Extensive docs, dry-run on VM |
| Longhorn stability | Low | High | Test on staging first |
| Secret migration gaps | Medium | High | Audit script + manual review |

## Success Criteria
- [ ] All services accessible via HTTPS
- [ ] Authelia SSO works for all services
- [ ] `make verify-v1` passes
- [ ] Backup/restore test passes
- [ ] Supply chain verification passes
- [ ] All Hermes skills functional
- [ ] 48h stability without issues

## Rollback Trigger
If >2 critical services fail or data loss detected:
1. Switch DNS to old system (5 min TTL)
2. Restore from pre-migration backup
3. Document failure in GitHub issue
4. Plan retry with fixes

---

*ADR-008 | 2026-06-09 | v2.0 Migration Decision*