"""
Test configuration and utilities for the GenASL Sign Language Agent

This module provides test configuration, fixtures, and utilities for
comprehensive testing of the agent and tools.
"""

import os
import json
import time
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from unittest.mock import Mock, MagicMock
import boto3
from moto import mock_dynamodb, mock_s3, mock_bedrock_runtime

# Test configuration
TEST_CONFIG = {
    'aws': {
        'region': 'us-west-2',
        'pose_bucket': 'test-genasl-avatar',
        'asl_data_bucket': 'test-genasl-data',
        'table_name': 'Test_Pose_Data',
        'key_prefix': 'test/aslavatarv2/gloss2pose/lookup/'
    },
    'model': {
        'eng_to_asl_model': 'test.amazon.nova-lite-v1:0',
        'max_tokens': 1000,
        'temperature': 0.0,
        'top_p': 0.5
    },
    'agent': {
        'log_level': 'DEBUG',
        'timeout_seconds': 30,
        'max_retries': 2,
        'retry_delay': 0.1
    }
}

@dataclass
class TestCase:
    """Test case data structure"""
    name: str
    input_data: Dict[str, Any]
    expected_output: Any
    expected_error: Optional[str] = None
    description: str = ""

# Test data fixtures
SAMPLE_GLOSSES = [
    'HELLO',
    'WORLD',
    'THANK-YOU',
    'IX-1P',
    'LIKE',
    'MOVIE'
]

SAMPLE_SIGN_IDS = [
    'sign_001',
    'sign_002', 
    'sign_003',
    'sign_004',
    'sign_005',
    'sign_006'
]

TEXT_TO_GLOSS_TEST_CASES = [
    TestCase(
        name="simple_greeting",
        input_data={"text": "Hello world"},
        expected_output="HELLO WORLD",
        description="Simple greeting conversion"
    ),
    TestCase(
        name="personal_statement",
        input_data={"text": "I like movies"},
        expected_output="IX-1P LIKE MOVIE",
        description="Personal statement with pronoun"
    ),
    TestCase(
        name="gratitude",
        input_data={"text": "Thank you"},
        expected_output="THANK-YOU",
        description="Gratitude expression"
    ),
    TestCase(
        name="empty_text",
        input_data={"text": ""},
        expected_output=None,
        expected_error="Text cannot be empty",
        description="Empty text input should raise error"
    ),
    TestCase(
        name="whitespace_only",
        input_data={"text": "   "},
        expected_output=None,
        expected_error="Text cannot be empty",
        description="Whitespace-only text should raise error"
    )
]

GLOSS_TO_VIDEO_TEST_CASES = [
    TestCase(
        name="simple_gloss",
        input_data={"gloss_sentence": "HELLO WORLD", "text": "Hello world"},
        expected_output={
            "PoseURL": "https://test-url.com/pose.webm",
            "SignURL": "https://test-url.com/sign.webm", 
            "AvatarURL": "https://test-url.com/avatar.webm",
            "Gloss": "HELLO WORLD",
            "Text": "Hello world"
        },
        description="Simple gloss to video conversion"
    ),
    TestCase(
        name="pose_only",
        input_data={"gloss_sentence": "HELLO", "pose_only": True},
        expected_output={
            "PoseURL": "https://test-url.com/pose.webm",
            "Gloss": "HELLO",
            "Text": None
        },
        description="Pose-only video generation"
    ),
    TestCase(
        name="empty_gloss",
        input_data={"gloss_sentence": ""},
        expected_output=None,
        expected_error="Gloss sentence cannot be empty",
        description="Empty gloss should raise error"
    )
]

AGENT_WORKFLOW_TEST_CASES = [
    TestCase(
        name="text_to_asl_workflow",
        input_data={
            "message": "Hello world",
            "type": "text"
        },
        expected_output="Translation completed successfully",
        description="Complete text-to-ASL workflow"
    ),
    TestCase(
        name="audio_to_asl_workflow", 
        input_data={
            "message": "Process audio file",
            "type": "audio",
            "metadata": {
                "bucket_name": "test-bucket",
                "key_name": "test-audio.mp3"
            }
        },
        expected_output="Translation completed successfully",
        description="Complete audio-to-ASL workflow"
    ),
    TestCase(
        name="help_request",
        input_data={
            "message": "What can you do?",
            "type": "text"
        },
        expected_output="I can help you with ASL translation",
        description="Help request handling"
    )
]

class MockAWSServices:
    """Mock AWS services for testing"""
    
    def __init__(self):
        self.dynamodb_mock = mock_dynamodb()
        self.s3_mock = mock_s3()
        self.bedrock_mock = mock_bedrock_runtime()
        
    def __enter__(self):
        self.dynamodb_mock.start()
        self.s3_mock.start() 
        self.bedrock_mock.start()
        
        # Set up mock DynamoDB table
        self._setup_dynamodb_table()
        
        # Set up mock S3 buckets
        self._setup_s3_buckets()
        
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.bedrock_mock.stop()
        self.s3_mock.stop()
        self.dynamodb_mock.stop()
    
    def _setup_dynamodb_table(self):
        """Set up mock DynamoDB table with test data"""
        dynamodb = boto3.resource('dynamodb', region_name='us-west-2')
        
        # Create table
        table = dynamodb.create_table(
            TableName=TEST_CONFIG['aws']['table_name'],
            KeySchema=[
                {'AttributeName': 'Gloss', 'KeyType': 'HASH'}
            ],
            AttributeDefinitions=[
                {'AttributeName': 'Gloss', 'AttributeType': 'S'}
            ],
            BillingMode='PAY_PER_REQUEST'
        )
        
        # Add test data
        for gloss, sign_id in zip(SAMPLE_GLOSSES, SAMPLE_SIGN_IDS):
            table.put_item(Item={'Gloss': gloss, 'SignID': sign_id})
    
    def _setup_s3_buckets(self):
        """Set up mock S3 buckets with test data"""
        s3 = boto3.client('s3', region_name='us-west-2')
        
        # Create buckets
        s3.create_bucket(
            Bucket=TEST_CONFIG['aws']['pose_bucket'],
            CreateBucketConfiguration={'LocationConstraint': 'us-west-2'}
        )
        s3.create_bucket(
            Bucket=TEST_CONFIG['aws']['asl_data_bucket'],
            CreateBucketConfiguration={'LocationConstraint': 'us-west-2'}
        )
        
        # Add test video files
        for sign_id in SAMPLE_SIGN_IDS:
            for video_type in ['pose', 'sign', 'avatar']:
                key = f"{TEST_CONFIG['aws']['key_prefix']}{video_type}/{video_type}-{sign_id}.mp4"
                s3.put_object(
                    Bucket=TEST_CONFIG['aws']['pose_bucket'],
                    Key=key,
                    Body=b'fake video content'
                )

def setup_test_environment():
    """Set up test environment variables"""
    for section, config in TEST_CONFIG.items():
        if isinstance(config, dict):
            for key, value in config.items():
                env_key = key.upper()
                if section == 'aws':
                    if key == 'region':
                        env_key = 'AWS_REGION'
                    elif key == 'pose_bucket':
                        env_key = 'POSE_BUCKET'
                    elif key == 'asl_data_bucket':
                        env_key = 'ASL_DATA_BUCKET'
                    elif key == 'table_name':
                        env_key = 'TABLE_NAME'
                    elif key == 'key_prefix':
                        env_key = 'KEY_PREFIX'
                elif section == 'model':
                    if key == 'eng_to_asl_model':
                        env_key = 'ENG_TO_ASL_MODEL'
                    elif key == 'max_tokens':
                        env_key = 'MAX_TOKENS'
                    elif key == 'temperature':
                        env_key = 'TEMPERATURE'
                    elif key == 'top_p':
                        env_key = 'TOP_P'
                elif section == 'agent':
                    if key == 'log_level':
                        env_key = 'LOG_LEVEL'
                    elif key == 'timeout_seconds':
                        env_key = 'TIMEOUT_SECONDS'
                    elif key == 'max_retries':
                        env_key = 'MAX_RETRIES'
                    elif key == 'retry_delay':
                        env_key = 'RETRY_DELAY'
                
                os.environ[env_key] = str(value)

def create_mock_bedrock_response(gloss_output: str) -> Dict[str, Any]:
    """Create mock Bedrock response"""
    return {
        "output": {
            "message": {
                "content": [{"text": gloss_output}]
            }
        },
        "usage": {
            "inputTokens": 50,
            "outputTokens": 10
        }
    }

def create_mock_transcribe_response(transcribed_text: str) -> Dict[str, Any]:
    """Create mock Transcribe response"""
    return {
        "TranscriptionJob": {
            "TranscriptionJobName": "test-job",
            "TranscriptionJobStatus": "COMPLETED",
            "Transcript": {
                "TranscriptFileUri": "https://test-transcript-url.com"
            }
        }
    }

class PerformanceBenchmark:
    """Performance benchmarking utilities"""
    
    def __init__(self):
        self.results: List[Dict[str, Any]] = []
    
    def benchmark_function(self, func, *args, iterations: int = 10, **kwargs):
        """Benchmark a function's performance"""
        times = []
        errors = 0
        
        for i in range(iterations):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                success = True
            except Exception as e:
                result = None
                success = False
                errors += 1
            
            end_time = time.time()
            times.append(end_time - start_time)
        
        avg_time = sum(times) / len(times)
        min_time = min(times)
        max_time = max(times)
        
        benchmark_result = {
            'function': func.__name__,
            'iterations': iterations,
            'avg_time': avg_time,
            'min_time': min_time,
            'max_time': max_time,
            'success_rate': (iterations - errors) / iterations,
            'errors': errors
        }
        
        self.results.append(benchmark_result)
        return benchmark_result
    
    def get_report(self) -> Dict[str, Any]:
        """Get performance benchmark report"""
        return {
            'timestamp': time.time(),
            'total_benchmarks': len(self.results),
            'results': self.results
        }

# Global benchmark instance
performance_benchmark = PerformanceBenchmark()

def assert_response_structure(response: Dict[str, Any], expected_keys: List[str]):
    """Assert that response has expected structure"""
    for key in expected_keys:
        assert key in response, f"Expected key '{key}' not found in response"

def assert_valid_url(url: str):
    """Assert that URL is valid"""
    assert url.startswith('http'), f"Invalid URL: {url}"
    assert len(url) > 10, f"URL too short: {url}"

def assert_valid_gloss(gloss: str):
    """Assert that gloss is valid ASL notation"""
    assert isinstance(gloss, str), "Gloss must be a string"
    assert len(gloss.strip()) > 0, "Gloss cannot be empty"
    # ASL gloss is typically uppercase
    assert gloss.isupper() or gloss.strip() == "", f"Gloss should be uppercase: {gloss}"