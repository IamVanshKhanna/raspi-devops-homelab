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

## 2. Create Homelab Profile

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
  available:
    - github-code-review
    - github-pr-workflow
    - docker-compose management
EOF
```

---

## 3. Install Skills

```bash
# homelab-ops
mkdir -p ~/.hermes/profiles/homelab/skills/homelab-ops
cat > ~/.hermes/profiles/homelab/skills/homelab-ops/SKILL.md << 'EOF'
---
name: homelab-ops
description: Safe read-only homelab inspection + approved restarts
version: 1.0.0
---

## Allowed Commands (no confirmation)
- `docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'`
- `docker stats --no-stream --format 'table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}'`
- `df -h /mnt/data && df -h /mnt/backup`
- `free -h && vcgencmd measure_temp`
- `docker logs --tail 50 <service>`
- `systemctl status <service>`

## Allowed Actions (require confirmation)
- `docker compose -f /home/vansh/homelab-prod/compose/<stack>.yml restart <service>`
- `systemctl restart <service>`

## Forbidden
- `docker stop`/`rm`/`kill`
- `docker compose down`
- Any `sudo` or file writes
EOF

# gitops-helper
mkdir -p ~/.hermes/profiles/homelab/skills/gitops-helper
cat > ~/.hermes/profiles/homelab/skills/gitops-helper/SKILL.md << 'EOF'
---
name: gitops-helper
description: Read repo, propose changes to CI/Compose/Docs, user reviews
version: 1.0.0
---

## Capabilities
- Read any file in `/home/vansh/homelab-prod`
- Create/edit files under `.github/workflows/`, `compose/`, `docs/`
- Run `docker compose config` to validate
- Run `yamllint`, `markdownlint` on changes
- **Never** `git commit`/`push`/`pr create` — outputs diff + instructions
EOF
```

---

## 4. Systemd Service

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

## 6. Usage Examples

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
```