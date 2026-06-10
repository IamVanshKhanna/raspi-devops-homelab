# Runbook: Power Optimization / Pi Energy Issues

## Detection
- Grafana dashboard "Pi Power Consumption" shows unexpected spike
- `./scripts/pi-power-optimize.sh` reports high draw
- Prometheus alerts: `pi_power_watts > threshold`
- Electricity cost allocation report shows Pi baseline exceeded

## Diagnosis
```bash
# Current power draw
./scripts/pi-power-exporter.py --once

# Or via PromQL
curl -s "http://prometheus:9090/api/v1/query?query=pi_power_watts" | jq '.data.result[] | .metric.instance + ": " + .value[1]'

# Check optimization status
systemctl status pi-power-optimize.service

# View applied optimizations
cat /var/log/pi-power-optimize.log

# Check CPU governor
cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor
cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_max_freq
```

## v2.10 Power Optimization Setup
| Component | Configuration |
|-----------|---------------|
| Exporter | `scripts/pi-power-exporter.py` (reads INA219/VCGENCMD) |
| Optimizer | `scripts/pi-power-optimize.sh` (systemd timer: hourly) |
| Governor | `powersave` (idle), `ondemand` (load) |
| Max Freq | 1.5 GHz cap (from 1.8/2.0 GHz) |
| Disabled | WiFi, Bluetooth, HDMI, LED (if headless) |
| USB Power | Autosuspend enabled |
| Network | WoL disabled, eth0 speed 100Mbps (if sufficient) |
| Storage | SSD APM level 128 (balanced) |

## Common Causes & Fixes

### 1. CPU Governor Stuck on Performance
```bash
# Check current governor
cat /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor

# Fix: Force powersave
echo powersave | sudo tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor

# Persist: Add to pi-power-optimize.sh or /etc/rc.local
```

### 2. Frequency Cap Not Applied
```bash
# Check max freq
cat /sys/devices/system/cpu/cpu*/cpufreq/scaling_max_freq

# Fix: Cap at 1.5 GHz (1500000 kHz)
echo 1500000 | sudo tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_max_freq
```

### 3. Unnecessary Hardware Active
```bash
# Check WiFi/Bluetooth
rfkill list

# Fix: Disable if not needed
sudo rfkill block wifi
sudo rfkill block bluetooth

# Disable HDMI (headless)
/usr/bin/tvservice -o

# Disable ACT/PWR LEDs
echo none | sudo tee /sys/class/leds/ACT/trigger
echo none | sudo tee /sys/class/leds/PWR/trigger
```

### 4. USB Devices Preventing Suspend
```bash
# Check USB autosuspend
for dev in /sys/bus/usb/devices/*/power/autosuspend_delay_ms; do
  echo "1000" | sudo tee $dev
done

# Check USB wakeup
cat /proc/acpi/wakeup | grep USB
```

### 5. Exporter/Scraper Overhead
```bash
# Check Prometheus scrape interval for pi-power
# Should be ≥ 60s (default 15s may keep CPU awake)

# Fix: Update Prometheus scrape config
# scrape_interval: 60s for pi-power-exporter job
```

## Recovery Steps
1. Run optimizer manually: `sudo ./scripts/pi-power-optimize.sh`
2. Verify with exporter: `./scripts/pi-power-exporter.py --once`
3. Check governor/freq/LED status
4. Monitor for 1 hour in Grafana
5. If persistent high draw: Check for runaway process (`top`, `htop`)

## Prevention
- Hourly optimizer run via systemd timer (enabled by default)
- Daily summary: `scripts/cost_optimizer.py --power-report`
- Weekly: Compare power trend vs baseline
- Alert: `pi_power_watts > 8W` (idle baseline ~3-4W)

## Escalation
- If power >10W sustained: Check for thermal throttling (`vcgencmd measure_temp`)
- If optimizer fails: Check `journalctl -u pi-power-optimize.service`
- Hardware issue suspected: Test with fresh OS image

## Related
- Exporter: `scripts/pi-power-exporter.py` (Prometheus metrics)
- Optimizer: `scripts/pi-power-optimize.sh` (systemd service+timer)
- Cost optimizer: `scripts/cost_optimizer.py --power-report`
- Grafana dashboard: `config/grafana/provisioning/dashboards/pi-power.json`
- systemd units: `scripts/pi-power-optimize.{service,timer}`, `pi-power-exporter.{service,timer}`