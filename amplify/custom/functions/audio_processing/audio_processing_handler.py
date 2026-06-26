import json
import os
import time
import logging
from typing import Optional, Dict, Any
import uuid
import sys
from pathlib import Path

import boto3
from botocore.exceptions import ClientError, BotoCoreError
import requests
import re
from strands import tool

# Configure logging first
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Add signlanguageagent to path for error handling imports
current_dir = Path(__file__).parent
agent_dir = current_dir.parent / 'signlanguageagent'
if agent_dir.exists():
    sys.path.insert(0, str(agent_dir))

try:
    from error_handling import (
        transcribe_retry, handle_tool_error, FallbackStrategy,
        with_retry_and_circuit_breaker, RetryConfig, CircuitBreakerConfig
    )
    ERROR_HANDLING_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Error handling module not available: {e}")
    ERROR_HANDLING_AVAILABLE = False
    # Create dummy decorator if error handling not available
    def transcribe_retry(func):
        return func

# Environment variables
transcribe_region = os.environ.get('AWS_REGION', 'us-east-1')


def lambda_handler(event, context):
    """Lambda handler for audio processing and transcription
    
    Parameters
    ----------
    event: dict, required
        Input event containing bucket name and key name
    context: object, required
        Lambda Context runtime methods and attributes
    Returns
    ------
        dict: Object containing transcribed text
    """
    try:
        bucket_name = event.get("BucketName", "")
        key_name = event.get("KeyName", "")
        
        if not bucket_name or not key_name:
            return {'Error': 'BucketName and KeyName are required'}
        
        text = process_audio_input(bucket_name, key_name)
        return {'Text': text, 'BucketName': bucket_name, 'KeyName': key_name}
        
    except Exception as e:
        logger.error(f"Error in lambda_handler: {str(e)}")
        return {'Error': f'Audio processing failed: {str(e)}'}


@tool
@transcribe_retry
def process_audio_input(bucket_name: str, key_name: str) -> str:
    """Process audio file and return transcribed text with enhanced error handling
    
    Args:
        bucket_name: S3 bucket containing the audio file
        key_name: S3 key (path) to the audio file
        
    Returns:
        str: Transcribed text from the audio file
        
    Raises:
        ValueError: If bucket_name or key_name is empty
        RuntimeError: If transcription fails after retries
    """
    if not bucket_name or not bucket_name.strip():
        raise ValueError("Bucket name cannot be empty")
    
    if not key_name or not key_name.strip():
        raise ValueError("Key name cannot be empty")
    
    bucket_name = bucket_name.strip()
    key_name = key_name.strip()
    
    logger.info(f"Starting audio processing for s3://{bucket_name}/{key_name}")
    
    try:
        return _perform_audio_processing(bucket_name, key_name)
    except Exception as e:
        if ERROR_HANDLING_AVAILABLE:
            error_info = handle_tool_error("process_audio_input", e, {
                "bucket_name": bucket_name, "key_name": key_name
            })
            logger.error(f"Audio processing failed: {error_info}")
            
            # Try fallback strategy
            try:
                fallback_result = FallbackStrategy.audio_processing_fallback(bucket_name, key_name)
                logger.info(f"Using fallback result for audio processing")
                return fallback_result
            except Exception as fallback_error:
                logger.error(f"Fallback strategy also failed: {fallback_error}")
                raise RuntimeError(f"Audio processing failed: {str(e)}")
        else:
            raise RuntimeError(f"Audio processing failed: {str(e)}")


def _perform_audio_processing(bucket_name: str, key_name: str) -> str:
    """Perform the actual audio processing and transcription"""
    # Start transcription job
    job_name = start_transcription_job(bucket_name, key_name)
    
    # Wait for job completion and get results
    transcribed_text = wait_for_transcription_and_extract_text(job_name)
    
    logger.info(f"Successfully transcribed audio: '{transcribed_text[:100]}...'")
    return transcribed_text


def start_transcription_job(bucket_name: str, key_name: str) -> str:
    """Start AWS Transcribe job with enhanced error handling"""
    # Generate unique job name
    timestamp = int(time.time())
    random_suffix = str(uuid.uuid4())[:8]
    job_name = f"transcription-{timestamp}-{random_suffix}"
    
    # Construct S3 URI
    media_uri = f"s3://{bucket_name}/{key_name}"
    
    try:
        transcribe_client = boto3.client('transcribe', region_name=transcribe_region)
        
        # Determine media format from file extension
        media_format = get_media_format(key_name)
        
        logger.info(f"Starting transcription job '{job_name}'")
        
        response = transcribe_client.start_transcription_job(
            TranscriptionJobName=job_name,
            Media={'MediaFileUri': media_uri},
            MediaFormat=media_format,
            LanguageCode='en-US',
            Settings={
                'ShowSpeakerLabels': False,
                'MaxSpeakerLabels': 2,
                'ShowAlternatives': False,
                'MaxAlternatives': 1
            }
        )
        
        logger.info(f"Successfully started transcription job: {job_name}")
        return job_name
        
    except (ClientError, BotoCoreError) as e:
        # Let the retry decorator handle AWS-specific errors
        raise e
    except Exception as e:
        logger.error(f"Unexpected error starting transcription job: {str(e)}")
        raise RuntimeError(f"Failed to start transcription job: {str(e)}")


def get_media_format(key_name: str) -> str:
    """Determine media format from file extension"""
    extension = key_name.lower().split('.')[-1]
    
    format_mapping = {
        'mp3': 'mp3',
        'mp4': 'mp4',
        'm4a': 'mp4',
        'wav': 'wav',
        'flac': 'flac',
        'ogg': 'ogg',
        'amr': 'amr',
        'webm': 'webm'
    }
    
    return format_mapping.get(extension, 'mp3')  # Default to mp3


def wait_for_transcription_and_extract_text(job_name: str) -> str:
    """Wait for transcription job completion and extract text with comprehensive error handling"""
    max_wait_time = 600  # 10 minutes
    poll_interval = 10   # 10 seconds
    start_time = time.time()
    
    transcribe_client = boto3.client('transcribe', region_name=transcribe_region)
    
    logger.info(f"Waiting for transcription job '{job_name}' to complete...")
    
    while time.time() - start_time < max_wait_time:
        try:
            response = transcribe_client.get_transcription_job(TranscriptionJobName=job_name)
            job_status = response['TranscriptionJob']['TranscriptionJobStatus']
            
            logger.info(f"Transcription job status: {job_status}")
            
            if job_status == 'COMPLETED':
                # Extract transcript from the completed job
                return extract_transcript_from_job(response['TranscriptionJob'])
                
            elif job_status == 'FAILED':
                failure_reason = response['TranscriptionJob'].get('FailureReason', 'Unknown failure')
                raise RuntimeError(f"Transcription job failed: {failure_reason}")
                
            elif job_status in ['IN_PROGRESS', 'QUEUED']:
                # Continue waiting
                time.sleep(poll_interval)
                continue
            else:
                raise RuntimeError(f"Unexpected transcription job status: {job_status}")
                
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            error_message = e.response.get('Error', {}).get('Message', 'Unknown')
            raise RuntimeError(f"Error checking transcription job status: {error_code} - {error_message}")
            
        except Exception as e:
            logger.error(f"Unexpected error while waiting for transcription: {str(e)}")
            raise RuntimeError(f"Error waiting for transcription completion: {str(e)}")
    
    # Timeout reached
    raise RuntimeError(f"Transcription job '{job_name}' did not complete within {max_wait_time} seconds")


def extract_transcript_from_job(transcription_job: Dict[str, Any]) -> str:
    """Extract transcript text from completed transcription job"""
    try:
        transcript_uri = transcription_job['Transcript']['TranscriptFileUri']
        logger.info(f"Extracting transcript from: {transcript_uri}")
        
        # Validate that the URL is from an expected AWS domain
        if not re.match(r'^https://.*\.amazonaws\.com/.*', transcript_uri):
            raise RuntimeError("Invalid transcript URL: The URL does not point to an AWS domain")
        
        # Download and parse transcript
        max_retries = 3
        base_delay = 1.0
        
        for attempt in range(max_retries):
            try:
                response = requests.get(transcript_uri, timeout=30)
                response.raise_for_status()
                
                # Parse the JSON response
                transcript_data = response.json()
                
                # Extract the transcript text
                transcripts = transcript_data.get("results", {}).get("transcripts", [])
                if not transcripts:
                    raise RuntimeError("No transcripts found in the response")
                
                transcript_text = transcripts[0].get("transcript", "").strip()
                
                if not transcript_text:
                    raise RuntimeError("Empty transcript text")
                
                logger.info(f"Successfully extracted transcript: '{transcript_text[:100]}...'")
                return transcript_text
                
            except requests.exceptions.RequestException as e:
                logger.warning(f"Request error on attempt {attempt + 1}: {str(e)}")
                if attempt == max_retries - 1:
                    raise RuntimeError(f"Failed to download transcript after {max_retries} attempts: {str(e)}")
                    
            except json.JSONDecodeError as e:
                logger.error(f"JSON decode error: {str(e)}")
                raise RuntimeError(f"Failed to parse transcript JSON: {str(e)}")
                
            except Exception as e:
                logger.error(f"Unexpected error extracting transcript: {str(e)}")
                if attempt == max_retries - 1:
                    raise RuntimeError(f"Failed to extract transcript after {max_retries} attempts: {str(e)}")
            
            # Exponential backoff
            if attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt)
                logger.info(f"Retrying transcript extraction in {delay} seconds...")
                time.sleep(delay)
                
    except KeyError as e:
        raise RuntimeError(f"Missing expected field in transcription job response: {str(e)}")
    except Exception as e:
        raise RuntimeError(f"Error extracting transcript: {str(e)}")


@tool
def get_transcription_result(transcription_job_name: str) -> str:
    """Get the result from an existing AWS Transcription Job
    
    Args:
        transcription_job_name: Name of the transcription job
        
    Returns:
        str: Transcribed text
        
    Raises:
        ValueError: If job name is empty
        RuntimeError: If job retrieval fails
    """
    if not transcription_job_name or not transcription_job_name.strip():
        raise ValueError("Transcription job name cannot be empty")
    
    job_name = transcription_job_name.strip()
    
    try:
        transcribe_client = boto3.client('transcribe', region_name=transcribe_region)
        
        logger.info(f"Getting transcription job result for: {job_name}")
        
        response = transcribe_client.get_transcription_job(TranscriptionJobName=job_name)
        transcription_job = response['TranscriptionJob']
        
        job_status = transcription_job['TranscriptionJobStatus']
        
        if job_status == 'COMPLETED':
            return extract_transcript_from_job(transcription_job)
        elif job_status == 'FAILED':
            failure_reason = transcription_job.get('FailureReason', 'Unknown failure')
            raise RuntimeError(f"Transcription job failed: {failure_reason}")
        else:
            raise RuntimeError(f"Transcription job is not completed. Current status: {job_status}")
            
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', 'Unknown')
        error_message = e.response.get('Error', {}).get('Message', 'Unknown')
        raise RuntimeError(f"Error retrieving transcription job: {error_code} - {error_message}")
    except Exception as e:
        raise RuntimeError(f"Error getting transcription result: {str(e)}")


if __name__ == "__main__":
    # Test cases
    test_cases = [
        {"BucketName": "test-bucket", "KeyName": "test-audio.mp3"},
        {"BucketName": "test-bucket", "KeyName": "sample-speech.wav"}
    ]
    
    for test_case in test_cases:
        try:
            result = lambda_handler(test_case, {})
            print(f"Input: {test_case}")
            print(f"Result: {result}")
            print("-" * 50)
        except Exception as e:
            print(f"Error testing {test_case}: {str(e)}")