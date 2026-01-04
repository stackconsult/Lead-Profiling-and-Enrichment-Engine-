"""
Comprehensive stress testing suite for ProspectPulse reliability.
Tests API endpoints, database operations, and agent pipeline under load.
"""
from __future__ import annotations

import asyncio
import concurrent.futures
import json
import time
import uuid
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import statistics

import httpx
import pytest
from backend.core.valkey import valkey_client, get_client
from backend.agents.pipeline import AgentPipeline
from backend.core.llm import LLMClient, LLMKeys


@dataclass
class TestResult:
    """Result of a stress test operation"""
    operation: str
    success: bool
    duration_ms: float
    error: Optional[str] = None
    response_data: Optional[Dict[str, Any]] = None


@dataclass 
class StressTestSummary:
    """Summary of stress test results"""
    operation: str
    total_requests: int
    successful_requests: int
    failed_requests: int
    success_rate: float
    avg_response_time_ms: float
    min_response_time_ms: float
    max_response_time_ms: float
    p95_response_time_ms: float
    errors: List[str]


class StressTestSuite:
    """Comprehensive stress testing suite"""
    
    def __init__(self, api_base_url: str = "http://localhost:8000", api_token: Optional[str] = None):
        self.api_base_url = api_base_url
        self.api_token = api_token
        self.client = httpx.Client(timeout=30.0)
        self.results: List[TestResult] = []
    
    async def test_workspace_creation_load(self, concurrent_users: int = 10, requests_per_user: int = 5) -> StressTestSummary:
        """Stress test workspace creation endpoint"""
        print(f"🧪 Testing workspace creation with {concurrent_users} users, {requests_per_user} requests each")
        
        async def create_workspace_batch(user_id: int) -> List[TestResult]:
            results = []
            for i in range(requests_per_user):
                workspace_id = f"stress-test-{user_id}-{i}-{int(time.time())}"
                payload = {
                    "provider": "openai",
                    "workspace_id": workspace_id,
                    "keys": {
                        "provider": "openai",
                        "openai_key": f"sk-test-{user_id}-{i}",
                        "gemini_key": "",
                        "tavily_key": ""
                    }
                }
                
                start_time = time.time()
                try:
                    response = self.client.post(
                        f"{self.api_base_url}/api/workspaces",
                        json=payload,
                        headers={"X-API-TOKEN": self.api_token} if self.api_token else None
                    )
                    duration_ms = (time.time() - start_time) * 1000
                    
                    results.append(TestResult(
                        operation="workspace_creation",
                        success=response.status_code == 200,
                        duration_ms=duration_ms,
                        response_data=response.json() if response.status_code == 200 else None
                    ))
                    
                except Exception as e:
                    duration_ms = (time.time() - start_time) * 1000
                    results.append(TestResult(
                        operation="workspace_creation",
                        success=False,
                        duration_ms=duration_ms,
                        error=str(e)
                    ))
            
            return results
        
        # Run concurrent batches
        tasks = [create_workspace_batch(user_id) for user_id in range(concurrent_users)]
        all_results = await asyncio.gather(*tasks)
        
        # Flatten results
        workspace_results = [result for batch in all_results for result in batch]
        self.results.extend(workspace_results)
        
        return self._calculate_summary("workspace_creation", workspace_results)
    
    async def test_workspace_listing_load(self, concurrent_users: int = 20, requests_per_user: int = 10) -> StressTestSummary:
        """Stress test workspace listing endpoint"""
        print(f"🧪 Testing workspace listing with {concurrent_users} users, {requests_per_user} requests each")
        
        async def list_workspaces_batch(user_id: int) -> List[TestResult]:
            results = []
            for i in range(requests_per_user):
                start_time = time.time()
                try:
                    response = self.client.get(
                        f"{self.api_base_url}/api/workspaces",
                        headers={"X-API-TOKEN": self.api_token} if self.api_token else None
                    )
                    duration_ms = (time.time() - start_time) * 1000
                    
                    results.append(TestResult(
                        operation="workspace_listing",
                        success=response.status_code == 200,
                        duration_ms=duration_ms,
                        response_data=response.json() if response.status_code == 200 else None
                    ))
                    
                except Exception as e:
                    duration_ms = (time.time() - start_time) * 1000
                    results.append(TestResult(
                        operation="workspace_listing",
                        success=False,
                        duration_ms=duration_ms,
                        error=str(e)
                    ))
            
            return results
        
        # Run concurrent batches
        tasks = [list_workspaces_batch(user_id) for user_id in range(concurrent_users)]
        all_results = await asyncio.gather(*tasks)
        
        # Flatten results
        listing_results = [result for batch in all_results for result in batch]
        self.results.extend(listing_results)
        
        return self._calculate_summary("workspace_listing", listing_results)
    
    def test_valkey_operations_load(self, operations: int = 1000, concurrent_workers: int = 10) -> StressTestSummary:
        """Stress test Valkey operations directly"""
        print(f"🧪 Testing Valkey operations with {operations} operations, {concurrent_workers} workers")
        
        def valkey_operation_batch(worker_id: int, ops_per_worker: int) -> List[TestResult]:
            results = []
            for i in range(ops_per_worker):
                key = f"stress-test-{worker_id}-{i}-{int(time.time())}"
                value = json.dumps({"worker_id": worker_id, "operation": i, "timestamp": time.time()})
                
                # Test SET operation
                start_time = time.time()
                try:
                    valkey_client.set(key, value)
                    set_duration = (time.time() - start_time) * 1000
                    
                    # Test GET operation
                    get_start = time.time()
                    retrieved = valkey_client.get(key)
                    get_duration = (time.time() - get_start) * 1000
                    
                    total_duration = set_duration + get_duration
                    
                    results.append(TestResult(
                        operation="valkey_set_get",
                        success=retrieved == value,
                        duration_ms=total_duration,
                        response_data={"set_ms": set_duration, "get_ms": get_duration}
                    ))
                    
                    # Clean up
                    valkey_client.delete(key)
                    
                except Exception as e:
                    duration_ms = (time.time() - start_time) * 1000
                    results.append(TestResult(
                        operation="valkey_set_get",
                        success=False,
                        duration_ms=duration_ms,
                        error=str(e)
                    ))
            
            return results
        
        # Calculate operations per worker
        ops_per_worker = operations // concurrent_workers
        
        # Run with thread pool
        with concurrent.futures.ThreadPoolExecutor(max_workers=concurrent_workers) as executor:
            futures = [
                executor.submit(valkey_operation_batch, worker_id, ops_per_worker)
                for worker_id in range(concurrent_workers)
            ]
            
            all_results = []
            for future in concurrent.futures.as_completed(futures):
                try:
                    batch_results = future.result()
                    all_results.extend(batch_results)
                except Exception as e:
                    print(f"Worker batch failed: {e}")
        
        self.results.extend(all_results)
        return self._calculate_summary("valkey_operations", all_results)
    
    def test_agent_pipeline_load(self, leads: int = 100, concurrent_workers: int = 5) -> StressTestSummary:
        """Stress test agent pipeline with fake workspace"""
        print(f"🧪 Testing agent pipeline with {leads} leads, {concurrent_workers} workers")
        
        def process_lead_batch(worker_id: int, leads_per_worker: int) -> List[TestResult]:
            results = []
            
            # Create test workspace
            workspace = {
                "id": f"stress-workspace-{worker_id}",
                "provider": "openai",
                "openai_key": "sk-test-key",
                "gemini_key": "",
                "tavily_key": ""
            }
            
            pipeline = AgentPipeline(workspace)
            
            for i in range(leads_per_worker):
                lead = {
                    "id": f"stress-lead-{worker_id}-{i}",
                    "company": f"Test Company {worker_id}-{i}",
                    "email": f"test{worker_id}{i}@example.com"
                }
                
                start_time = time.time()
                try:
                    result = pipeline.run(lead)
                    duration_ms = (time.time() - start_time) * 1000
                    
                    results.append(TestResult(
                        operation="agent_pipeline",
                        success=bool(result and result.get("id")),
                        duration_ms=duration_ms,
                        response_data={"lead_id": lead["id"], "result_id": result.get("id")}
                    ))
                    
                except Exception as e:
                    duration_ms = (time.time() - start_time) * 1000
                    results.append(TestResult(
                        operation="agent_pipeline",
                        success=False,
                        duration_ms=duration_ms,
                        error=str(e)
                    ))
            
            return results
        
        # Calculate leads per worker
        leads_per_worker = leads // concurrent_workers
        
        # Run with thread pool
        with concurrent.futures.ThreadPoolExecutor(max_workers=concurrent_workers) as executor:
            futures = [
                executor.submit(process_lead_batch, worker_id, leads_per_worker)
                for worker_id in range(concurrent_workers)
            ]
            
            all_results = []
            for future in concurrent.futures.as_completed(futures):
                try:
                    batch_results = future.result()
                    all_results.extend(batch_results)
                except Exception as e:
                    print(f"Pipeline worker batch failed: {e}")
        
        self.results.extend(all_results)
        return self._calculate_summary("agent_pipeline", all_results)
    
    def test_connection_pool_stress(self, connections: int = 100, operations_per_connection: int = 10) -> StressTestSummary:
        """Stress test connection pool with many concurrent connections"""
        print(f"🧪 Testing connection pool with {connections} connections, {operations_per_connection} ops each")
        
        def connection_batch(connection_id: int) -> List[TestResult]:
            results = []
            
            # Get fresh client for this connection
            try:
                client = get_client()
                
                for i in range(operations_per_connection):
                    key = f"pool-test-{connection_id}-{i}"
                    value = f"connection-{connection_id}-operation-{i}"
                    
                    start_time = time.time()
                    try:
                        # Test basic operations
                        client.set(key, value)
                        retrieved = client.get(key)
                        client.delete(key)
                        
                        duration_ms = (time.time() - start_time) * 1000
                        
                        results.append(TestResult(
                            operation="connection_pool",
                            success=retrieved == value,
                            duration_ms=duration_ms
                        ))
                        
                    except Exception as e:
                        duration_ms = (time.time() - start_time) * 1000
                        results.append(TestResult(
                            operation="connection_pool",
                            success=False,
                            duration_ms=duration_ms,
                            error=str(e)
                        ))
                        
            except Exception as e:
                results.append(TestResult(
                    operation="connection_pool",
                    success=False,
                    duration_ms=0,
                    error=f"Connection failed: {str(e)}"
                ))
            
            return results
        
        # Run with thread pool
        with concurrent.futures.ThreadPoolExecutor(max_workers=connections) as executor:
            futures = [
                executor.submit(connection_batch, connection_id)
                for connection_id in range(connections)
            ]
            
            all_results = []
            for future in concurrent.futures.as_completed(futures):
                try:
                    batch_results = future.result()
                    all_results.extend(batch_results)
                except Exception as e:
                    print(f"Connection batch failed: {e}")
        
        self.results.extend(all_results)
        return self._calculate_summary("connection_pool", all_results)
    
    def _calculate_summary(self, operation: str, results: List[TestResult]) -> StressTestSummary:
        """Calculate summary statistics for test results"""
        if not results:
            return StressTestSummary(
                operation=operation,
                total_requests=0,
                successful_requests=0,
                failed_requests=0,
                success_rate=0.0,
                avg_response_time_ms=0.0,
                min_response_time_ms=0.0,
                max_response_time_ms=0.0,
                p95_response_time_ms=0.0,
                errors=[]
            )
        
        successful_results = [r for r in results if r.success]
        failed_results = [r for r in results if not r.success]
        
        durations = [r.duration_ms for r in successful_results]
        
        if durations:
            avg_duration = statistics.mean(durations)
            min_duration = min(durations)
            max_duration = max(durations)
            p95_duration = statistics.quantiles(durations, n=20)[18] if len(durations) > 20 else max_duration
        else:
            avg_duration = min_duration = max_duration = p95_duration = 0.0
        
        errors = [r.error for r in failed_results if r.error][:10]  # Limit to first 10 errors
        
        return StressTestSummary(
            operation=operation,
            total_requests=len(results),
            successful_requests=len(successful_results),
            failed_requests=len(failed_results),
            success_rate=len(successful_results) / len(results) * 100,
            avg_response_time_ms=avg_duration,
            min_response_time_ms=min_duration,
            max_response_time_ms=max_duration,
            p95_response_time_ms=p95_duration,
            errors=errors
        )
    
    async def run_full_stress_test_suite(self) -> Dict[str, StressTestSummary]:
        """Run complete stress test suite"""
        print("🚀 Starting comprehensive stress test suite")
        print("=" * 60)
        
        results = {}
        
        # Test 1: Workspace Creation
        results["workspace_creation"] = await self.test_workspace_creation_load(
            concurrent_users=5, requests_per_user=3
        )
        
        # Test 2: Workspace Listing
        results["workspace_listing"] = await self.test_workspace_listing_load(
            concurrent_users=10, requests_per_user=5
        )
        
        # Test 3: Valkey Operations
        results["valkey_operations"] = self.test_valkey_operations_load(
            operations=100, concurrent_workers=5
        )
        
        # Test 4: Agent Pipeline
        results["agent_pipeline"] = self.test_agent_pipeline_load(
            leads=20, concurrent_workers=3
        )
        
        # Test 5: Connection Pool
        results["connection_pool"] = self.test_connection_pool_stress(
            connections=20, operations_per_connection=5
        )
        
        print("=" * 60)
        print("✅ Stress test suite completed")
        
        return results
    
    def print_summary(self, results: Dict[str, StressTestSummary]):
        """Print formatted summary of stress test results"""
        print("\n📊 STRESS TEST RESULTS SUMMARY")
        print("=" * 80)
        
        for operation, summary in results.items():
            print(f"\n🧪 {operation.upper()}")
            print(f"   Total Requests: {summary.total_requests}")
            print(f"   Success Rate: {summary.success_rate:.1f}%")
            print(f"   Avg Response Time: {summary.avg_response_time_ms:.2f}ms")
            print(f"   Min Response Time: {summary.min_response_time_ms:.2f}ms")
            print(f"   Max Response Time: {summary.max_response_time_ms:.2f}ms")
            print(f"   95th Percentile: {summary.p95_response_time_ms:.2f}ms")
            
            if summary.errors:
                print(f"   Sample Errors: {summary.errors[:3]}")
        
        print("\n" + "=" * 80)
        
        # Overall assessment
        total_requests = sum(s.total_requests for s in results.values())
        total_successful = sum(s.successful_requests for s in results.values())
        overall_success_rate = (total_successful / total_requests * 100) if total_requests > 0 else 0
        
        print(f"\n🎯 OVERALL ASSESSMENT")
        print(f"   Total Operations: {total_requests}")
        print(f"   Overall Success Rate: {overall_success_rate:.1f}%")
        
        if overall_success_rate >= 95:
            print("   ✅ EXCELLENT - System is highly reliable under stress")
        elif overall_success_rate >= 90:
            print("   ⚠️  GOOD - System is mostly reliable with minor issues")
        elif overall_success_rate >= 80:
            print("   ❌ FAIR - System has reliability concerns")
        else:
            print("   🚨 POOR - System has significant reliability issues")


# Standalone test runner
async def run_stress_tests():
    """Run stress tests with default configuration"""
    # Test against local development or production
    api_url = "http://localhost:8000"
    api_token = None  # Set if required
    
    suite = StressTestSuite(api_base_url=api_url, api_token=api_token)
    results = await suite.run_full_stress_test_suite()
    suite.print_summary(results)
    
    return results


if __name__ == "__main__":
    asyncio.run(run_stress_tests())
