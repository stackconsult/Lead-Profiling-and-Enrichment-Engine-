"""
API load testing script for continuous reliability monitoring.
Tests endpoints under realistic load patterns.
"""
from __future__ import annotations

import asyncio
import json
import time
import random
from typing import Dict, List, Any
import httpx
from concurrent.futures import ThreadPoolExecutor, as_completed


class APILoadTester:
    """Load tester for API endpoints"""
    
    def __init__(self, base_url: str, api_token: str = None):
        self.base_url = base_url
        self.api_token = api_token
        self.session = httpx.Client(timeout=30.0)
        self.results = []
    
    def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make HTTP request with timing"""
        start_time = time.time()
        try:
            headers = kwargs.pop('headers', {})
            if self.api_token:
                headers['X-API-TOKEN'] = self.api_token
            
            response = self.session.request(
                method, 
                f"{self.base_url}{endpoint}", 
                headers=headers,
                **kwargs
            )
            
            duration_ms = (time.time() - start_time) * 1000
            
            return {
                'success': response.status_code < 400,
                'status_code': response.status_code,
                'duration_ms': duration_ms,
                'response_size': len(response.content),
                'endpoint': endpoint,
                'method': method
            }
            
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            return {
                'success': False,
                'status_code': 0,
                'duration_ms': duration_ms,
                'response_size': 0,
                'endpoint': endpoint,
                'method': method,
                'error': str(e)
            }
    
    def test_health_endpoint(self, requests: int = 100) -> List[Dict[str, Any]]:
        """Load test health endpoint"""
        print(f"🏥 Testing health endpoint with {requests} requests")
        
        results = []
        for i in range(requests):
            result = self._make_request('GET', '/health')
            results.append(result)
            
            # Small delay to simulate realistic traffic
            time.sleep(0.01)
        
        return results
    
    def test_workspace_endpoints(self, create_requests: int = 50, list_requests: int = 200) -> List[Dict[str, Any]]:
        """Load test workspace endpoints"""
        print(f"💼 Testing workspace endpoints: {create_requests} creates, {list_requests} lists")
        
        results = []
        
        # Test workspace creation
        for i in range(create_requests):
            workspace_id = f"load-test-{i}-{int(time.time())}"
            payload = {
                "provider": "openai",
                "workspace_id": workspace_id,
                "keys": {
                    "provider": "openai",
                    "openai_key": f"sk-load-test-{i}",
                    "gemini_key": "",
                    "tavily_key": ""
                }
            }
            
            result = self._make_request('POST', '/api/workspaces', json=payload)
            results.append(result)
            
            # Random delay
            time.sleep(random.uniform(0.01, 0.05))
        
        # Test workspace listing
        for i in range(list_requests):
            result = self._make_request('GET', '/api/workspaces')
            results.append(result)
            
            # Random delay
            time.sleep(random.uniform(0.005, 0.02))
        
        return results
    
    def test_enterprise_endpoints(self, requests: int = 50) -> List[Dict[str, Any]]:
        """Load test enterprise endpoints"""
        print(f"🏢 Testing enterprise endpoints with {requests} requests")
        
        results = []
        
        # Test enterprise status
        for i in range(requests):
            result = self._make_request('GET', '/api/enterprise/status')
            results.append(result)
            
            time.sleep(random.uniform(0.02, 0.1))
        
        return results
    
    def test_mixed_workload(self, duration_seconds: int = 60, target_rps: int = 10) -> List[Dict[str, Any]]:
        """Test mixed workload over time"""
        print(f"🔄 Testing mixed workload for {duration_seconds}s at {target_rps} RPS")
        
        results = []
        start_time = time.time()
        request_count = 0
        
        # Define workload mix
        workload_mix = [
            ('GET', '/health', 0.3),           # 30% health checks
            ('GET', '/api/workspaces', 0.4),   # 40% workspace lists
            ('GET', '/api/enterprise/status', 0.2),  # 20% enterprise status
            ('POST', '/api/workspaces', 0.1)   # 10% workspace creation
        ]
        
        while time.time() - start_time < duration_seconds:
            # Choose random endpoint based on mix
            rand = random.random()
            cumulative = 0
            
            for method, endpoint, weight in workload_mix:
                cumulative += weight
                if rand <= cumulative:
                    if method == 'POST':
                        # Generate random payload for POST
                        payload = {
                            "provider": "openai",
                            "workspace_id": f"mixed-{int(time.time())}-{request_count}",
                            "keys": {
                                "provider": "openai",
                                "openai_key": f"sk-mixed-{request_count}",
                                "gemini_key": "",
                                "tavily_key": ""
                            }
                        }
                        result = self._make_request(method, endpoint, json=payload)
                    else:
                        result = self._make_request(method, endpoint)
                    
                    results.append(result)
                    request_count += 1
                    break
            
            # Rate limiting to maintain target RPS
            time.sleep(1.0 / target_rps)
        
        print(f"   Completed {request_count} requests")
        return results
    
    def test_concurrent_bursts(self, bursts: int = 5, requests_per_burst: int = 20) -> List[Dict[str, Any]]:
        """Test concurrent request bursts"""
        print(f"💥 Testing {bursts} bursts of {requests_per_burst} concurrent requests")
        
        results = []
        
        for burst in range(bursts):
            print(f"   Burst {burst + 1}/{bursts}")
            
            # Create concurrent requests
            with ThreadPoolExecutor(max_workers=requests_per_burst) as executor:
                futures = [
                    executor.submit(self._make_request, 'GET', '/api/workspaces')
                    for _ in range(requests_per_burst)
                ]
                
                burst_results = []
                for future in as_completed(futures):
                    try:
                        result = future.result()
                        burst_results.append(result)
                    except Exception as e:
                        burst_results.append({
                            'success': False,
                            'error': str(e),
                            'endpoint': '/api/workspaces',
                            'method': 'GET'
                        })
                
                results.extend(burst_results)
            
            # Wait between bursts
            time.sleep(2)
        
        return results
    
    def analyze_results(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze test results"""
        if not results:
            return {}
        
        successful = [r for r in results if r['success']]
        failed = [r for r in results if not r['success']]
        
        durations = [r['duration_ms'] for r in successful]
        
        # Calculate statistics
        stats = {
            'total_requests': len(results),
            'successful_requests': len(successful),
            'failed_requests': len(failed),
            'success_rate': (len(successful) / len(results)) * 100,
            'avg_response_time_ms': sum(durations) / len(durations) if durations else 0,
            'min_response_time_ms': min(durations) if durations else 0,
            'max_response_time_ms': max(durations) if durations else 0,
            'total_response_size_mb': sum(r['response_size'] for r in results) / (1024 * 1024)
        }
        
        # Calculate percentiles
        if len(durations) >= 10:
            sorted_durations = sorted(durations)
            stats['p50_response_time_ms'] = sorted_durations[len(sorted_durations) // 2]
            stats['p95_response_time_ms'] = sorted_durations[int(len(sorted_durations) * 0.95)]
            stats['p99_response_time_ms'] = sorted_durations[int(len(sorted_durations) * 0.99)]
        
        # Error analysis
        if failed:
            error_counts = {}
            for result in failed:
                error = result.get('error', f"HTTP {result.get('status_code', 'Unknown')}")
                error_counts[error] = error_counts.get(error, 0) + 1
            stats['error_breakdown'] = error_counts
        
        return stats
    
    def run_comprehensive_load_test(self) -> Dict[str, Any]:
        """Run comprehensive load test suite"""
        print("🚀 Starting comprehensive API load test")
        print("=" * 60)
        
        all_results = []
        test_results = {}
        
        # Test 1: Health endpoint
        health_results = self.test_health_endpoint(100)
        all_results.extend(health_results)
        test_results['health'] = self.analyze_results(health_results)
        
        # Test 2: Workspace endpoints
        workspace_results = self.test_workspace_endpoints(30, 100)
        all_results.extend(workspace_results)
        test_results['workspaces'] = self.analyze_results(workspace_results)
        
        # Test 3: Enterprise endpoints
        enterprise_results = self.test_enterprise_endpoints(30)
        all_results.extend(enterprise_results)
        test_results['enterprise'] = self.analyze_results(enterprise_results)
        
        # Test 4: Mixed workload
        mixed_results = self.test_mixed_workload(30, 5)  # 30 seconds at 5 RPS
        all_results.extend(mixed_results)
        test_results['mixed_workload'] = self.analyze_results(mixed_results)
        
        # Test 5: Concurrent bursts
        burst_results = self.test_concurrent_bursts(3, 10)
        all_results.extend(burst_results)
        test_results['bursts'] = self.analyze_results(burst_results)
        
        # Overall analysis
        test_results['overall'] = self.analyze_results(all_results)
        
        print("=" * 60)
        print("✅ Load test completed")
        
        return test_results
    
    def print_results(self, results: Dict[str, Any]):
        """Print formatted results"""
        print("\n📊 API LOAD TEST RESULTS")
        print("=" * 80)
        
        for test_name, stats in results.items():
            if test_name == 'overall':
                print(f"\n🎯 OVERALL PERFORMANCE")
            else:
                print(f"\n🧪 {test_name.upper().replace('_', ' ')}")
            
            print(f"   Requests: {stats['total_requests']}")
            print(f"   Success Rate: {stats['success_rate']:.1f}%")
            print(f"   Avg Response: {stats['avg_response_time_ms']:.2f}ms")
            
            if 'p95_response_time_ms' in stats:
                print(f"   95th Percentile: {stats['p95_response_time_ms']:.2f}ms")
                print(f"   99th Percentile: {stats['p99_response_time_ms']:.2f}ms")
            
            print(f"   Data Transferred: {stats['total_response_size_mb']:.2f}MB")
            
            if stats.get('error_breakdown'):
                print(f"   Top Errors: {list(stats['error_breakdown'].items())[:3]}")
        
        print("\n" + "=" * 80)
        
        # Performance assessment
        overall = results['overall']
        if overall['success_rate'] >= 99 and overall['p95_response_time_ms'] < 500:
            print("🟢 EXCELLENT - API is highly performant and reliable")
        elif overall['success_rate'] >= 95 and overall['p95_response_time_ms'] < 1000:
            print("🟡 GOOD - API performs well with minor room for improvement")
        elif overall['success_rate'] >= 90:
            print("🟠 FAIR - API has performance issues that should be addressed")
        else:
            print("🔴 POOR - API has significant performance and reliability issues")


def run_load_test(base_url: str, api_token: str = None):
    """Run load test against specified API"""
    tester = APILoadTester(base_url, api_token)
    results = tester.run_comprehensive_load_test()
    tester.print_results(results)
    return results


if __name__ == "__main__":
    # Example usage
    base_url = "http://localhost:8000"
    api_token = None  # Set if required
    
    run_load_test(base_url, api_token)
