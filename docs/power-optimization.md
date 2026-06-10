# Power/Electricity Cost Optimization for Raspberry Pi Hardware

## Overview
This document describes power optimization strategies for Raspberry Pi 4B/5 homelab clusters to minimize electricity costs while maintaining performance.

## Power Consumption Baselines

| Pi Model | Idle Power | Full Load Power | Typical Power | Monthly Cost ($0.15/kWh) |
|----------|------------|-----------------|---------------|---------------------------|
| Pi 4B 4GB | 3.0W | 7.5W | 4.5W | $0.49 |
| Pi 4B 8GB | 3.5W | 8.0W | 5.0W | $0.55 |
| Pi 5 4GB | 3.0W | 12.0W | 6.0W | $0.66 |
| Pi 5 8GB | 3.5W | 14.0W | 7.0W | $0.77 |

### Power Breakdown by Component

| Component | Power Draw | Notes |
|-----------|------------|-------|
| Pi CPU/SoC | 2-10W | Varies with load |
| NVMe SSD (PCIe) | 3-6W | Active, lower when idle |
| SATA SSD | 2-4W | Lower than NVMe |
| HDD (2.5") | 3-5W | Higher spin-up |
| Fan (PWM) | 0.5-1.5W | Variable speed |
| PoE HAT | 1-2W | Power loss in conversion |
| USB devices | 0.5-5W | Per device |

## Power Optimization Strategies

### 1. CPU Frequency Scaling

```bash
# Install cpufrequtils
sudo apt install cpufrequtils

# Set conservative governor for idle-heavy workloads
echo 'GOVERNOR="conservative"' | sudo tee /etc/default/cpufrequtils
sudo systemctl restart cpufrequtils

# Or use powersave for maximum savings
echo 'GOVERNOR="powersave"' | sudo tee /etc/default/cpufrequtils

# Or ondemand for balance (default)
echo 'GOVERNOR="ondemand"' | sudo tee /etc/default/cpufrequtils
```

### 2. CPU Frequency Limits

```bash
# Set max frequency lower for Pi 4/5
echo 1500000 | sudo tee /sys/devices/system/cpu/cpu0/cpufreq/scaling_max_freq
echo 1500000 | sudo tee /sys/devices/system/cpu/cpu1/cpufreq/scaling_max_freq
echo 1500000 | sudo tee /sys/devices/system/cpu/cpu2/cpufreq/scaling_max_freq
echo 1500000 | sudo tee /sys/devices/system/cpu/cpu3/cpufreq/scaling_max_freq

# Make persistent
echo 'echo 1500000 > /sys/devices/system/cpu/cpu0/cpufreq/scaling_max_freq' | sudo tee -a /etc/rc.local
# ... repeat for cpu1-3
```

### 3. Disable Unused Hardware

```bash
# Disable HDMI if headless
sudo sh -c 'echo "hdmi_blanking=2" >> /boot/firmware/config.txt'

# Disable WiFi/Bluetooth if using Ethernet
sudo sh -c 'echo "dtoverlay=disable-wifi" >> /boot/firmware/config.txt'
sudo sh -c 'echo "dtoverlay=disable-bt" >> /boot/firmware/config.txt'

# Disable LED activity lights
sudo sh -c 'echo "dtparam=act_led_trigger=none" >> /boot/firmware/config.txt'
sudo sh -c 'echo "dtparam=act_led_activelow=on" >> /boot/firmware/config.txt'
sudo sh -c 'echo "dtparam=pwr_led_trigger=none" >> /boot/firmware/config.txt'
sudo sh -c 'echo "dtparam=pwr_led_activelow=on" >> /boot/firmware/config.txt'

# Disable USB ports if not needed (saves ~0.5W per port)
# Add to /boot/firmware/cmdline.txt: usbcore.autosuspend=1
```

### 4. Storage Power Management

```bash
# Enable APM for HDDs (spin down when idle)
sudo hdparm -B 127 -S 120 /dev/sda  # Spin down after 10 min

# For SSDs, ensure TRIM is enabled
sudo systemctl enable fstrim.timer
sudo systemctl start fstrim.timer

# NVMe power saving
echo 1 > /sys/module/nvme/parameters/default_ps_max_latency_us
```

### 5. Network Power Management

```bash
# Disable Ethernet if using WiFi (or vice versa)
# In /boot/firmware/config.txt: dtoverlay=disable-ethernet

# Enable Ethernet EEE (Energy Efficient Ethernet)
ethtool --set-eee eth0 eee on

# Reduce link speed if 1Gbps not needed
ethtool -s eth0 speed 100 duplex full autoneg on
```

### 6. ZRAM Swap (Reduces Disk I/O)

```bash
# Already configured in homelab - 2GB ZRAM
# Reduces SD card/SSD wear and power consumption
# Check: zramctl
```

### 7. Container Resource Limits (Prevent CPU Spikes)

```yaml
# Already implemented via quotas/limits
resources:
  requests:
    cpu: "250m"
    memory: "512Mi"
  limits:
    cpu: "500m"
    memory: "1Gi"
```

## Power Monitoring

### BPi/Generic USB Power Meter
```bash
# Using INA219 I2C power monitor
# Connect to Pi I2C pins (GPIO 2/3)

# Python monitoring script
import smbus2
import time

bus = smbus2.SMBus(1)
ina219 = INA219(addr=0x40, bus=bus)

while True:
    voltage = ina219.getBusVoltage_V()
    current = ina219.getCurrent_mA()
    power = voltage * current / 1000  # Watts
    print(f"Voltage: {voltage:.2f}V, Current: {current:.0f}mA, Power: {power:.2f}W")
    time.sleep(5)
```

### Prometheus Power Exporter

```yaml
# prometheus-power-exporter.yaml
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: power-exporter
  namespace: monitoring
spec:
  selector:
    matchLabels:
      app: power-exporter
  template:
    metadata:
      labels:
        app: power-exporter
    spec:
      hostNetwork: true
      containers:
      - name: power-exporter
        image: ghcr.io/user/power-exporter:latest
        env:
        - name: I2C_BUS
          value: "1"
        - name: I2C_ADDRESS
          value: "0x40"
        ports:
        - containerPort: 9090
```

### Prometheus Metrics

```promql
# Power consumption per node (Watts)
node_power_watts

# Power cost per month
node_power_watts * 24 * 30 * 0.15 / 1000

# CPU power efficiency
rate(container_cpu_usage_seconds_total[5m]) / node_power_watts

# Power per request
rate(http_requests_total[5m]) / node_power_watts
```

## Cost Optimization Calculations

### Monthly Electricity Cost

```python
#!/usr/bin/env python3
"""
Calculate monthly electricity cost for Pi cluster
"""

# Configuration
NODES = [
    {"name": "pi4-1", "model": "Pi 4B 8GB", "idle_w": 3.5, "load_w": 8.0, "avg_load_pct": 0.3},
    {"name": "pi4-2", "model": "Pi 4B 4GB", "idle_w": 3.0, "load_w": 7.5, "avg_load_pct": 0.4},
    {"name": "pi5-1", "model": "Pi 5 8GB", "idle_w": 3.5, "load_w": 14.0, "avg_load_pct": 0.25},
]

ELECTRICITY_RATE = 0.15  # $/kWh
HOURS_PER_MONTH = 730

def calculate_monthly_cost(node):
    avg_w = node["idle_w"] + (node["load_w"] - node["idle_w"]) * node["avg_load_pct"]
    kwh_per_month = avg_w * HOURS_PER_MONTH / 1000
    return kwh_per_month * ELECTRICITY_RATE

for node in NODES:
    cost = calculate_monthly_cost(node)
    print(f"{node['name']}: {cost:.2f}/month")

# Total
total = sum(calculate_monthly_cost(n) for n in NODES)
print(f"Total: ${total:.2f}/month")
```

### Typical Monthly Costs

| Cluster Size | Configuration | Monthly Cost | Annual Cost |
|--------------|---------------|--------------|-------------|
| 1x Pi 4B 4GB | Idle 24/7 | $0.49 | $5.88 |
| 2x Pi 4B 4GB | Light load | $1.20 | $14.40 |
| 3x Pi 4B (2x 4GB, 1x 8GB) | Mixed load | $1.80 | $21.60 |
| 3x Pi 5 8GB | Moderate load | $2.30 | $27.60 |
| 4x Pi 5 (2x 4GB, 2x 8GB) | Heavy load | $3.20 | $38.40 |

## Power Optimization Checklist

- [ ] Set CPU governor to `ondemand` or `conservative`
- [ ] Set CPU max frequency to 1.5GHz (Pi 4) or 2.0GHz (Pi 5)
- [ ] Disable HDMI output if headless
- [ ] Disable WiFi/Bluetooth if using Ethernet
- [ ] Disable activity/power LEDs
- [ ] Enable SSD TRIM/discard
- [ ] Configure HDD spin-down (if using HDDs)
- [ ] Enable Ethernet EEE (Energy Efficient Ethernet)
- [ ] Set CPU max frequency limits
- [ ] Configure ZRAM swap (2GB)
- [ ] Set container resource limits
- [ ] Enable CPU frequency scaling
- [ ] Monitor power with INA219 or similar

## Cost Savings Summary

| Optimization | Power Savings | Monthly Savings | Annual Savings |
|--------------|---------------|-----------------|----------------|
| CPU governor ondemand | 15-20% | $0.30 | $3.60 |
| CPU frequency limit 1.5GHz | 10-15% | $0.18 | $2.16 |
| Disable HDMI/LEDs | 5-10% | $0.12 | $1.44 |
| Disable WiFi/BT | 3-5% | $0.06 | $0.72 |
| SSD power management | 10-15% | $0.15 | $1.80 |
| **Total** | **40-50%** | **$0.80** | **$9.60** |

### ROI Calculation

| Optimization | Effort | Annual Savings | ROI |
|--------------|--------|----------------|-----|
| CPU governor | 5 min | $4.32 | ∞ |
| Frequency limit | 5 min | $2.16 | ∞ |
| Disable peripherals | 10 min | $2.16 | ∞ |
| SSD power mgmt | 5 min | $1.80 | ∞ |
| **Total** | **25 min** | **$10.08/year** | **∞** |

## Monitoring Dashboard

### Grafana Power Dashboard

```json
{
  "panels": [
    {
      "title": "Power Consumption by Node",
      "type": "timeseries",
      "targets": [
        {"expr": "node_power_watts", "legendFormat": "{{node}}"}
      ]
    },
    {
      "title": "Monthly Electricity Cost",
      "type": "stat",
      "targets": [
        {"expr": "sum(node_power_watts) * 24 * 30 * 0.15 / 1000", "legendFormat": "Monthly Cost"}
      ]
    },
    {
      "title": "Power Efficiency (Requests/Watt)",
      "type": "timeseries",
      "targets": [
        {"expr": "sum(rate(http_requests_total[5m])) / sum(node_power_watts)", "legendFormat": "Req/Watt"}
      ]
    }
  ]
}
```

## Automation

### Systemd Service for Power Optimization

```ini
# /etc/systemd/system/pi-power-optimize.service
[Unit]
Description=Pi Power Optimization
After=network.target

[Service]
Type=oneshot
ExecStart=/usr/local/bin/pi-power-optimize.sh
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
```

```bash
# /usr/local/bin/pi-power-optimize.sh
#!/bin/bash
# Apply all power optimizations

# CPU governor
echo ondemand | tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor

# Max frequency (adjust per Pi model)
echo 1500000 > /sys/devices/system/cpu/cpu0/cpufreq/scaling_max_freq

# LED control
echo none > /sys/class/leds/led0/trigger
echo none > /sys/class/leds/led1/trigger

# USB autosuspend
echo 1 > /sys/module/usbcore/parameters/autosuspend

# SSD power management
for disk in /dev/nvme*; do
  nvme set-feature $disk -f 0x0c -v 0
done
```

### Cron Job for Periodic Optimization

```bash
# /etc/cron.d/pi-power-optimize
# Run every hour to ensure settings persist
0 * * * * root /usr/local/bin/pi-power-optimize.sh
```

## Summary

| Component | Typical Power | Optimized Power | Savings |
|-----------|---------------|-----------------|---------|
| Pi 4B 4GB (idle) | 3.0W | 2.0W | 33% |
| Pi 4B 4GB (load) | 7.5W | 5.0W | 33% |
| Pi 5 8GB (idle) | 3.5W | 2.5W | 29% |
| Pi 5 8GB (load) | 14.0W | 8.0W | 43% |

**Estimated Annual Electricity Savings: $9-15 per Pi node**

For a 4-node cluster: **$36-60/year savings** with ~30 minutes of configuration effort.