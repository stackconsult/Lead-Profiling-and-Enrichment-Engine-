"""
Reliability monitoring and health check script.
Monitors system health, performance metrics, and detects anomalies.
"""
from __future__ import annotations

import asyncio
import json
import time
import statistics
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import httpx
from backend.core.valkey import valkey_client


class ReliabilityMonitor:
    """Monitor system reliability and performance"""
    
    def __init__(self, api_base_url: str = "http://localhost:8000", api_token: str = None):
        self.api_base_url = api_base_url
        self.api_token = api_token
        self.client = httpx.Client(timeout=10.0)
        self.metrics_history = []
        self.alerts = []
    
    def check_api_health(self) -> Dict[str, Any]:
        """Check API health endpoint"""
        try:
            response = self.client.get(f"{self.api_base_url}/health")
            return {
                'healthy': response.status_code == 200,
                'status_code': response.status_code,
                'response_time_ms': (time.time() - response.elapsed.total_seconds()) * 1000,
                'response_data': response.json() if response.status_code == 200 else None
            }
        except Exception as e:
            return {
                'healthy': False,
                'status_code': 0,
                'response_time_ms': 10000,  # Timeout
                'error': str(e)
            }
    
    def check_valkey_health(self) -> Dict[str, Any]:
        """Check Valkey connection health"""
        try:
            start_time = time.time()
            valkey_client.ping()
            response_time_ms = (time.time() - start_time) * 1000
            
            # Test basic operations
            test_key = f"health-check-{int(time.time())}"
            test_value = json.dumps({"timestamp": time.time()})
            
            # Test SET
            set_start = time.time()
            valkey_client.set(test_key, test_value)
            set_time_ms = (time.time() - set_start) * 1000
            
            # Test GET
            get_start = time.time()
            retrieved = valkey_client.get(test_key)
            get_time_ms = (time.time() - get_start) * 1000
            
            # Test DELETE
            valkey_client.delete(test_key)
            
            return {
                'healthy': retrieved == test_value,
                'ping_time_ms': response_time_ms,
                'set_time_ms': set_time_ms,
                'get_time_ms': get_time_ms,
                'total_time_ms': response_time_ms + set_time_ms + get_time_ms
            }
            
        except Exception as e:
            return {
                'healthy': False,
                'error': str(e)
            }
    
    def check_workspace_operations(self) -> Dict[str, Any]:
        """Check workspace CRUD operations"""
        try:
            # Test workspace creation
            workspace_id = f"health-workspace-{int(time.time())}"
            payload = {
                "provider": "openai",
                "workspace_id": workspace_id,
                "keys": {
                    "provider": "openai",
                    "openai_key": "sk-health-test",
                    "gemini_key": "",
                    "tavily_key": ""
                }
            }
            
            headers = {}
            if self.api_token:
                headers['X-API-TOKEN'] = self.api_token
            
            # Test creation
            create_start = time.time()
            create_response = self.client.post(
                f"{self.api_base_url}/api/workspaces",
                json=payload,
                headers=headers
            )
            create_time_ms = (time.time() - create_start) * 1000
            
            # Test listing
            list_start = time.time()
            list_response = self.client.get(f"{self.api_base_url}/api/workspaces", headers=headers)
            list_time_ms = (time.time() - list_start) * 1000
            
            # Cleanup
            if create_response.status_code == 200:
                try:
                    self.client.delete(f"{self.api_base_url}/api/workspaces/{workspace_id}", headers=headers)
                except:
                    pass  # Cleanup not critical
            
            return {
                'healthy': create_response.status_code == 200 and list_response.status_code == 200,
                'create_status': create_response.status_code,
                'list_status': list_response.status_code,
                'create_time_ms': create_time_ms,
                'list_time_ms': list_time_ms,
                'total_time_ms': create_time_ms + list_time_ms
            }
            
        except Exception as e:
            return {
                'healthy': False,
                'error': str(e)
            }
    
    def check_enterprise_operations(self) -> Dict[str, Any]:
        """Check enterprise integration operations"""
        try:
            headers = {}
            if self.api_token:
                headers['X-API-TOKEN'] = self.api_token
            
            # Test enterprise status
            start_time = time.time()
            response = self.client.get(f"{self.api_base_url}/api/enterprise/status", headers=headers)
            response_time_ms = (time.time() - start_time) * 1000
            
            return {
                'healthy': response.status_code == 200,
                'status_code': response.status_code,
                'response_time_ms': response_time_ms,
                'response_data': response.json() if response.status_code == 200 else None
            }
            
        except Exception as e:
            return {
                'healthy': False,
                'error': str(e)
            }
    
    def check_memory_usage(self) -> Dict[str, Any]:
        """Check system memory usage"""
        try:
            import psutil
            process = psutil.Process()
            memory_info = process.memory_info()
            
            return {
                'healthy': True,
                'rss_mb': memory_info.rss / (1024 * 1024),
                'vms_mb': memory_info.vms / (1024 * 1024),
                'percent': process.memory_percent()
            }
        except ImportError:
            return {
                'healthy': True,
                'note': 'psutil not available for memory monitoring'
            }
        except Exception as e:
            return {
                'healthy': False,
                'error': str(e)
            }
    
    def collect_metrics(self) -> Dict[str, Any]:
        """Collect all health metrics"""
        timestamp = datetime.now()
        
        metrics = {
            'timestamp': timestamp.isoformat(),
            'api_health': self.check_api_health(),
            'valkey_health': self.check_valkey_health(),
            'workspace_health': self.check_workspace_operations(),
            'enterprise_health': self.check_enterprise_operations(),
            'memory_health': self.check_memory_usage()
        }
        
        # Calculate overall health
        health_checks = [
            metrics['api_health']['healthy'],
            metrics['valkey_health']['healthy'],
            metrics['workspace_health']['healthy'],
            metrics['enterprise_health']['healthy']
        ]
        
        metrics['overall_healthy'] = all(health_checks)
        metrics['health_score'] = sum(health_checks) / len(health_checks) * 100
        
        self.metrics_history.append(metrics)
        
        # Keep only last 100 measurements
        if len(self.metrics_history) > 100:
            self.metrics_history = self.metrics_history[-100:]
        
        return metrics
    
    def detect_anomalies(self, current_metrics: Dict[str, Any]) -> List[str]:
        """Detect anomalies in current metrics"""
        anomalies = []
        
        # Check response times
        if current_metrics['api_health'].get('response_time_ms', 0) > 5000:
            anomalies.append("API response time > 5s")
        
        if current_metrics['valkey_health'].get('total_time_ms', 0) > 1000:
            anomalies.append("Valkey operation time > 1s")
        
        if current_metrics['workspace_health'].get('total_time_ms', 0) > 3000:
            anomalies.append("Workspace operation time > 3s")
        
        # Check memory usage
        memory_mb = current_metrics['memory_health'].get('rss_mb', 0)
        if memory_mb > 500:  # 500MB threshold
            anomalies.append(f"High memory usage: {memory_mb:.1f}MB")
        
        # Check health score trend
        if len(self.metrics_history) >= 5:
            recent_scores = [m['health_score'] for m in self.metrics_history[-5:]]
            if all(score < 80 for score in recent_scores):
                anomalies.append("Consistently low health scores")
        
        return anomalies
    
    def generate_alerts(self, metrics: Dict[str, Any]) -> List[str]:
        """Generate alerts based on metrics"""
        alerts = []
        
        if not metrics['overall_healthy']:
            alerts.append("🚨 CRITICAL: System health check failed")
        
        # Component-specific alerts
        if not metrics['api_health']['healthy']:
            alerts.append("🔴 API endpoint unhealthy")
        
        if not metrics['valkey_health']['healthy']:
            alerts.append("🔴 Valkey connection unhealthy")
        
        if not metrics['workspace_health']['healthy']:
            alerts.append("🔴 Workspace operations unhealthy")
        
        if not metrics['enterprise_health']['healthy']:
            alerts.append("🔴 Enterprise operations unhealthy")
        
        # Performance alerts
        api_time = metrics['api_health'].get('response_time_ms', 0)
        if api_time > 2000:
            alerts.append(f"⚠️ Slow API response: {api_time:.0f}ms")
        
        valkey_time = metrics['valkey_health'].get('total_time_ms', 0)
        if valkey_time > 500:
            alerts.append(f"⚠️ Slow Valkey operations: {valkey_time:.0f}ms")
        
        # Memory alerts
        memory_mb = metrics['memory_health'].get('rss_mb', 0)
        if memory_mb > 300:
            alerts.append(f"⚠️ High memory usage: {memory_mb:.1f}MB")
        
        return alerts
    
    def calculate_performance_stats(self) -> Dict[str, Any]:
        """Calculate performance statistics from history"""
        if not self.metrics_history:
            return {}
        
        recent_metrics = self.metrics_history[-20:]  # Last 20 measurements
        
        # API performance
        api_times = [m['api_health'].get('response_time_ms', 0) for m in recent_metrics if m['api_health']['healthy']]
        if api_times:
            api_stats = {
                'avg_ms': statistics.mean(api_times),
                'min_ms': min(api_times),
                'max_ms': max(api_times),
                'p95_ms': statistics.quantiles(api_times, n=20)[18] if len(api_times) > 20 else max(api_times)
            }
        else:
            api_stats = {}
        
        # Valkey performance
        valkey_times = [m['valkey_health'].get('total_time_ms', 0) for m in recent_metrics if m['valkey_health']['healthy']]
        if valkey_times:
            valkey_stats = {
                'avg_ms': statistics.mean(valkey_times),
                'min_ms': min(valkey_times),
                'max_ms': max(valkey_times),
                'p95_ms': statistics.quantiles(valkey_times, n=20)[18] if len(valkey_times) > 20 else max(valkey_times)
            }
        else:
            valkey_stats = {}
        
        # Health score trend
        health_scores = [m['health_score'] for m in recent_metrics]
        health_trend = "stable"
        if len(health_scores) >= 5:
            recent_avg = statistics.mean(health_scores[-3:])
            older_avg = statistics.mean(health_scores[-6:-3])
            if recent_avg > older_avg + 5:
                health_trend = "improving"
            elif recent_avg < older_avg - 5:
                health_trend = "degrading"
        
        return {
            'api_performance': api_stats,
            'valkey_performance': valkey_stats,
            'health_trend': health_trend,
            'avg_health_score': statistics.mean(health_scores),
            'min_health_score': min(health_scores),
            'max_health_score': max(health_scores)
        }
    
    def print_health_report(self, metrics: Dict[str, Any]):
        """Print comprehensive health report"""
        print("\n🏥 SYSTEM HEALTH REPORT")
        print("=" * 60)
        print(f"Timestamp: {metrics['timestamp']}")
        print(f"Overall Health: {'✅ HEALTHY' if metrics['overall_healthy'] else '🔴 UNHEALTHY'}")
        print(f"Health Score: {metrics['health_score']:.1f}%")
        
        print("\n📊 Component Status:")
        components = [
            ('API', metrics['api_health']),
            ('Valkey', metrics['valkey_health']),
            ('Workspaces', metrics['workspace_health']),
            ('Enterprise', metrics['enterprise_health']),
            ('Memory', metrics['memory_health'])
        ]
        
        for name, health in components:
            status = "✅" if health['healthy'] else "🔴"
            print(f"   {status} {name}: {'Healthy' if health['healthy'] else 'Unhealthy'}")
            
            if not health['healthy'] and 'error' in health:
                print(f"      Error: {health['error']}")
        
        # Performance stats
        stats = self.calculate_performance_stats()
        if stats:
            print(f"\n⚡ Performance (Last 20 checks):")
            
            if stats.get('api_performance'):
                api_perf = stats['api_performance']
                print(f"   API: {api_perf['avg_ms']:.1f}ms avg, {api_perf['p95_ms']:.1f}ms p95")
            
            if stats.get('valkey_performance'):
                valkey_perf = stats['valkey_performance']
                print(f"   Valkey: {valkey_perf['avg_ms']:.1f}ms avg, {valkey_perf['p95_ms']:.1f}ms p95")
            
            print(f"   Health Trend: {stats['health_trend']}")
            print(f"   Health Score: {stats['avg_health_score']:.1f}% avg")
        
        # Alerts
        alerts = self.generate_alerts(metrics)
        if alerts:
            print(f"\n🚨 Alerts:")
            for alert in alerts:
                print(f"   {alert}")
        
        # Anomalies
        anomalies = self.detect_anomalies(metrics)
        if anomalies:
            print(f"\n🔍 Anomalies Detected:")
            for anomaly in anomalies:
                print(f"   • {anomaly}")
        
        print("=" * 60)
    
    async def start_monitoring(self, interval_seconds: int = 30, duration_minutes: int = 10):
        """Start continuous monitoring"""
        print(f"🔍 Starting reliability monitoring (every {interval_seconds}s for {duration_minutes} minutes)")
        
        end_time = time.time() + (duration_minutes * 60)
        check_count = 0
        
        while time.time() < end_time:
            check_count += 1
            print(f"\n🔍 Health Check #{check_count}")
            
            metrics = self.collect_metrics()
            self.print_health_report(metrics)
            
            if time.time() < end_time:
                await asyncio.sleep(interval_seconds)
        
        print(f"\n✅ Monitoring completed after {check_count} checks")
        
        # Final summary
        stats = self.calculate_performance_stats()
        if stats:
            print(f"\n📈 MONITORING SUMMARY")
            print(f"   Total Checks: {len(self.metrics_history)}")
            print(f"   Avg Health Score: {stats['avg_health_score']:.1f}%")
            print(f"   Health Trend: {stats['health_trend']}")


async def run_reliability_monitor():
    """Run reliability monitoring with default settings"""
    monitor = ReliabilityMonitor()
    await monitor.start_monitoring(interval_seconds=30, duration_minutes=5)


if __name__ == "__main__":
    asyncio.run(run_reliability_monitor())
