"""
Integration tests for GenASL Sign Language Agent

This module contains integration tests for complete agent workflows,
API endpoints, and end-to-end functionality.
"""

import unittest
import json
import time
import sys
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

# Add current directory to path for imports
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

from test_config import (
    setup_test_environment, MockAWSServices, AGENT_WORKFLOW_TEST_CASES,
    create_mock_bedrock_response, create_mock_transcribe_response,
    assert_response_structure, performance_benchmark
)

class TestAgentWorkflows(unittest.TestCase):
    """Test complete agent workflows"""
    
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
    def test_text_to_asl_workflow(self, mock_boto_client):
        """Test complete text-to-ASL workflow"""
        from slagent import invoke
        
        # Mock Bedrock and S3 clients
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
        
        # Mock file operations for video processing
        with patch('subprocess.run') as mock_subprocess, \
             patch('os.path.exists', return_value=True), \
             patch('os.path.getsize', return_value=1000), \
             patch('pathlib.Path.mkdir'), \
             patch('builtins.open', create=True):
            
            mock_subprocess.return_value = Mock(returncode=0)
            
            # Test the workflow
            payload = {
                "message": "Hello world",
                "type": "text"
            }
            
            result = invoke(payload)
        
        # Assertions
        self.assertIsInstance(result, str)
        self.assertIn("Translation completed successfully", result)
        self.assertIn("HELLO WORLD", result)
        
        # Verify tools were called
        mock_bedrock.converse.assert_called()
    
    @patch('boto3.client')
    def test_audio_to_asl_workflow(self, mock_boto_client):
        """Test complete audio-to-ASL workflow"""
        from slagent import invoke
        
        # Mock AWS clients
        mock_transcribe = Mock()
        mock_bedrock = Mock()
        mock_s3 = Mock()
        
        def mock_client_factory(service_name, **kwargs):
            if service_name == 'transcribe':
                return mock_transcribe
            elif service_name == 'bedrock-runtime':
                return mock_bedrock
            elif service_name == 's3':
                return mock_s3
            return Mock()
        
        mock_boto_client.side_effect = mock_client_factory
        
        # Mock responses
        mock_transcribe.start_transcription_job.return_value = {
            'TranscriptionJob': {'TranscriptionJobName': 'test-job'}
        }
        mock_transcribe.get_transcription_job.return_value = {
            'TranscriptionJob': {
                'TranscriptionJobStatus': 'COMPLETED',
                'Transcript': {'TranscriptFileUri': 'https://test-transcript.com'}
            }
        }
        mock_bedrock.converse.return_value = create_mock_bedrock_response("HELLO WORLD")
        mock_s3.generate_presigned_url.return_value = "https://test-video-url.com/video.webm"
        
        # Mock transcript retrieval
        with patch('requests.get') as mock_requests, \
             patch('subprocess.run') as mock_subprocess, \
             patch('os.path.exists', return_value=True), \
             patch('os.path.getsize', return_value=1000), \
             patch('pathlib.Path.mkdir'), \
             patch('builtins.open', create=True):
            
            mock_requests.return_value.text = '{"results": {"transcripts": [{"transcript": "Hello world"}]}}'
            mock_subprocess.return_value = Mock(returncode=0)
            
            # Test the workflow
            payload = {
                "message": "Process audio file",
                "type": "audio",
                "bucket_name": "test-bucket",
                "key_name": "test-audio.mp3"
            }
            
            result = invoke(payload)
        
        # Assertions
        self.assertIsInstance(result, str)
        self.assertIn("Translation completed successfully", result)
        
        # Verify services were called
        mock_transcribe.start_transcription_job.assert_called()
        mock_bedrock.converse.assert_called()
    
    def test_help_request_workflow(self):
        """Test help request workflow"""
        from slagent import invoke
        
        payload = {
            "message": "What can you do?",
            "type": "text"
        }
        
        result = invoke(payload)
        
        # Assertions
        self.assertIsInstance(result, str)
        self.assertIn("help", result.lower())
    
    def test_error_handling_workflow(self):
        """Test error handling in workflows"""
        from slagent import invoke
        
        # Test with invalid payload
        with self.assertRaises(Exception):
            invoke({})  # Empty payload should raise error
        
        # Test with missing required fields for audio
        payload = {
            "message": "Process audio",
            "type": "audio"
            # Missing bucket_name and key_name
        }
        
        result = invoke(payload)
        self.assertIsInstance(result, str)
        self.assertIn("error", result.lower())
    
    def test_conversation_context(self):
        """Test conversation context management"""
        from slagent import invoke
        
        session_id = "test-session-123"
        
        # First request
        payload1 = {
            "message": "Hello world",
            "type": "text",
            "session_id": session_id
        }
        
        with patch('boto3.client') as mock_boto_client:
            mock_bedrock = Mock()
            mock_s3 = Mock()
            
            def mock_client_factory(service_name, **kwargs):
                if service_name == 'bedrock-runtime':
                    return mock_bedrock
                elif service_name == 's3':
                    return mock_s3
                return Mock()
            
            mock_boto_client.side_effect = mock_client_factory
            mock_bedrock.converse.return_value = create_mock_bedrock_response("HELLO WORLD")
            mock_s3.generate_presigned_url.return_value = "https://test-video-url.com/video.webm"
            
            with patch('subprocess.run') as mock_subprocess, \
                 patch('os.path.exists', return_value=True), \
                 patch('os.path.getsize', return_value=1000), \
                 patch('pathlib.Path.mkdir'), \
                 patch('builtins.open', create=True):
                
                mock_subprocess.return_value = Mock(returncode=0)
                
                result1 = invoke(payload1)
        
        # Second request - status check
        payload2 = {
            "message": "What was my last translation?",
            "type": "text",
            "session_id": session_id
        }
        
        result2 = invoke(payload2)
        
        # Assertions
        self.assertIsInstance(result1, str)
        self.assertIsInstance(result2, str)
        # Context should be maintained between requests


class TestAPIIntegration(unittest.TestCase):
    """Test API endpoint integration"""
    
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
    def test_rest_api_handler(self, mock_boto_client):
        """Test REST API handler integration"""
        try:
            from audio2sign_handler import lambda_handler as rest_handler
        except ImportError:
            self.skipTest("REST API handler not available")
        
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
        
        # Test REST API event
        event = {
            'body': json.dumps({
                'text': 'Hello world'
            }),
            'headers': {'Content-Type': 'application/json'}
        }
        context = Mock()
        
        with patch('subprocess.run') as mock_subprocess, \
             patch('os.path.exists', return_value=True), \
             patch('os.path.getsize', return_value=1000), \
             patch('pathlib.Path.mkdir'), \
             patch('builtins.open', create=True):
            
            mock_subprocess.return_value = Mock(returncode=0)
            
            result = rest_handler(event, context)
        
        # Assertions
        self.assertIsInstance(result, dict)
        self.assertIn('statusCode', result)
        self.assertEqual(result['statusCode'], 200)
        
        # Parse response body
        body = json.loads(result['body'])
        self.assertIn('message', body)
    
    @patch('boto3.client')
    def test_websocket_handler(self, mock_boto_client):
        """Test WebSocket handler integration"""
        try:
            from handler import lambda_handler as websocket_handler
        except ImportError:
            self.skipTest("WebSocket handler not available")
        
        # Mock AWS clients
        mock_bedrock = Mock()
        mock_apigateway = Mock()
        
        def mock_client_factory(service_name, **kwargs):
            if service_name == 'bedrock-runtime':
                return mock_bedrock
            elif service_name == 'apigatewaymanagementapi':
                return mock_apigateway
            return Mock()
        
        mock_boto_client.side_effect = mock_client_factory
        
        # Mock responses
        mock_bedrock.converse.return_value = create_mock_bedrock_response("HELLO WORLD")
        
        # Test WebSocket event
        event = {
            'requestContext': {
                'connectionId': 'test-connection-123',
                'domainName': 'test-domain.com',
                'stage': 'test'
            },
            'body': json.dumps({
                'text': 'Hello world'
            })
        }
        context = Mock()
        
        result = websocket_handler(event, context)
        
        # Assertions
        self.assertIsInstance(result, dict)
        self.assertIn('statusCode', result)


class TestPerformanceIntegration(unittest.TestCase):
    """Test performance and load handling"""
    
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
    def test_concurrent_requests(self, mock_boto_client):
        """Test handling of concurrent requests"""
        from slagent import invoke
        import threading
        
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
        mock_bedrock.converse.return_value = create_mock_bedrock_response("TEST GLOSS")
        mock_s3.generate_presigned_url.return_value = "https://test-video-url.com/video.webm"
        
        results = []
        errors = []
        
        def make_request(request_id):
            try:
                payload = {
                    "message": f"Test request {request_id}",
                    "type": "text",
                    "session_id": f"session-{request_id}"
                }
                
                with patch('subprocess.run') as mock_subprocess, \
                     patch('os.path.exists', return_value=True), \
                     patch('os.path.getsize', return_value=1000), \
                     patch('pathlib.Path.mkdir'), \
                     patch('builtins.open', create=True):
                    
                    mock_subprocess.return_value = Mock(returncode=0)
                    result = invoke(payload)
                    results.append(result)
            except Exception as e:
                errors.append(str(e))
        
        # Create multiple threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=make_request, args=(i,))
            threads.append(thread)
        
        # Start all threads
        for thread in threads:
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join(timeout=10)
        
        # Assertions
        self.assertEqual(len(results), 5)
        self.assertEqual(len(errors), 0)
        
        for result in results:
            self.assertIsInstance(result, str)
    
    def test_load_testing(self):
        """Test system under load"""
        from slagent import invoke
        
        # Benchmark multiple requests
        def test_request():
            payload = {
                "message": "Load test request",
                "type": "text"
            }
            
            with patch('boto3.client') as mock_boto_client:
                mock_bedrock = Mock()
                mock_boto_client.return_value = mock_bedrock
                mock_bedrock.converse.return_value = create_mock_bedrock_response("LOAD TEST")
                
                return invoke(payload)
        
        # Run load test
        result = performance_benchmark.benchmark_function(
            test_request, iterations=10
        )
        
        # Assertions
        self.assertGreaterEqual(result['success_rate'], 0.8)  # At least 80% success rate
        self.assertLess(result['avg_time'], 2.0)  # Average response time under 2 seconds
    
    def test_memory_usage(self):
        """Test memory usage under load"""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss
        
        # Perform multiple operations
        from slagent import invoke
        
        with patch('boto3.client') as mock_boto_client:
            mock_bedrock = Mock()
            mock_boto_client.return_value = mock_bedrock
            mock_bedrock.converse.return_value = create_mock_bedrock_response("MEMORY TEST")
            
            for i in range(20):
                payload = {
                    "message": f"Memory test {i}",
                    "type": "text"
                }
                invoke(payload)
        
        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory
        
        # Memory increase should be reasonable (less than 100MB)
        self.assertLess(memory_increase, 100 * 1024 * 1024)


class TestErrorRecovery(unittest.TestCase):
    """Test error recovery and resilience"""
    
    @classmethod
    def setUpClass(cls):
        """Set up test environment"""
        setup_test_environment()
    
    def test_bedrock_service_failure(self):
        """Test recovery from Bedrock service failure"""
        from slagent import invoke
        from botocore.exceptions import ClientError
        
        with patch('boto3.client') as mock_boto_client:
            mock_bedrock = Mock()
            mock_boto_client.return_value = mock_bedrock
            
            # First call fails, second succeeds
            mock_bedrock.converse.side_effect = [
                ClientError({'Error': {'Code': 'ThrottlingException'}}, 'converse'),
                create_mock_bedrock_response("RECOVERY TEST")
            ]
            
            payload = {
                "message": "Test recovery",
                "type": "text"
            }
            
            result = invoke(payload)
            
            # Should handle error gracefully
            self.assertIsInstance(result, str)
    
    def test_dynamodb_failure_recovery(self):
        """Test recovery from DynamoDB failure"""
        from gloss2pose_handler import get_sign_ids_from_gloss
        from botocore.exceptions import ClientError
        
        with patch('boto3.resource') as mock_boto_resource:
            mock_table = Mock()
            mock_dynamodb = Mock()
            mock_dynamodb.Table.return_value = mock_table
            mock_boto_resource.return_value = mock_dynamodb
            
            # Mock DynamoDB failure
            mock_table.query.side_effect = ClientError(
                {'Error': {'Code': 'ServiceUnavailable'}}, 'query'
            )
            
            # Should handle gracefully and return empty list
            result = get_sign_ids_from_gloss("HELLO WORLD")
            self.assertIsInstance(result, list)
    
    def test_s3_failure_recovery(self):
        """Test recovery from S3 failure"""
        from gloss2pose_handler import gloss_to_video
        from botocore.exceptions import ClientError
        
        with patch('boto3.client') as mock_boto_client, \
             patch('boto3.resource') as mock_boto_resource:
            
            # Mock DynamoDB success
            mock_table = Mock()
            mock_dynamodb = Mock()
            mock_dynamodb.Table.return_value = mock_table
            mock_boto_resource.return_value = mock_dynamodb
            mock_table.query.return_value = {
                'Count': 1,
                'Items': [{'SignID': 'test_sign_001'}]
            }
            
            # Mock S3 failure
            mock_s3 = Mock()
            mock_boto_client.return_value = mock_s3
            mock_s3.download_file.side_effect = ClientError(
                {'Error': {'Code': 'NoSuchKey'}}, 'download_file'
            )
            
            # Should handle gracefully
            with self.assertRaises(RuntimeError):
                gloss_to_video("HELLO")


if __name__ == '__main__':
    # Set up logging for tests
    import logging
    logging.basicConfig(level=logging.DEBUG)
    
    # Run tests
    unittest.main(verbosity=2)