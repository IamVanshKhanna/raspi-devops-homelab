#!/usr/bin/env python3
"""
Pi Power Exporter - Exposes Raspberry Pi power metrics for Prometheus
Requires INA219 or similar I2C power monitor
"""

import time
import sys
import signal
from http.server import HTTPServer, BaseHTTPRequestHandler
from threading import Thread
from typing import Optional

try:
    import smbus2
    I2C_AVAILABLE = True
except ImportError:
    I2C_AVAILABLE = False
    print("Warning: smbus2 not available, INA219 support disabled")

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    print("Warning: psutil not available, system metrics limited")

# INA219 constants
INA219_ADDRESS = 0x40
INA219_REG_CONFIG = 0x00
INA219_REG_SHUNT_VOLTAGE = 0x01
INA219_REG_BUS_VOLTAGE = 0x02
INA219_REG_POWER = 0x03
INA219_REG_CURRENT = 0x04
INA219_REG_CALIBRATION = 0x05

class INA219:
    """INA219 I2C Power Monitor Driver"""
    
    def __init__(self, bus: int = 1, address: int = INA219_ADDRESS, max_expected_amps: float = 5.0):
        if not I2C_AVAILABLE:
            raise RuntimeError("smbus2 not available")
        
        self.bus = smbus2.SMBus(bus)
        self.address = address
        self.max_expected_amps = max_expected_amps
        self.current_lsb = max_expected_amps / 32768  # 15-bit signed
        self._configure()
    
    def _configure(self):
        """Configure INA219"""
        # Config: 32V range, 320mV shunt, 12-bit bus/shunt, continuous
        config = (0b00 << 13) | (0b00 << 11) | (0b1111 << 7) | (0b1111 << 3) | (0b111)
        self._write_register(INA219_REG_CONFIG, config)
        
        # Calibration
        cal = int(0.04096 / (self.current_lsb * 0.01))
        self._write_register(INA219_REG_CALIBRATION, cal)
    
    def _write_register(self, reg: int, value: int):
        self.bus.write_i2c_block_data(self.address, reg, [(value >> 8) & 0xFF, value & 0xFF])
    
    def _read_register(self, reg: int) -> int:
        data = self.bus.read_i2c_block_data(self.address, reg, 2)
        return (data[0] << 8) | data[1]
    
    def get_shunt_voltage_mV(self) -> float:
        """Get shunt voltage in mV"""
        raw = self._read_register(INA219_REG_SHUNT_VOLTAGE)
        if raw > 32767:
            raw -= 65536
        return raw * 0.01  # 10uV per LSB
    
    def get_bus_voltage_V(self) -> float:
        """Get bus voltage in V"""
        raw = self._read_register(INA219_REG_BUS_VOLTAGE)
        return (raw >> 3) * 0.004  # 4mV per LSB
    
    def get_current_mA(self) -> float:
        """Get current in mA"""
        raw = self._read_register(INA219_REG_CURRENT)
        if raw > 32767:
            raw -= 65536
        return raw * self.current_lsb * 1000
    
    def get_power_mW(self) -> float:
        """Get power in mW"""
        raw = self._read_register(INA219_REG_POWER)
        return raw * self.current_lsb * 1000 * 20  # 20x scaling factor
    
    def get_power_W(self) -> float:
        """Get power in W"""
        return self.get_power_mW() / 1000


class MockINA219:
    """Mock INA219 for testing without hardware"""
    
    def get_bus_voltage_V(self) -> float:
        return 5.0
    
    def get_current_mA(self) -> float:
        return 1000.0
    
    def get_power_W(self) -> float:
        return 5.0


class PowerMetricsCollector:
    """Collects power and system metrics"""
    
    def __init__(self, i2c_bus: int = 1, i2c_address: int = 0x40, mock: bool = False):
        self.mock = mock or not I2C_AVAILABLE
        
        if not self.mock:
            try:
                self.ina219 = INA219(bus=i2c_bus, address=i2c_address)
            except Exception as e:
                print(f"Failed to initialize INA219: {e}, using mock")
                self.mock = True
                self.ina219 = MockINA219()
        else:
            self.ina219 = MockINA219()
    
    def collect(self) -> dict:
        """Collect all power metrics"""
        metrics = {}
        
        try:
            # Power metrics from INA219
            if not self.mock:
                metrics['voltage_V'] = self.ina219.get_bus_voltage_V()
                metrics['current_mA'] = self.ina219.get_current_mA()
                metrics['power_W'] = self.ina219.get_power_W()
            else:
                metrics['voltage_V'] = 5.0
                metrics['current_mA'] = 1000.0
                metrics['power_W'] = 5.0
            
            # System metrics
            if PSUTIL_AVAILABLE:
                cpu_percent = psutil.cpu_percent(interval=0.1)
                mem = psutil.virtual_memory()
                disk = psutil.disk_usage('/')
                
                metrics['cpu_percent'] = cpu_percent
                metrics['memory_percent'] = mem.percent
                metrics['memory_used_GB'] = mem.used / (1024**3)
                metrics['memory_total_GB'] = mem.total / (1024**3)
                metrics['disk_percent'] = disk.percent
                metrics['disk_used_GB'] = disk.used / (1024**3)
                metrics['disk_total_GB'] = disk.total / (1024**3)
                
                # CPU frequency
                try:
                    freqs = psutil.cpu_freq(percpu=True)
                    if freqs:
                        metrics['cpu_freq_avg_MHz'] = sum(f.current for f in freqs) / len(freqs)
                        metrics['cpu_freq_min_MHz'] = min(f.current for f in freqs)
                        metrics['cpu_freq_max_MHz'] = max(f.current for f in freqs)
                except:
                    pass
                
                # Temperature
                try:
                    temps = psutil.sensors_temperatures()
                    if temps:
                        for name, entries in temps.items():
                            for entry in entries:
                                if entry.current:
                                    metrics[f'temp_{name}_{entry.label or "core"}_C'] = entry.current
                except:
                    pass
            
            # CPU frequency from sysfs
            try:
                with open('/sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq', 'r') as f:
                    metrics['cpu_freq_cur_MHz'] = int(f.read().strip()) / 1000
            except:
                pass
            
            try:
                with open('/sys/class/thermal/thermal_zone0/temp', 'r') as f:
                    temp = int(f.read().strip()) / 1000
                    metrics['cpu_temp_C'] = temp
            except:
                pass
            
        except Exception as e:
            print(f"Error collecting metrics: {e}")
        
        return metrics


class MetricsHandler(BaseHTTPRequestHandler):
    """HTTP handler for Prometheus metrics"""
    
    collector: PowerMetricsCollector = None
    
    def do_GET(self):
        if self.path == '/metrics':
            self.send_response(200)
            self.send_header('Content-Type', 'text/plain; version=0.0.4')
            self.end_headers()
            
            metrics = self.collector.collect()
            output = self._format_prometheus(metrics)
            self.wfile.write(output.encode())
        elif self.path == '/health':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(b'{"status": "ok"}')
        else:
            self.send_response(404)
            self.end_headers()
    
    def _format_prometheus(self, metrics: dict) -> str:
        lines = []
        for key, value in metrics.items():
            if isinstance(value, (int, float)):
                # Sanitize metric name
                metric_name = key.replace('.', '_').replace('-', '_')
                lines.append(f'pi_power_{metric_name} {value}')
        return '\n'.join(lines) + '\n'
    
    def log_message(self, format, *args):
        pass  # Suppress default logging


def run_server(collector: PowerMetricsCollector, port: int = 9090):
    """Run HTTP server for metrics"""
    PowerMetricsHandler.collector = collector
    
    server = HTTPServer(('0.0.0.0', port), PowerMetricsHandler)
    print(f"Starting power exporter on port {port}")
    
    def signal_handler(sig, frame):
        print("Shutting down...")
        server.shutdown()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Pi Power Exporter for Prometheus')
    parser.add_argument('--port', type=int, default=9090, help='HTTP port')
    parser.add_argument('--i2c-bus', type=int, default=1, help='I2C bus number')
    parser.add_argument('--i2c-address', type=lambda x: int(x, 0), default=0x40, help='I2C address')
    parser.add_argument('--mock', action='store_true', help='Use mock data (no INA219 hardware)')
    parser.add_argument('--collect-interval', type=int, default=10, help='Collection interval (seconds)')
    
    args = parser.parse_args()
    
    collector = PowerMetricsCollector(
        i2c_bus=args.i2c_bus,
        i2c_address=args.i2c_address,
        mock=args.mock
    )
    
    if args.mock:
        print("Running in MOCK mode (no INA219 hardware)")
    else:
        print("INA219 initialized successfully")
    
    # Start metrics collection thread
    def collect_loop():
        while True:
            try:
                collector.collect()
            except Exception as e:
                print(f"Collection error: {e}")
            time.sleep(args.collect_interval)
    
    collector_thread = Thread(target=collect_loop, daemon=True)
    collector_thread.start()
    
    run_server(collector, args.port)


if __name__ == '__main__':
    main()