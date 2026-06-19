# v2.0 Migration Guide — Breaking Changes

> **⚠️ BREAKING CHANGES** — v2.0 is NOT backward compatible with v1.x
> This guide covers migration from v1.7 (Docker Compose) to v2.0 (K3s)

---

## Overview of Breaking Changes

| Area | v1.x | v2.0 | Migration Required |
|------|------|------|-------------------|
| **Orchestration** | Docker Compose | K3s (Kubernetes) | Full redeploy |
| **Secrets** | `.env` files | Infisical only | Full migration |
| **TLS/ACME** | HTTP-01 + DNS-01 | DNS-01 only (port 80 closed) | Reconfigure Traefik |
| **Auth** | Basic auth + Authelia optional | Authelia mandatory for ALL external | Update all services |
| **Service Definitions** | `docker-compose.yml` | K8s manifests + Helm | Rewrite |
| **Storage** | Local volumes + NFS | Longhorn (distributed) | Migrate data |
| **Networking** | Docker networks | CNI (Flannel) + Services/Ingress | Reconfigure |
| **Backup** | Restic → B2 (host) | Longhorn snapshots + Restic → B2 | Update scripts |

---

## Pre-Migration Checklist

### Hardware Requirements
- [ ] 2+ Raspberry Pi 4/5 (4GB+ RAM each)
- [ ] 2TB+ SSD per node (for Longhorn)
- [ ] Gigabit Ethernet switch
- [ ] UPS recommended

### Software Prerequisites
- [ ] Raspberry Pi OS Lite 64-bit (Bookworm) on all nodes
- [ ] SSH keys exchanged between nodes
- [ ] Static IPs / DHCP reservations configured
- [ ] Domain with Cloudflare DNS configured
- [ ] Cloudflare API Token with Zone:DNS:Edit permissions
- [ ] Backblaze B2 bucket created
- [ ] Telegram bot created for alerts

### Backup Current State
```bash
# On current v1.7 system
make backup
# Verify backup
make verify-backup
# Export Infisical secrets (if already using Infisical)
infisical export --format=dotenv > infisical-backup.env
```

---

## Migration Procedure

### Phase 1: Prepare New Nodes

```bash
# On each new Pi node:
# 1. Flash Raspberry Pi OS Lite 64-bit (Bookworm) to SSD
sudo raspi-config
# Advanced Options > Boot Order > USB Boot (B2)
# Reboot and remove SD card

# 2. Set static IPs
sudo nano /etc/dhcpcd.conf
# interface eth0
# static ip_address=192.168.1.50/24  # node-1
# static ip_address=192.168.1.51/24  # node-2
# static routers=192.168.1.1
# static domain_name_servers=1.1.1.1 8.8.8.8

# 3. Set hostnames
sudo hostnamectl set-hostname node-1  # or node-2, node-3
echo "192.168.1.50 node-1" | sudo tee -a /etc/hosts
echo "192.168.1.51 node-2" | sudo tee -a /etc/hosts
```

### Phase 2: Bootstrap K3s Cluster

```bash
# On node-1 (control plane)
git clone https://github.com/IamVanshKhanna/homelab-prod.git
cd homelab-prod
chmod +x scripts/k3s-cluster-setup.sh
sudo ./scripts/k3s-cluster-setup.sh

# On node-2, node-3 (workers) - run after control plane is ready
# The setup script handles worker joins automatically via k3sup
```

### Phase 3: Deploy Core Infrastructure

```bash
# Verify cluster
kubectl get nodes -o wide

# Deploy core stacks in order
make up-phase1   # Core: Traefik + Portainer
make up-phase2   # Secrets: Infisical
make up-phase3   # Auth: Authelia
make up-phase4   # Monitoring: Prometheus, Grafana, Loki, Tempo, Alertmanager
make up-phase5   # Apps: Nextcloud, Vaultwarden, Ollama
make up-phase6   # Smarthome: Home Assistant
make up-phase7   # Uptime: Uptime Kuma
make up-phase8   # Security: CrowdSec
make up-phase9   # Tracing: Tempo, OTEL
make up-phase10  # Storage: Longhorn

# Verify
make verify-v1
```

### Phase 4: Migrate Data

#### Nextcloud
```bash
# 1. Put old Nextcloud in maintenance mode
docker exec nextcloud php occ maintenance:mode --on

# 2. Export database
docker exec mariadb mysqldump -u root -p nextcloud > nextcloud-backup.sql

# 3. Copy data directory
rsync -avz /mnt/data/nextcloud/userdata/ node-1:/mnt/data/nextcloud/userdata/

# 3. Import to new cluster
kubectl exec -n databases homelab-postgres-0 -- psql -U admin -d nextcloud < nextcloud-backup.sql

# 4. Update Nextcloud config for K8s
kubectl exec -n apps nextcloud-0 -- php occ maintenance:mode --off
```

#### Vaultwarden
```bash
# 1. Export from old instance
docker exec vaultwarden sqlite3 /data/db.sqlite3 .dump > vaultwarden-backup.sql

# 2. Import to new
kubectl exec -n apps vaultwarden-0 -- sqlite3 /data/db.sqlite3 < vaultwarden-backup.sql
```

#### Home Assistant
```bash
# 1. Backup config
rsync -avz /mnt/data/homeassistant/ node-1:/mnt/data/homeassistant/

# 2. Home Assistant will auto-migrate on first start in K8s
```

#### Grafana Dashboards
```bash
# Grafana dashboards are provisioned from config - no migration needed
# Just verify: https://grafana.yourdomain.com
```

### Phase 5: Migrate Secrets to Infisical

```bash
# 1. Run migration script
./scripts/migrate-to-infisical.sh

# 2. Verify all secrets in Infisical UI
# https://infisical.yourdomain.com

# 3. Update deploy to use Infisical CLI
infisical run --projectId=... --env=production -- docker compose up -d
# OR update CI/CD to inject secrets at deploy

# 3. Remove secrets from .env
# Keep only Infisical config vars in .env
```

### Phase 6: Switch DNS & Verify

```bash
# 1. Update Cloudflare DNS to point to new Traefik IPs
# 2. Wait for DNS propagation
# 3. Test all services
make verify-v1

# 3. Run health checks
./scripts/health-check.sh --strict

# 4. Test backup/restore
make backup && make verify-backup
```

### Phase 7: Decommission Old System

```bash
# 1. Verify new system stable for 48 hours
# 2. Stop old Docker Compose stacks
cd /path/to/old/homelab-prod
make down-all

# 2. Archive old data
tar -czf homelab-v1-backup-$(date +%Y%m%d).tar.gz /mnt/data /mnt/backup
# Store in B2 or offsite

# 3. Update monitoring alerts to point to new system
```

---

## Rollback Plan

If migration fails:

```bash
# 1. Switch DNS back to old system
# 2. Restore secrets from backup
source infisical-backup.env
# 3. Start old Docker Compose
cd /path/to/old/homelab-prod
make up-all

# 3. Verify old system
make verify-v1
```

---

## Post-Migration Validation

### Automated Checks
```bash
# Full verification suite
make verify-v1

# Supply chain verification
./scripts/verify-supply-chain.sh

# Backup verification
make verify-backup
make restore-test

# Security scan
./scripts/health-check.sh --strict
```

### Manual Checks
- [ ] All services accessible via HTTPS
- [ ] Authelia SSO works for all services
- [ ] Nextcloud sync works (desktop/mobile clients)
- [ ] Vaultwarden browser extension works
- [ ] Home Assistant devices connected
- [ ] Grafana dashboards show data
- [ ] Loki logs searchable
- [ ] Tempo traces visible
- [ ] Uptime Kuma shows all green
- [ ] Backup completes without errors
- [ ] Telegram alerts received
- [ ] Tailscale access works

---

## Migration Timeline

| Phase | Duration | Downtime |
|-------|----------|----------|
| Phase 1: Prepare Nodes | 2 hours | None |
| Phase 2: K3s Bootstrap | 30 min | None |
| Phase 3: Core Deploy | 30 min | None |
| Phase 4: Data Migration | 2-4 hours | **2-4 hours** (Nextcloud/DB) |
| Phase 5: Secrets Migration | 30 min | None |
| Phase 6: DNS Switch | 30 min | **5-15 min** (DNS TTL) |
| Phase 7: Decommission | 1 hour | None |
| **Total** | **~5-8 hours** | **~2-4 hours** |

---

## Support Contacts

| Role | Contact |
|------|---------|
| Primary Admin | Vansh (self) |
| GitHub Issues | [homelab-prod/issues](https://github.com/IamVanshKhanna/homelab-prod/issues) |
| Infisical Docs | https://infisical.com/docs |
| K3s Docs | https://docs.k3s.io |
| Longhorn Docs | https://longhorn.io/docs |

---

## Post-Migration

After successful migration:
1. Update `VERSION_ROADMAP.md` to mark v2.0 complete
2. Create v2.0 release tag
3. Update `CHANGELOG.md` with migration notes
4. Archive v1.x documentation
5. Schedule v2.1 planning (Tempo + OpenTelemetry)

---

*Migration Guide Version: 1.0*
*For homelab-prod v2.0*
*Last Updated: 2026-06-09*