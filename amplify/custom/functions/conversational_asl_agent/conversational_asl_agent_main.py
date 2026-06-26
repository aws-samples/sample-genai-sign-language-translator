"""
Main Conversational ASL Agent Entry Point

This module provides the main entry point for the conversational ASL agent,
maintaining backward compatibility with the existing SignLanguageAgent interface
while providing enhanced conversational capabilities.
"""

import logging
import time
import json
from typing import Dict, Any, Optional, Union
from datetime import datetime

# Import existing SignLanguageAgent components for compatibility
import sys
from pathlib import Path

# Add parent directory to path for imports
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir))

try:
    from signlanguageagent.utils import setup_logging, validate_payload, extract_response_content, retry_with_backoff
    from signlanguageagent.config import config
    from signlanguageagent.monitoring import monitoring_manager
except ImportError:
    # Fallback imports if signlanguageagent module is not available
    def setup_logging(level):
        logging.basicConfig(level=getattr(logging, level.upper(), logging.INFO))
        return logging.getLogger(__name__)
    
    def validate_payload(payload):
        return {
            "message": payload.get("message", ""),
            "type": payload.get("type", "text"),
            "metadata": payload.get("metadata", {})
        }
    
    def extract_response_content(response):
        if isinstance(response, str):
            return response
        return str(response)
    
    def retry_with_backoff(max_retries=3, delay=1):
        def decorator(func):
            return func
        return decorator
    
    # Mock config and monitoring
    class MockConfig:
        class Agent:
            log_level = "INFO"
            max_retries = 3
            retry_delay = 1
        agent = Agent()
    
    class MockMonitoring:
        def log_request_start(self, *args): return "mock_id"
        def log_request_success(self, *args): pass
        def log_request_failure(self, *args): pass
    
    config = MockConfig()
    monitoring_manager = MockMonitoring()

# Import conversational components
from .conversation_router import ConversationRouter, ConversationResponse
from .memory_manager import ConversationMemoryManager
from .data_models import ConversationContext, ConversationIntent, TranslationResult
from .error_handler import ConversationErrorHandler
from .response_formatter import ConversationResponseFormatter
from .conversation_monitoring import (
    ConversationMonitoringManager, 
    track_conversation_start,
    track_conversation_success,
    track_conversation_failure,
    track_session_lifecycle
)

# Configure logging
logger = setup_logging(config.agent.log_level)

class ConversationalASLAgentMain:
    """
    Main conversational ASL agent that provides the primary entry point
    
    This class maintains backward compatibility with the existing SignLanguageAgent
    interface while providing enhanced conversational capabilities through:
    - Natural conversation flow management
    - Context-aware interactions using AgentCore Memory
    - Enhanced response formatting
    - Session persistence across invocations
    - Intent classification and parameter extraction
    """
    
    def __init__(self, memory_manager: Optional[ConversationMemoryManager] = None):
        """
        Initialize the main conversational ASL agent
        
        Args:
            memory_manager: Optional memory manager instance. If None, creates a new one.
        """
        self.memory_manager = memory_manager or ConversationMemoryManager()
        self.conversation_router = ConversationRouter(self.memory_manager)
        self.error_handler = ConversationErrorHandler()
        self.response_formatter = ConversationResponseFormatter()
        self.monitoring_manager = ConversationMonitoringManager()
        
        # Agent metadata
        self.agent_version = "2.0.0-conversational"
        self.capabilities = {
            'text_to_asl': True,
            'audio_to_asl': True,
            'asl_to_text': True,
            'conversational_context': True,
            'session_persistence': True,
            'multi_modal_input': True,
            'intent_classification': True,
            'parameter_extraction': True,
            'context_aware_analysis': True,
            'natural_language_responses': True,
            'error_recovery': True,
            'backward_compatibility': True
        }
        
        logger.info(f"ConversationalASLAgentMain initialized (version: {self.agent_version})")
    
    @retry_with_backoff(max_retries=config.agent.max_retries, delay=config.agent.retry_delay)
    def invoke(self, payload: Dict[str, Any]) -> str:
        """
        Main entry point for the conversational ASL agent
        
        This method handles conversational interactions and maintains backward compatibility 
        with the existing SignLanguageAgent interface while providing enhanced conversational capabilities.
        
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
        operation_id = None
        conversation_response = None
        
        try:
            logger.info(f"Conversational agent invoked with payload keys: {list(payload.keys())}")
            
            # Validate and normalize payload for backward compatibility
            normalized_payload = validate_payload(payload)
            
            user_message = normalized_payload["message"]
            request_type = normalized_payload["type"]
            metadata = normalized_payload["metadata"]
            
            # Extract session and user information
            session_id = payload.get("session_id") or payload.get("sessionId")
            user_id = payload.get("user_id") or payload.get("userId")
            
            # Add additional metadata from payload for routing
            for key in ['bucket_name', 'BucketName', 'key_name', 'KeyName', 'stream_name', 'StreamName']:
                if key in payload:
                    metadata[key] = payload[key]
            
            # Add request type to metadata for context
            metadata['request_type'] = request_type
            
            logger.info(f"Processing conversational {request_type} request: {user_message[:100]}...")
            
            # Start monitoring the request
            operation_id = monitoring_manager.log_request_start(
                session_id or "anonymous",
                user_id or "anonymous", 
                f"conversational_{request_type}",
                user_message
            )
            
            # Start conversation monitoring
            conversation_operation_id = self.monitoring_manager.track_conversation_start(
                session_id or "anonymous",
                user_id,
                request_type
            )
            
            # Route the conversation through the conversation router
            conversation_response = self.conversation_router.handle_conversation(
                user_input=user_message,
                session_id=session_id,
                user_id=user_id,
                metadata=metadata
            )
            
            # Extract the response message
            response_message = conversation_response.message
            
            # Add conversational enhancements to the response (response coordination)
            enhanced_response = self._enhance_response_with_context(
                response_message, conversation_response, metadata
            )
            
            logger.info(f"Conversational response generated successfully (length: {len(enhanced_response)})")
            
            # Log successful completion
            if operation_id:
                monitoring_manager.log_request_success(
                    operation_id,
                    session_id or "anonymous",
                    len(enhanced_response)
                )
            
            # Track conversation success
            if conversation_operation_id:
                translation_success = conversation_response.translation_result is not None and conversation_response.translation_result.success
                response_time = time.time() - time.time()  # This would be calculated properly in real implementation
                self.monitoring_manager.track_conversation_success(
                    conversation_operation_id,
                    intent_accuracy=None,  # Could be extracted from conversation_response
                    translation_success=translation_success,
                    response_time=response_time
                )
            
            return enhanced_response
            
        except ValueError as e:
            error_msg = f"Invalid conversational request: {str(e)}"
            logger.warning(f"Validation error: {e}")
            
            # Handle validation error with conversational context and error recovery
            recovery_response = self._handle_validation_error(e, payload, conversation_response)
            
            # Log the error
            if operation_id:
                monitoring_manager.log_request_failure(
                    operation_id,
                    payload.get("session_id", "anonymous"),
                    e,
                    "validation_error"
                )
            
            # Track conversation failure
            if 'conversation_operation_id' in locals():
                self.monitoring_manager.track_conversation_failure(
                    conversation_operation_id,
                    e,
                    error_recovery_attempted=True,
                    error_recovery_successful=True  # Since we're providing a recovery response
                )
            
            return recovery_response
            
        except Exception as e:
            error_msg = f"An error occurred while processing your conversational request: {str(e)}"
            logger.error(f"Conversational agent invocation error: {e}", exc_info=True)
            
            # Handle general error with conversational context
            recovery_response = self._handle_general_error(e, payload, conversation_response)
            
            # Log the error
            if operation_id:
                monitoring_manager.log_request_failure(
                    operation_id,
                    payload.get("session_id", "anonymous"),
                    e,
                    "conversational_agent_error"
                )
            
            # Track conversation failure
            if 'conversation_operation_id' in locals():
                self.monitoring_manager.track_conversation_failure(
                    conversation_operation_id,
                    e,
                    error_recovery_attempted=True,
                    error_recovery_successful=True  # Since we're providing a recovery response
                )
            
            return recovery_response
    
    def _enhance_response_with_context(self, response_message: str, 
                                     conversation_response: ConversationResponse,
                                     metadata: Dict[str, Any]) -> str:
        """
        Enhance the response with additional conversational context
        
        Args:
            response_message: The base response message
            conversation_response: Complete conversation response object
            metadata: Request metadata
        
        Returns:
            str: Enhanced response message
        """
        try:
            # Check if we have translation results to highlight
            if conversation_response.translation_result:
                # The response formatter should have already handled this,
                # but we can add any final enhancements here
                pass
            
            # Add session information if this is a new session
            session_info = self._get_session_enhancement(conversation_response.session_id)
            if session_info:
                response_message = f"{session_info}\n\n{response_message}"
            
            # Add any final conversational touches
            enhanced_response = self._add_conversational_touches(response_message, metadata)
            
            return enhanced_response
            
        except Exception as e:
            logger.warning(f"Error enhancing response: {e}")
            # Return original response if enhancement fails
            return response_message
    
    def _get_session_enhancement(self, session_id: str) -> Optional[str]:
        """
        Get session-specific enhancement message
        
        Args:
            session_id: Session identifier
        
        Returns:
            Optional enhancement message for new sessions
        """
        try:
            # Check if this is a new session by looking at conversation history
            context = self.memory_manager.get_conversation_context(session_id)
            
            if context and len(context.conversation_history) == 1:
                # This is the first interaction in a new session
                return "👋 Starting a new conversation session! I'll remember our context as we chat."
            
            return None
            
        except Exception as e:
            logger.debug(f"Error getting session enhancement: {e}")
            return None
    
    def _add_conversational_touches(self, response: str, metadata: Dict[str, Any]) -> str:
        """
        Add final conversational touches to the response
        
        Args:
            response: Base response message
            metadata: Request metadata
        
        Returns:
            str: Response with conversational touches
        """
        # For now, just return the response as-is
        # Future enhancements could add personalization, emoji, etc.
        return response
    
    def _handle_validation_error(self, error: Exception, payload: Dict[str, Any],
                                conversation_response: Optional[ConversationResponse]) -> str:
        """
        Handle validation errors with conversational context
        
        Args:
            error: The validation error
            payload: Original request payload
            conversation_response: Conversation response if available
        
        Returns:
            str: Conversational error response
        """
        try:
            # Try to get session context for better error handling
            session_id = payload.get("session_id")
            if session_id and conversation_response:
                context = self.memory_manager.get_conversation_context(session_id)
                return self.error_handler.handle_error(error, context, {'operation_type': 'validation'})
            
            # Fallback to basic conversational error response
            return self._generate_basic_validation_error_response(str(error))
            
        except Exception as handler_error:
            logger.error(f"Error handling validation error: {handler_error}")
            return self._generate_fallback_error_response(str(error))
    
    def _handle_general_error(self, error: Exception, payload: Dict[str, Any],
                            conversation_response: Optional[ConversationResponse]) -> str:
        """
        Handle general errors with conversational context
        
        Args:
            error: The general error
            payload: Original request payload
            conversation_response: Conversation response if available
        
        Returns:
            str: Conversational error response
        """
        try:
            # Try to get session context for better error handling
            session_id = payload.get("session_id")
            if session_id and conversation_response:
                context = self.memory_manager.get_conversation_context(session_id)
                return self.error_handler.handle_error(error, context, {'operation_type': 'general'})
            
            # Fallback to basic conversational error response
            return self._generate_basic_general_error_response(str(error))
            
        except Exception as handler_error:
            logger.error(f"Error handling general error: {handler_error}")
            return self._generate_fallback_error_response(str(error))
    
    def _generate_basic_validation_error_response(self, error_message: str) -> str:
        """Generate basic validation error response"""
        return (f"I'm having trouble understanding your request: {error_message}. "
               f"Could you please rephrase your message or provide more details? "
               f"I'm here to help with ASL translation - just tell me what you'd like to translate!")
    
    def _generate_basic_general_error_response(self, error_message: str) -> str:
        """Generate basic general error response"""
        return (f"I apologize, but I encountered an issue while processing your request: {error_message}. "
               f"Please try again, and if the problem continues, you might want to try a simpler request "
               f"or start a new conversation. I'm here to help with ASL translation!")
    
    def _generate_fallback_error_response(self, error_message: str) -> str:
        """Generate fallback error response when all else fails"""
        return (f"I'm sorry, but something unexpected happened: {error_message}. "
               f"Please try again or start a new conversation. "
               f"I'm your ASL translation assistant and I'm here to help!")
    
    def health_check(self) -> Dict[str, Any]:
        """
        Health check endpoint for monitoring conversational agent
        
        Returns:
            Dict containing health status and capability information
        """
        try:
            # Get basic health information
            health_info = {
                "status": "healthy",
                "timestamp": datetime.now().isoformat(),
                "agent_version": self.agent_version,
                "capabilities": self.capabilities,
                "components": {
                    "conversation_router": "active",
                    "memory_manager": "active",
                    "error_handler": "active",
                    "response_formatter": "active"
                }
            }
            
            # Test memory manager connectivity
            try:
                test_context = self.memory_manager.get_conversation_context("health_check_test")
                health_info["components"]["memory_manager"] = "connected"
            except Exception as e:
                health_info["components"]["memory_manager"] = f"error: {str(e)}"
                health_info["status"] = "degraded"
            
            # Test conversation router
            try:
                # Simple test to ensure router is responsive
                router_status = hasattr(self.conversation_router, 'handle_conversation')
                health_info["components"]["conversation_router"] = "ready" if router_status else "not_ready"
            except Exception as e:
                health_info["components"]["conversation_router"] = f"error: {str(e)}"
                health_info["status"] = "degraded"
            
            return health_info
            
        except Exception as e:
            return {
                "status": "critical",
                "timestamp": datetime.now().isoformat(),
                "error": str(e),
                "agent_version": self.agent_version
            }
    
    def get_capabilities(self) -> Dict[str, Any]:
        """
        Get detailed capability information
        
        Returns:
            Dict containing detailed capability information
        """
        return {
            "agent_version": self.agent_version,
            "capabilities": self.capabilities,
            "supported_inputs": ["text", "audio", "video"],
            "supported_outputs": ["text", "gloss", "video_urls"],
            "conversation_features": [
                "context_awareness",
                "intent_classification", 
                "parameter_extraction",
                "context_aware_analysis",
                "natural_responses",
                "error_recovery",
                "multi_modal_input_detection",
                "conversation_history_analysis",
                "user_pattern_recognition",
                "proactive_tips",
                "contextual_guidance",
                "next_step_suggestions",
                "follow_up_recommendations",
                "session_persistence",
                "backward_compatibility"
            ],
            "memory_integration": {
                "agentcore_memory": True,
                "session_persistence": True,
                "conversation_history": True,
                "user_preferences": True,
                "translation_results_cache": True
            },
            "error_handling": {
                "graceful_degradation": True,
                "alternative_suggestions": True,
                "recovery_workflows": True,
                "user_friendly_messages": True
            }
        }
    
    def get_session_info(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a conversation session
        
        Args:
            session_id: The session identifier
        
        Returns:
            Dict containing session information or None if session doesn't exist
        """
        try:
            return self.conversation_router.get_session_info(session_id)
        except Exception as e:
            logger.error(f"Error getting session info: {e}")
            return None
    
    def cleanup_session(self, session_id: str) -> bool:
        """
        Clean up a conversation session
        
        Args:
            session_id: The session identifier to clean up
        
        Returns:
            bool: True if cleanup was successful, False otherwise
        """
        try:
            return self.conversation_router.cleanup_session(session_id)
        except Exception as e:
            logger.error(f"Error cleaning up session {session_id}: {e}")
            return False

# Create the main agent instance for backward compatibility
conversational_asl_agent = ConversationalASLAgentMain()

# Backward compatibility functions that match the existing SignLanguageAgent interface
def invoke(payload: Dict[str, Any]) -> str:
    """
    Backward compatibility invoke function
    
    This function maintains the same interface as the existing SignLanguageAgent
    while providing enhanced conversational capabilities.
    
    Args:
        payload: Request payload dictionary
    
    Returns:
        str: Conversational response message
    """
    return conversational_asl_agent.invoke(payload)

def health_check() -> Dict[str, Any]:
    """
    Backward compatibility health check function
    
    Returns:
        Dict containing health status information
    """
    return conversational_asl_agent.health_check()

# Export the main functions for use as module-level functions
__all__ = [
    'ConversationalASLAgentMain',
    'conversational_asl_agent', 
    'invoke',
    'health_check'
]

if __name__ == "__main__":
    # Test the agent
    logger.info("Starting Conversational ASL Agent Main")
    logger.info(f"Health check: {health_check()}")
    
    # Example test invocation
    test_payload = {
        "message": "Hello, can you help me translate text to ASL?",
        "type": "text",
        "session_id": "test_session_123"
    }
    
    try:
        response = invoke(test_payload)
        logger.info(f"Test response: {response[:200]}...")
    except Exception as e:
        logger.error(f"Test invocation failed: {e}")