# HOMELAB CREDENTIALS REFERENCE
> Last updated: 2026-06-13 | Host: AutoBot (192.168.68.59)

## IMPORTANT SECURITY NOTICE
All credentials below marked `changeme_*` are DEFAULT/UPSECURE passwords that MUST be changed.
Services were freshly deployed with these defaults during rebuild.

---

## Service Credentials

### TRAEFIK DASHBOARD
- URL: https://192.168.68.59 (via Traefik at traefik.homelab.local)
- Username: `admin`
- Password: `<CHANGE_ME_TRAEFIK_ADMIN_PASSWORD>`
- Status: ✅ FIXED (was corrupted, now has proper bcrypt hash)

### PORTAINER
- URL: https://portainer.homelab.local (or http://192.168.68.59:9000)
- Username: Set on first visit
- Password: Set on first visit
- Status: ⚠️ Needs first-time setup

### GRAFANA
- URL: https://grafana.homelab.local (or http://192.168.68.59:3000)
- Username: `admin`
- Password: `changeme_grafana`
- Status: 🔴 CHANGE IMMEDIATELY

### NEXTCLOUD
- URL: https://cloud.homelab.local
- Username: `admin`
- Password: `changeme_nextcloud`
- Status: 🔴 CHANGE IMMEDIATELY

### VAULTWARDEN (Bitwarden)
- URL: https://vault.homelab.local
- First user: Create your account on first visit
- Admin token: `changeme_vaultwarden`
- Status: 🔴 CHANGE IMMEDIATELY

### PI-HOLE
- Web URL: http://192.168.68.59:8053/admin
- Password: `changeme_pihole`
- Status: 🔴 CHANGE IMMEDIATELY

### HOME ASSISTANT
- URL: http://192.168.68.59:8123
- Username: Set on first visit
- Password: Set on first visit
- Status: ⚠️ Needs first-time setup

### UPTIME KUMA
- URL: https://uptime.homelab.local
- Username: Set on first visit
- Password: Set on first visit
- Status: ⚠️ Needs first-time setup

### AUTHELIA (SSO)
- URL: https://auth.homelab.local
- Status: ⚠️ Currently restarting — needs debug
- JWT Secret: Set (from .env)
- Session Secret: Set (from .env)

### DATABASES (Internal - not directly accessible)

| Service | User | Password | Status |
|---------|------|----------|--------|
| MariaDB (root) | root | `changeme_root` | 🔴 CHANGE |
| MariaDB (nextcloud) | nextcloud | `changeme_db` | 🔴 CHANGE |
| Postgres (crowdsec) | crowdsec | `changeme_crowdsec_db` | 🔴 CHANGE |

### OTHER SERVICES
- **Ollama**: No auth (127.0.0.1:11434, local only)
- **WireGuard**: No web UI. Peer configs in Docker volume.
- **CrowdSec**: No web UI. Logs only.
- **Prometheus**: No auth (127.0.0.1:9090, local only)
- **Alertmanager**: No auth (127.0.0.1:9093, local only)
- **Loki**: No auth (127.0.0.1:3100, local only)

---

## HOW TO CHANGE PASSWORDS

### Pi-hole
```bash
docker exec pihole pihole -a -p NEWPASSWORD
```

### MariaDB Root
```bash
docker exec mariadb mysql -u root -p'changeme_root' -e "ALTER USER 'root'@'localhost' IDENTIFIED BY 'NEWPASSWORD';"
```
Then update MYSQL_ROOT_PASSWORD in .env

### Grafana
Login with admin/changeme_grafana → Profile → Change Password. Then update GF_SECURITY_ADMIN_PASSWORD in .env (for reference only, Grafana stores internally).

### Nextcloud
Login with admin/changeme_nextcloud → Settings → Personal → Security → Change Password. Then update NEXTCLOUD_ADMIN_PASSWORD in .env (for reference only, Nextcloud stores internally).

### Vaultwarden
Change ADMIN_TOKEN in .env and restart:
```bash
cd ~/homelab-prod
docker compose --env-file .env -f stacks/apps/docker-compose.yml up -d vaultwarden
```

---

## PORT SUMMARY

| Port | Service | Access | Auth? |
|------|---------|--------|-------|
| 22 | SSH | External | Key-based |
| 53 | Pi-hole DNS | External | No |
| 80 | Traefik HTTP | External | Redirects to 443 |
| 443 | Traefik HTTPS | External | Per-service |
| 8053 | Pi-hole Web | External | Password |
| 8123 | Home Assistant | External | User-set |
| 9090 | Prometheus | Local only | No |
| 9093 | Alertmanager | Local only | No |
| 3000 | Grafana | Local/Proxy | User: admin |
| 3100 | Loki | Local only | No |
| 9617 | Pi-hole Exporter | Local only | No |
| 11434 | Ollama | Local only | No |
| 51820 | WireGuard UDP | External | Key-based |