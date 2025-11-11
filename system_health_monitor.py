#!/usr/bin/env python3
"""
System Health Monitoring Script
Monitors CPU, Memory, Disk usage and running processes
Sends alerts when thresholds are exceeded
"""

import psutil
import datetime
import logging
import sys
from pathlib import Path

# Configuration
THRESHOLDS = {
    'cpu_percent': 80,
    'memory_percent': 80,
    'disk_percent': 85,
    'process_count': 300
}

LOG_FILE = '/var/log/system_health_monitor.log'
ALERT_LOG = '/var/log/system_health_alerts.log'

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout)
    ]
)

alert_logger = logging.getLogger('alerts')
alert_handler = logging.FileHandler(ALERT_LOG)
alert_handler.setFormatter(logging.Formatter('%(asctime)s - ALERT - %(message)s'))
alert_logger.addHandler(alert_handler)
alert_logger.setLevel(logging.WARNING)


def check_cpu_usage():
    """Monitor CPU usage"""
    cpu_percent = psutil.cpu_percent(interval=1)
    cpu_per_core = psutil.cpu_percent(interval=1, percpu=True)

    status = {
        'metric': 'CPU',
        'value': cpu_percent,
        'threshold': THRESHOLDS['cpu_percent'],
        'status': 'OK',
        'details': f"Per core: {cpu_per_core}"
    }

    if cpu_percent > THRESHOLDS['cpu_percent']:
        status['status'] = 'CRITICAL'
        alert_logger.warning(f"CPU usage critical: {cpu_percent}% (Threshold: {THRESHOLDS['cpu_percent']}%)")

    return status


def check_memory_usage():
    """Monitor memory usage"""
    memory = psutil.virtual_memory()
    swap = psutil.swap_memory()

    status = {
        'metric': 'Memory',
        'value': memory.percent,
        'threshold': THRESHOLDS['memory_percent'],
        'status': 'OK',
        'details': f"Used: {memory.used / (1024**3):.2f}GB / Total: {memory.total / (1024**3):.2f}GB, Swap: {swap.percent}%"
    }

    if memory.percent > THRESHOLDS['memory_percent']:
        status['status'] = 'CRITICAL'
        alert_logger.warning(f"Memory usage critical: {memory.percent}% (Threshold: {THRESHOLDS['memory_percent']}%)")

    return status


def check_disk_usage():
    """Monitor disk usage for all partitions"""
    disk_status = []

    for partition in psutil.disk_partitions():
        try:
            usage = psutil.disk_usage(partition.mountpoint)

            status = {
                'metric': f'Disk ({partition.mountpoint})',
                'value': usage.percent,
                'threshold': THRESHOLDS['disk_percent'],
                'status': 'OK',
                'details': f"Used: {usage.used / (1024**3):.2f}GB / Total: {usage.total / (1024**3):.2f}GB"
            }

            if usage.percent > THRESHOLDS['disk_percent']:
                status['status'] = 'CRITICAL'
                alert_logger.warning(
                    f"Disk usage critical on {partition.mountpoint}: {usage.percent}% "
                    f"(Threshold: {THRESHOLDS['disk_percent']}%)"
                )

            disk_status.append(status)

        except PermissionError:
            continue

    return disk_status


def check_running_processes():
    """Monitor running processes"""
    process_count = len(psutil.pids())

    # Get top 5 CPU consuming processes
    processes = []
    for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
        try:
            processes.append(proc.info)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

    top_processes = sorted(processes, key=lambda x: x['cpu_percent'], reverse=True)[:5]

    status = {
        'metric': 'Processes',
        'value': process_count,
        'threshold': THRESHOLDS['process_count'],
        'status': 'OK',
        'details': f"Top CPU consumers: {[f\"{p['name']}({p['cpu_percent']:.1f}%)\" for p in top_processes]}"
    }

    if process_count > THRESHOLDS['process_count']:
        status['status'] = 'WARNING'
        alert_logger.warning(
            f"High process count: {process_count} (Threshold: {THRESHOLDS['process_count']})"
        )

    return status


def print_report(results):
    """Print formatted health report"""
    print("\n" + "="*80)
    print(f"{'SYSTEM HEALTH MONITORING REPORT':^80}")
    print(f"{'Generated: ' + datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'):^80}")
    print("="*80 + "\n")

    for result in results:
        if isinstance(result, list):
            for item in result:
                print_status(item)
        else:
            print_status(result)

    print("\n" + "="*80 + "\n")


def print_status(status):
    """Print individual metric status"""
    status_symbol = "✓" if status['status'] == 'OK' else "✗"
    status_color = "\033[92m" if status['status'] == 'OK' else "\033[91m"
    reset_color = "\033[0m"

    print(f"{status_color}{status_symbol} {status['metric']:<20}{reset_color} "
          f"Current: {status['value']:.1f}% | Threshold: {status['threshold']}% | "
          f"Status: {status['status']}")
    print(f"  Details: {status['details']}\n")


def main():
    """Main monitoring function"""
    logging.info("Starting system health check...")

    try:
        results = [
            check_cpu_usage(),
            check_memory_usage(),
            check_disk_usage(),
            check_running_processes()
        ]

        print_report(results)

        # Check if any critical alerts
        critical_count = sum(1 for r in results if isinstance(r, dict) and r['status'] == 'CRITICAL')
        critical_count += sum(1 for r in results if isinstance(r, list) for item in r if item['status'] == 'CRITICAL')

        if critical_count > 0:
            logging.error(f"System health check completed with {critical_count} CRITICAL alert(s)")
            sys.exit(1)
        else:
            logging.info("System health check completed successfully - All metrics within thresholds")
            sys.exit(0)

    except Exception as e:
        logging.error(f"Error during health check: {str(e)}")
        sys.exit(2)


if __name__ == "__main__":
    main()
