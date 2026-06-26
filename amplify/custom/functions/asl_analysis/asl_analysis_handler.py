import json
import os
import time
import logging
import subprocess
import base64
import io
from typing import Optional, Dict, Any, Union
from datetime import datetime

import boto3
from botocore.exceptions import ClientError, BotoCoreError
from PIL import Image
from strands import tool

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Environment variables
asl_to_eng_model = os.environ.get('ASL_TO_ENG_MODEL', 'us.meta.llama3-2-11b-instruct-v1:0')
input_bucket = os.environ.get('INPUT_BUCKET', '')
aws_region = os.environ.get('AWS_REGION', 'us-east-1')

# Initialize Bedrock client
bedrock_runtime = boto3.client('bedrock-runtime', region_name=aws_region)


def lambda_handler(event, context):
    """Lambda handler for ASL analysis
    
    Parameters
    ----------
    event: dict, required
        Input event containing stream name or S3 location
    context: object, required
        Lambda Context runtime methods and attributes
    Returns
    ------
        dict: Object containing analyzed ASL text
    """
    try:
        # Handle different input types
        stream_name = event.get('StreamName')
        bucket_name = event.get('BucketName')
        key_name = event.get('KeyName')
        
        if stream_name:
            text = analyze_asl_video_stream(stream_name)
            return {'Text': text, 'StreamName': stream_name}
        elif bucket_name and key_name:
            text = analyze_asl_from_s3(bucket_name, key_name)
            return {'Text': text, 'BucketName': bucket_name, 'KeyName': key_name}
        else:
            return {'Error': 'Either StreamName or BucketName/KeyName must be provided'}
            
    except Exception as e:
        logger.error(f"Error in lambda_handler: {str(e)}")
        return {'Error': f'ASL analysis failed: {str(e)}'}


@tool
def analyze_asl_video_stream(stream_name: str) -> str:
    """Analyze ASL video from Kinesis Video Stream and return interpreted text
    
    Args:
        stream_name: Name of the Kinesis Video Stream
        
    Returns:
        str: Interpreted ASL text
        
    Raises:
        ValueError: If stream_name is empty
        RuntimeError: If analysis fails
    """
    if not stream_name or not stream_name.strip():
        raise ValueError("Stream name cannot be empty")
    
    stream_name = stream_name.strip()
    
    logger.info(f"Starting ASL analysis for video stream: {stream_name}")
    
    try:
        # Process KVS stream to extract frame
        output_path = '/tmp/'
        frame_file = process_kvs_to_webp(stream_name, output_path)
        
        if not frame_file or not os.path.exists(frame_file):
            raise RuntimeError("Failed to extract frame from video stream")
        
        # Analyze the extracted frame
        interpreted_text = analyze_asl_image(frame_file)
        
        # Clean up temporary file
        try:
            os.remove(frame_file)
        except Exception as e:
            logger.warning(f"Failed to clean up temporary file {frame_file}: {str(e)}")
        
        logger.info(f"Successfully analyzed ASL stream: '{interpreted_text}'")
        return interpreted_text
        
    except Exception as e:
        logger.error(f"Error analyzing ASL video stream: {str(e)}")
        raise RuntimeError(f"ASL video stream analysis failed: {str(e)}")


@tool
def analyze_asl_from_s3(bucket_name: str, key_name: str) -> str:
    """Analyze ASL video/image from S3 and return interpreted text
    
    Args:
        bucket_name: S3 bucket containing the media file
        key_name: S3 key (path) to the media file
        
    Returns:
        str: Interpreted ASL text
        
    Raises:
        ValueError: If bucket_name or key_name is empty
        RuntimeError: If analysis fails
    """
    if not bucket_name or not bucket_name.strip():
        raise ValueError("Bucket name cannot be empty")
    
    if not key_name or not key_name.strip():
        raise ValueError("Key name cannot be empty")
    
    bucket_name = bucket_name.strip()
    key_name = key_name.strip()
    
    logger.info(f"Starting ASL analysis for s3://{bucket_name}/{key_name}")
    
    try:
        # Download file from S3
        local_file = download_from_s3(bucket_name, key_name)
        
        # Convert to WebP if it's a video file
        file_extension = key_name.lower().split('.')[-1]
        if file_extension in ['mp4', 'avi', 'mov', 'webm']:
            # Convert video to WebP
            file_name_without_ext = os.path.splitext(os.path.basename(local_file))[0]
            webp_file = f'/tmp/{file_name_without_ext}.webp'
            webp_file = convert_mp4_to_webp(local_file, webp_file)
        else:
            # Assume it's already an image
            webp_file = local_file
        
        # Analyze the image/frame
        interpreted_text = analyze_asl_image(webp_file)
        
        # Clean up temporary files
        for temp_file in [local_file, webp_file]:
            try:
                if temp_file and os.path.exists(temp_file):
                    os.remove(temp_file)
            except Exception as e:
                logger.warning(f"Failed to clean up temporary file {temp_file}: {str(e)}")
        
        logger.info(f"Successfully analyzed ASL from S3: '{interpreted_text}'")
        return interpreted_text
        
    except Exception as e:
        logger.error(f"Error analyzing ASL from S3: {str(e)}")
        raise RuntimeError(f"ASL S3 analysis failed: {str(e)}")


def analyze_asl_image(image_path: str) -> str:
    """Analyze ASL image using Bedrock and return interpreted text with error handling"""
    if not image_path or not os.path.exists(image_path):
        raise ValueError(f"Invalid image path: {image_path}")
    
    max_retries = 3
    base_delay = 1.0
    
    logger.info(f"Analyzing ASL image: {image_path}")
    
    for attempt in range(max_retries):
        try:
            with open(image_path, "rb") as file:
                file_content = file.read()
            
            if not file_content:
                raise ValueError("Image file is empty")
            
            system_prompt = """You are an American Sign Language interpreter. 
            Analyze the provided video and return the ASL sign shown in the video. Look at the hand and face. 
            Ignore the letters and numbers shown in the video. Those are not correct.
            Return only the ASL sign word and don't provide explanation."""
            
            system = [{'text': system_prompt}]
            
            conversation = [
                {
                    "role": "user",
                    "content": [{"image": {
                        "format": "webp",
                        "source": {
                            "bytes": file_content,
                        }
                    }}],
                }
            ]
            
            inference_config = {
                "maxTokens": 3000, 
                "temperature": 0.1, 
                "topP": 0.5
            }
            
            logger.info(f"Attempting ASL analysis with Bedrock (attempt {attempt + 1}/{max_retries})")
            
            response = bedrock_runtime.converse(
                modelId=asl_to_eng_model,
                system=system,
                messages=conversation,
                inferenceConfig=inference_config,
            )
            
            eng_text = response["output"]["message"]["content"][0]["text"]
            
            # Clean up the response
            eng_text = eng_text.replace("The ASL sign shown in the video is", "").strip()
            
            if not eng_text:
                raise RuntimeError("Empty response from Bedrock model")
            
            logger.info(f"Successfully analyzed ASL image: '{eng_text}'")
            return eng_text
            
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            error_message = e.response.get('Error', {}).get('Message', 'Unknown')
            
            logger.warning(f"Bedrock ClientError on attempt {attempt + 1}: {error_code} - {error_message}")
            
            # Don't retry on certain error types
            if error_code in ['ValidationException', 'AccessDeniedException']:
                raise RuntimeError(f"Non-retryable error: {error_code} - {error_message}")
            
            if attempt == max_retries - 1:
                raise RuntimeError(f"ASL analysis failed after {max_retries} attempts: {error_message}")
                
        except BotoCoreError as e:
            logger.warning(f"BotoCoreError on attempt {attempt + 1}: {str(e)}")
            if attempt == max_retries - 1:
                raise RuntimeError(f"ASL analysis failed after {max_retries} attempts: {str(e)}")
                
        except Exception as e:
            logger.error(f"Unexpected error on attempt {attempt + 1}: {str(e)}")
            if attempt == max_retries - 1:
                raise RuntimeError(f"ASL analysis failed after {max_retries} attempts: {str(e)}")
        
        # Exponential backoff with jitter
        if attempt < max_retries - 1:
            delay = base_delay * (2 ** attempt) + (time.time() % 1)
            logger.info(f"Retrying in {delay:.2f} seconds...")
            time.sleep(delay)


def process_kvs_to_webp(stream_name: str, output_path: str) -> str:
    """Process Kinesis Video Stream to extract a frame as WebP with error handling"""
    try:
        # Get the endpoint for the video stream
        endpoint = get_kvs_endpoint(stream_name)
        
        # Create Kinesis Video Media client using the endpoint
        kvs_media_client = boto3.client(
            'kinesis-video-media',
            endpoint_url=endpoint,
            region_name=aws_region
        )
        
        # Get the media stream
        logger.info(f"Getting media stream for: {stream_name}")
        media_data = kvs_media_client.get_media(
            StreamName=stream_name,
            StartSelector={
                'StartSelectorType': 'NOW'
            }
        )
        
        # Read the media stream and process frames
        stream = media_data['Payload']
        
        # Create output directory if it doesn't exist
        os.makedirs(output_path, exist_ok=True)
        
        # Process the stream and save frame as WebP
        buffer = io.BytesIO()
        max_attempts = 10
        attempt = 0
        
        while attempt < max_attempts:
            try:
                # Read chunks of data from the stream
                chunk = stream.read(1024 * 1024)  # Read 1MB at a time
                if not chunk:
                    break
                
                buffer.write(chunk)
                
                # Try to create an image from the buffer
                try:
                    buffer.seek(0)
                    image = Image.open(buffer)
                    
                    # Generate output filename with timestamp
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
                    output_file = os.path.join(
                        output_path,
                        f'frame_{timestamp}.webp'
                    )
                    
                    # Convert and save as WebP
                    image.save(
                        output_file,
                        'WEBP',
                        quality=80,
                        method=6
                    )
                    
                    logger.info(f"Successfully extracted frame to {output_file}")
                    return output_file
                    
                except Exception:
                    # If we can't create an image, continue accumulating data
                    attempt += 1
                    continue
                    
            except Exception as e:
                logger.warning(f"Error processing stream chunk: {str(e)}")
                attempt += 1
                continue
        
        raise RuntimeError(f"Failed to extract valid frame from stream after {max_attempts} attempts")
        
    except Exception as e:
        logger.error(f"Error processing KVS stream: {str(e)}")
        raise RuntimeError(f"KVS processing failed: {str(e)}")


def get_kvs_endpoint(stream_name: str) -> str:
    """Get Kinesis Video Stream endpoint with error handling"""
    try:
        kvs_client = boto3.client('kinesisvideo', region_name=aws_region)
        
        logger.info(f"Getting KVS endpoint for stream: {stream_name}")
        
        endpoint_response = kvs_client.get_data_endpoint(
            StreamName=stream_name,
            APIName='GET_MEDIA'
        )
        
        endpoint = endpoint_response['DataEndpoint']
        logger.info(f"Got KVS endpoint: {endpoint}")
        return endpoint
        
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', 'Unknown')
        error_message = e.response.get('Error', {}).get('Message', 'Unknown')
        raise RuntimeError(f"Failed to get KVS endpoint: {error_code} - {error_message}")
    except Exception as e:
        raise RuntimeError(f"Error getting KVS endpoint: {str(e)}")


def convert_mp4_to_webp(input_file: str, output_file: str, fps: int = 15, quality: int = 80) -> str:
    """Convert MP4 video to WebP with error handling"""
    if not os.path.exists(input_file):
        raise FileNotFoundError(f"Input file not found: {input_file}")
    
    ffmpeg_cmd = [
        "/opt/bin/ffmpeg",
        "-i", input_file,
        "-vf", f"fps={fps},scale=320:-1:flags=lanczos",
        "-vcodec", "libwebp",
        "-lossless", "0",
        "-compression_level", "6",
        "-q:v", str(quality),
        "-loop", "0",
        "-preset", "picture",
        "-an",
        "-vsync", "0",
        "-y",  # Overwrite output file
        output_file
    ]
    
    try:
        logger.info(f"Converting {input_file} to WebP: {output_file}")
        
        result = subprocess.run(
            ffmpeg_cmd, 
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=120  # 2 minute timeout
        )
        
        if not os.path.exists(output_file) or os.path.getsize(output_file) == 0:
            raise RuntimeError("FFmpeg did not produce valid output file")
        
        logger.info(f"Successfully converted to WebP: {output_file}")
        return output_file
        
    except subprocess.TimeoutExpired:
        raise RuntimeError("FFmpeg conversion timeout")
    except subprocess.CalledProcessError as e:
        error_msg = e.stderr.decode() if e.stderr else "Unknown FFmpeg error"
        raise RuntimeError(f"FFmpeg conversion failed: {error_msg}")
    except Exception as e:
        raise RuntimeError(f"Video conversion failed: {str(e)}")


def download_from_s3(bucket_name: str, s3_key: str, local_path: Optional[str] = None) -> str:
    """Download a file from S3 to Lambda's /tmp folder with error handling"""
    try:
        s3_client = boto3.client('s3', region_name=aws_region)
        
        # If local_path is not provided, extract filename from s3_key
        if local_path is None:
            filename = os.path.basename(s3_key)
            local_path = f"/tmp/{filename}"
        
        # Ensure the file path is within /tmp
        if not local_path.startswith('/tmp/'):
            local_path = f"/tmp/{os.path.basename(local_path)}"
        
        # Check available space and object size
        check_available_space(bucket_name, s3_key)
        
        logger.info(f"Downloading s3://{bucket_name}/{s3_key} to {local_path}")
        
        # Download the file
        s3_client.download_file(bucket_name, s3_key, local_path)
        
        # Verify the download
        if not os.path.exists(local_path):
            raise FileNotFoundError(f"Failed to download file to {local_path}")
        
        file_size = os.path.getsize(local_path)
        logger.info(f"Successfully downloaded file. Size: {file_size} bytes")
        
        return local_path
        
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', 'Unknown')
        error_message = e.response.get('Error', {}).get('Message', 'Unknown')
        raise RuntimeError(f"S3 download failed: {error_code} - {error_message}")
    except Exception as e:
        raise RuntimeError(f"Error downloading file: {str(e)}")


def check_available_space(bucket_name: str, s3_key: str):
    """Check if there's enough space in /tmp before downloading"""
    try:
        s3_client = boto3.client('s3', region_name=aws_region)
        
        # Get S3 object size
        response = s3_client.head_object(Bucket=bucket_name, Key=s3_key)
        file_size = response['ContentLength']
        
        # Check available space in /tmp
        stat = os.statvfs('/tmp')
        free_space = stat.f_frsize * stat.f_bavail
        
        # Ensure we have at least twice the required space
        required_space = file_size * 2
        
        if free_space < required_space:
            raise RuntimeError(
                f"Insufficient space in /tmp. Need {required_space} bytes, "
                f"but only {free_space} bytes available"
            )
        
        logger.info(f"Sufficient space available in /tmp: {free_space} bytes")
        
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', 'Unknown')
        raise RuntimeError(f"Error checking S3 object: {error_code}")
    except Exception as e:
        raise RuntimeError(f"Error checking available space: {str(e)}")


if __name__ == "__main__":
    # Test cases
    test_cases = [
        {"StreamName": "test-stream"},
        {"BucketName": "test-bucket", "KeyName": "test-video.mp4"}
    ]
    
    for test_case in test_cases:
        try:
            result = lambda_handler(test_case, {})
            print(f"Input: {test_case}")
            print(f"Result: {result}")
            print("-" * 50)
        except Exception as e:
            print(f"Error testing {test_case}: {str(e)}")