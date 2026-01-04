#!/usr/bin/env python3
"""
Comprehensive test runner for ProspectPulse stress testing and reliability monitoring.
"""
from __future__ import annotations

import asyncio
import argparse
import sys
import os
from typing import Dict, Any

# Add project root to Python path for imports
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# Now import the test modules
try:
    from tests.stress_test import StressTestSuite, run_stress_tests
    from tests.load_test import run_load_test
    from tests.reliability_monitor import ReliabilityMonitor, run_reliability_monitor
except ImportError as e:
    print(f"Import error: {e}")
    print(f"Project root: {project_root}")
    print(f"Python path: {sys.path}")
    sys.exit(1)


def run_stress_test_suite(api_url: str, api_token: str = None):
    """Run comprehensive stress test suite"""
    print("🚀 Running Comprehensive Stress Test Suite")
    print("=" * 60)
    
    async def run_suite():
        suite = StressTestSuite(api_base_url=api_url, api_token=api_token)
        results = await suite.run_full_stress_test_suite()
        suite.print_summary(results)
        return results
    
    return asyncio.run(run_suite())


def run_load_test_suite(api_url: str, api_token: str = None):
    """Run API load testing"""
    print("🔄 Running API Load Test Suite")
    print("=" * 60)
    
    return run_load_test(api_url, api_token)


def run_reliability_check(api_url: str, api_token: str = None, duration: int = 5):
    """Run reliability monitoring"""
    print("🔍 Running Reliability Monitoring")
    print("=" * 60)
    
    async def run_monitor():
        monitor = ReliabilityMonitor(api_base_url=api_url, api_token=api_token)
        await monitor.start_monitoring(interval_seconds=30, duration_minutes=duration)
    
    asyncio.run(run_monitor())


def run_quick_health_check(api_url: str, api_token: str = None):
    """Run quick health check"""
    print("⚡ Running Quick Health Check")
    print("=" * 60)
    
    monitor = ReliabilityMonitor(api_base_url=api_url, api_token=api_token)
    metrics = monitor.collect_metrics()
    monitor.print_health_report(metrics)
    
    return metrics


def main():
    """Main test runner"""
    parser = argparse.ArgumentParser(description="ProspectPulse Stress Testing & Reliability Suite")
    parser.add_argument("--api-url", default="http://localhost:8000", help="API base URL")
    parser.add_argument("--api-token", help="API token for authentication")
    parser.add_argument("--test-type", choices=["stress", "load", "reliability", "health", "all"], 
                       default="all", help="Type of test to run")
    parser.add_argument("--duration", type=int, default=5, help="Duration in minutes for reliability monitoring")
    
    args = parser.parse_args()
    
    print(f"🧪 ProspectPulse Test Suite")
    print(f"   API URL: {args.api_url}")
    print(f"   Test Type: {args.test_type}")
    print("=" * 60)
    
    results = {}
    
    try:
        if args.test_type in ["stress", "all"]:
            print("\n" + "=" * 60)
            results['stress'] = run_stress_test_suite(args.api_url, args.api_token)
        
        if args.test_type in ["load", "all"]:
            print("\n" + "=" * 60)
            results['load'] = run_load_test_suite(args.api_url, args.api_token)
        
        if args.test_type in ["reliability", "all"]:
            print("\n" + "=" * 60)
            run_reliability_check(args.api_url, args.api_token, args.duration)
        
        if args.test_type in ["health", "all"]:
            print("\n" + "=" * 60)
            results['health'] = run_quick_health_check(args.api_url, args.api_token)
        
        # Final assessment
        if args.test_type == "all":
            print("\n" + "=" * 60)
            print("🎯 FINAL ASSESSMENT")
            print("=" * 60)
            
            # Stress test assessment
            if 'stress' in results:
                stress_success = sum(s.success_rate for s in results['stress'].values()) / len(results['stress'])
                print(f"   Stress Test Success Rate: {stress_success:.1f}%")
            
            # Load test assessment
            if 'load' in results:
                load_success = results['load']['overall']['success_rate']
                load_p95 = results['load']['overall'].get('p95_response_time_ms', 0)
                print(f"   Load Test Success Rate: {load_success:.1f}%")
                print(f"   Load Test P95 Response: {load_p95:.1f}ms")
            
            # Health check assessment
            if 'health' in results:
                health_score = results['health']['health_score']
                print(f"   System Health Score: {health_score:.1f}%")
            
            print("\n🎉 Test Suite Completed!")
            
    except KeyboardInterrupt:
        print("\n⚠️ Tests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Test suite failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
