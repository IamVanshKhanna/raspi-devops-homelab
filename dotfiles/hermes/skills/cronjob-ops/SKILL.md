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