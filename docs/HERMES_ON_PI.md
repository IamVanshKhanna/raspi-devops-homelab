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

## 2. Create Homelab Profile (v1.6)

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
    - cronjob-ops
    - tts-alerts
  available:
    - github-code-review
    - github-pr-workflow
    - docker-compose management
EOF
```

---

## 3. Install Skills (v1.6: 7 skills)

```bash
# homelab-ops (v1.1)
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

# gitops-helper (v1.1)
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

# backup-ops (v1.3)
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

# security-audit (v1.3)
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

# capacity-plan (v1.3)
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

# cronjob-ops (NEW v1.6)
mkdir -p ~/.hermes/profiles/homelab/skills/cronjob-ops
cat > ~/.hermes/profiles/homelab/skills/cronjob-ops/SKILL.md << 'EOF'
---
name: cronjob-ops
description: Scheduled operations and automated health summaries
version: 1.0.0
category: homelab
---

## Triggers
- "daily health summary"
- "schedule health check"
- "weekly report"
- "run cron job"

## Allowed Commands (read-only, no confirmation)
- `make verify-v1`
- `make verify-health`
- `make verify-backup`
- `./scripts/health-check.sh --quiet`
- `restic -r $RESTIC_REPOSITORY snapshots --latest 5`
- `free -h && df -h /mnt/data /mnt/backup`
- `vcgencmd measure_temp`

## Allowed Actions (require confirmation)
- **Send daily summary via Telegram**: Send formatted health summary to TELEGRAM_CHAT_ID
- **Run weekly backup verify**: `./scripts/restore-test.sh`
- **Generate weekly report**: Compile metrics, alerts, and capacity trends

## Forbidden
- Any `docker stop/rm/kill`
- Any `docker compose down`
- Any `sudo` or file writes
- Modifying cron jobs

## Context Variables
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`
- `RESTIC_REPOSITORY`
- `RESTIC_PASSWORD`
- `B2_ACCOUNT_ID`
- `B2_ACCOUNT_KEY`

## Example Usage
> "Send me a daily health summary"
> "Run the weekly backup verification"
> "Generate a weekly system report"

## Cron Schedule (systemd timer recommended)
```ini
# /etc/systemd/system/homelab-daily-summary.timer
[Unit]
Description=Daily Homelab Health Summary
Requires=homelab-daily-summary.service

[Timer]
OnCalendar=*-*-* 08:00:00
Persistent=true

[Install]
WantedBy=timers.target
```

```ini
# /etc/systemd/system/homelab-daily-summary.service
[Unit]
Description=Generate and send daily homelab health summary
After=network-online.target

[Service]
Type=oneshot
User=vansh
Environment=HOME=/home/vansh
WorkingDirectory=/home/vansh/homelab-prod
ExecStart=/home/vansh/hermes-agent/.venv/bin/hermes --profile homelab "send daily health summary via Telegram"
```
EOF

# tts-alerts (NEW v1.6)
mkdir -p ~/.hermes/profiles/homelab/skills/tts-alerts
cat > ~/.hermes/profiles/homelab/skills/tts-alerts/SKILL.md << 'EOF'
---
name: tts-alerts
description: Text-to-speech for critical alerts and notifications
version: 1.0.0
category: homelab
---

## Triggers
- "speak alert"
- "read alert"
- "announce"
- "tts"

## Allowed Commands (require confirmation)
- **Speak text via edge-tts**: `edge-tts --voice en-US-AriaNeural --text "<text>" --write-media /tmp/alert.mp3 && mpv /tmp/alert.mp3`
- **Speak text via espeak**: `espeak -v en+f3 -s 150 "<text>"`
- **Send TTS to Telegram**: Use Telegram bot API to send voice message

## Allowed Actions (require confirmation)
- **Speak critical alert**: Read alert summary aloud
- **Speak daily summary**: Read daily health summary aloud

## Forbidden
- Any unbounded TTS loops
- Speaking sensitive data (passwords, tokens, keys)
- Volume above 80%

## Context Variables
- `TTS_ENGINE` (edge-tts, espeak, pico2wave)
- `TTS_VOICE` (e.g., en-US-AriaNeural, en+f3)
- `ALERT_VOLUME` (0-100)

## Example Usage
> "Speak the critical alert: Nextcloud is down"
> "Read the daily health summary aloud"
> "Announce: Backup completed successfully"

## Systemd Service for TTS Alerts
```ini
# /etc/systemd/system/homelab-tts-alert.service
[Unit]
Description=Homelab TTS Alert
After=network.target

[Service]
Type=oneshot
User=vansh
Environment=HOME=/home/vansh
ExecStart=/usr/bin/edge-tts --voice en-US-AriaNeural --text "%i" --write-media /tmp/alert.mp3 && /usr/bin/mpv /tmp/alert.mp3

# /etc/systemd/system/homelab-tts-alert.timer
[Unit]
Description=Trigger TTS alert

[Timer]
OnCalendar=*-*-* *:*:00
Persistent=false
```

## Edge-TTS Installation
```bash
pip install edge-tts
# or
pip install --user edge-tts
```
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

## 6. Usage Examples (v1.6)

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

# Backup operations
hermes --profile homelab "list restic snapshots"
hermes --profile homelab "verify backup repository"
hermes --profile homelab "restore latest snapshot to /mnt/restore-test"

# Security audit
hermes --profile homelab "scan nextcloud image for critical vulnerabilities"
hermes --profile homelab "generate CVE report for all images"

# Capacity planning
hermes --profile homelab "when will /mnt/data run out of space"
hermes --profile homelab "generate capacity planning report"

# NEW v1.6: Cronjob operations
hermes --profile homelab "send daily health summary"
hermes --profile homelab "run weekly backup verification"
hermes --profile homelab "generate weekly system report"

# NEW v1.6: TTS alerts
hermes --profile homelab "speak the critical alert: Nextcloud is down"
hermes --profile homelab "read the daily health summary aloud"
hermes --profile homelab "announce: Backup completed successfully"
```

---

## Skills Summary (v1.6)

| Skill | Category | Trust | Auto-load | Version |
|-------|----------|-------|-----------|---------|
| `homelab-ops` | homelab | Medium | ✅ | 1.1.0 |
| `gitops-helper` | gitops | Medium | ✅ | 1.1.0 |
| `backup-ops` | backup | High | ✅ | 1.0.0 |
| `security-audit` | security | Medium | ✅ | 1.0.0 |
| `capacity-plan` | capacity | Low | ✅ | 1.0.0 |
| `cronjob-ops` | homelab | Medium | ✅ | 1.0.0 |
| `tts-alerts` | homelab | Medium | ✅ | 1.0.0 |

All 7 skills auto-loaded for maximum utility.

---

## 8. Edge-TTS Installation (for TTS alerts)

```bash
pip install edge-tts
# or
pip install --user edge-tts

# Test
edge-tts --voice en-US-AriaNeural --text "Homelab alert test" --write-media /tmp/test.mp3 && mpv /tmp/test.mp3
```