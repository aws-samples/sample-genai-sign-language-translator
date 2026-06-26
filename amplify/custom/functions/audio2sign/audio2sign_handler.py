import json
import os
import boto3
import time
import logging
import sys
from pathlib import Path

# Set up logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# AgentCore configuration
AGENTCORE_AGENT_ID = os.environ.get('AGENTCORE_AGENT_ID')
AGENTCORE_AGENT_ARN = os.environ.get('AGENTCORE_AGENT_ARN')
AGENTCORE_REGION = os.environ.get('AGENTCORE_REGION', 'us-west-2')

# Initialize Bedrock AgentCore client
# AgentCore uses a custom service endpoint
agent_core_client = boto3.client('bedrock-agentcore', region_name=AGENTCORE_REGION)

AGENT_AVAILABLE = bool(AGENTCORE_AGENT_ID and AGENTCORE_AGENT_ARN)
if AGENT_AVAILABLE:
    logger.info(f"AgentCore agent available: {AGENTCORE_AGENT_ID}")
    logger.info(f"AgentCore agent ARN: {AGENTCORE_AGENT_ARN}")
else:
    logger.warning("AgentCore agent not configured")

def lambda_handler(event, context):
    """
    REST API handler that routes requests to the AgentCore agent
    Maintains backward compatibility with existing API response format
    """
    print('received event:')
    print(event)
    
    try:
        # Handle CORS preflight requests
        if event.get('httpMethod') == 'OPTIONS':
            return {
                'statusCode': 200,
                'headers': {
                    'Access-Control-Allow-Headers': '*',
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Methods': 'OPTIONS,POST,GET'
                }
            }
        
        # Check if agent is available
        if not AGENT_AVAILABLE:
            return format_error_response("AgentCore agent is not available", 503)
        
        # Extract query parameters
        query_params = event.get("queryStringParameters") or {}
        
        # Build input text for the agent
        input_text, metadata = build_agent_input(query_params, event)
        
        # Generate session ID
        session_id = event.get("requestContext", {}).get("requestId", str(int(time.time())))
        
        logger.info(f"=== REQUEST DETAILS ===")
        logger.info(f"Query Parameters: {json.dumps(query_params)}")
        logger.info(f"Metadata: {json.dumps(metadata)}")
        logger.info(f"Input Text: {input_text}")
        logger.info(f"Session ID: {session_id}")
        logger.info(f"Agent ID: {AGENTCORE_AGENT_ID}")
        logger.info(f"======================")
        
        logger.info(f"Invoking AgentCore agent {AGENTCORE_AGENT_ID} with input: {input_text}")
        
        # Invoke the agent using bedrock-agent-runtime
        agent_response = invoke_agentcore_agent(AGENTCORE_AGENT_ID, input_text, session_id)
        
        # Format response to maintain API compatibility
        logger.info(f"=== RAW AGENT RESPONSE ===")
        logger.info(f"Type: {type(agent_response)}")
        logger.info(f"Response: {json.dumps(agent_response) if isinstance(agent_response, dict) else str(agent_response)[:500]}")
        logger.info(f"==========================")
        
        formatted_response = format_agent_response(agent_response, query_params)
        
        logger.info(f"=== FORMATTED RESPONSE ===")
        logger.info(f"Response: {json.dumps(formatted_response, indent=2)}")
        logger.info(f"==========================")
        
        logger.info("AgentCore agent invocation completed successfully")
        
        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Headers': '*',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'OPTIONS,POST,GET'
            },
            'body': json.dumps(formatted_response)
        }
        
    except Exception as e:
        error_msg = f"Error processing request: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return format_error_response(error_msg, 500)

def invoke_agentcore_agent(agent_id, input_text, session_id):
    """
    Invoke AgentCore agent using bedrock-agentcore client
    """
    try:
        # Prepare the payload as shown in the sample
        payload_dict = {"prompt": input_text}
        payload = json.dumps(payload_dict).encode()
        
        logger.info(f"=== AGENT INVOCATION ===")
        logger.info(f"Agent ARN: {AGENTCORE_AGENT_ARN}")
        logger.info(f"Session ID: {session_id}")
        logger.info(f"Payload: {json.dumps(payload_dict)}")
        logger.info(f"========================")
        
        # Invoke the agent using bedrock-agentcore
        response = agent_core_client.invoke_agent_runtime(
            agentRuntimeArn=AGENTCORE_AGENT_ARN,
            runtimeSessionId=session_id,
            payload=payload
        )
        
        # Process the response based on content type
        content_type = response.get("contentType", "")
        logger.info(f"=== AGENT RESPONSE ===")
        logger.info(f"Content Type: {content_type}")
        logger.info(f"Response Keys: {list(response.keys())}")
        logger.info(f"======================")
        
        if "text/event-stream" in content_type:
            # Handle streaming response
            content = []
            for line in response["response"].iter_lines(chunk_size=10):
                if line:
                    line = line.decode("utf-8")
                    if line.startswith("data: "):
                        line = line[6:]
                    logger.info(f"Stream line: {line}")
                    content.append(line)
            
            result = "\n".join(content)
            logger.info(f"Complete streaming response: {result[:200]}...")
            
            # Try to parse as JSON
            try:
                return json.loads(result)
            except json.JSONDecodeError:
                return {"message": result, "raw_response": result}
                
        elif content_type == "application/json":
            # Handle standard JSON response
            content = []
            for chunk in response.get("response", []):
                content.append(chunk.decode('utf-8'))
            
            result = json.loads(''.join(content))
            logger.info(f"=== PARSED JSON RESPONSE ===")
            logger.info(f"Response: {json.dumps(result, indent=2)}")
            logger.info(f"============================")
            return result
            
        else:
            # Handle other content types
            logger.warning(f"Unexpected content type: {content_type}")
            raw_response = response.get("response", "")
            return {"message": "Response received", "contentType": content_type, "response": str(raw_response)}
            
    except Exception as e:
        logger.error(f"Error invoking AgentCore agent: {e}", exc_info=True)
        raise

def build_agent_input(query_params, event):
    """Build agent input text from API request parameters"""
    metadata = {}
    
    # Determine request type and build appropriate input
    if "Gloss" in query_params:
        # Direct gloss-to-video request
        input_text = f"Translate this ASL gloss to sign language video: {query_params['Gloss']}"
        metadata["gloss"] = query_params["Gloss"]
        metadata["type"] = "gloss"
        
    elif "Text" in query_params:
        # Text-to-ASL translation request
        input_text = f"Translate this English text to American Sign Language: {query_params['Text']}"
        metadata["text"] = query_params["Text"]
        metadata["type"] = "text"
        
    elif "BucketName" in query_params and "KeyName" in query_params:
        # Audio-to-ASL translation request
        input_text = f"Translate the audio file from S3 bucket {query_params['BucketName']} with key {query_params['KeyName']} to American Sign Language"
        metadata["bucket_name"] = query_params["BucketName"]
        metadata["key_name"] = query_params["KeyName"]
        metadata["type"] = "audio"
        
    else:
        # Default to text processing if no specific parameters
        input_text = f"Translate this English text to American Sign Language: {query_params.get('message', 'Hello')}"
        metadata["type"] = "text"
    
    return input_text, metadata

def format_agent_response(agent_response, query_params):
    """Format agent response using the enhanced response formatter"""
    try:
        # Import the response formatter
        from response_formatters import format_rest_api_response
        
        # Use the enhanced formatter for better compatibility and debugging
        formatted_response = format_rest_api_response(
            agent_response=agent_response,
            request_params=query_params,
            include_debug=os.environ.get('DEBUG_MODE', 'false').lower() == 'true'
        )
        
        return formatted_response
        
    except ImportError:
        logger.warning("Response formatter not available, using fallback formatting")
        return format_agent_response_fallback(agent_response, query_params)
    except Exception as e:
        logger.warning(f"Error using enhanced formatter: {e}, falling back to basic formatting")
        return format_agent_response_fallback(agent_response, query_params)

def format_agent_response_fallback(agent_response, query_params):
    """Fallback formatting method for backward compatibility"""
    try:
        # Try to parse agent response as JSON if it contains structured data
        if isinstance(agent_response, str):
            # Look for JSON-like content in the response
            import re
            json_match = re.search(r'\{[^{}]*"[^"]*URL"[^{}]*\}', agent_response)
            if json_match:
                try:
                    structured_data = json.loads(json_match.group())
                    return structured_data
                except json.JSONDecodeError:
                    pass
        
        # For backward compatibility, try to extract key information
        response_data = {}
        
        # If response is already a dict, use it
        if isinstance(agent_response, dict):
            return agent_response
        
        # Extract URLs from response text
        import re
        url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
        urls = re.findall(url_pattern, str(agent_response))
        
        # Map URLs to expected format
        if urls:
            for i, url in enumerate(urls):
                if 'pose' in url.lower():
                    response_data['PoseURL'] = url
                elif 'sign' in url.lower():
                    response_data['SignURL'] = url
                elif 'avatar' in url.lower():
                    response_data['AvatarURL'] = url
                elif i == 0 and 'PoseURL' not in response_data:
                    response_data['PoseURL'] = url
                elif i == 1 and 'SignURL' not in response_data:
                    response_data['SignURL'] = url
                elif i == 2 and 'AvatarURL' not in response_data:
                    response_data['AvatarURL'] = url
        
        # Extract gloss information
        gloss_match = re.search(r'(?:ASL Gloss|Gloss):\s*([^\n]+)', str(agent_response), re.IGNORECASE)
        if gloss_match:
            response_data['Gloss'] = gloss_match.group(1).strip()
        elif "Gloss" in query_params:
            response_data['Gloss'] = query_params["Gloss"]
        
        # Extract text information
        text_match = re.search(r'(?:Original text|Text):\s*"([^"]+)"', str(agent_response), re.IGNORECASE)
        if text_match:
            response_data['Text'] = text_match.group(1).strip()
        elif "Text" in query_params:
            response_data['Text'] = query_params["Text"]
        
        # If no structured data found, return the response as-is with metadata
        if not response_data:
            response_data = {
                "message": str(agent_response),
                "status": "completed",
                "timestamp": int(time.time())
            }
        
        return response_data
        
    except Exception as e:
        logger.warning(f"Error formatting agent response: {e}")
        return {
            "message": str(agent_response),
            "status": "completed",
            "timestamp": int(time.time())
        }

def format_error_response(error_message, status_code=500):
    """Format error response with proper CORS headers"""
    return {
        'statusCode': status_code,
        'headers': {
            'Access-Control-Allow-Headers': '*',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'OPTIONS,POST,GET'
        },
        'body': json.dumps({
            "error": error_message,
            "status": "failed",
            "timestamp": int(time.time())
        })
    }
