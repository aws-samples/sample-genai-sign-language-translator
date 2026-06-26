"""
Unit tests for GenASL Strands tools

This module contains comprehensive unit tests for all Strands tools
including text2gloss, gloss2pose, audio processing, and ASL analysis.
"""

import unittest
import sys
import os
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

# Add parent directories to path for imports
current_dir = Path(__file__).parent
functions_dir = current_dir.parent
sys.path.insert(0, str(functions_dir / 'text2gloss'))
sys.path.insert(0, str(functions_dir / 'gloss2pose'))
sys.path.insert(0, str(functions_dir / 'audio_processing'))
sys.path.insert(0, str(functions_dir / 'asl_analysis'))

from test_config import (
    setup_test_environment, MockAWSServices, TEXT_TO_GLOSS_TEST_CASES,
    GLOSS_TO_VIDEO_TEST_CASES, create_mock_bedrock_response,
    assert_response_structure, assert_valid_url, assert_valid_gloss,
    performance_benchmark
)

class TestText2GlossTools(unittest.TestCase):
    """Test cases for text-to-gloss conversion tools"""
    
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
    def test_text_to_asl_gloss_success(self, mock_boto_client):
        """Test successful text-to-gloss conversion"""
        # Import after setting up environment
        from text2gloss_handler import text_to_asl_gloss
        
        # Mock Bedrock client
        mock_client = Mock()
        mock_boto_client.return_value = mock_client
        mock_client.converse.return_value = create_mock_bedrock_response("HELLO WORLD")
        
        # Test conversion
        result = text_to_asl_gloss("Hello world")
        
        # Assertions
        self.assertIsInstance(result, str)
        assert_valid_gloss(result)
        self.assertEqual(result, "HELLO WORLD")
        
        # Verify Bedrock was called
        mock_client.converse.assert_called_once()
    
    def test_text_to_asl_gloss_empty_input(self):
        """Test text-to-gloss with empty input"""
        from text2gloss_handler import text_to_asl_gloss
        
        with self.assertRaises(ValueError) as context:
            text_to_asl_gloss("")
        
        self.assertIn("Text cannot be empty", str(context.exception))
    
    def test_text_to_asl_gloss_whitespace_input(self):
        """Test text-to-gloss with whitespace-only input"""
        from text2gloss_handler import text_to_asl_gloss
        
        with self.assertRaises(ValueError) as context:
            text_to_asl_gloss("   ")
        
        self.assertIn("Text cannot be empty", str(context.exception))
    
    @patch('boto3.client')
    def test_text_to_asl_gloss_bedrock_error(self, mock_boto_client):
        """Test text-to-gloss with Bedrock error"""
        from text2gloss_handler import text_to_asl_gloss
        from botocore.exceptions import ClientError
        
        # Mock Bedrock client to raise error
        mock_client = Mock()
        mock_boto_client.return_value = mock_client
        mock_client.converse.side_effect = ClientError(
            {'Error': {'Code': 'ThrottlingException'}}, 'converse'
        )
        
        with self.assertRaises(RuntimeError):
            text_to_asl_gloss("Hello world")
    
    def test_text_to_asl_gloss_performance(self):
        """Test text-to-gloss performance"""
        from text2gloss_handler import text_to_asl_gloss
        
        with patch('boto3.client') as mock_boto_client:
            mock_client = Mock()
            mock_boto_client.return_value = mock_client
            mock_client.converse.return_value = create_mock_bedrock_response("TEST GLOSS")
            
            # Benchmark the function
            result = performance_benchmark.benchmark_function(
                text_to_asl_gloss, "Test text", iterations=5
            )
            
            # Assert performance metrics
            self.assertLess(result['avg_time'], 1.0)  # Should complete in under 1 second
            self.assertEqual(result['success_rate'], 1.0)  # Should have 100% success rate


class TestGloss2PoseTools(unittest.TestCase):
    """Test cases for gloss-to-pose conversion tools"""
    
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
    
    @patch('subprocess.run')
    @patch('boto3.client')
    def test_gloss_to_video_success(self, mock_boto_client, mock_subprocess):
        """Test successful gloss-to-video conversion"""
        from gloss2pose_handler import gloss_to_video
        
        # Mock S3 client
        mock_s3_client = Mock()
        mock_boto_client.return_value = mock_s3_client
        mock_s3_client.generate_presigned_url.return_value = "https://test-url.com/video.webm"
        
        # Mock subprocess (FFmpeg)
        mock_subprocess.return_value = Mock(returncode=0)
        
        # Mock file operations
        with patch('os.path.exists', return_value=True), \
             patch('os.path.getsize', return_value=1000), \
             patch('pathlib.Path.mkdir'), \
             patch('builtins.open', create=True):
            
            result = gloss_to_video("HELLO WORLD", "Hello world")
        
        # Assertions
        self.assertIsInstance(result, dict)
        assert_response_structure(result, ['PoseURL', 'SignURL', 'AvatarURL', 'Gloss', 'Text'])
        assert_valid_url(result['PoseURL'])
        self.assertEqual(result['Gloss'], "HELLO WORLD")
        self.assertEqual(result['Text'], "Hello world")
    
    def test_gloss_to_video_empty_input(self):
        """Test gloss-to-video with empty input"""
        from gloss2pose_handler import gloss_to_video
        
        with self.assertRaises(ValueError) as context:
            gloss_to_video("")
        
        self.assertIn("Gloss sentence cannot be empty", str(context.exception))
    
    @patch('subprocess.run')
    @patch('boto3.client')
    def test_gloss_to_video_pose_only(self, mock_boto_client, mock_subprocess):
        """Test gloss-to-video with pose_only=True"""
        from gloss2pose_handler import gloss_to_video
        
        # Mock S3 client
        mock_s3_client = Mock()
        mock_boto_client.return_value = mock_s3_client
        mock_s3_client.generate_presigned_url.return_value = "https://test-url.com/pose.webm"
        
        # Mock subprocess (FFmpeg)
        mock_subprocess.return_value = Mock(returncode=0)
        
        # Mock file operations
        with patch('os.path.exists', return_value=True), \
             patch('os.path.getsize', return_value=1000), \
             patch('pathlib.Path.mkdir'), \
             patch('builtins.open', create=True):
            
            result = gloss_to_video("HELLO", pose_only=True)
        
        # Assertions
        self.assertIsInstance(result, dict)
        self.assertIn('PoseURL', result)
        self.assertNotIn('SignURL', result)
        self.assertNotIn('AvatarURL', result)
    
    def test_gloss_to_video_missing_env_vars(self):
        """Test gloss-to-video with missing environment variables"""
        from gloss2pose_handler import gloss_to_video
        
        # Temporarily remove environment variable
        original_bucket = os.environ.get('POSE_BUCKET')
        if 'POSE_BUCKET' in os.environ:
            del os.environ['POSE_BUCKET']
        
        try:
            with self.assertRaises(RuntimeError) as context:
                gloss_to_video("HELLO")
            
            self.assertIn("Missing required environment variables", str(context.exception))
        finally:
            # Restore environment variable
            if original_bucket:
                os.environ['POSE_BUCKET'] = original_bucket
    
    def test_gloss_to_video_performance(self):
        """Test gloss-to-video performance"""
        from gloss2pose_handler import gloss_to_video
        
        with patch('subprocess.run') as mock_subprocess, \
             patch('boto3.client') as mock_boto_client, \
             patch('os.path.exists', return_value=True), \
             patch('os.path.getsize', return_value=1000), \
             patch('pathlib.Path.mkdir'), \
             patch('builtins.open', create=True):
            
            mock_s3_client = Mock()
            mock_boto_client.return_value = mock_s3_client
            mock_s3_client.generate_presigned_url.return_value = "https://test-url.com/video.webm"
            mock_subprocess.return_value = Mock(returncode=0)
            
            # Benchmark the function
            result = performance_benchmark.benchmark_function(
                gloss_to_video, "HELLO", iterations=3
            )
            
            # Assert performance metrics
            self.assertLess(result['avg_time'], 5.0)  # Should complete in under 5 seconds
            self.assertGreaterEqual(result['success_rate'], 0.8)  # Should have at least 80% success rate


class TestAudioProcessingTools(unittest.TestCase):
    """Test cases for audio processing tools"""
    
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
    def test_process_audio_input_success(self, mock_boto_client):
        """Test successful audio processing"""
        try:
            from audio_processing_handler import process_audio_input
        except ImportError:
            self.skipTest("Audio processing handler not available")
        
        # Mock Transcribe client
        mock_client = Mock()
        mock_boto_client.return_value = mock_client
        mock_client.start_transcription_job.return_value = {
            'TranscriptionJob': {'TranscriptionJobName': 'test-job'}
        }
        mock_client.get_transcription_job.return_value = {
            'TranscriptionJob': {
                'TranscriptionJobStatus': 'COMPLETED',
                'Transcript': {'TranscriptFileUri': 'https://test-transcript.com'}
            }
        }
        
        # Mock S3 client for transcript retrieval
        with patch('requests.get') as mock_requests:
            mock_requests.return_value.text = '{"results": {"transcripts": [{"transcript": "Hello world"}]}}'
            
            result = process_audio_input("test-bucket", "test-audio.mp3")
        
        # Assertions
        self.assertIsInstance(result, str)
        self.assertEqual(result, "Hello world")
    
    def test_process_audio_input_invalid_params(self):
        """Test audio processing with invalid parameters"""
        try:
            from audio_processing_handler import process_audio_input
        except ImportError:
            self.skipTest("Audio processing handler not available")
        
        with self.assertRaises(ValueError):
            process_audio_input("", "test-audio.mp3")
        
        with self.assertRaises(ValueError):
            process_audio_input("test-bucket", "")


class TestASLAnalysisTools(unittest.TestCase):
    """Test cases for ASL analysis tools"""
    
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
    def test_analyze_asl_video_stream_success(self, mock_boto_client):
        """Test successful ASL video stream analysis"""
        try:
            from asl_analysis_handler import analyze_asl_video_stream
        except ImportError:
            self.skipTest("ASL analysis handler not available")
        
        # Mock Kinesis Video client
        mock_kvs_client = Mock()
        mock_bedrock_client = Mock()
        
        def mock_client_factory(service_name, **kwargs):
            if service_name == 'kinesisvideo':
                return mock_kvs_client
            elif service_name == 'bedrock-runtime':
                return mock_bedrock_client
            return Mock()
        
        mock_boto_client.side_effect = mock_client_factory
        
        # Mock responses
        mock_kvs_client.get_data_endpoint.return_value = {
            'DataEndpoint': 'https://test-endpoint.com'
        }
        mock_bedrock_client.converse.return_value = create_mock_bedrock_response("Hello world")
        
        with patch('cv2.VideoCapture') as mock_cv2:
            mock_cap = Mock()
            mock_cv2.return_value = mock_cap
            mock_cap.read.return_value = (True, Mock())  # Mock frame
            mock_cap.isOpened.return_value = True
            
            result = analyze_asl_video_stream("test-stream")
        
        # Assertions
        self.assertIsInstance(result, str)
        self.assertEqual(result, "Hello world")
    
    def test_analyze_asl_video_stream_invalid_params(self):
        """Test ASL video stream analysis with invalid parameters"""
        try:
            from asl_analysis_handler import analyze_asl_video_stream
        except ImportError:
            self.skipTest("ASL analysis handler not available")
        
        with self.assertRaises(ValueError):
            analyze_asl_video_stream("")


class TestCachingAndPerformance(unittest.TestCase):
    """Test cases for caching and performance optimizations"""
    
    def setUp(self):
        """Set up each test"""
        setup_test_environment()
    
    def test_gloss_pose_cache(self):
        """Test gloss-to-pose mapping cache"""
        from caching import GlossPoseMappingCache
        
        cache = GlossPoseMappingCache(max_size=10, ttl_seconds=60)
        
        # Test cache miss and population
        with patch('boto3.resource') as mock_boto:
            mock_table = Mock()
            mock_dynamodb = Mock()
            mock_dynamodb.Table.return_value = mock_table
            mock_boto.return_value = mock_dynamodb
            
            mock_table.query.return_value = {
                'Count': 1,
                'Items': [{'SignID': 'test_sign_001'}]
            }
            
            # First call should query DynamoDB
            result1 = cache.get_sign_id('HELLO')
            self.assertEqual(result1, 'test_sign_001')
            mock_table.query.assert_called_once()
            
            # Second call should use cache
            mock_table.query.reset_mock()
            result2 = cache.get_sign_id('HELLO')
            self.assertEqual(result2, 'test_sign_001')
            mock_table.query.assert_not_called()
    
    def test_lru_cache(self):
        """Test LRU cache implementation"""
        from caching import LRUCache
        
        cache = LRUCache(max_size=3, ttl_seconds=60)
        
        # Test basic operations
        cache.put('key1', 'value1')
        cache.put('key2', 'value2')
        cache.put('key3', 'value3')
        
        self.assertEqual(cache.get('key1'), 'value1')
        self.assertEqual(cache.get('key2'), 'value2')
        self.assertEqual(cache.get('key3'), 'value3')
        
        # Test LRU eviction
        cache.put('key4', 'value4')  # Should evict key1
        self.assertIsNone(cache.get('key1'))
        self.assertEqual(cache.get('key4'), 'value4')
    
    def test_aws_connection_pool(self):
        """Test AWS connection pooling"""
        from caching import AWSConnectionPool
        
        pool = AWSConnectionPool()
        
        with patch('boto3.client') as mock_boto_client:
            mock_client = Mock()
            mock_boto_client.return_value = mock_client
            
            # First call should create client
            client1 = pool.get_client('s3')
            mock_boto_client.assert_called_once_with(service_name='s3')
            
            # Second call should reuse client
            mock_boto_client.reset_mock()
            client2 = pool.get_client('s3')
            mock_boto_client.assert_not_called()
            
            # Should be the same client instance
            self.assertIs(client1, client2)
    
    def test_request_throttler(self):
        """Test request throttling mechanism"""
        from caching import RequestThrottler
        
        throttler = RequestThrottler(max_concurrent=2, max_queue_size=3)
        
        # First two requests should be allowed
        self.assertTrue(throttler.can_process_request('req1'))
        self.assertTrue(throttler.can_process_request('req2'))
        
        # Third request should be queued
        self.assertFalse(throttler.can_process_request('req3'))
        
        # Complete one request
        throttler.complete_request('req1')
        
        # Now another request should be allowed
        self.assertTrue(throttler.can_process_request('req4'))


if __name__ == '__main__':
    # Set up logging for tests
    import logging
    logging.basicConfig(level=logging.DEBUG)
    
    # Run tests
    unittest.main(verbosity=2)