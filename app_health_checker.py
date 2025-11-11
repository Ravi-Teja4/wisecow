#!/usr/bin/env python3
"""
Application Health Checker Script
Monitors application uptime and health by checking HTTP status codes
Supports multiple endpoints and provides detailed reporting
"""

import requests
import time
import datetime
import logging
import json
import sys
from typing import List, Dict
from requests.exceptions import RequestException, Timeout, ConnectionError

# Configuration
APPLICATIONS = [
    {
        'name': 'Wisecow App',
        'url': 'http://3.94.125.204:31134',
        'expected_status': 200,
        'timeout': 5
    },
    {
        'name': 'Example API',
        'url': 'https://httpbin.org/status/200',
        'expected_status': 200,
        'timeout': 10
    },
    # Add more applications here
]

CHECK_INTERVAL = 60  # seconds
LOG_FILE = '/var/log/app_health_checker.log'
REPORT_FILE = '/var/log/app_health_report.json'

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)


class ApplicationHealthChecker:
    """Health checker for web applications"""
    
    def __init__(self, app_config: Dict):
        self.name = app_config['name']
        self.url = app_config['url']
        self.expected_status = app_config.get('expected_status', 200)
        self.timeout = app_config.get('timeout', 5)
        self.history = []
        
    def check_health(self) -> Dict:
        """Check application health and return status"""
        timestamp = datetime.datetime.now().isoformat()
        
        try:
            start_time = time.time()
            response = requests.get(
                self.url,
                timeout=self.timeout,
                allow_redirects=True,
                verify=True
            )
            response_time = (time.time() - start_time) * 1000  # Convert to ms
            
            status = {
                'timestamp': timestamp,
                'application': self.name,
                'url': self.url,
                'status_code': response.status_code,
                'expected_status': self.expected_status,
                'response_time_ms': round(response_time, 2),
                'health': 'UP' if response.status_code == self.expected_status else 'DEGRADED',
                'message': self._get_status_message(response.status_code),
                'headers': dict(response.headers)
            }
            
            # Log based on health status
            if status['health'] == 'UP':
                logger.info(f"✓ {self.name} is UP - Status: {response.status_code}, Response time: {response_time:.2f}ms")
            else:
                logger.warning(f"⚠ {self.name} is DEGRADED - Expected: {self.expected_status}, Got: {response.status_code}")
                
        except Timeout:
            status = {
                'timestamp': timestamp,
                'application': self.name,
                'url': self.url,
                'status_code': None,
                'expected_status': self.expected_status,
                'response_time_ms': None,
                'health': 'DOWN',
                'message': f'Request timeout after {self.timeout} seconds',
                'error': 'TIMEOUT'
            }
            logger.error(f"✗ {self.name} is DOWN - Timeout after {self.timeout}s")
            
        except ConnectionError as e:
            status = {
                'timestamp': timestamp,
                'application': self.name,
                'url': self.url,
                'status_code': None,
                'expected_status': self.expected_status,
                'response_time_ms': None,
                'health': 'DOWN',
                'message': 'Connection failed - Application unreachable',
                'error': str(e)
            }
            logger.error(f"✗ {self.name} is DOWN - Connection failed: {str(e)}")
            
        except RequestException as e:
            status = {
                'timestamp': timestamp,
                'application': self.name,
                'url': self.url,
                'status_code': None,
                'expected_status': self.expected_status,
                'response_time_ms': None,
                'health': 'DOWN',
                'message': 'Request failed',
                'error': str(e)
            }
            logger.error(f"✗ {self.name} is DOWN - Request failed: {str(e)}")
            
        # Store history
        self.history.append(status)
        
        return status
    
    def _get_status_message(self, status_code: int) -> str:
        """Get human-readable message for HTTP status code"""
        status_messages = {
            200: 'OK - Application is functioning correctly',
            201: 'Created - Request successful',
            204: 'No Content - Request successful',
            301: 'Moved Permanently - Redirect',
            302: 'Found - Temporary redirect',
            400: 'Bad Request - Invalid request',
            401: 'Unauthorized - Authentication required',
            403: 'Forbidden - Access denied',
            404: 'Not Found - Resource does not exist',
            500: 'Internal Server Error - Application error',
            502: 'Bad Gateway - Upstream server error',
            503: 'Service Unavailable - Application temporarily unavailable',
            504: 'Gateway Timeout - Upstream timeout'
        }
        
        return status_messages.get(status_code, f'HTTP {status_code}')
    
    def get_uptime_percentage(self, hours: int = 24) -> float:
        """Calculate uptime percentage for last N hours"""
        if not self.history:
            return 0.0
            
        recent_checks = [h for h in self.history if self._is_recent(h['timestamp'], hours)]
        
        if not recent_checks:
            return 0.0
            
        up_count = sum(1 for h in recent_checks if h['health'] == 'UP')
        return (up_count / len(recent_checks)) * 100
    
    def _is_recent(self, timestamp: str, hours: int) -> bool:
        """Check if timestamp is within last N hours"""
        check_time = datetime.datetime.fromisoformat(timestamp)
        cutoff_time = datetime.datetime.now() - datetime.timedelta(hours=hours)
        return check_time > cutoff_time


def generate_report(checkers: List[ApplicationHealthChecker]):
    """Generate comprehensive health report"""
    report = {
        'generated_at': datetime.datetime.now().isoformat(),
        'summary': {
            'total_applications': len(checkers),
            'up': 0,
            'degraded': 0,
            'down': 0
        },
        'applications': []
    }
    
    print("\n" + "="*100)
    print(f"{'APPLICATION HEALTH CHECK REPORT':^100}")
    print(f"{'Generated: ' + datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'):^100}")
    print("="*100 + "\n")
    
    for checker in checkers:
        latest_status = checker.history[-1] if checker.history else None
        
        if latest_status:
            # Update summary counts
            if latest_status['health'] == 'UP':
                report['summary']['up'] += 1
            elif latest_status['health'] == 'DEGRADED':
                report['summary']['degraded'] += 1
            else:
                report['summary']['down'] += 1
            
            # App details
            app_report = {
                'name': checker.name,
                'url': checker.url,
                'current_status': latest_status['health'],
                'status_code': latest_status.get('status_code'),
                'response_time_ms': latest_status.get('response_time_ms'),
                'message': latest_status['message'],
                'uptime_24h': round(checker.get_uptime_percentage(24), 2),
                'last_check': latest_status['timestamp']
            }
            
            report['applications'].append(app_report)
            
            # Print to console
            status_symbol = {
                'UP': '✓',
                'DEGRADED': '⚠',
                'DOWN': '✗'
            }[latest_status['health']]
            
            status_color = {
                'UP': '\033[92m',
                'DEGRADED': '\033[93m',
                'DOWN': '\033[91m'
            }[latest_status['health']]
            
            reset = '\033[0m'
            
            print(f"{status_color}{status_symbol} {checker.name:<30}{reset}")
            print(f"  URL: {checker.url}")
            print(f"  Status: {latest_status['health']} | Code: {latest_status.get('status_code', 'N/A')} | "
                  f"Response Time: {latest_status.get('response_time_ms', 'N/A')}ms")
            print(f"  Message: {latest_status['message']}")
            print(f"  24h Uptime: {checker.get_uptime_percentage(24):.2f}%\n")
    
    # Print summary
    print("="*100)
    print(f"SUMMARY: UP: {report['summary']['up']} | "
          f"DEGRADED: {report['summary']['degraded']} | "
          f"DOWN: {report['summary']['down']}")
    print("="*100 + "\n")
    
    # Save report to file
    try:
        with open(REPORT_FILE, 'w') as f:
            json.dump(report, f, indent=2)
        logger.info(f"Report saved to {REPORT_FILE}")
    except Exception as e:
        logger.error(f"Failed to save report: {str(e)}")
    
    return report


def main():
    """Main health check function"""
    logger.info("Starting Application Health Checker...")
    
    # Initialize checkers
    checkers = [ApplicationHealthChecker(app) for app in APPLICATIONS]
    
    try:
        # Perform health checks
        for checker in checkers:
            checker.check_health()
        
        # Generate report
        report = generate_report(checkers)
        
        # Exit with appropriate code
        if report['summary']['down'] > 0:
            logger.error(f"{report['summary']['down']} application(s) are DOWN")
            sys.exit(1)
        elif report['summary']['degraded'] > 0:
            logger.warning(f"{report['summary']['degraded']} application(s) are DEGRADED")
            sys.exit(0)
        else:
            logger.info("All applications are UP and healthy")
            sys.exit(0)
            
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        sys.exit(2)


if __name__ == "__main__":
    main()
