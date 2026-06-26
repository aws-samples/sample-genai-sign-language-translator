'''WebSocket handler for GenASL with Strands agent integration'''
import json
import boto3
import sys
from libs import aws
from libs.helpers import safe_dumps
import subprocess
import os
import base64
from PIL import Image
import io
import time
from datetime import datetime
from botocore.exceptions import ClientError
from pathlib import Path

BUCKET_NAME = os.environ['INPUT_BUCKET']
ASL_TO_ENG_MODEL = os.environ['ASL_TO_ENG_MODEL']
ASL_TO_ENG_MODEL = "us.meta.llama3-2-11b-instruct-v1:0"

# AgentCore configuration
AGENTCORE_AGENT_ID = os.environ.get('AGENTCORE_AGENT_ID')
AGENTCORE_AGENT_ARN = os.environ.get('AGENTCORE_AGENT_ARN')
AGENTCORE_REGION = os.environ.get('AGENTCORE_REGION', 'us-west-2')

# Initialize Bedrock clients
bedrock_runtime = boto3.client('bedrock-runtime', region_name='us-east-1')
bedrock_agentcore = boto3.client('bedrock-agentcore-runtime', region_name=AGENTCORE_REGION)

AGENT_AVAILABLE = bool(AGENTCORE_AGENT_ID and AGENTCORE_AGENT_ARN)
if AGENT_AVAILABLE:
    print(f"AgentCore agent available: {AGENTCORE_AGENT_ID}")
else:
    print("AgentCore agent not configured")


def default(event, context):
    """Default handler for websocket messages with Strands agent integration"""
    print(event)
    message = event.get('body', '')
    print(BUCKET_NAME)
    
    if not message.strip():
        return {
            'statusCode': 200,
        }

    if message.startswith('/'):
        return _handle_slash(message, event)

    connection_id, request_time = _get_conn_id_and_time(event)

    user = aws.get_user(connection_id)
    channel_name = user.get('channel_name', 'general')
    username = user.get('username', 'anonymous')

    # Save the message to dynamodb
    aws.save_message(connection_id, request_time, message, channel_name)

    try:
        # Parse the message to determine processing type
        data = json.loads(message)
        response_message = process_websocket_message_with_agent(data, connection_id, event)
        
    except json.JSONDecodeError:
        # Handle plain text messages
        response_message = process_text_message_with_agent(message, connection_id, event)
    except Exception as e:
        print(f"Error processing WebSocket message: {e}")
        response_message = f"Error processing your request: {str(e)}"

    # broadcast the message to all connected users
    _broadcast(
        response_message,
        _get_endpoint(event),
        connection_id,
        channel_name,
        username,
    )

    return {
        'statusCode': 200,
        'body': safe_dumps(response_message),
    }

def process_websocket_message_with_agent(data, connection_id, event):
    """Process structured WebSocket message using AgentCore agent"""
    
    if not AGENT_AVAILABLE:
        # Fallback to legacy processing
        return process_legacy_websocket_message(data)
    
    try:
        print(f"=== WEBSOCKET MESSAGE RECEIVED ===")
        print(f"Raw data: {json.dumps(data, indent=2)}")
        print(f"Data keys: {list(data.keys())}")
        
        # Build agent input based on message content
        stream_name = data.get('StreamName', '')
        bucket_name = data.get('BucketName', '')
        key_name = data.get('KeyName', '')
        text_content = data.get('text', data.get('message', ''))
        
        print(f"Extracted text_content: '{text_content}'")
        
        # Construct the input message for the agent
        if stream_name:
            input_text = f"Analyze ASL video from Kinesis stream: {stream_name}"
            input_data = {"StreamName": stream_name, "type": "video"}
        elif bucket_name and key_name:
            if key_name.lower().endswith(('.mp4', '.webm', '.avi', '.mov')):
                input_text = f"Analyze ASL video from S3: {bucket_name}/{key_name}"
                input_data = {"BucketName": bucket_name, "KeyName": key_name, "type": "video"}
            else:
                input_text = f"Process audio file from S3: {bucket_name}/{key_name}"
                input_data = {"BucketName": bucket_name, "KeyName": key_name, "type": "audio"}
        elif text_content:
            input_text = text_content
            input_data = {"type": "text"}
        else:
            input_text = "Hello, how can I help you with ASL translation?"
            input_data = {"type": "text"}
        
        print(f"Invoking AgentCore agent {AGENTCORE_AGENT_ID} with input: {input_text}")
        print(f"Input data: {json.dumps(input_data)}")
        
        # Invoke the AgentCore agent via HTTP
        # AgentCore agents are invoked through their runtime endpoint
        payload = {
            "prompt": input_text,
            "message": input_text,
            **input_data
        }
        
        print(f"Agent payload: {json.dumps(payload)}")
        
        response = bedrock_agentcore.invoke_agent(
            agentId=AGENTCORE_AGENT_ID,
            sessionId=connection_id,
            inputText=json.dumps(payload)  # Send the full payload as JSON
        )
        
        # Process the streaming response
        agent_response = process_agentcore_response(response)
        
        # Format response for WebSocket
        return format_websocket_agent_response(agent_response, data)
        
    except Exception as e:
        print(f"Error invoking AgentCore agent for WebSocket: {e}")
        import traceback
        traceback.print_exc()
        return f"I encountered an error processing your request: {str(e)}"

def process_text_message_with_agent(message, connection_id, event):
    """Process plain text WebSocket message using AgentCore agent"""
    
    if not AGENT_AVAILABLE:
        return f"Echo: {message}"
    
    try:
        print(f"Processing text message with AgentCore agent: {message}")
        
        # Invoke the AgentCore agent
        response = bedrock_agentcore.invoke_agent(
            agentId=AGENTCORE_AGENT_ID,
            sessionId=connection_id,
            inputText=message
        )
        
        # Process the streaming response
        agent_response = process_agentcore_response(response)
        
        return agent_response
        
    except Exception as e:
        print(f"Error processing text message with AgentCore agent: {e}")
        import traceback
        traceback.print_exc()
        return f"I encountered an error: {str(e)}"

def process_agentcore_response(response):
    """Process AgentCore streaming response and extract the result"""
    try:
        # AgentCore returns a streaming response
        event_stream = response.get('completion', [])
        
        result_text = ""
        result_data = {}
        
        for event in event_stream:
            if 'chunk' in event:
                chunk = event['chunk']
                if 'bytes' in chunk:
                    # Decode the bytes to text
                    chunk_text = chunk['bytes'].decode('utf-8')
                    result_text += chunk_text
            elif 'trace' in event:
                # Handle trace events for debugging
                trace = event['trace']
                print(f"Agent trace: {trace}")
            elif 'returnControl' in event:
                # Handle return control events
                return_control = event['returnControl']
                print(f"Agent return control: {return_control}")
                result_data = return_control
        
        # Try to parse as JSON if possible
        try:
            parsed_result = json.loads(result_text)
            return parsed_result
        except json.JSONDecodeError:
            # Return as plain text if not JSON
            return result_text if result_text else result_data
            
    except Exception as e:
        print(f"Error processing AgentCore response: {e}")
        import traceback
        traceback.print_exc()
        return f"Error processing agent response: {str(e)}"

def format_websocket_agent_response(agent_response, original_data):
    """Format agent response for WebSocket broadcast using enhanced formatter"""
    try:
        # Try to use the enhanced response formatter
        try:
            from response_formatters import format_websocket_response
            
            connection_id = "websocket_connection"  # Default connection ID
            formatted_response = format_websocket_response(
                agent_response=agent_response,
                original_message=original_data,
                connection_id=connection_id,
                include_debug=os.environ.get('DEBUG_MODE', 'false').lower() == 'true'
            )
            
            # Return the formatted message for broadcasting
            return formatted_response.get('message', str(agent_response))
            
        except ImportError:
            print("Response formatter not available, using fallback formatting")
            return format_websocket_response_fallback(agent_response, original_data)
        
    except Exception as e:
        print(f"Error using enhanced formatter: {e}, falling back to basic formatting")
        return format_websocket_response_fallback(agent_response, original_data)

def format_websocket_response_fallback(agent_response, original_data):
    """Fallback WebSocket response formatting"""
    try:
        # For WebSocket, we want to return user-friendly messages
        if isinstance(agent_response, str):
            return agent_response
        
        # If it's structured data, format it nicely
        if isinstance(agent_response, dict):
            formatted_parts = []
            
            if 'message' in agent_response:
                formatted_parts.append(agent_response['message'])
            
            if 'Gloss' in agent_response:
                formatted_parts.append(f"ASL Gloss: {agent_response['Gloss']}")
            
            if any(key.endswith('URL') for key in agent_response.keys()):
                formatted_parts.append("Generated ASL videos:")
                for key, value in agent_response.items():
                    if key.endswith('URL') and value:
                        video_type = key.replace('URL', '').lower()
                        formatted_parts.append(f"• {video_type.title()}: {value}")
            
            return "\n".join(formatted_parts) if formatted_parts else str(agent_response)
        
        return str(agent_response)
        
    except Exception as e:
        print(f"Error formatting WebSocket agent response: {e}")
        return str(agent_response)

def process_legacy_websocket_message(data):
    """Legacy WebSocket message processing (fallback when agent is not available)"""
    stream_name = data.get('StreamName', '')
    
    if stream_name:
        try:
            output_path = '/tmp/'
            asl_input_file = process_kvs_to_webp(stream_name, output_path)
            print(asl_input_file)
            return analyze_asl_image(asl_input_file)
        except Exception as e:
            print(f"Error processing stream: {e}")
            return f"Error processing video stream: {str(e)}"
    else:
        bucket_name = data.get('BucketName', '')
        key_name = data.get('KeyName', '')
        
        if bucket_name and key_name:
            try:
                input_file = download_from_s3(bucket_name, key_name)
                file_name_without_ext, ext = os.path.splitext(os.path.basename(input_file))
                output_path = '/tmp/' + file_name_without_ext + '.webp'
                asl_input_file = convert_mp4_to_webp(input_file, output_path)
                return analyze_asl_image(asl_input_file)
            except Exception as e:
                print(f"Error processing S3 file: {e}")
                return f"Error processing file: {str(e)}"
        else:
            return "Please provide either StreamName or BucketName/KeyName for processing."


def handle_cmd(event, context):
    payload = json.loads(event['body'])
    command = payload['data']

    handlers = {
        'fetchChannels': fetch_channels,
    }

    handlers[command](event)

    return {
        'statusCode': 200,
    }


def fetch_channels(event):
    channels = aws.get_channels_list()
    _send_message_to_client(event, safe_dumps({'channelsList': sorted(channels)}))


def _broadcast(message, endpoint, sender, channel, username):
    client = boto3.client('apigatewaymanagementapi', endpoint_url=endpoint)

    # need to look up what channel the user is connected to
    for connection_id in aws.get_connected_connection_ids(channel):
        #if connection_id == sender:
        #    continue
        try:
            client.post_to_connection(
                ConnectionId=connection_id,
                Data='{}'.format(message),
            )
        except Exception as e:
            print(f"Error sending message to connection {connection_id}: {str(e)}")


def connect(event, context):
    connection_id = _get_connection_id(event)
    aws.set_connection_id(connection_id)

    return {
        'statusCode': 200,
        'body': 'Successfully connect',
    }


def disconnect(event, context):
    connection_id = _get_connection_id(event)

    user = aws.get_user(connection_id)
    channel_name = user.get('channel_name', 'general')
    aws.delete_connection_id(connection_id, channel_name)

    return {
        'statusCode': 200,
        'body': 'disconnect',
    }


def _handle_slash(message, event):
    if message.startswith('/name '):
        return _set_name(message, event)

    if message.startswith('/channel '):
        return _set_channel(message, event)

    return _help(event)


def _help(event):
    message = "Valid commands: /help, /name [NAME], /channel [CHAN_NAME]"
    _send_message_to_client(event, message)
    return {
        'statusCode': 200,
        'body': 'help',
    }


def _set_name(message, event):
    name = message.split('/name')[-1]
    connection_id = _get_connection_id(event)
    aws.save_username(connection_id, name.strip())

    _send_message_to_client(event, 'Set username to {}'.format(name.strip()))

    return {
        'statusCode': 200,
        'body': 'name',
    }


def _set_channel(message, event):
    channel_name = message.split('/channel')[-1]
    channel_name = channel_name.strip('# ')

    connection_id = _get_connection_id(event)

    aws.update_channel_name(connection_id, channel_name)
    aws.set_connection_id(connection_id, channel=channel_name)

    _send_message_to_client(event, 'Changed to #{}'.format(channel_name))

    return {
        'statusCode': 200,
        'body': 'name',
    }


def _send_message_to_client(event, message):
    client = boto3.client('apigatewaymanagementapi', endpoint_url=_get_endpoint(event))
    client.post_to_connection(
        ConnectionId=_get_connection_id(event),
        Data=message,
    )


def _get_connection_id(event):
    ctx = event['requestContext']
    return ctx['connectionId']


def _get_request_time(event):
    ctx = event['requestContext']
    return ctx['requestTimeEpoch']


def _get_conn_id_and_time(event):
    ctx = event['requestContext']
    return (ctx['connectionId'], ctx['requestTimeEpoch'])


def _get_endpoint(event):
    ctx = event['requestContext']
    domain = ctx['domainName']
    stage = ctx['stage']
    return 'https://{}/{}'.format(domain, stage)


# Websocket changes
def convert_mp4_to_webp(input_file, output_file, fps=15, quality=80):
    #if not os.path.exists(input_file):
    #raise FileNotFoundError(f"Input file not found: {input_file}")

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
        output_file
    ]

    try:
        res = subprocess.run(ffmpeg_cmd, check=True)
        print(f"Successfully converted {input_file} to {output_file}")
        print(res)
        return output_file
    except subprocess.CalledProcessError as e:
        print(f"Error during conversion: {e}")
        return e


def encode_image(image_path):
    with Image.open(image_path) as img:
        # Convert to RGB if the image is in RGBA mode
        if img.mode == 'RGBA':
            img = img.convert('RGB')

        buffered = io.BytesIO()
        img.save(buffered, format="JPEG")
        return base64.b64encode(buffered.getvalue()).decode('utf-8')


def analyze_asl_image(image_path):
    print("Analyzing ASL image...")
    with open(image_path, "rb") as file:
        file_content = file.read()

    # encoded_image = encode_image(image_path)

    system_prompt = f"""You are an American Sign Language interpreter. 
    Analyze the provided video and return the ASL sign shown in the video.Look at the hand and face. 
    Ignore the letters and numbers shown in the video. Those are not correct.
    Return only the ASL sign word and don't provide explanation. 
    """
    system = [
        {
            'text': system_prompt
        }]
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
    inferenceConfig = {"maxTokens": 3000, "temperature": 0.1, "topP": 0.5, }
    print(ASL_TO_ENG_MODEL)
    try:
        response = bedrock_runtime.converse(
            modelId=ASL_TO_ENG_MODEL,
            system=system,
            messages=conversation,
            inferenceConfig=inferenceConfig,
        )
        eng_text= response["output"]["message"]["content"][0]["text"]
        eng_text=eng_text.replace("The ASL sign shown in the video is","")
        return eng_text
    except Exception as e:
        print(f"An error occurred: {e}")
        return None


def get_kvs_endpoint(stream_name):
    # Create Kinesis Video client
    kvs_client = boto3.client('kinesisvideo')

    # Get data endpoint for the stream
    endpoint = kvs_client.get_data_endpoint(
        StreamName=stream_name,
        APIName='GET_MEDIA'
    )

    return endpoint['DataEndpoint']


def process_kvs_to_webp(stream_name, output_path):
    try:
        # Get the endpoint for the video stream
        endpoint = get_kvs_endpoint(stream_name)

        # Create Kinesis Video Media client using the endpoint
        kvs_media_client = boto3.client(
            'kinesis-video-media',
            endpoint_url=endpoint
        )

        # Get the media stream
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

        # Process the stream and save frames as WebP
        frame_count = 0
        buffer = io.BytesIO()

        while True:
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

                    frame_count += 1
                    print(f"Saved frame {frame_count} to {output_file}")

                    # Clear buffer for next frame
                    buffer = io.BytesIO()
                    return output_file

                except Exception as e:
                    # If we can't create an image, continue accumulating data
                    continue

            except Exception as e:
                print(f"Error processing stream: {str(e)}")
                break

    except Exception as e:
        print(f"Error: {str(e)}")
        raise


def download_from_s3(bucket_name, s3_key, local_path=None):
    """
    Download a file from S3 to Lambda's /tmp folder

    Args:
        bucket_name (str): S3 bucket name
        s3_key (str): S3 object key (path to file in S3)
        local_path (str): Optional local path in /tmp. If not provided,
                         will use the filename from s3_key

    Returns:
        str: Path to the downloaded file in /tmp
    """
    try:
        # Create S3 client
        s3_client = boto3.client('s3')

        # If local_path is not provided, extract filename from s3_key
        if local_path is None:
            filename = os.path.basename(s3_key)
            local_path = f"/tmp/{filename}"

        # Ensure the file path is within /tmp
        if not local_path.startswith('/tmp/'):
            local_path = f"/tmp/{os.path.basename(local_path)}"

        # Check available space in /tmp
        check_available_space(bucket_name, s3_key)

        print(f"Downloading s3://{bucket_name}/{s3_key} to {local_path}")

        # Download the file
        s3_client.download_file(bucket_name, s3_key, local_path)

        # Verify the download
        if not os.path.exists(local_path):
            raise FileNotFoundError(f"Failed to download file to {local_path}")

        file_size = os.path.getsize(local_path)
        print(f"Successfully downloaded file. Size: {file_size} bytes")

        return local_path

    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', 'Unknown')
        error_message = e.response.get('Error', {}).get('Message', 'Unknown')
        print(f"S3 Client Error: {error_code} - {error_message}")
        raise
    except Exception as e:
        print(f"Error downloading file: {str(e)}")
        raise


def check_available_space(bucket_name, s3_key):
    """
    Check if there's enough space in /tmp before downloading

    Args:
        bucket_name (str): S3 bucket name
        s3_key (str): S3 object key
    """
    try:
        s3_client = boto3.client('s3')

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

        print(f"Sufficient space available in /tmp: {free_space} bytes")

    except ClientError as e:
        print(f"Error checking S3 object: {str(e)}")
        raise
    except Exception as e:
        print(f"Error checking available space: {str(e)}")
        raise
