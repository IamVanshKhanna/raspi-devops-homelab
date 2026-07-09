# Skills Demonstrated

This project documents the practical, hands-on skills developed and applied while building a production-grade homelab on a Raspberry Pi 4B.

---

## Infrastructure & DevOps

### Docker & Container Orchestration
- Deployed and managed multi-container applications using Docker Compose
- Designed isolated Docker networks (proxy, monitoring, apps, smarthome)
- Implemented service health checks and restart policies
- Applied resource limits and memory constraints for ARM hardware
- Used named volumes and bind mounts for persistent data

### Reverse Proxy & Networking
- Configured Traefik v3 as a dynamic reverse proxy
- Automated TLS certificate provisioning via Let's Encrypt (ACME)
- Implemented HTTP-to-HTTPS redirects and security headers
- Designed middleware chains (rate limiting, basic auth, IP whitelisting)
- Built Docker label-based service discovery

### DNS & Network Services
- Deployed Pi-hole for network-wide DNS filtering and ad blocking
- Configured custom DNS entries for local service discovery
- Set up WireGuard VPN for encrypted remote access
- Managed split-DNS for local vs external resolution

---

## Monitoring & Observability

### Prometheus
- Configured Prometheus with multi-target scrape jobs
- Monitored host metrics (node-exporter), containers (cAdvisor), and Traefik
- Designed scrape intervals and relabeling rules
- Understood time-series data models and PromQL basics

### Grafana
- Provisioned Grafana datasources and dashboard providers via code (IaC)
- Imported community dashboards (Node Exporter Full, cAdvisor, Traefik)
- Created custom panels and alert thresholds
- Configured persistent storage for dashboards and user preferences

---

## Security Engineering

- Implemented defense-in-depth: TLS, auth middleware, IP whitelisting
- Managed secrets via `.env` files, never committed to version control
- Applied strict TLS cipher suites and minimum TLS version policies
- Set HTTP security headers (HSTS, X-Frame-Options, CSP, XSS Protection)
- Used non-root Docker users where supported
- Understood OWASP best practices for self-hosted applications

---

## Linux & Systems Administration

- Configured Raspberry Pi OS for server workloads
- Enabled and tuned cgroups for Docker memory management
- Applied sysctl kernel parameters for performance optimization
- Managed systemd services and journal logs
- Wrote Bash automation scripts with error handling (`set -euo pipefail`)
- Set up automated backups with cron scheduling
- Performed file permission management for container volumes

---

## Application Services

| Service | Skills Applied |
|---------|---------------|
| Nextcloud | Self-hosted cloud storage, PHP-FPM + Nginx configuration, database management |
| Vaultwarden | Password manager deployment, admin panel hardening |
| Home Assistant | IoT platform configuration, automation workflows, integration setup |
| Pi-hole | DNS management, blocklist curation, DHCP server configuration |
| WireGuard | VPN key generation, peer configuration, firewall rules |
| Ollama | Local LLM deployment, model management, API endpoints |

---

## Software Engineering Practices

- **Infrastructure as Code**: All configuration in version-controlled files
- **Environment separation**: `.env` pattern for secrets, `.env.example` for documentation
- **Git workflow**: Atomic commits with descriptive messages
- **Documentation**: Architecture diagrams, setup guides, troubleshooting runbooks
- **DRY principles**: Shared Docker networks, reusable middleware configurations
- **Idempotency**: Setup scripts safe to run multiple times

---

## Technologies Used

`Docker` `Docker Compose` `Traefik` `Prometheus` `Grafana` `Nextcloud` `Vaultwarden` `Home Assistant` `Pi-hole` `WireGuard` `Ollama` `Bash` `YAML` `Linux` `Raspberry Pi OS` `Let's Encrypt` `Git` `GitHub`
