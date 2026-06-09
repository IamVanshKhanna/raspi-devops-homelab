# Hermes Agent on Pi — Install & Config

## Prerequisites
- Pi 4B 4GB with homelab-prod stack running
- Ollama + `gemma:2b` model pulled
- Tailscale for remote SSH access

---

## 1. Install Hermes (in venv)

```bash
cd /home/vansh
git clone https://github.com/NousResearch/hermes-agent.git
cd hermes-agent
python3 -m venv .venv
source .venv/bin/activate
pip install -e . --no-deps
pip install textual rich pyyaml python-dotenv
```

---

## 2. Create Homelab Profile (v1.3)

```bash
mkdir -p ~/.hermes/profiles/homelab/skills
cat > ~/.hermes/profiles/homelab/config.yaml << 'EOF'
model:
  provider: ollama
  name: gemma:2b
  base_url: http://localhost:11434/v1
  temperature: 0.3
  max_tokens: 4096

tools:
  enabled:
    - terminal
    - file
    - web
    - search
    - session_search
    - memory
    - cronjob
    - skills
  terminal:
    workdir: /home/vansh
    shell: /bin/bash
  file:
    allowed_paths:
      - /home/vansh
      - /mnt/data
      - /etc

memory:
  user_profile: |
    User: Vansh, software engineer, runs Pi 4B homelab.
    Prefers token-efficient, concise responses.
    Hardware: RPi 4B 4GB, 2TB SSD, DeskPi 3B Pro, headless.
  project_context: |
    Active homelab stacks: Traefik, Portainer, Nextcloud, Vaultwarden,
    Ollama, Home Assistant, Pi-hole, Prometheus, Grafana, WireGuard/Tailscale.
    Network: Tailscale tailnet, DNS via Pi-hole+Unbound.
    Storage: /mnt/data (Nextcloud, backups), /mnt/backup (Restic→B2).

skills:
  auto_load:
    - homelab-ops
    - gitops-helper
    - backup-ops
    - security-audit
    - capacity-plan
  available:
    - github-code-review
    - github-pr-workflow
    - docker-compose management
EOF
```

---

## 3. Install Skills (v1.3: 5 skills)

```bash
# homelab-ops (existing)
mkdir -p ~/.hermes/profiles/homelab/skills/homelab-ops
cat > ~/.hermes/profiles/homelab/skills/homelab-ops/SKILL.md << 'EOF'
---
name: homelab-ops
description: Safe read-only homelab inspection + approved restarts
version: 1.1.0
---

## Triggers
- "health check"
- "show status"
- "container status"
- "show logs for <service>"
- "restart <service>"

## Allowed Commands (no confirmation)
- `docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'`
- `docker stats --no-stream --format 'table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}'`
- `df -h /mnt/data && df -h /mnt/backup`
- `free -h && vcgencmd measure_temp`
- `docker logs --tail 50 <service>`
- `systemctl status <service>`

## Allowed Actions (require confirmation)
- `docker compose -f /home/vansh/homelab-prod/stacks/<stack>.yml restart <service>`
- `systemctl restart <service>`

## Forbidden
- `docker stop`/`rm`/`kill`
- `docker compose down`
- Any `sudo` or file writes
EOF

# gitops-helper (existing)
mkdir -p ~/.hermes/profiles/homelab/skills/gitops-helper
cat > ~/.hermes/profiles/homelab/skills/gitops-helper/SKILL.md << 'EOF'
---
name: gitops-helper
description: Read repo, propose changes to CI/Compose/Docs, user reviews
version: 1.1.0
---

## Triggers
- "add workflow"
- "propose CI change"
- "update compose"
- "create docs"

## Capabilities
- Read any file in `/home/vansh/homelab-prod`
- Create/edit files under `.github/workflows/`, `stacks/`, `docs/`
- Run `docker compose config` to validate
- Run `yamllint`, `markdownlint` on changes
- **Never** `git commit`/`push`/`pr create` — outputs diff + instructions
EOF

# backup-ops (NEW v1.3)
mkdir -p ~/.hermes/profiles/homelab/skills/backup-ops
cat > ~/.hermes/profiles/homelab/skills/backup-ops/SKILL.md << 'EOF'
---
name: backup-ops
description: Restic/B2 backup operations — list, verify, restore snapshots
version: 1.0.0
category: homelab
---

## Triggers
- "backup status"
- "list restic snapshots"
- "verify backup"
- "restore from backup"
- "when was last backup"

## Allowed Commands (read-only, no confirmation)
- `restic -r $RESTIC_REPOSITORY snapshots`
- `restic -r $RESTIC_REPOSITORY snapshots --latest 5`
- `restic -r $RESTIC_REPOSITORY snapshots --json`
- `restic -r $RESTIC_REPOSITORY check --read-data-subset=5%`
- `restic -r $RESTIC_REPOSITORY stats --mode raw-data`

## Allowed Actions (require confirmation)
- **Restore specific snapshot (dry-run)**: `restic -r $RESTIC_REPOSITORY restore <snapshot_id> --target /mnt/restore-test --dry-run`
- **Restore latest (dry-run)**: `restic -r $RESTIC_REPOSITORY restore latest --target /mnt/restore-test --dry-run`
- **Full restore (production)**: `restic -r $RESTIC_REPOSITORY restore latest --target /mnt/restore` (requires explicit "yes, restore to production")

## Forbidden
- `restic forget` (pruning)
- `restic prune`
- `restic init` (already initialized)
- Any `rm` or destructive commands

## Context Variables (from environment)
- `RESTIC_REPOSITORY`
- `RESTIC_PASSWORD`
- `B2_ACCOUNT_ID`
- `B2_ACCOUNT_KEY`

## Example Usage
> "Show me the last 3 restic snapshots"
> "Verify the backup repository integrity"
> "Restore the latest snapshot to /mnt/restore-test"
> "What's the size of the last backup?"
EOF

# security-audit (NEW v1.3)
mkdir -p ~/.hermes/profiles/homelab/skills/security-audit
cat > ~/.hermes/profiles/homelab/skills/security-audit/SKILL.md << 'EOF'
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

## Allowed Actions (require confirmation)
- **Generate Trivy SARIF for GitHub**: `trivy image --severity CRITICAL,HIGH --format sarif --output trivy.sarif <image>`
- **Update vulnerability database**: `trivy image --download-db-only`
- **Enforce policy in CI**: Add Trivy gate to GitHub Actions

## Forbidden
- Modifying running containers
- Installing packages in running containers
- Any `docker exec` with privileged commands

## Integration
- **GitHub Actions**: `.github/workflows/trivy-scan.yml` (weekly + push)
- **PR Gate**: Trivy SARIF upload to GitHub Security tab
- **Alerting**: Critical/High CVEs → Telegram via Alertmanager

## Example Usage
> "Scan the nextcloud image for critical vulnerabilities"
> "Generate a CVE report for all deployed images"
> "Check if any deployed images have unfixed high-severity CVEs"
EOF

# capacity-plan (NEW v1.3)
mkdir -p ~/.hermes/profiles/homelab/skills/capacity-plan
cat > ~/.hermes/profiles/homelab/skills/capacity-plan/SKILL.md << 'EOF'
---
name: capacity-plan
description: Resource forecasting and capacity planning for homelab
version: 1.0.0
category: homelab
---

## Triggers
- "capacity forecast"
- "disk forecast"
- "ram forecast"
- "when will disk be full"
- "resource trends"

## Allowed Commands (read-only, no confirmation)
- `df -h /mnt/data /mnt/backup`
- `free -h`
- `vcgencmd measure_temp`
- `promtool query instant 'node_filesystem_size_bytes{mountpoint="/mnt/data"}'`
- `promtool query instant 'node_filesystem_avail_bytes{mountpoint="/mnt/data"}'`
- `promtool query instant '(1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)) * 100'`

## Allowed Actions (require confirmation)
- **Generate capacity report**: Run promql queries and format as markdown
- **Project disk exhaustion**: `promtool query instant 'predict_linear(node_filesystem_avail_bytes{mountpoint="/mnt/data"}[30d], 30d)'`
- **Project RAM exhaustion**: `promtool query instant 'predict_linear(1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)[30d], 30d)'`
- **Set alert threshold**: Update Prometheus rules (requires PR)

## Forbidden
- Modifying Prometheus rules directly (requires PR)
- Changing disk partitions
- Modifying ZRAM configuration

## PromQL Queries for Forecasting

### Disk Exhaustion (30-day linear projection)
```promql
predict_linear(node_filesystem_avail_bytes{mountpoint="/mnt/data"}[30d], 30d) < 0
```

### Disk Days Remaining
```promql
node_filesystem_avail_bytes{mountpoint="/mnt/data"} / (node_filesystem_size_bytes{mountpoint="/mnt/data"} - node_filesystem_avail_bytes{mountpoint="/mnt/data"}) * 30
```

### RAM Growth Rate
```promql
rate(container_memory_usage_bytes[30d])
```

## Context Variables
- `DATA_DIR` (/mnt/data)
- `BACKUP_DIR` (/mnt/backup)
- Prometheus endpoint: `http://localhost:9090`

## Alert Thresholds (current)
- Disk warning: 80%
- Disk critical: 90%
- RAM warning: 85%
- RAM critical: 95%

## Example Usage
> "When will /mnt/data run out of space?"
> "Show me 30-day RAM usage trend"
> "Generate capacity planning report"
> "What's the disk growth rate per day?"
EOF
```

---

## 4. Systemd Service (unchanged)

```bash
sudo tee /etc/systemd/system/hermes-agent.service > /dev/null << 'EOF'
[Unit]
Description=Hermes AI Agent Daemon
After=network-online.target ollama.service tailscale.service
Wants=ollama.service tailscale.service
Requires=docker.service

[Service]
Type=simple
User=vansh
Group=vansh
WorkingDirectory=/home/vansh/hermes-agent
Environment=PATH=/home/vansh/hermes-agent/.venv/bin:/usr/local/bin:/usr/bin:/bin
Environment=HERMES_MODEL=ollama/gemma:2b
Environment=HERMES_PROVIDER=ollama
Environment=HERMES_BASE_URL=http://localhost:11434/v1
Environment=HERMES_PROFILE=homelab
Environment=PYTHONUNBUFFERED=1
ExecStartPre=/bin/sleep 10
ExecStart=/home/vansh/hermes-agent/.venv/bin/hermes --daemon --profile homelab
Restart=always
RestartSec=15
TimeoutStartSec=60
TimeoutStopSec=30
MemoryMax=600M
MemorySwapMax=1G
CPUQuota=80%
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=read-only
ReadWritePaths=/home/vansh/hermes-agent /home/vansh/.hermes

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable --now hermes-agent
journalctl -u hermes-agent -f
```

---

## 5. Test

```bash
# Local test
hermes --profile homelab "health check"

# Remote test (from laptop via Tailscale)
ssh vansh@pi4b-homelab "hermes --profile homelab 'health check'"
```

---

## 6. Usage Examples (v1.3)

```bash
# Health summary
hermes --profile homelab "health check"

# Inspect service logs
hermes --profile homelab "show last 20 logs for nextcloud"

# Restart service (asks for confirmation)
hermes --profile homelab "restart nextcloud safely"

# Propose CI change
hermes --profile homelab "add trivy scan job to .github/workflows/ci.yml"

# Check backup status
hermes --profile homelab "when was last restic snapshot and verify it"

# NEW v1.3: Backup operations
hermes --profile homelab "list restic snapshots"
hermes --profile homelab "verify backup repository"
hermes --profile homelab "restore latest snapshot to /mnt/restore-test"

# NEW v1.3: Security audit
hermes --profile homelab "scan nextcloud image for critical vulnerabilities"
hermes --profile homelab "generate CVE report for all images"

# NEW v1.3: Capacity planning
hermes --profile homelab "when will /mnt/data run out of space"
hermes --profile homelab "generate capacity planning report"
```

---

## 7. Skills Summary (v1.3)

| Skill | Category | Trust | Auto-load |
|-------|----------|-------|-----------|
| `homelab-ops` | homelab | Medium | ✅ |
| `gitops-helper` | gitops | Medium | ✅ |
| `backup-ops` | backup | High | ✅ |
| `security-audit` | security | Medium | ✅ |
| `capacity-plan` | capacity | Low | ✅ |

All 5 skills auto-loaded for maximum utility.