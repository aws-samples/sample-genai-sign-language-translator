"""
GenASL Sign Language Agent - Strands-based agent for ASL translation
This module implements the main agent entry point and configuration for the
GenASL system using AWS Bedrock AgentCore and Strands framework.
"""

import json
import os
import sys
import time
from typing import Dict, Any, Optional, Tuple, Union
from pathlib import Path
from datetime import datetime

# Import utility functions
from .utils import setup_logging, retry_with_backoff, validate_payload, extract_response_content
from .config import config
from .conversation import conversation_manager, RequestType, ConversationState
from .workflows import workflow_orchestrator, WorkflowStatus
from .agent_error_recovery import agent_error_recovery, ErrorRecoveryContext
from .error_handling import ErrorClassifier
from .monitoring import monitoring_manager

# Configure logging
logger = setup_logging(config.agent.log_level)

# Import the AgentCore SDK
from bedrock_agentcore.runtime import BedrockAgentCoreApp
from strands import Agent
from strands.models import BedrockModel



# Set up module paths for tool imports
def setup_module_paths():
    """Set up Python paths to import tools from sibling directories"""
    current_dir = Path(__file__).parent
    functions_dir = current_dir.parent
    
    # List of tool directories to add to path
    tool_dirs = ['text2gloss', 'gloss2pose', 'audio_processing', 'asl_analysis', 'audio2sign']
    
    for tool_dir in tool_dirs:
        tool_path = functions_dir / tool_dir
        if tool_path.exists():
            sys.path.insert(0, str(tool_path))
            logger.info(f"Added {tool_dir} path: {tool_path}")
        else:
            logger.warning(f"Tool directory not found: {tool_path}")

# Set up paths and import tools
setup_module_paths()

# Import all available tools
available_tools = []

try:
    from text2gloss_handler import text_to_asl_gloss
    available_tools.append(text_to_asl_gloss)
    logger.info("Successfully imported text_to_asl_gloss tool")
except ImportError as e:
    logger.error(f"Failed to import text2gloss tool: {e}")

try:
    from gloss2pose_handler import gloss_to_video
    available_tools.append(gloss_to_video)
    logger.info("Successfully imported gloss_to_video tool")
except ImportError as e:
    logger.error(f"Failed to import gloss2pose tool: {e}")

try:
    from audio_processing_handler import process_audio_input, get_transcription_result
    available_tools.extend([process_audio_input, get_transcription_result])
    logger.info("Successfully imported audio processing tools")
except ImportError as e:
    logger.error(f"Failed to import audio processing tools: {e}")

try:
    from asl_analysis_handler import analyze_asl_video_stream, analyze_asl_from_s3
    available_tools.extend([analyze_asl_video_stream, analyze_asl_from_s3])
    logger.info("Successfully imported ASL analysis tools")
except ImportError as e:
    logger.error(f"Failed to import ASL analysis tools: {e}")

# Define placeholder tools if imports failed
if not available_tools:
    logger.warning("No tools imported successfully, creating placeholder tools")
    from strands import tool
    
    @tool
    def text_to_asl_gloss(text: str) -> str:
        """Placeholder text to ASL gloss conversion tool"""
        logger.warning("Using placeholder text_to_asl_gloss tool")
        return f"PLACEHOLDER_GLOSS_FOR_{text.upper().replace(' ', '_')}"
    
    @tool
    def gloss_to_video(gloss_sentence: str, text: str = None, pose_only: bool = False, pre_sign: bool = True) -> dict:
        """Placeholder gloss to video conversion tool"""
        logger.warning("Using placeholder gloss_to_video tool")
        return {
            'PoseURL': 'https://placeholder-pose-url.com',
            'SignURL': 'https://placeholder-sign-url.com',
            'AvatarURL': 'https://placeholder-avatar-url.com',
            'Gloss': gloss_sentence,
            'Text': text
        }
    
    @tool
    def process_audio_input(bucket_name: str, key_name: str) -> str:
        """Placeholder audio processing tool"""
        logger.warning("Using placeholder process_audio_input tool")
        return f"PLACEHOLDER_TRANSCRIPTION_FOR_{bucket_name}_{key_name}"
    
    @tool
    def analyze_asl_video_stream(stream_name: str) -> str:
        """Placeholder ASL video analysis tool"""
        logger.warning("Using placeholder analyze_asl_video_stream tool")
        return f"PLACEHOLDER_ASL_ANALYSIS_FOR_{stream_name}"
    
    available_tools = [text_to_asl_gloss, gloss_to_video, process_audio_input, analyze_asl_video_stream]

# Comprehensive system prompt for the agent
SYSTEM_PROMPT = """You are GenASL, an AI-powered American Sign Language (ASL) translation agent. You are a helpful, knowledgeable, and patient assistant specializing in ASL translation services.

## Your Core Capabilities:

### 1. Text-to-ASL Translation
- Convert English text to ASL gloss notation using the text_to_asl_gloss tool
- Generate ASL videos (pose, sign, and avatar) from gloss using the gloss_to_video tool
- Handle various text inputs from simple phrases to complex sentences

### 2. Audio-to-ASL Translation
- Process audio files from S3 using the process_audio_input tool
- Transcribe audio to text, then convert to ASL
- Handle various audio formats (mp3, wav, mp4, etc.)
- Monitor transcription job status and provide updates

### 3. ASL-to-Text Analysis (Reverse Translation)
- Analyze ASL videos from Kinesis Video Streams using analyze_asl_video_stream
- Analyze ASL videos/images from S3 using analyze_asl_from_s3
- Interpret ASL signs and convert them back to English text

### 4. Conversational Interaction
- Understand natural language requests for translation services
- Provide clear status updates during processing
- Explain results and offer additional help
- Handle multiple requests in context

## Request Routing Logic:

### Text Input Requests:
- Identify when user provides text for ASL translation
- Use text_to_asl_gloss followed by gloss_to_video
- Provide both gloss notation and video URLs

### Audio Input Requests:
- Identify when user mentions audio files, S3 locations, or transcription
- Use process_audio_input for transcription
- Follow up with text-to-ASL translation workflow
- Handle transcription job monitoring

### Video Analysis Requests:
- Identify when user wants to analyze ASL videos or streams
- Use analyze_asl_video_stream for Kinesis streams
- Use analyze_asl_from_s3 for S3-stored videos/images
- Provide interpreted text results

### Status and Help Requests:
- Provide information about capabilities and available services
- Explain how to use different features
- Offer guidance on input formats and requirements

## Interaction Guidelines:

1. **Be Conversational**: Respond naturally and maintain context across multiple exchanges
2. **Provide Status Updates**: Keep users informed during processing, especially for longer operations
3. **Handle Errors Gracefully**: Explain errors in user-friendly terms and suggest solutions
4. **Be Specific**: When providing results, clearly explain what was translated and how
5. **Offer Additional Help**: Suggest related services or next steps when appropriate
6. **Maintain Context**: Remember previous requests and build upon them when relevant

## Response Format:

- Start with a brief acknowledgment of the request
- Provide status updates during tool execution
- Present results clearly with explanations
- Offer additional assistance or related services
- Use friendly, professional language throughout

## Error Handling:

- If a tool fails, explain what went wrong in simple terms
- Suggest alternative approaches when possible
- Provide guidance on correct input formats
- Offer to retry or try different methods

Remember: You are here to make ASL translation accessible and easy for everyone. Be patient, helpful, and thorough in your assistance."""

# Create the AgentCore app
app = BedrockAgentCoreApp()

# Initialize the Bedrock model with configuration
bedrock_model = BedrockModel(
    model_id=config.model.eng_to_asl_model,
    max_tokens=config.model.max_tokens,
    temperature=config.model.temperature,
    region_name=config.aws.region
)

# Initialize the Strands agent with all available tools
agent = Agent(
    model=bedrock_model,
    system_prompt=SYSTEM_PROMPT,
    tools=available_tools
)

logger.info(f"Agent initialized with {len(available_tools)} tools: {[tool.__name__ for tool in available_tools]}")

def route_request_with_workflow(user_message: str, request_type: str, 
                              metadata: Dict[str, Any], session_id: Optional[str] = None,
                              user_id: Optional[str] = None) -> Tuple[Union[str, Dict[str, Any]], Any]:
    """
    Route requests with workflow orchestration and conversational context
    
    Args:
        user_message: The user's message/text to process
        request_type: The request type ('text', 'audio', 'video')
        metadata: Additional context and parameters
        session_id: Optional session identifier
        user_id: Optional user identifier
    
    Returns:
        Tuple[Union[str, Dict], ConversationContext]: Workflow result or enhanced message and conversation context
    """
    logger.info("=" * 80)
    logger.info("AGENT REQUEST RECEIVED")
    logger.info("=" * 80)
    logger.info(f"User Message: {user_message}")
    logger.info(f"Request Type: {request_type}")
    logger.info(f"Metadata: {json.dumps(metadata, indent=2)}")
    logger.info(f"Session ID: {session_id}")
    logger.info(f"User ID: {user_id}")
    logger.info("=" * 80)
    
    # Get or create conversation context
    context = conversation_manager.get_or_create_context(session_id, user_id)
    
    # Analyze user intent using conversation manager
    detected_intent, intent_params = conversation_manager.analyze_user_intent(user_message, context)
    
    # Handle help requests directly
    if detected_intent == RequestType.HELP:
        help_response = conversation_manager.generate_help_response(context)
        return help_response, context
    
    # Handle status requests
    if detected_intent == RequestType.STATUS:
        if context.pending_operations:
            status_response = f"I'm currently working on: {', '.join(context.pending_operations)}. Please wait a moment."
        elif context.last_translation_text:
            status_response = f"Last translation: \"{context.last_translation_text}\" -> {context.last_gloss}"
            if context.last_video_urls:
                status_response += f"\nVideo URLs: {', '.join(context.last_video_urls.keys())}"
        else:
            status_response = "I'm ready to help you with ASL translation! What would you like to translate?"
        return status_response, context
    
    # Determine workflow template and execute workflow
    workflow_template = None
    workflow_params = dict(metadata)
    workflow_params.update({"message": user_message, "text": user_message})
    
    if detected_intent == RequestType.TEXT_TO_ASL or request_type == "text":
        workflow_template = "text_to_asl"
        context.pending_operations = ["text to gloss conversion", "ASL video generation"]
        
    elif detected_intent == RequestType.AUDIO_TO_ASL or request_type == "audio":
        workflow_template = "audio_to_asl"
        context.pending_operations = ["audio transcription", "text to gloss conversion", "ASL video generation"]
        
        # Validate required parameters
        bucket_name = metadata.get('bucket_name', metadata.get('BucketName', ''))
        key_name = metadata.get('key_name', metadata.get('KeyName', ''))
        
        if not bucket_name or not key_name:
            error_response = conversation_manager.handle_error_response(
                "Missing required parameters: bucket_name and key_name are required for audio processing",
                context
            )
            return error_response, context
            
    elif detected_intent == RequestType.ASL_TO_TEXT or request_type == "video":
        workflow_template = "asl_to_text"
        context.pending_operations = ["ASL video analysis"]
        
        # Validate required parameters
        stream_name = metadata.get('stream_name', metadata.get('StreamName', ''))
        bucket_name = metadata.get('bucket_name', metadata.get('BucketName', ''))
        key_name = metadata.get('key_name', metadata.get('KeyName', ''))
        
        if not stream_name and not (bucket_name and key_name):
            error_response = conversation_manager.handle_error_response(
                "Missing required parameters: either stream_name or bucket_name/key_name are required for ASL analysis",
                context
            )
            return error_response, context
        
        # Adjust workflow template based on input type
        if stream_name:
            workflow_params["stream_name"] = stream_name
        else:
            workflow_params["bucket_name"] = bucket_name
            workflow_params["key_name"] = key_name
    
    if workflow_template:
        # Execute workflow orchestration
        try:
            # Generate unique workflow ID
            import uuid
            workflow_id = f"{workflow_template}_{int(time.time())}_{str(uuid.uuid4())[:8]}"
            
            # Create and execute workflow
            workflow = workflow_orchestrator.create_workflow(
                workflow_template, workflow_id, workflow_params
            )
            
            logger.info(f"Executing workflow: {workflow_template} with ID: {workflow_id}")
            
            # Execute workflow with progress tracking
            def progress_callback(progress: float, wf_id: str):
                logger.info(f"Workflow {wf_id} progress: {progress:.1%}")
            
            result = workflow_orchestrator.execute_workflow(workflow_id, progress_callback)
            
            # Clear pending operations
            context.pending_operations = []
            
            logger.info("=" * 80)
            logger.info("AGENT WORKFLOW RESULT")
            logger.info("=" * 80)
            logger.info(f"Workflow ID: {workflow_id}")
            logger.info(f"Result Type: {type(result)}")
            logger.info(f"Result: {json.dumps(result, indent=2) if isinstance(result, dict) else str(result)[:500]}")
            logger.info("=" * 80)
            
            return result, context
            
        except Exception as e:
            error_msg = f"Workflow execution failed: {str(e)}"
            logger.error(error_msg)
            context.pending_operations = []
            
            # Use agent-level error recovery
            recovery_context = ErrorRecoveryContext(
                original_request=user_message,
                request_type=detected_intent,
                failed_operation=workflow_template or "workflow_execution",
                error_type=ErrorClassifier.classify_error(e),
                error_message=str(e),
                conversation_state=context
            )
            
            if agent_error_recovery.should_attempt_recovery(e, recovery_context):
                recovery_message, should_continue = agent_error_recovery.handle_agent_error(e, recovery_context)
                logger.info(f"Applied error recovery: {recovery_message[:100]}...")
                return recovery_message, context
            else:
                error_response = conversation_manager.handle_error_response(error_msg, context)
                return error_response, context
    
    # Fallback to agent-based processing for unknown intents
    response_prefix = conversation_manager.generate_contextual_response_prefix(context, detected_intent)
    routing_context = "[GENERAL] The user has a general request. Please provide helpful assistance. "
    
    enhanced_message_parts = []
    if response_prefix:
        enhanced_message_parts.append(response_prefix)
    enhanced_message_parts.append(routing_context)
    enhanced_message_parts.append(user_message)
    
    enhanced_message = " ".join(enhanced_message_parts)
    
    logger.info(f"Request routed to agent processing: {detected_intent.value}")
    logger.info("=" * 80)
    logger.info("AGENT RESPONSE (Enhanced Message)")
    logger.info("=" * 80)
    logger.info(f"Enhanced Message: {enhanced_message}")
    logger.info("=" * 80)
    return enhanced_message, context


def format_workflow_result(workflow_result: Dict[str, Any], context: Any) -> str:
    """Format workflow execution results into conversational response"""
    
    if workflow_result["status"] == WorkflowStatus.FAILED.value:
        # Handle workflow failure
        error_msg = "; ".join(workflow_result.get("errors", ["Unknown workflow error"]))
        return conversation_manager.handle_error_response(error_msg, context)
    
    elif workflow_result["status"] == WorkflowStatus.COMPLETED.value:
        # Format successful workflow results
        results = workflow_result.get("results", {})
        execution_time = workflow_result.get("execution_time", 0)
        
        response_parts = []
        
        # Add completion message
        response_parts.append(f"✅ Translation completed successfully in {execution_time:.1f} seconds!")
        response_parts.append("")
        
        # Format results based on workflow type
        if "text_to_gloss" in results and "gloss_to_video" in results:
            # Text-to-ASL workflow
            gloss = results["text_to_gloss"]
            video_result = results["gloss_to_video"]
            
            if isinstance(video_result, dict):
                response_parts.append(f"**ASL Gloss:** {gloss}")
                response_parts.append("")
                response_parts.append("**Generated Videos:**")
                
                for video_type in ["PoseURL", "SignURL", "AvatarURL"]:
                    if video_type in video_result and video_result[video_type]:
                        video_name = video_type.replace("URL", "").lower()
                        response_parts.append(f"• {video_name.title()}: {video_result[video_type]}")
                
                # Store in context
                context.last_gloss = gloss
                context.last_video_urls = {
                    k.replace("URL", "").lower(): v 
                    for k, v in video_result.items() 
                    if k.endswith("URL") and v
                }
        
        elif "process_audio" in results:
            # Audio-to-ASL workflow
            transcribed_text = results["process_audio"]
            response_parts.append(f"**Transcribed Text:** \"{transcribed_text}\"")
            
            if "text_to_gloss" in results:
                gloss = results["text_to_gloss"]
                response_parts.append(f"**ASL Gloss:** {gloss}")
                context.last_gloss = gloss
            
            if "gloss_to_video" in results:
                video_result = results["gloss_to_video"]
                if isinstance(video_result, dict):
                    response_parts.append("")
                    response_parts.append("**Generated Videos:**")
                    
                    for video_type in ["PoseURL", "SignURL", "AvatarURL"]:
                        if video_type in video_result and video_result[video_type]:
                            video_name = video_type.replace("URL", "").lower()
                            response_parts.append(f"• {video_name.title()}: {video_result[video_type]}")
                    
                    context.last_video_urls = {
                        k.replace("URL", "").lower(): v 
                        for k, v in video_result.items() 
                        if k.endswith("URL") and v
                    }
        
        elif "analyze_asl" in results:
            # ASL-to-Text workflow
            interpreted_text = results["analyze_asl"]
            response_parts.append(f"**Interpreted ASL:** \"{interpreted_text}\"")
        
        # Add helpful follow-up
        response_parts.append("")
        response_parts.append("Is there anything else you'd like me to translate or analyze?")
        
        return "\n".join(response_parts)
    
    else:
        # Handle other statuses (running, pending, cancelled)
        status = workflow_result["status"]
        progress = workflow_result.get("progress", 0)
        return f"Workflow status: {status} ({progress:.1%} complete)"


@app.entrypoint
@retry_with_backoff(max_retries=config.agent.max_retries, delay=config.agent.retry_delay)
def invoke(payload: Dict[str, Any]) -> str:
    """
    Main entry point for the GenASL agent with conversational capabilities
    
    Args:
        payload: Dictionary containing the request data
                Expected keys:
                - message: The user's message/text to process
                - type: Optional request type ('text', 'audio', 'video')
                - metadata: Optional additional context
                - session_id: Optional session identifier for conversation context
                - user_id: Optional user identifier
                - bucket_name/BucketName: S3 bucket for audio/video files
                - key_name/KeyName: S3 key for audio/video files
                - stream_name/StreamName: Kinesis Video Stream name
    
    Returns:
        str: The agent's conversational response message
    """
    context = None
    operation_id = None
    try:
        logger.info(f"Agent invoked with payload keys: {list(payload.keys())}")
        
        # Validate and normalize payload
        normalized_payload = validate_payload(payload)
        
        user_message = normalized_payload["message"]
        request_type = normalized_payload["type"]
        metadata = normalized_payload["metadata"]
        session_id = normalized_payload.get("session_id") or payload.get("session_id")
        user_id = normalized_payload.get("user_id") or payload.get("user_id")
        
        # Add additional metadata from payload for routing
        for key in ['bucket_name', 'BucketName', 'key_name', 'KeyName', 'stream_name', 'StreamName']:
            if key in payload:
                metadata[key] = payload[key]
        
        logger.info(f"Processing {request_type} request: {user_message[:100]}...")
        
        # Start monitoring the request
        operation_id = monitoring_manager.log_request_start(
            session_id or "anonymous",
            user_id or "anonymous", 
            request_type,
            user_message
        )
        
        # Route the request with workflow orchestration
        workflow_result, context = route_request_with_workflow(
            user_message, request_type, metadata, session_id, user_id
        )
        
        # Check if this is a direct response (help, status, etc.)
        if isinstance(workflow_result, str):
            # This is a direct response, update context and return
            if context:
                conversation_manager.update_context(
                    context, RequestType.HELP, user_message, workflow_result
                )
            return workflow_result
        
        # Check if this is a workflow result
        if isinstance(workflow_result, dict) and "workflow_id" in workflow_result:
            # Process workflow result
            result = format_workflow_result(workflow_result, context)
            
            # Update conversation context
            detected_intent = RequestType.TEXT_TO_ASL  # Default
            if 'audio' in request_type.lower():
                detected_intent = RequestType.AUDIO_TO_ASL
            elif 'video' in request_type.lower():
                detected_intent = RequestType.ASL_TO_TEXT
            
            conversation_manager.update_context(context, detected_intent, user_message, result)
            
            return result
        
        # Fallback to agent processing for enhanced messages
        if isinstance(workflow_result, str) and workflow_result.startswith('['):
            # Invoke the agent with the enhanced message
            response = agent(workflow_result)
            
            # Extract the response content using utility function
            result = extract_response_content(response)
            
            # Format the result with conversational context
            if context:
                formatted_result = conversation_manager.format_translation_result(result, context)
                
                # Update conversation context
                detected_intent = RequestType.TEXT_TO_ASL  # Default
                if 'audio' in request_type.lower():
                    detected_intent = RequestType.AUDIO_TO_ASL
                elif 'video' in request_type.lower():
                    detected_intent = RequestType.ASL_TO_TEXT
                
                conversation_manager.update_context(context, detected_intent, user_message, formatted_result)
                
                # Clear pending operations
                context.pending_operations = []
                
                result = formatted_result
        
        logger.info(f"Agent response generated successfully (length: {len(result)})")
        
        # Log successful completion
        if operation_id:
            monitoring_manager.log_request_success(
                operation_id,
                session_id or "anonymous",
                len(result)
            )
        
        # Log the final response being returned
        logger.info("=" * 80)
        logger.info("AGENT RESPONSE BEING RETURNED TO CALLER")
        logger.info("=" * 80)
        logger.info(f"Response Type: {type(result)}")
        logger.info(f"Response Length: {len(result)} characters")
        logger.info(f"Response Preview (first 500 chars):\n{result[:500]}")
        if len(result) > 500:
            logger.info(f"Response Preview (last 200 chars):\n...{result[-200:]}")
        logger.info("=" * 80)
        
        return result
        
    except ValueError as e:
        error_msg = f"Invalid request: {str(e)}"
        logger.warning(f"Validation error: {e}")
        
        # Handle error with conversational context and recovery
        if context:
            recovery_context = ErrorRecoveryContext(
                original_request=normalized_payload.get("message", ""),
                request_type=RequestType.TEXT_TO_ASL,  # Default
                failed_operation="request_validation",
                error_type=ErrorClassifier.classify_error(e),
                error_message=str(e),
                conversation_state=context
            )
            
            recovery_message = agent_error_recovery.generate_user_friendly_error_message(e, recovery_context)
            
            # Log the error
            if operation_id:
                monitoring_manager.log_request_failure(
                    operation_id,
                    context.session_id if context else "anonymous",
                    e,
                    "validation_error"
                )
            
            # Log error response being returned
            logger.info("=" * 80)
            logger.info("ERROR RESPONSE BEING RETURNED TO CALLER")
            logger.info("=" * 80)
            logger.info(f"Error Type: Validation Error")
            logger.info(f"Error Message: {str(e)}")
            logger.info(f"Recovery Message: {recovery_message}")
            logger.info("=" * 80)
            
            return recovery_message
        
        # Log the error
        if operation_id:
            monitoring_manager.log_request_failure(
                operation_id,
                "anonymous",
                e,
                "validation_error"
            )
        
        # Log error response being returned
        logger.info("=" * 80)
        logger.info("ERROR RESPONSE BEING RETURNED TO CALLER")
        logger.info("=" * 80)
        logger.info(f"Error Type: Validation Error")
        logger.info(f"Error Message: {error_msg}")
        logger.info("=" * 80)
        
        return error_msg
        
    except Exception as e:
        error_msg = f"An error occurred while processing your request: {str(e)}"
        logger.error(f"Agent invocation error: {e}", exc_info=True)
        
        # Handle error with conversational context and recovery
        if context:
            recovery_context = ErrorRecoveryContext(
                original_request=normalized_payload.get("message", "") if 'normalized_payload' in locals() else "",
                request_type=RequestType.TEXT_TO_ASL,  # Default
                failed_operation="agent_invocation",
                error_type=ErrorClassifier.classify_error(e),
                error_message=str(e),
                conversation_state=context
            )
            
            if agent_error_recovery.should_attempt_recovery(e, recovery_context):
                recovery_message, should_continue = agent_error_recovery.handle_agent_error(e, recovery_context)
                
                # Log the error with recovery
                if operation_id:
                    monitoring_manager.log_request_failure(
                        operation_id,
                        context.session_id if context else "anonymous",
                        e,
                        "agent_error_recovered"
                    )
                
                # Log error response being returned
                logger.info("=" * 80)
                logger.info("ERROR RESPONSE (WITH RECOVERY) BEING RETURNED TO CALLER")
                logger.info("=" * 80)
                logger.info(f"Error Type: {type(e).__name__}")
                logger.info(f"Error Message: {str(e)}")
                logger.info(f"Recovery Message: {recovery_message}")
                logger.info("=" * 80)
                
                return recovery_message
            else:
                error_response = conversation_manager.handle_error_response(str(e), context)
                
                # Log the error
                if operation_id:
                    monitoring_manager.log_request_failure(
                        operation_id,
                        context.session_id if context else "anonymous",
                        e,
                        "agent_error"
                    )
                
                # Log error response being returned
                logger.info("=" * 80)
                logger.info("ERROR RESPONSE BEING RETURNED TO CALLER")
                logger.info("=" * 80)
                logger.info(f"Error Type: {type(e).__name__}")
                logger.info(f"Error Message: {str(e)}")
                logger.info(f"Error Response: {error_response}")
                logger.info("=" * 80)
                
                return error_response
        
        # Log the error
        if operation_id:
            monitoring_manager.log_request_failure(
                operation_id,
                "anonymous",
                e,
                "agent_error"
            )
        
        return error_msg

def health_check() -> Dict[str, Any]:
    """Health check endpoint for monitoring"""
    try:
        tool_names = [tool.__name__ for tool in available_tools]
        
        # Get health metrics from monitoring manager
        health_metrics = monitoring_manager.get_health_metrics()
        
        # Determine overall health status
        error_rate = health_metrics.get('error_rate', 0)
        recent_alerts = health_metrics.get('recent_alerts', 0)
        
        if error_rate > 0.5:  # More than 50% error rate
            status = "critical"
        elif error_rate > 0.2 or recent_alerts > 5:  # More than 20% error rate or many alerts
            status = "degraded"
        else:
            status = "healthy"
        
        return {
            "status": status,
            "timestamp": datetime.now().isoformat(),
            "agent_model": config.model.eng_to_asl_model,
            "tools_count": len(available_tools),
            "available_tools": tool_names,
            "capabilities": {
                "text_to_asl": "text_to_asl_gloss" in tool_names,
                "gloss_to_video": "gloss_to_video" in tool_names,
                "audio_processing": "process_audio_input" in tool_names,
                "asl_analysis": any(name in tool_names for name in ["analyze_asl_video_stream", "analyze_asl_from_s3"])
            },
            "metrics": health_metrics,
            "config": {
                "pose_bucket": config.aws.pose_bucket,
                "data_bucket": config.aws.asl_data_bucket,
                "table_name": config.aws.table_name,
                "region": config.aws.region,
                "max_tokens": config.model.max_tokens,
                "temperature": config.model.temperature
            }
        }
    except Exception as e:
        # Log the health check failure
        from .monitoring import AlertLevel
        monitoring_manager.alert_manager.create_alert(
            "health_check_failure",
            AlertLevel.ERROR,
            f"Health check failed: {str(e)}"
        )
        
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

if __name__ == "__main__":
    logger.info("Starting GenASL Sign Language Agent")
    logger.info(f"Health check: {health_check()}")
    
    # Run the AgentCore app
    app.run()