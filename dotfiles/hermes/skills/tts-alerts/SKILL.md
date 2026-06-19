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