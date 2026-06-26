"""
Agent-level error recovery for the GenASL Sign Language Agent

This module provides agent-level error recovery capabilities including:
- Conversation context preservation during errors
- Alternative workflow paths when tools fail
- User-friendly error messaging system
- Recovery strategies for different error scenarios
"""

import logging
import time
from typing import Dict, Any, List, Optional, Tuple
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from .conversation import ConversationState, RequestType
from .error_handling import ErrorType, ErrorClassifier

logger = logging.getLogger(__name__)


class RecoveryStrategy(Enum):
    """Recovery strategies for different error scenarios"""
    RETRY_WITH_FALLBACK = "retry_with_fallback"
    ALTERNATIVE_WORKFLOW = "alternative_workflow"
    GRACEFUL_DEGRADATION = "graceful_degradation"
    USER_GUIDANCE = "user_guidance"
    ESCALATION = "escalation"


@dataclass
class ErrorRecoveryContext:
    """Context for error recovery operations"""
    original_request: str
    request_type: RequestType
    failed_operation: str
    error_type: ErrorType
    error_message: str
    conversation_state: Any  # ConversationState
    recovery_attempts: int = 0
    max_recovery_attempts: int = 3
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


class AgentErrorRecovery:
    """Agent-level error recovery manager"""
    
    def __init__(self):
        self.recovery_history: Dict[str, List[ErrorRecoveryContext]] = {}
        self.recovery_strategies = {
            ErrorType.TRANSIENT: RecoveryStrategy.RETRY_WITH_FALLBACK,
            ErrorType.THROTTLING: RecoveryStrategy.RETRY_WITH_FALLBACK,
            ErrorType.TIMEOUT: RecoveryStrategy.ALTERNATIVE_WORKFLOW,
            ErrorType.AUTHENTICATION: RecoveryStrategy.USER_GUIDANCE,
            ErrorType.VALIDATION: RecoveryStrategy.USER_GUIDANCE,
            ErrorType.RESOURCE_NOT_FOUND: RecoveryStrategy.GRACEFUL_DEGRADATION,
            ErrorType.SERVICE_UNAVAILABLE: RecoveryStrategy.ALTERNATIVE_WORKFLOW,
            ErrorType.PERMANENT: RecoveryStrategy.ESCALATION
        }
    
    def handle_agent_error(self, error: Exception, context: ErrorRecoveryContext) -> Tuple[str, bool]:
        """
        Handle agent-level errors with recovery strategies
        
        Args:
            error: The exception that occurred
            context: Error recovery context
            
        Returns:
            Tuple[str, bool]: (recovery_message, should_continue)
        """
        error_type = ErrorClassifier.classify_error(error)
        context.error_type = error_type
        context.error_message = str(error)
        
        # Record error in history
        session_id = getattr(context.conversation_state, 'session_id', 'default')
        if session_id not in self.recovery_history:
            self.recovery_history[session_id] = []
        self.recovery_history[session_id].append(context)
        
        # Determine recovery strategy
        strategy = self.recovery_strategies.get(error_type, RecoveryStrategy.ESCALATION)
        
        logger.info(f"Applying recovery strategy {strategy.value} for error type {error_type.value}")
        
        # Apply recovery strategy
        if strategy == RecoveryStrategy.RETRY_WITH_FALLBACK:
            return self._handle_retry_with_fallback(context)
        elif strategy == RecoveryStrategy.ALTERNATIVE_WORKFLOW:
            return self._handle_alternative_workflow(context)
        elif strategy == RecoveryStrategy.GRACEFUL_DEGRADATION:
            return self._handle_graceful_degradation(context)
        elif strategy == RecoveryStrategy.USER_GUIDANCE:
            return self._handle_user_guidance(context)
        else:  # ESCALATION
            return self._handle_escalation(context)
    
    def _handle_retry_with_fallback(self, context: ErrorRecoveryContext) -> Tuple[str, bool]:
        """Handle retry with fallback strategy"""
        if context.recovery_attempts < context.max_recovery_attempts:
            context.recovery_attempts += 1
            
            # Preserve conversation context
            self._preserve_conversation_context(context)
            
            if context.error_type == ErrorType.THROTTLING:
                wait_time = min(2 ** context.recovery_attempts, 30)  # Max 30 seconds
                message = (
                    f"I'm experiencing high demand right now. Let me try again in {wait_time} seconds. "
                    f"Your request for '{context.original_request}' is still being processed."
                )
                time.sleep(wait_time)
            else:
                message = (
                    f"I encountered a temporary issue while processing your request. "
                    f"Let me try a different approach for '{context.original_request}'."
                )
            
            return message, True  # Continue processing
        else:
            # Max retries reached, fall back to alternative approach
            return self._handle_alternative_workflow(context)
    
    def _handle_alternative_workflow(self, context: ErrorRecoveryContext) -> Tuple[str, bool]:
        """Handle alternative workflow strategy"""
        self._preserve_conversation_context(context)
        
        # Suggest alternative approaches based on request type
        if context.request_type == RequestType.TEXT_TO_ASL:
            message = (
                f"I'm having trouble with the standard translation process for '{context.original_request}'. "
                f"Let me try a simplified approach that might take a bit longer but should still work."
            )
            # Could implement simplified text-to-gloss mapping here
            
        elif context.request_type == RequestType.AUDIO_TO_ASL:
            message = (
                f"I'm experiencing issues with audio processing. "
                f"Could you try uploading the audio file again, or provide the text directly? "
                f"I can translate text to ASL sign language immediately."
            )
            
        elif context.request_type == RequestType.ASL_TO_TEXT:
            message = (
                f"I'm having trouble analyzing the ASL video right now. "
                f"Could you try with a shorter video clip, or describe what you're signing? "
                f"I can help translate text to ASL in the meantime."
            )
            
        else:
            message = (
                f"I encountered an issue with your request. "
                f"Let me try a different approach or suggest an alternative way to help you."
            )
        
        return message, False  # Don't continue with original workflow
    
    def _handle_graceful_degradation(self, context: ErrorRecoveryContext) -> Tuple[str, bool]:
        """Handle graceful degradation strategy"""
        self._preserve_conversation_context(context)
        
        if context.failed_operation == "gloss_to_video":
            message = (
                f"I successfully converted your text '{context.original_request}' to ASL gloss notation, "
                f"but I'm having trouble generating the video right now. "
                f"The ASL gloss is available, and I can try the video generation again later. "
                f"Would you like me to show you the gloss notation instead?"
            )
            
        elif context.failed_operation == "text_to_asl_gloss":
            message = (
                f"I'm having trouble with the advanced translation system right now. "
                f"Let me provide a basic ASL translation for '{context.original_request}' using "
                f"a simplified approach. The result might be less refined but should still be helpful."
            )
            
        else:
            message = (
                f"I encountered an issue with part of your request, but I can still help you "
                f"with a simplified version. Let me provide what I can right now."
            )
        
        return message, False  # Provide degraded service
    
    def _handle_user_guidance(self, context: ErrorRecoveryContext) -> Tuple[str, bool]:
        """Handle user guidance strategy"""
        self._preserve_conversation_context(context)
        
        if context.error_type == ErrorType.AUTHENTICATION:
            message = (
                f"I'm having trouble accessing the translation services due to authentication issues. "
                f"This is likely a temporary system issue. Please try again in a few minutes, "
                f"or contact support if the problem persists."
            )
            
        elif context.error_type == ErrorType.VALIDATION:
            message = (
                f"I had trouble understanding your request '{context.original_request}'. "
                f"Could you please rephrase it or provide more details? For example:\n"
                f"• For text translation: 'Translate \"Hello world\" to ASL'\n"
                f"• For audio: 'Process audio from bucket-name/file.mp3'\n"
                f"• For ASL analysis: 'Analyze ASL video from stream-name'"
            )
            
        else:
            message = (
                f"I encountered an issue with your request. "
                f"Could you please try rephrasing it or providing additional details? "
                f"I'm here to help with ASL translation in any way I can."
            )
        
        return message, False  # Wait for user input
    
    def _handle_escalation(self, context: ErrorRecoveryContext) -> Tuple[str, bool]:
        """Handle escalation strategy"""
        self._preserve_conversation_context(context)
        
        # Log detailed error information for support
        logger.error(f"Escalating error for session {getattr(context.conversation_state, 'session_id', 'unknown')}: "
                    f"{context.failed_operation} - {context.error_message}")
        
        message = (
            f"I apologize, but I'm experiencing a technical issue that I can't resolve automatically. "
            f"Your request for '{context.original_request}' has been logged, and our support team "
            f"will be notified. Please try again later, or contact support with reference ID: "
            f"{context.timestamp.strftime('%Y%m%d-%H%M%S')}"
        )
        
        return message, False  # Stop processing
    
    def _preserve_conversation_context(self, context: ErrorRecoveryContext):
        """Preserve conversation context during error recovery"""
        try:
            # Update conversation state with error information
            if hasattr(context.conversation_state, 'last_error'):
                context.conversation_state.last_error = {
                    'operation': context.failed_operation,
                    'error_type': context.error_type.value,
                    'message': context.error_message,
                    'timestamp': context.timestamp.isoformat(),
                    'recovery_attempts': context.recovery_attempts
                }
            
            # Preserve the original request for potential retry
            if hasattr(context.conversation_state, 'pending_retry'):
                context.conversation_state.pending_retry = {
                    'request': context.original_request,
                    'type': context.request_type.value,
                    'attempts': context.recovery_attempts
                }
            
            logger.info(f"Preserved conversation context for error recovery")
            
        except Exception as e:
            logger.warning(f"Failed to preserve conversation context: {str(e)}")
    
    def get_recovery_suggestions(self, error_type: ErrorType, request_type: RequestType) -> List[str]:
        """Get recovery suggestions for specific error and request types"""
        suggestions = []
        
        if error_type == ErrorType.THROTTLING:
            suggestions.extend([
                "Wait a few moments before trying again",
                "Try breaking large requests into smaller parts",
                "Consider using the service during off-peak hours"
            ])
            
        elif error_type == ErrorType.TIMEOUT:
            if request_type == RequestType.AUDIO_TO_ASL:
                suggestions.extend([
                    "Try with a shorter audio file",
                    "Ensure the audio file is in a supported format (MP3, WAV, MP4)",
                    "Check that the audio quality is clear"
                ])
            elif request_type == RequestType.ASL_TO_TEXT:
                suggestions.extend([
                    "Try with a shorter video clip",
                    "Ensure good lighting and clear view of signs",
                    "Make sure signs are performed at a moderate pace"
                ])
            else:
                suggestions.extend([
                    "Try with shorter text input",
                    "Break complex requests into simpler parts"
                ])
                
        elif error_type == ErrorType.VALIDATION:
            if request_type == RequestType.AUDIO_TO_ASL:
                suggestions.extend([
                    "Verify the S3 bucket name and file path are correct",
                    "Ensure the audio file exists and is accessible",
                    "Check that the file format is supported"
                ])
            else:
                suggestions.extend([
                    "Check that your input is properly formatted",
                    "Ensure all required parameters are provided",
                    "Try with simpler input to test the service"
                ])
        
        return suggestions
    
    def generate_user_friendly_error_message(self, error: Exception, context: ErrorRecoveryContext) -> str:
        """Generate user-friendly error messages"""
        error_type = ErrorClassifier.classify_error(error)
        
        # Base message
        if error_type == ErrorType.TRANSIENT:
            base_msg = "I'm experiencing a temporary issue"
        elif error_type == ErrorType.THROTTLING:
            base_msg = "I'm currently handling a lot of requests"
        elif error_type == ErrorType.TIMEOUT:
            base_msg = "Your request is taking longer than expected"
        elif error_type == ErrorType.AUTHENTICATION:
            base_msg = "I'm having trouble accessing the translation services"
        elif error_type == ErrorType.VALIDATION:
            base_msg = "There seems to be an issue with your request format"
        elif error_type == ErrorType.RESOURCE_NOT_FOUND:
            base_msg = "I couldn't find the requested resource"
        elif error_type == ErrorType.SERVICE_UNAVAILABLE:
            base_msg = "The translation service is temporarily unavailable"
        else:
            base_msg = "I encountered an unexpected issue"
        
        # Add context-specific information
        if context.failed_operation:
            operation_msg = f" while {context.failed_operation.replace('_', ' ')}"
        else:
            operation_msg = ""
        
        # Add recovery information
        suggestions = self.get_recovery_suggestions(error_type, context.request_type)
        if suggestions:
            suggestion_msg = f"\n\nHere's what you can try:\n• " + "\n• ".join(suggestions[:3])
        else:
            suggestion_msg = "\n\nPlease try again in a few moments."
        
        return f"{base_msg}{operation_msg}.{suggestion_msg}"
    
    def should_attempt_recovery(self, error: Exception, context: ErrorRecoveryContext) -> bool:
        """Determine if recovery should be attempted for this error"""
        error_type = ErrorClassifier.classify_error(error)
        
        # Don't attempt recovery for certain error types
        if error_type in [ErrorType.AUTHENTICATION, ErrorType.VALIDATION]:
            return False
        
        # Don't attempt recovery if max attempts reached
        if context.recovery_attempts >= context.max_recovery_attempts:
            return False
        
        # Check if we've had too many recent errors for this session
        session_id = getattr(context.conversation_state, 'session_id', 'default')
        if session_id in self.recovery_history:
            recent_errors = [
                err for err in self.recovery_history[session_id]
                if (datetime.now() - err.timestamp).seconds < 300  # Last 5 minutes
            ]
            if len(recent_errors) > 5:  # Too many recent errors
                return False
        
        return True
    
    def clear_recovery_history(self, session_id: str):
        """Clear recovery history for a session"""
        if session_id in self.recovery_history:
            del self.recovery_history[session_id]
            logger.info(f"Cleared recovery history for session {session_id}")


# Global instance
agent_error_recovery = AgentErrorRecovery()