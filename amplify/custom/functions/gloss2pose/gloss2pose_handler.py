import multiprocessing
import os
import re
import subprocess
import sys
import time
import logging
from threading import Thread
from typing import Optional, Dict, Any, List
from pathlib import Path

import boto3
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError, BotoCoreError
import uuid
import pathlib
from strands import tool

# Configure logging first
logger = logging.getLogger(__name__)

# Add signlanguageagent to path for error handling imports
current_dir = Path(__file__).parent
agent_dir = current_dir.parent / 'signlanguageagent'
if agent_dir.exists():
    sys.path.insert(0, str(agent_dir))

try:
    from error_handling import (
        dynamodb_retry, s3_retry, handle_tool_error, FallbackStrategy,
        with_retry_and_circuit_breaker, RetryConfig, CircuitBreakerConfig
    )
    ERROR_HANDLING_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Error handling module not available: {e}")
    ERROR_HANDLING_AVAILABLE = False
    # Create dummy decorators if error handling not available
    def dynamodb_retry(func):
        return func
    def s3_retry(func):
        return func

try:
    from performance import (
        with_performance_monitoring, optimize_gloss_to_sign_ids,
        get_optimized_dynamodb_resource, get_optimized_s3_client
    )
    PERFORMANCE_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Performance module not available: {e}")
    PERFORMANCE_AVAILABLE = False
    # Create dummy decorator if performance not available
    def with_performance_monitoring(func):
        return func

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Environment variables with defaults
pose_bucket = os.environ.get('POSE_BUCKET', '')
asl_data_bucket = os.environ.get('ASL_DATA_BUCKET', '')
key_prefix = os.environ.get("KEY_PREFIX", "")
table_name = os.environ.get('TABLE_NAME', '')
output_ext = 'webm'


def lambda_handler(event, context):
    """Lambda handler for gloss-to-video conversion
    
    Parameters
    ----------
    event: dict, required
        Input event to the Lambda function
    context: object, required
        Lambda Context runtime methods and attributes
    Returns
    ------
        dict: Object containing video URLs and metadata
    """
    try:
        gloss = event.get("Gloss", "")
        text = event.get('Text')
        
        if not gloss.strip():
            return {'Error': 'No gloss provided for video generation'}
        
        result = gloss_to_video(gloss, text)
        return result
    except Exception as e:
        logger.error(f"Error in lambda_handler: {str(e)}")
        return {'Error': f'Video generation failed: {str(e)}'}


@tool
@with_performance_monitoring
def gloss_to_video(gloss_sentence: str, text: Optional[str] = None, 
                  pose_only: bool = False, pre_sign: bool = True) -> Dict[str, Any]:
    """Convert ASL gloss to pose sequences and generate videos with enhanced error handling
    
    Args:
        gloss_sentence: ASL gloss string to convert
        text: Optional original text for reference
        pose_only: If True, only generate pose video
        pre_sign: If True, generate presigned URLs for S3 objects
        
    Returns:
        dict: Dictionary containing video URLs and metadata
        
    Raises:
        ValueError: If gloss_sentence is empty or invalid
        RuntimeError: If video generation fails
    """
    if not gloss_sentence or not gloss_sentence.strip():
        raise ValueError("Gloss sentence cannot be empty")
    
    # Validate environment variables
    required_env_vars = {
        'POSE_BUCKET': pose_bucket,
        'ASL_DATA_BUCKET': asl_data_bucket,
        'TABLE_NAME': table_name,
        'KEY_PREFIX': key_prefix
    }
    
    missing_vars = [var for var, value in required_env_vars.items() if not value]
    if missing_vars:
        raise RuntimeError(f"Missing required environment variables: {', '.join(missing_vars)}")
    
    gloss_sentence = gloss_sentence.strip()
    uniq_key = str(uuid.uuid4())
    
    logger.info(f"Starting gloss-to-video conversion for: '{gloss_sentence}' (ID: {uniq_key})")
    
    try:
        return _perform_gloss_to_video_conversion(gloss_sentence, text, pose_only, pre_sign, uniq_key)
    except Exception as e:
        if ERROR_HANDLING_AVAILABLE:
            error_info = handle_tool_error("gloss_to_video", e, {
                "gloss": gloss_sentence, "text": text, "pose_only": pose_only
            })
            logger.error(f"Gloss-to-video conversion failed: {error_info}")
            
            # Try fallback strategy
            try:
                fallback_result = FallbackStrategy.gloss_to_video_fallback(gloss_sentence, text)
                logger.info(f"Using fallback result for gloss-to-video")
                return fallback_result
            except Exception as fallback_error:
                logger.error(f"Fallback strategy also failed: {fallback_error}")
                raise RuntimeError(f"Video generation failed: {str(e)}")
        else:
            raise RuntimeError(f"Video generation failed: {str(e)}")


def _perform_gloss_to_video_conversion(gloss_sentence: str, text: Optional[str], 
                                     pose_only: bool, pre_sign: bool, uniq_key: str) -> Dict[str, Any]:
    """Perform the actual gloss-to-video conversion"""
    # Get sign IDs from DynamoDB with error handling and caching
    if PERFORMANCE_AVAILABLE:
        sign_ids = optimize_gloss_to_sign_ids(gloss_sentence)
    else:
        sign_ids = get_sign_ids_from_gloss(gloss_sentence)
    
    if not sign_ids:
        logger.warning(f"No sign IDs found for gloss: '{gloss_sentence}'")
        raise RuntimeError(f'No signs found for gloss: {gloss_sentence}')
    
    logger.info(f"Found {len(sign_ids)} sign IDs: {sign_ids}")
    
    # Process videos with error handling
    manager = multiprocessing.Manager()
    return_dict = manager.dict()
    threads = []
    
    # Always create pose video
    pose_thread = Thread(
        target=process_videos_with_error_handling,
        args=(return_dict, "pose", sign_ids, uniq_key, pre_sign)
    )
    threads.append(pose_thread)
    pose_thread.start()
    
    # Create sign and avatar videos if not pose_only
    if not pose_only:
        sign_thread = Thread(
            target=process_videos_with_error_handling,
            args=(return_dict, "sign", sign_ids, uniq_key, pre_sign)
        )
        avatar_thread = Thread(
            target=process_videos_with_error_handling,
            args=(return_dict, "avatar", sign_ids, uniq_key, pre_sign)
        )
        threads.extend([sign_thread, avatar_thread])
        sign_thread.start()
        avatar_thread.start()
    
    # Wait for all threads to complete with timeout
    timeout = 300  # 5 minutes
    start_time = time.time()
    
    for thread in threads:
        remaining_time = timeout - (time.time() - start_time)
        if remaining_time <= 0:
            raise RuntimeError("Video processing timeout exceeded")
        thread.join(timeout=remaining_time)
        if thread.is_alive():
            raise RuntimeError(f"Video processing thread timed out")
    
    # Check for errors in thread results
    errors = [return_dict.get(f"{video_type}_error") for video_type in ["pose", "sign", "avatar"] 
             if return_dict.get(f"{video_type}_error")]
    
    if errors:
        error_msg = f"Video processing errors: {'; '.join(errors)}"
        logger.error(error_msg)
        raise RuntimeError(error_msg)
    
    # Build result dictionary
    result = {
        'PoseURL': return_dict.get("pose"),
        'Gloss': gloss_sentence,
        'Text': text
    }
    
    if not pose_only:
        result.update({
            'SignURL': return_dict.get("sign"),
            'AvatarURL': return_dict.get("avatar")
        })
    
    logger.info(f"Successfully generated videos for gloss: '{gloss_sentence}'")
    return result


@dynamodb_retry
def get_sign_ids_from_gloss(gloss_sentence: str) -> List[str]:
    """Extract sign IDs from gloss sentence using DynamoDB lookup with enhanced error handling"""
    sign_ids = []
    
    try:
        dynamodb = boto3.resource('dynamodb')
        table = dynamodb.Table(table_name)
    except Exception as e:
        raise RuntimeError(f"Failed to connect to DynamoDB table '{table_name}': {str(e)}")
    
    for gloss in gloss_sentence.split(" "):
        gloss = re.sub('[,!?.]', '', gloss.strip())
        if not gloss:
            continue
            
        try:
            sign_id = _query_single_gloss(table, gloss)
            if sign_id:
                sign_ids.append(sign_id)
        except Exception as e:
            logger.warning(f"Failed to process gloss '{gloss}': {str(e)}")
            continue  # Skip this gloss and continue with next
    
    return sign_ids


def _query_single_gloss(table, gloss: str) -> Optional[str]:
    """Query a single gloss from DynamoDB with fallback to finger spelling"""
    try:
        response = table.query(
            KeyConditionExpression=Key('Gloss').eq(gloss)
        )
        
        if response['Count'] > 0:
            return response['Items'][0]['SignID']
        
        # If no direct sign found, try finger spelling
        logger.info(f"No direct sign found for '{gloss}', attempting finger spelling...")
        finger_spell_ids = []
        
        for char in gloss:
            if char.isalpha():  # Only finger spell alphabetic characters
                char_response = table.query(
                    KeyConditionExpression=Key('Gloss').eq(char.upper())
                )
                if char_response['Count'] > 0:
                    finger_spell_ids.append(char_response['Items'][0]['SignID'])
        
        if finger_spell_ids:
            # Return the first character's sign ID for simplicity
            # In a more sophisticated implementation, we might return all IDs
            return finger_spell_ids[0]
        
        logger.warning(f"No sign or finger spelling found for '{gloss}'")
        return None
        
    except Exception as e:
        logger.error(f"Error querying gloss '{gloss}': {str(e)}")
        raise


def process_videos_with_error_handling(return_dict, video_type: str, sign_ids: List[str], 
                                     uniq_key: str, pre_sign: bool):
    """Wrapper for process_videos with error handling"""
    try:
        result = process_videos(return_dict, video_type, sign_ids, uniq_key, pre_sign)
        return result
    except Exception as e:
        error_msg = f"Error processing {video_type} video: {str(e)}"
        logger.error(error_msg)
        return_dict[f"{video_type}_error"] = error_msg


def process_videos(return_dict, video_type: str, sign_ids: List[str], uniq_key: str, pre_sign: bool):
    """Process videos with enhanced error handling and validation"""
    if not sign_ids:
        raise ValueError(f"No sign IDs provided for {video_type} video processing")
    
    try:
        result = _process_single_video_type(video_type, sign_ids, uniq_key, pre_sign)
        return_dict[video_type] = result
        return result
    except Exception as e:
        error_msg = f"Failed to process {video_type} video: {str(e)}"
        logger.error(error_msg)
        return_dict[f"{video_type}_error"] = error_msg
        raise


@s3_retry
def _process_single_video_type(video_type: str, sign_ids: List[str], uniq_key: str, pre_sign: bool) -> str:
    """Process a single video type with S3 operations wrapped in retry logic"""
    if PERFORMANCE_AVAILABLE:
        s3 = get_optimized_s3_client()
    else:
        s3 = boto3.client('s3')
    temp_folder = f"/tmp/{uniq_key}/"
    video_folder = f"{temp_folder}{video_type}/"
    
    # Create directories
    pathlib.Path(video_folder).mkdir(parents=True, exist_ok=True)
    
    # Download video files
    downloaded_files = _download_video_files(s3, video_type, sign_ids, video_folder, temp_folder)
    
    if not downloaded_files:
        raise RuntimeError(f"No video files were successfully downloaded for {video_type}")
    
    logger.info(f"Successfully downloaded {len(downloaded_files)} files for {video_type}")
    
    # Combine videos using FFmpeg
    output_file = _combine_videos_with_ffmpeg(video_type, temp_folder)
    
    # Upload to S3 or return local path
    if pre_sign:
        return _upload_and_generate_presigned_url(s3, output_file, video_type, uniq_key)
    else:
        return output_file


def _download_video_files(s3, video_type: str, sign_ids: List[str], video_folder: str, temp_folder: str) -> List[str]:
    """Download video files from S3 with error handling"""
    downloaded_files = []
    
    with open(f"{temp_folder}{video_type}.txt", 'w') as writer:
        for sign_id in sign_ids:
            # Determine S3 key based on video type
            if video_type == "sign":
                key = f"{key_prefix}sign/sign-{sign_id}.mp4"
            elif video_type == "pose":
                key = f"{key_prefix}pose2/pose-{sign_id}.mp4"
            else:  # avatar
                key = f"{key_prefix}avatar/avatar-{sign_id}.mp4"
            
            local_file_name = f"{video_folder}{video_type}-{sign_id}.mp4"
            
            try:
                logger.info(f"Downloading {key} to {local_file_name}")
                s3.download_file(pose_bucket, key, local_file_name)
                
                # Verify file was downloaded and has content
                if os.path.exists(local_file_name) and os.path.getsize(local_file_name) > 0:
                    writer.write(f"file '{local_file_name}'\n")
                    downloaded_files.append(local_file_name)
                else:
                    logger.warning(f"Downloaded file {local_file_name} is empty or doesn't exist")
                    
            except ClientError as e:
                error_code = e.response.get('Error', {}).get('Code', 'Unknown')
                logger.warning(f"Failed to download {key}: {error_code}")
                # Continue with other files instead of failing completely
                continue
            except Exception as e:
                logger.warning(f"Unexpected error downloading {key}: {str(e)}")
                continue
    
    return downloaded_files


def _combine_videos_with_ffmpeg(video_type: str, temp_folder: str) -> str:
    """Combine videos using FFmpeg with error handling"""
    output_file = f"{temp_folder}{video_type}.{output_ext}"
    ffmpeg_args = [
        "/opt/bin/ffmpeg",
        "-f", "concat",
        "-safe", "0",
        "-i", f"{temp_folder}{video_type}.txt",
        "-c:v", "libvpx-vp9",
        "-y",  # Overwrite output file
        output_file
    ]
    
    logger.info(f"Running FFmpeg command: {' '.join(ffmpeg_args)}")
    
    try:
        result = subprocess.run(
            ffmpeg_args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=False,
            check=True,
            timeout=300  # 5 minute timeout
        )
        logger.info(f"FFmpeg completed successfully for {video_type}")
        
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"FFmpeg timeout for {video_type} video processing")
    except subprocess.CalledProcessError as e:
        error_msg = e.stderr.decode() if e.stderr else "Unknown FFmpeg error"
        raise RuntimeError(f"FFmpeg failed for {video_type}: {error_msg}")
    
    # Verify output file was created
    if not os.path.exists(output_file) or os.path.getsize(output_file) == 0:
        raise RuntimeError(f"FFmpeg did not produce valid output file for {video_type}")
    
    return output_file


def _upload_and_generate_presigned_url(s3, output_file: str, video_type: str, uniq_key: str) -> str:
    """Upload file to S3 and generate presigned URL"""
    output_key = f"{uniq_key}/{video_type}.{output_ext}"
    
    try:
        logger.info(f"Uploading {output_file} to s3://{asl_data_bucket}/{output_key}")
        s3.upload_file(output_file, asl_data_bucket, output_key)
        
        # Generate presigned URL
        video_url = s3.generate_presigned_url(
            ClientMethod='get_object',
            Params={
                'Bucket': asl_data_bucket,
                'Key': output_key
            },
            ExpiresIn=604800  # 7 days
        )
        
        logger.info(f"Successfully uploaded and generated presigned URL for {video_type}")
        return video_url
        
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', 'Unknown')
        raise RuntimeError(f"Failed to upload {video_type} video to S3: {error_code}")


if __name__ == "__main__":
    # Test cases
    test_cases = [
        {"Gloss": "HELLO WORLD", "Text": "Hello world"},
        {"Gloss": "IX-1P LIKE MOVIE", "Text": "I like movies"},
        {"Gloss": "THANK-YOU", "Text": "Thank you"}
    ]
    
    for test_case in test_cases:
        try:
            result = lambda_handler(test_case, {})
            print(f"Input: {test_case}")
            print(f"Result: {result}")
            print("-" * 50)
        except Exception as e:
            print(f"Error testing {test_case}: {str(e)}")