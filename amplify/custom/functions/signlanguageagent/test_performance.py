"""
Performance benchmarks and load testing for GenASL Sign Language Agent

This module contains performance tests, benchmarks, and load testing
to ensure the agent meets performance requirements.
"""

import unittest
import time
import threading
import statistics
import sys
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from unittest.mock import Mock, patch
from pathlib import Path

# Add current directory to path for imports
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

from test_config import (
    setup_test_environment, MockAWSServices, create_mock_bedrock_response,
    performance_benchmark, PerformanceBenchmark
)

class TestPerformanceBenchmarks(unittest.TestCase):
    """Performance benchmark tests"""
    
    @classmethod
    def setUpClass(cls):
        """Set up test environment"""
        setup_test_environment()
        cls.benchmark = PerformanceBenchmark()
    
    def setUp(self):
        """Set up each test"""
        self.mock_aws = MockAWSServices()
        self.mock_aws.__enter__()
    
    def tearDown(self):
        """Clean up after each test"""
        self.mock_aws.__exit__(None, None, None)
    
    @patch('boto3.client')
    def test_text_to_gloss_performance(self, mock_boto_client):
        """Benchmark text-to-gloss conversion performance"""
        try:
            from text2gloss_handler import text_to_asl_gloss
        except ImportError:
            self.skipTest("Text2gloss handler not available")
        
        # Mock Bedrock client
        mock_bedrock = Mock()
        mock_boto_client.return_value = mock_bedrock
        mock_bedrock.converse.return_value = create_mock_bedrock_response("TEST GLOSS")
        
        # Benchmark different text lengths
        test_cases = [
            "Hello",
            "Hello world",
            "I want to learn sign language",
            "This is a longer sentence with more words to test performance with increased input length",
            "This is an even longer sentence that contains multiple clauses and complex grammar structures to test how the system performs with very long input text that might require more processing time and resources"
        ]
        
        results = []
        for text in test_cases:
            result = self.benchmark.benchmark_function(
                text_to_asl_gloss, text, iterations=10
            )
            result['input_length'] = len(text)
            results.append(result)
        
        # Analyze results
        for result in results:
            # Performance requirements
            self.assertLess(result['avg_time'], 2.0, 
                          f"Text-to-gloss conversion too slow for input length {result['input_length']}")
            self.assertGreaterEqual(result['success_rate'], 0.95,
                                  f"Success rate too low for input length {result['input_length']}")
        
        # Check if performance scales reasonably with input length
        avg_times = [r['avg_time'] for r in results]
        input_lengths = [r['input_length'] for r in results]
        
        # Performance should not degrade dramatically with input length
        max_time = max(avg_times)
        min_time = min(avg_times)
        self.assertLess(max_time / min_time, 3.0, "Performance degrades too much with input length")
    
    @patch('boto3.client')
    @patch('subprocess.run')
    def test_gloss_to_video_performance(self, mock_subprocess, mock_boto_client):
        """Benchmark gloss-to-video conversion performance"""
        try:
            from gloss2pose_handler import gloss_to_video
        except ImportError:
            self.skipTest("Gloss2pose handler not available")
        
        # Mock AWS clients
        mock_s3 = Mock()
        mock_boto_client.return_value = mock_s3
        mock_s3.generate_presigned_url.return_value = "https://test-video-url.com/video.webm"
        
        # Mock subprocess (FFmpeg)
        mock_subprocess.return_value = Mock(returncode=0)
        
        # Test different gloss lengths
        test_cases = [
            "HELLO",
            "HELLO WORLD",
            "IX-1P LIKE MOVIE WATCH",
            "HELLO IX-1P NAME JOHN IX-1P LIKE MEET IX-2P",
            "MORNING IX-1P WAKE-UP BRUSH-TEETH EAT BREAKFAST GO WORK DRIVE CAR ARRIVE OFFICE"
        ]
        
        results = []
        
        with patch('os.path.exists', return_value=True), \
             patch('os.path.getsize', return_value=1000), \
             patch('pathlib.Path.mkdir'), \
             patch('builtins.open', create=True):
            
            for gloss in test_cases:
                result = self.benchmark.benchmark_function(
                    gloss_to_video, gloss, iterations=5  # Fewer iterations due to complexity
                )
                result['gloss_length'] = len(gloss.split())
                results.append(result)
        
        # Analyze results
        for result in results:
            # Performance requirements (more lenient for video processing)
            self.assertLess(result['avg_time'], 10.0,
                          f"Gloss-to-video conversion too slow for {result['gloss_length']} signs")
            self.assertGreaterEqual(result['success_rate'], 0.8,
                                  f"Success rate too low for {result['gloss_length']} signs")
    
    @patch('boto3.client')
    def test_agent_invoke_performance(self, mock_boto_client):
        """Benchmark complete agent invocation performance"""
        from slagent import invoke
        
        # Mock AWS clients
        mock_bedrock = Mock()
        mock_s3 = Mock()
        
        def mock_client_factory(service_name, **kwargs):
            if service_name == 'bedrock-runtime':
                return mock_bedrock
            elif service_name == 's3':
                return mock_s3
            return Mock()
        
        mock_boto_client.side_effect = mock_client_factory
        
        # Mock responses
        mock_bedrock.converse.return_value = create_mock_bedrock_response("HELLO WORLD")
        mock_s3.generate_presigned_url.return_value = "https://test-video-url.com/video.webm"
        
        # Test different request types
        test_cases = [
            {"message": "Hello", "type": "text"},
            {"message": "What can you do?", "type": "text"},
            {"message": "I want to learn sign language", "type": "text"}
        ]
        
        with patch('subprocess.run') as mock_subprocess, \
             patch('os.path.exists', return_value=True), \
             patch('os.path.getsize', return_value=1000), \
             patch('pathlib.Path.mkdir'), \
             patch('builtins.open', create=True):
            
            mock_subprocess.return_value = Mock(returncode=0)
            
            for payload in test_cases:
                result = self.benchmark.benchmark_function(
                    invoke, payload, iterations=5
                )
                
                # Performance requirements for complete workflow
                self.assertLess(result['avg_time'], 5.0,
                              f"Agent invocation too slow for: {payload['message']}")
                self.assertGreaterEqual(result['success_rate'], 0.9,
                                      f"Success rate too low for: {payload['message']}")
    
    def test_caching_performance(self):
        """Test caching performance improvements"""
        from caching import GlossPoseMappingCache
        
        cache = GlossPoseMappingCache(max_size=100, ttl_seconds=300)
        
        # Mock DynamoDB
        with patch('boto3.resource') as mock_boto:
            mock_table = Mock()
            mock_dynamodb = Mock()
            mock_dynamodb.Table.return_value = mock_table
            mock_boto.return_value = mock_dynamodb
            
            mock_table.query.return_value = {
                'Count': 1,
                'Items': [{'SignID': 'test_sign_001'}]
            }
            
            # Benchmark cache miss (first call)
            miss_result = self.benchmark.benchmark_function(
                cache.get_sign_id, 'HELLO', iterations=10
            )
            
            # Benchmark cache hit (subsequent calls)
            hit_result = self.benchmark.benchmark_function(
                cache.get_sign_id, 'HELLO', iterations=10
            )
            
            # Cache hits should be significantly faster
            self.assertLess(hit_result['avg_time'], miss_result['avg_time'] / 2,
                          "Cache hits should be at least 2x faster than misses")
            
            # Both should have high success rates
            self.assertGreaterEqual(miss_result['success_rate'], 0.95)
            self.assertGreaterEqual(hit_result['success_rate'], 0.95)


class TestLoadTesting(unittest.TestCase):
    """Load testing for concurrent requests"""
    
    @classmethod
    def setUpClass(cls):
        """Set up test environment"""
        setup_test_environment()
    
    def setUp(self):
        """Set up each test"""
        self.mock_aws = MockAWSServices()
        self.mock_aws.__enter__()
    
    def tearDown(self):
        """Clean up after each test"""
        self.mock_aws.__exit__(None, None, None)
    
    @patch('boto3.client')
    def test_concurrent_text_requests(self, mock_boto_client):
        """Test handling concurrent text-to-ASL requests"""
        from slagent import invoke
        
        # Mock AWS clients
        mock_bedrock = Mock()
        mock_s3 = Mock()
        
        def mock_client_factory(service_name, **kwargs):
            if service_name == 'bedrock-runtime':
                return mock_bedrock
            elif service_name == 's3':
                return mock_s3
            return Mock()
        
        mock_boto_client.side_effect = mock_client_factory
        
        # Mock responses
        mock_bedrock.converse.return_value = create_mock_bedrock_response("CONCURRENT TEST")
        mock_s3.generate_presigned_url.return_value = "https://test-video-url.com/video.webm"
        
        def make_request(request_id):
            """Make a single request"""
            payload = {
                "message": f"Concurrent test {request_id}",
                "type": "text",
                "session_id": f"session-{request_id}"
            }
            
            with patch('subprocess.run') as mock_subprocess, \
                 patch('os.path.exists', return_value=True), \
                 patch('os.path.getsize', return_value=1000), \
                 patch('pathlib.Path.mkdir'), \
                 patch('builtins.open', create=True):
                
                mock_subprocess.return_value = Mock(returncode=0)
                start_time = time.time()
                result = invoke(payload)
                end_time = time.time()
                
                return {
                    'request_id': request_id,
                    'result': result,
                    'duration': end_time - start_time,
                    'success': isinstance(result, str) and len(result) > 0
                }
        
        # Test with different concurrency levels
        concurrency_levels = [5, 10, 20]
        
        for concurrency in concurrency_levels:
            start_time = time.time()
            
            # Use ThreadPoolExecutor for concurrent requests
            with ThreadPoolExecutor(max_workers=concurrency) as executor:
                futures = [executor.submit(make_request, i) for i in range(concurrency)]
                results = [future.result(timeout=30) for future in as_completed(futures)]
            
            end_time = time.time()
            total_time = end_time - start_time
            
            # Analyze results
            successful_requests = sum(1 for r in results if r['success'])
            success_rate = successful_requests / len(results)
            avg_duration = statistics.mean(r['duration'] for r in results)
            max_duration = max(r['duration'] for r in results)
            
            # Performance assertions
            self.assertGreaterEqual(success_rate, 0.8,
                                  f"Success rate too low for concurrency {concurrency}")
            self.assertLess(avg_duration, 10.0,
                          f"Average duration too high for concurrency {concurrency}")
            self.assertLess(max_duration, 20.0,
                          f"Max duration too high for concurrency {concurrency}")
            
            # Throughput should be reasonable
            throughput = len(results) / total_time
            self.assertGreater(throughput, 0.5,
                             f"Throughput too low for concurrency {concurrency}")
    
    def test_sustained_load(self):
        """Test system under sustained load"""
        from slagent import invoke
        
        with patch('boto3.client') as mock_boto_client:
            mock_bedrock = Mock()
            mock_boto_client.return_value = mock_bedrock
            mock_bedrock.converse.return_value = create_mock_bedrock_response("SUSTAINED LOAD")
            
            # Run sustained load for 30 seconds
            duration = 30  # seconds
            request_interval = 0.5  # seconds between requests
            
            start_time = time.time()
            results = []
            request_count = 0
            
            while time.time() - start_time < duration:
                try:
                    payload = {
                        "message": f"Sustained load test {request_count}",
                        "type": "text"
                    }
                    
                    request_start = time.time()
                    result = invoke(payload)
                    request_end = time.time()
                    
                    results.append({
                        'success': isinstance(result, str) and len(result) > 0,
                        'duration': request_end - request_start,
                        'timestamp': request_start
                    })
                    
                    request_count += 1
                    time.sleep(request_interval)
                    
                except Exception as e:
                    results.append({
                        'success': False,
                        'error': str(e),
                        'timestamp': time.time()
                    })
            
            # Analyze sustained load results
            total_requests = len(results)
            successful_requests = sum(1 for r in results if r['success'])
            success_rate = successful_requests / total_requests if total_requests > 0 else 0
            
            successful_durations = [r['duration'] for r in results if r['success']]
            if successful_durations:
                avg_duration = statistics.mean(successful_durations)
                max_duration = max(successful_durations)
            else:
                avg_duration = float('inf')
                max_duration = float('inf')
            
            # Performance assertions for sustained load
            self.assertGreaterEqual(success_rate, 0.7,
                                  "Success rate too low under sustained load")
            self.assertLess(avg_duration, 5.0,
                          "Average response time too high under sustained load")
            self.assertGreater(total_requests, 10,
                             "Not enough requests processed during sustained load test")
    
    def test_memory_leak_detection(self):
        """Test for memory leaks under load"""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss
        
        from slagent import invoke
        
        with patch('boto3.client') as mock_boto_client:
            mock_bedrock = Mock()
            mock_boto_client.return_value = mock_bedrock
            mock_bedrock.converse.return_value = create_mock_bedrock_response("MEMORY TEST")
            
            # Process many requests
            for i in range(100):
                payload = {
                    "message": f"Memory leak test {i}",
                    "type": "text"
                }
                
                try:
                    invoke(payload)
                except Exception:
                    pass  # Ignore errors for memory leak test
                
                # Check memory every 20 requests
                if i % 20 == 0:
                    current_memory = process.memory_info().rss
                    memory_increase = current_memory - initial_memory
                    
                    # Memory increase should be reasonable (less than 200MB)
                    self.assertLess(memory_increase, 200 * 1024 * 1024,
                                  f"Excessive memory usage after {i} requests: {memory_increase / 1024 / 1024:.1f}MB")
        
        # Final memory check
        final_memory = process.memory_info().rss
        total_memory_increase = final_memory - initial_memory
        
        # Total memory increase should be reasonable
        self.assertLess(total_memory_increase, 300 * 1024 * 1024,
                      f"Total memory increase too high: {total_memory_increase / 1024 / 1024:.1f}MB")


class TestScalabilityMetrics(unittest.TestCase):
    """Test scalability and performance metrics"""
    
    def test_response_time_distribution(self):
        """Test response time distribution under various loads"""
        from slagent import invoke
        
        with patch('boto3.client') as mock_boto_client:
            mock_bedrock = Mock()
            mock_boto_client.return_value = mock_bedrock
            mock_bedrock.converse.return_value = create_mock_bedrock_response("DISTRIBUTION TEST")
            
            response_times = []
            
            # Collect response times
            for i in range(50):
                payload = {
                    "message": f"Distribution test {i}",
                    "type": "text"
                }
                
                start_time = time.time()
                try:
                    invoke(payload)
                    end_time = time.time()
                    response_times.append(end_time - start_time)
                except Exception:
                    pass  # Skip failed requests for this test
            
            if response_times:
                # Calculate percentiles
                response_times.sort()
                p50 = response_times[len(response_times) // 2]
                p95 = response_times[int(len(response_times) * 0.95)]
                p99 = response_times[int(len(response_times) * 0.99)]
                
                # Performance requirements
                self.assertLess(p50, 2.0, f"P50 response time too high: {p50:.2f}s")
                self.assertLess(p95, 5.0, f"P95 response time too high: {p95:.2f}s")
                self.assertLess(p99, 10.0, f"P99 response time too high: {p99:.2f}s")
    
    def test_throughput_scaling(self):
        """Test throughput scaling with different loads"""
        from slagent import invoke
        
        with patch('boto3.client') as mock_boto_client:
            mock_bedrock = Mock()
            mock_boto_client.return_value = mock_bedrock
            mock_bedrock.converse.return_value = create_mock_bedrock_response("THROUGHPUT TEST")
            
            # Test different request rates
            rates = [1, 2, 5]  # requests per second
            throughput_results = []
            
            for rate in rates:
                request_interval = 1.0 / rate
                test_duration = 10  # seconds
                
                start_time = time.time()
                successful_requests = 0
                total_requests = 0
                
                while time.time() - start_time < test_duration:
                    payload = {
                        "message": f"Throughput test at {rate} RPS",
                        "type": "text"
                    }
                    
                    try:
                        invoke(payload)
                        successful_requests += 1
                    except Exception:
                        pass  # Count failed requests
                    
                    total_requests += 1
                    time.sleep(request_interval)
                
                actual_duration = time.time() - start_time
                actual_throughput = successful_requests / actual_duration
                
                throughput_results.append({
                    'target_rate': rate,
                    'actual_throughput': actual_throughput,
                    'success_rate': successful_requests / total_requests if total_requests > 0 else 0
                })
            
            # Analyze throughput scaling
            for result in throughput_results:
                # Should achieve at least 70% of target throughput
                efficiency = result['actual_throughput'] / result['target_rate']
                self.assertGreater(efficiency, 0.7,
                                 f"Throughput efficiency too low at {result['target_rate']} RPS: {efficiency:.2f}")
                
                # Success rate should remain high
                self.assertGreater(result['success_rate'], 0.8,
                                 f"Success rate too low at {result['target_rate']} RPS: {result['success_rate']:.2f}")


if __name__ == '__main__':
    # Set up logging for tests
    import logging
    logging.basicConfig(level=logging.INFO)
    
    # Run performance tests
    unittest.main(verbosity=2)