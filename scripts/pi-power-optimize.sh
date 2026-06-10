#!/usr/bin/env bash
# pi-power-optimize.sh - Apply power optimizations to Raspberry Pi
# Schedule: @reboot or via cron every hour

set -euo pipefail

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log() { echo -e "${GREEN}[PI-POWER]${NC} $1"; }
info() { echo -e "${BLUE}[INFO]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
fail() { echo -e "${RED}[FAIL]${NC} $1"; }

# Detect Pi model
detect_pi_model() {
    if [[ -f /proc/device-tree/model ]]; then
        MODEL=$(cat /proc/device-tree/model)
        echo "$MODEL"
    else
        echo "Unknown"
    fi
}

# Apply CPU governor
set_cpu_governor() {
    local governor="${1:-ondemand}"
    log "Setting CPU governor to: $governor"
    
    for cpu in /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor; do
        if [[ -f "$cpu" ]]; then
            echo "$governor" > "$cpu" 2>/dev/null || warn "Failed to set governor on $cpu"
        fi
    done
}

# Set CPU max frequency
set_cpu_max_freq() {
    local max_freq="${1:-1500000}"  # 1.5 GHz default
    log "Setting CPU max frequency to: ${max_freq} Hz"
    
    for cpu in /sys/devices/system/cpu/cpu*/cpufreq/scaling_max_freq; do
        if [[ -f "$cpu" ]]; then
            echo "$max_freq" > "$cpu" 2>/dev/null || warn "Failed to set max freq on $cpu"
        fi
    done
}

# Set CPU min frequency
set_cpu_min_freq() {
    local min_freq="${1:-600000}"  # 600 MHz default
    log "Setting CPU min frequency to: ${min_freq} Hz"
    
    for cpu in /sys/devices/system/cpu/cpu*/cpufreq/scaling_min_freq; do
        if [[ -f "$cpu" ]]; then
            echo "$min_freq" > "$cpu" 2>/dev/null || warn "Failed to set min freq on $cpu"
        fi
    done
}

# Disable HDMI
disable_hdmi() {
    log "Disabling HDMI output"
    # This requires config.txt change and reboot
    if ! grep -q "hdmi_blanking=2" /boot/firmware/config.txt 2>/dev/null && \
       ! grep -q "hdmi_blanking=2" /boot/config.txt 2>/dev/null; then
        info "Add 'hdmi_blanking=2' to /boot/firmware/config.txt and reboot to disable HDMI"
    fi
}

# Disable LEDs
disable_leds() {
    log "Disabling activity/power LEDs"
    
    # ACT LED (green)
    if [[ -f /sys/class/leds/led0/trigger ]]; then
        echo none > /sys/class/leds/led0/trigger 2>/dev/null || warn "Failed to disable ACT LED"
    fi
    
    # PWR LED (red)
    if [[ -f /sys/class/leds/led1/trigger ]]; then
        echo none > /sys/class/leds/led1/trigger 2>/dev/null || warn "Failed to disable PWR LED"
    fi
}

# Disable WiFi/BT if using Ethernet
disable_wireless() {
    log "Checking wireless interfaces..."
    
    # Check if Ethernet is up
    if ip link show eth0 | grep -q "UP"; then
        log "Ethernet detected, disabling WiFi/Bluetooth"
        
        # Add to config.txt if not present
        for config_file in /boot/firmware/config.txt /boot/config.txt; do
            if [[ -f "$config_file" ]]; then
                if ! grep -q "dtoverlay=disable-wifi" "$config_file"; then
                    echo "dtoverlay=disable-wifi" >> "$config_file"
                    log "Added dtoverlay=disable-wifi to $config_file"
                fi
                if ! grep -q "dtoverlay=disable-bt" "$config_file"; then
                    echo "dtoverlay=disable-bt" >> "$config_file"
                    log "Added dtoverlay=disable-bt to $config_file"
                fi
            fi
        info "WiFi/Bluetooth will be disabled after reboot"
    else
        info "Ethernet not detected, keeping WiFi/Bluetooth enabled"
    fi
}

# Enable USB autosuspend
enable_usb_autosuspend() {
    log "Enabling USB autosuspend"
    echo 1 > /sys/module/usbcore/parameters/autosuspend 2>/dev/null || warn "Failed to enable USB autosuspend"
    
    # Set autosuspend delay to 2 seconds
    for dev in /sys/bus/usb/devices/*/power/autosuspend_delay_ms; do
        if [[ -f "$dev" ]]; then
            echo 2000 > "$dev" 2>/dev/null || true
        fi
    done
    
    # Set USB power management
    for dev in /sys/bus/usb/devices/*/power/control; do
        if [[ -f "$dev" ]]; then
            echo auto > "$dev" 2>/dev/null || true
        fi
    done
}

# SSD/NVMe power management
optimize_storage_power() {
    log "Optimizing storage power management"
    
    # NVMe power management
    for nvme in /dev/nvme*; do
        if [[ -b "$nvme" ]]; then
            # Set APST (Autonomous Power State Transition) to enabled
            nvme set-feature "$nvme" -f 0x0c -v 1 2>/dev/null && \
                log "Enabled APST on $nvme" || \
                info "APST not supported on $nvme"
        fi
    done
    
    # HDD spin-down (if any rotational disks)
    for disk in /dev/sd*; do
        if [[ -b "$disk" ]] && ! [[ "$disk" =~ nvme ]]; then
            # Check if rotational
            if [[ $(cat /sys/block/$(basename "$disk")/queue/rotational 2>/dev/null) -eq 1 ]]; then
                log "Configuring spin-down for HDD: $disk"
                hdparm -B 127 -S 120 "$disk" 2>/dev/null && \
                    log "Configured spin-down for $disk (10 min)" || \
                    warn "Failed to configure spin-down for $disk"
            fi
        done
    done
}

# Network power management
optimize_network_power() {
    log "Optimizing network power management"
    
    # Enable Energy Efficient Ethernet (EEE) on eth0
    if command -v ethtool >/dev/null 2>&1; then
        ethtool --set-eee eth0 eee on 2>/dev/null && \
            log "Enabled EEE on eth0" || \
            info "EEE not supported on eth0"
    fi
}

# USB power management
optimize_usb_power() {
    log "Optimizing USB power management"
    
    # Enable USB autosuspend
    echo 1 > /sys/module/usbcore/parameters/autosuspend 2>/dev/null || true
    
    # Set autosuspend delay to 2 seconds
    for dev in /sys/bus/usb/devices/*/power/autosuspend_delay_ms; do
        if [[ -f "$dev" ]]; then
            echo 2000 > "$dev" 2>/dev/null || true
        fi
    done
    
    # Set USB power control to auto
    for dev in /sys/bus/usb/devices/*/power/control; do
        if [[ -f "$dev" ]]; then
            echo auto > "$dev" 2>/dev/null || true
        fi
    done
}

# ZRAM configuration check
check_zram() {
    log "Checking ZRAM configuration"
    
    if command -v zramctl >/dev/null 2>&1; then
        zramctl
        local zram_size=$(zramctl --noheadings --bytes --output SIZE | awk '{sum+=$1} END {print sum}')
        if [[ -n "$zram_size" && "$zram_size" -gt 0 ]]; then
            local gib=$((zram_size / 1024 / 1024 / 1024))
            log "ZRAM active: ${gib}GB"
        else
            warn "ZRAM not configured or no space allocated"
        fi
    else
        warn "zramctl not available"
    fi
}

# CPU frequency limits based on Pi model
set_pi_specific_limits() {
    local model="$(detect_pi_model)"
    log "Detected model: $model"
    
    if [[ "$model" =~ "Pi 5" ]]; then
        # Pi 5 can go up to 2.4GHz, limit to 2.0GHz for power savings
        set_cpu_max_freq 2000000
        set_cpu_min_freq 600000
    elif [[ "$model" =~ "Pi 4" ]]; then
        # Pi 4 max is 1.5GHz
        set_cpu_max_freq 1500000
        set_cpu_min_freq 600000
    else
        # Default conservative limits
        set_cpu_max_freq 1200000
        set_cpu_min_freq 600000
    fi
}

# Print current power status
print_power_status() {
    log "=== Current Power Status ==="
    
    # CPU info
    for cpu in /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor; do
        if [[ -f "$cpu" ]]; then
            local cpu_num=$(basename $(dirname "$cpu"))
            local gov=$(cat "$cpu")
            local max_freq=$(cat "${cpu/governor/scaling_max_freq}" 2>/dev/null || echo "N/A")
            local cur_freq=$(cat "${cpu/governor/scaling_cur_freq}" 2>/dev/null || echo "N/A")
            info "CPU $cpu_num: Governor=$(cat $cpu), Max=${max_freq}Hz, Current=${cur_freq}Hz"
        done
    
    # Temperature
    if [[ -f /sys/class/thermal/thermal_zone0/temp ]]; then
        local temp=$(cat /sys/class/thermal/thermal_zone0/temp)
        local temp_c=$((temp / 1000))
        info "CPU Temperature: ${temp_c}°C"
    fi
    
    # Memory
    free -h | head -2
    
    # ZRAM
    if command -v zramctl >/dev/null; then
        zramctl
    fi
}

# Main function
main() {
    log "=== Raspberry Pi Power Optimization ==="
    log "Started at $(date)"
    
    # Detect model
    local model="$(detect_pi_model)"
    info "Model: $model"
    
    # Apply optimizations
    set_cpu_governor "ondemand"
    set_pi_specific_limits
    set_cpu_min_freq 600000
    disable_leds
    disable_wireless
    enable_usb_autosuspend
    optimize_storage_power
    optimize_network_power
    optimize_usb_power
    check_zram
    
    # Print status
    print_power_status
    
    log "=== Power Optimization Complete ==="
    log "Note: Some changes (HDMI, WiFi/BT) require reboot to take effect"
}

# Run main
main "$@"