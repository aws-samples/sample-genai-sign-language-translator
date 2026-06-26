"""
Conversational Error Handler

This module provides conversational error handling capabilities for the ASL agent,
including user-friendly error message generation, error classification, and
fallback strategy coordination with natural language explanations.
"""

import logging
import traceback
from typing import Dict, Any, List, Optional, Tuple
from enum import Enum
from dataclasses import dataclass

try:
    from .data_models import ConversationContext, ConversationInteraction, TranslationResult, InputType
except ImportError:
    # Handle case when running as standalone module
    from data_models import ConversationContext, ConversationInteraction, TranslationResult, InputType

# Configure logging
logger = logging.getLogger(__name__)

class ErrorType(Enum):
    """Classification of error types for appropriate response selection"""
    USER_INPUT_ERROR = "user_input_error"
    TRANSLATION_ERROR = "translation_error"
    SYSTEM_ERROR = "system_error"
    CONTEXT_ERROR = "context_error"
    NETWORK_ERROR = "network_error"
    TIMEOUT_ERROR = "timeout_error"
    VALIDATION_ERROR = "validation_error"
    AUTHENTICATION_ERROR = "authentication_error"
    RESOURCE_ERROR = "resource_error"
    UNKNOWN_ERROR = "unknown_error"

class ErrorSeverity(Enum):
    """Error severity levels for response customization"""
    LOW = "low"           # Minor issues, easy to fix
    MEDIUM = "medium"     # Moderate issues, may need guidance
    HIGH = "high"         # Serious issues, significant impact
    CRITICAL = "critical" # System failures, major problems

@dataclass
class ErrorClassification:
    """Data class for error classification results"""
    error_type: ErrorType
    severity: ErrorSeverity
    is_recoverable: bool
    user_actionable: bool
    requires_retry: bool
    suggested_actions: List[str]
    technical_details: Optional[str] = None

class ConversationErrorHandler:
    """
    Conversational error handler that provides user-friendly error messages,
    error classification, and fallback strategy coordination.
    
    This handler focuses on maintaining conversational tone while providing
    helpful guidance and recovery options for users.
    """
    
    def __init__(self):
        """Initialize the conversational error handler"""
        self.logger = logger
        
        # Error pattern mappings for classification
        self.error_patterns = {
            # User input errors
            "missing required parameter": ErrorType.USER_INPUT_ERROR,
            "invalid input format": ErrorType.USER_INPUT_ERROR,
            "unsupported file type": ErrorType.USER_INPUT_ERROR,
            "file too large": ErrorType.USER_INPUT_ERROR,
            "empty input": ErrorType.USER_INPUT_ERROR,
            "invalid audio format": ErrorType.USER_INPUT_ERROR,
            "invalid video format": ErrorType.USER_INPUT_ERROR,
            
            # Translation errors
            "translation failed": ErrorType.TRANSLATION_ERROR,
            "gloss generation failed": ErrorType.TRANSLATION_ERROR,
            "video generation failed": ErrorType.TRANSLATION_ERROR,
            "transcription failed": ErrorType.TRANSLATION_ERROR,
            "asl analysis failed": ErrorType.TRANSLATION_ERROR,
            "model error": ErrorType.TRANSLATION_ERROR,
            
            # System errors
            "internal server error": ErrorType.SYSTEM_ERROR,
            "service unavailable": ErrorType.SYSTEM_ERROR,
            "database error": ErrorType.SYSTEM_ERROR,
            "configuration error": ErrorType.SYSTEM_ERROR,
            
            # Network errors
            "connection timeout": ErrorType.NETWORK_ERROR,
            "network error": ErrorType.NETWORK_ERROR,
            "request timeout": ErrorType.TIMEOUT_ERROR,
            "operation timeout": ErrorType.TIMEOUT_ERROR,
            
            # Context errors
            "session expired": ErrorType.CONTEXT_ERROR,
            "invalid session": ErrorType.CONTEXT_ERROR,
            "context not found": ErrorType.CONTEXT_ERROR,
            
            # Resource errors
            "insufficient resources": ErrorType.RESOURCE_ERROR,
            "quota exceeded": ErrorType.RESOURCE_ERROR,
            "rate limit exceeded": ErrorType.RESOURCE_ERROR,
        }
        
        # Severity mappings
        self.severity_mappings = {
            ErrorType.USER_INPUT_ERROR: ErrorSeverity.LOW,
            ErrorType.VALIDATION_ERROR: ErrorSeverity.LOW,
            ErrorType.TRANSLATION_ERROR: ErrorSeverity.MEDIUM,
            ErrorType.CONTEXT_ERROR: ErrorSeverity.MEDIUM,
            ErrorType.NETWORK_ERROR: ErrorSeverity.MEDIUM,
            ErrorType.TIMEOUT_ERROR: ErrorSeverity.MEDIUM,
            ErrorType.RESOURCE_ERROR: ErrorSeverity.HIGH,
            ErrorType.SYSTEM_ERROR: ErrorSeverity.HIGH,
            ErrorType.AUTHENTICATION_ERROR: ErrorSeverity.HIGH,
            ErrorType.UNKNOWN_ERROR: ErrorSeverity.MEDIUM,
        }
        
        logger.info("ConversationErrorHandler initialized")
    
    def handle_error(self, error: Exception, context: ConversationContext, 
                    operation_context: Optional[Dict[str, Any]] = None) -> str:
        """
        Handle an error and generate a conversational response
        
        Args:
            error: The exception that occurred
            context: Current conversation context
            operation_context: Optional context about the operation that failed
        
        Returns:
            str: User-friendly conversational error response
        """
        try:
            # Classify the error
            classification = self.classify_error(error, operation_context)
            
            # Generate conversational response based on classification
            response = self.generate_error_response(error, classification, context, operation_context)
            
            # Log the error for monitoring
            self._log_error(error, classification, context, operation_context)
            
            return response
            
        except Exception as handler_error:
            # Fallback if error handler itself fails
            self.logger.error(f"Error handler failed: {handler_error}", exc_info=True)
            return self._generate_fallback_error_response(str(error))
    
    def classify_error(self, error: Exception, operation_context: Optional[Dict[str, Any]] = None) -> ErrorClassification:
        """
        Classify an error to determine appropriate response strategy
        
        Args:
            error: The exception to classify
            operation_context: Optional context about the failed operation
        
        Returns:
            ErrorClassification: Classification result with response guidance
        """
        error_message = str(error).lower()
        error_type_name = type(error).__name__.lower()
        
        # Determine error type based on patterns
        error_type = ErrorType.UNKNOWN_ERROR
        for pattern, pattern_type in self.error_patterns.items():
            if pattern in error_message or pattern in error_type_name:
                error_type = pattern_type
                break
        
        # Special handling for specific exception types
        if isinstance(error, ValueError):
            error_type = ErrorType.VALIDATION_ERROR
        elif isinstance(error, FileNotFoundError):
            error_type = ErrorType.USER_INPUT_ERROR
        elif isinstance(error, PermissionError):
            error_type = ErrorType.AUTHENTICATION_ERROR
        elif isinstance(error, TimeoutError):
            error_type = ErrorType.TIMEOUT_ERROR
        elif isinstance(error, ConnectionError):
            error_type = ErrorType.NETWORK_ERROR
        
        # Determine severity
        severity = self.severity_mappings.get(error_type, ErrorSeverity.MEDIUM)
        
        # Determine recovery characteristics
        is_recoverable = error_type in [
            ErrorType.USER_INPUT_ERROR,
            ErrorType.VALIDATION_ERROR,
            ErrorType.TRANSLATION_ERROR,
            ErrorType.NETWORK_ERROR,
            ErrorType.TIMEOUT_ERROR
        ]
        
        user_actionable = error_type in [
            ErrorType.USER_INPUT_ERROR,
            ErrorType.VALIDATION_ERROR,
            ErrorType.CONTEXT_ERROR
        ]
        
        requires_retry = error_type in [
            ErrorType.TRANSLATION_ERROR,
            ErrorType.NETWORK_ERROR,
            ErrorType.TIMEOUT_ERROR,
            ErrorType.SYSTEM_ERROR
        ]
        
        # Generate suggested actions
        suggested_actions = self._generate_suggested_actions(error_type, error_message, operation_context)
        
        return ErrorClassification(
            error_type=error_type,
            severity=severity,
            is_recoverable=is_recoverable,
            user_actionable=user_actionable,
            requires_retry=requires_retry,
            suggested_actions=suggested_actions,
            technical_details=str(error)
        )
    
    def generate_error_response(self, error: Exception, classification: ErrorClassification,
                              context: ConversationContext, 
                              operation_context: Optional[Dict[str, Any]] = None) -> str:
        """
        Generate a conversational error response based on error classification
        
        Args:
            error: The original exception
            classification: Error classification result
            context: Current conversation context
            operation_context: Optional operation context
        
        Returns:
            str: Conversational error response
        """
        # Start with empathetic acknowledgment
        response_parts = []
        
        # Add contextual opening based on error severity
        if classification.severity == ErrorSeverity.CRITICAL:
            response_parts.append("I'm really sorry, but I've encountered a serious issue that's preventing me from helping you right now.")
        elif classification.severity == ErrorSeverity.HIGH:
            response_parts.append("I apologize, but I've run into a significant problem while processing your request.")
        elif classification.severity == ErrorSeverity.MEDIUM:
            response_parts.append("I'm sorry, but I encountered an issue while working on your request.")
        else:
            response_parts.append("I noticed a small issue with your request that I can help you fix.")
        
        # Add specific error explanation based on type
        explanation = self._generate_error_explanation(classification, operation_context)
        if explanation:
            response_parts.append(explanation)
        
        # Add suggested actions if available
        if classification.suggested_actions:
            if classification.user_actionable:
                response_parts.append("Here's what you can do to fix this:")
                for i, action in enumerate(classification.suggested_actions[:3], 1):  # Limit to 3 suggestions
                    response_parts.append(f"{i}. {action}")
            else:
                response_parts.append("Here are some alternatives you can try:")
                for i, action in enumerate(classification.suggested_actions[:3], 1):
                    response_parts.append(f"{i}. {action}")
        
        # Add recovery guidance if error is recoverable
        if classification.is_recoverable:
            if classification.requires_retry:
                response_parts.append("Would you like me to try again, or would you prefer to try a different approach?")
            else:
                response_parts.append("Once you've made the adjustment, feel free to try again!")
        else:
            response_parts.append("I'll need to resolve this issue before I can continue. Please try again in a few moments.")
        
        # Add contextual help based on conversation history
        contextual_help = self._generate_contextual_help(classification, context)
        if contextual_help:
            response_parts.append(contextual_help)
        
        return "\n\n".join(response_parts)
    
    def suggest_fallback_strategies(self, error_type: ErrorType, context: ConversationContext,
                                  operation_context: Optional[Dict[str, Any]] = None) -> List[str]:
        """
        Generate fallback strategy suggestions based on error type and context
        
        Args:
            error_type: The classified error type
            context: Current conversation context
            operation_context: Optional operation context
        
        Returns:
            List[str]: List of fallback strategy suggestions
        """
        strategies = []
        
        if error_type == ErrorType.TRANSLATION_ERROR:
            strategies.extend([
                "Try breaking your text into shorter sentences",
                "Use simpler language or common words",
                "Check if there are any special characters that might be causing issues",
                "Try a different translation approach (e.g., if text failed, try audio input)"
            ])
        
        elif error_type == ErrorType.USER_INPUT_ERROR:
            strategies.extend([
                "Double-check that your file is in a supported format",
                "Make sure your input isn't empty or too short",
                "Try uploading a smaller file if size might be an issue",
                "Verify that all required information is provided"
            ])
        
        elif error_type == ErrorType.NETWORK_ERROR or error_type == ErrorType.TIMEOUT_ERROR:
            strategies.extend([
                "Wait a moment and try again",
                "Check your internet connection",
                "Try with a smaller file or shorter input",
                "If the problem persists, try again in a few minutes"
            ])
        
        elif error_type == ErrorType.SYSTEM_ERROR:
            strategies.extend([
                "Try again in a few moments",
                "Use a different translation method if available",
                "Contact support if the issue continues",
                "Try with simpler input to see if that works"
            ])
        
        elif error_type == ErrorType.CONTEXT_ERROR:
            strategies.extend([
                "Start a new conversation session",
                "Provide the full context again",
                "Try your request without referencing previous interactions",
                "Let me know what you were trying to do and I'll help from the beginning"
            ])
        
        # Add context-specific strategies based on conversation history
        if context.last_translation and context.last_translation.success:
            strategies.append("Try using the same approach that worked for your last successful translation")
        
        if len(context.conversation_history) > 5:
            strategies.append("We could start fresh with a new session if you'd like")
        
        return strategies[:4]  # Limit to 4 most relevant strategies
    
    def _generate_suggested_actions(self, error_type: ErrorType, error_message: str,
                                  operation_context: Optional[Dict[str, Any]] = None) -> List[str]:
        """Generate specific suggested actions based on error type and message"""
        actions = []
        
        if error_type == ErrorType.USER_INPUT_ERROR:
            if "file too large" in error_message:
                actions.extend([
                    "Try uploading a smaller file (under 10MB)",
                    "Compress your audio or video file",
                    "Break longer content into shorter segments"
                ])
            elif "unsupported file type" in error_message:
                actions.extend([
                    "Use a supported format: MP3, WAV, M4A for audio or MP4, AVI, MOV for video",
                    "Convert your file to a supported format",
                    "Try uploading a different file"
                ])
            elif "empty input" in error_message:
                actions.extend([
                    "Make sure to include the text you want to translate",
                    "Check that your file isn't empty or corrupted",
                    "Provide some content for me to work with"
                ])
            else:
                actions.extend([
                    "Double-check your input format",
                    "Make sure all required information is provided",
                    "Try rephrasing your request"
                ])
        
        elif error_type == ErrorType.TRANSLATION_ERROR:
            actions.extend([
                "Try with simpler or shorter text",
                "Break complex sentences into smaller parts",
                "Use more common words if possible",
                "Try a different input method (text instead of audio, etc.)"
            ])
        
        elif error_type == ErrorType.NETWORK_ERROR or error_type == ErrorType.TIMEOUT_ERROR:
            actions.extend([
                "Wait a moment and try again",
                "Check your internet connection",
                "Try with a smaller file or shorter input"
            ])
        
        elif error_type == ErrorType.CONTEXT_ERROR:
            actions.extend([
                "Start a new conversation",
                "Provide the full context again",
                "Try your request without referencing previous interactions"
            ])
        
        return actions
    
    def _generate_error_explanation(self, classification: ErrorClassification,
                                  operation_context: Optional[Dict[str, Any]] = None) -> Optional[str]:
        """Generate a user-friendly explanation of what went wrong"""
        error_type = classification.error_type
        
        explanations = {
            ErrorType.USER_INPUT_ERROR: "There seems to be an issue with the input you provided.",
            ErrorType.VALIDATION_ERROR: "The information you provided doesn't meet the required format.",
            ErrorType.TRANSLATION_ERROR: "I had trouble processing your translation request.",
            ErrorType.SYSTEM_ERROR: "I'm experiencing some internal technical difficulties.",
            ErrorType.NETWORK_ERROR: "I'm having trouble connecting to the translation services.",
            ErrorType.TIMEOUT_ERROR: "The operation took longer than expected and timed out.",
            ErrorType.CONTEXT_ERROR: "I'm having trouble accessing our conversation history.",
            ErrorType.RESOURCE_ERROR: "The system is currently under heavy load.",
            ErrorType.AUTHENTICATION_ERROR: "There's an issue with accessing the required services.",
            ErrorType.UNKNOWN_ERROR: "I encountered an unexpected issue."
        }
        
        base_explanation = explanations.get(error_type, "Something unexpected happened.")
        
        # Add operation-specific context if available
        if operation_context:
            operation_type = operation_context.get('operation_type', '')
            if operation_type:
                base_explanation += f" This happened while I was trying to {operation_type.replace('_', ' ')}."
        
        return base_explanation
    
    def _generate_contextual_help(self, classification: ErrorClassification,
                                context: ConversationContext) -> Optional[str]:
        """Generate contextual help based on conversation history and error pattern"""
        # Check for repeated errors
        recent_errors = [interaction for interaction in context.get_recent_interactions(5)
                        if interaction.error_occurred]
        
        if len(recent_errors) >= 2:
            return ("I notice you've encountered a few issues recently. "
                   "Would you like me to explain how to use a specific feature, "
                   "or would you prefer to start with a simpler example?")
        
        # Suggest help based on error type and user experience
        if classification.error_type == ErrorType.USER_INPUT_ERROR and len(context.conversation_history) < 3:
            return ("Since you're just getting started, feel free to ask me 'What can you do?' "
                   "if you'd like to learn about all my capabilities.")
        
        # Suggest alternative approaches based on successful past interactions
        successful_translations = context.get_successful_translations()
        if successful_translations:
            last_successful = successful_translations[-1]
            if last_successful.translation_result:
                input_type = last_successful.translation_result.input_type
                return (f"I notice your last successful translation used {input_type.value} input. "
                       f"Would you like to try that approach again?")
        
        return None
    
    def _generate_fallback_error_response(self, error_message: str) -> str:
        """Generate a basic fallback response when error handler fails"""
        return (f"I apologize, but I encountered an unexpected issue: {error_message}. "
               f"Please try again, and if the problem continues, "
               f"you might want to start a new conversation or try a simpler request.")
    
    def _log_error(self, error: Exception, classification: ErrorClassification,
                  context: ConversationContext, operation_context: Optional[Dict[str, Any]] = None):
        """Log error details for monitoring and debugging"""
        log_data = {
            'error_type': classification.error_type.value,
            'severity': classification.severity.value,
            'is_recoverable': classification.is_recoverable,
            'user_actionable': classification.user_actionable,
            'session_id': context.session_id,
            'user_id': context.user_id,
            'error_count_in_session': context.error_count,
            'operation_context': operation_context
        }
        
        if classification.severity in [ErrorSeverity.HIGH, ErrorSeverity.CRITICAL]:
            self.logger.error(f"High severity error: {error}", extra=log_data, exc_info=True)
        elif classification.severity == ErrorSeverity.MEDIUM:
            self.logger.warning(f"Medium severity error: {error}", extra=log_data)
        else:
            self.logger.info(f"Low severity error: {error}", extra=log_data)
    
    def get_error_recovery_suggestions(self, error_type: ErrorType, 
                                     context: ConversationContext) -> List[str]:
        """
        Get specific error recovery suggestions based on error type and context
        
        Args:
            error_type: The type of error that occurred
            context: Current conversation context
        
        Returns:
            List[str]: List of recovery suggestions
        """
        return self.suggest_fallback_strategies(error_type, context)
    
    def format_error_for_user(self, error: Exception, context: ConversationContext,
                            include_technical_details: bool = False) -> str:
        """
        Format an error for user display with conversational tone
        
        Args:
            error: The exception to format
            context: Current conversation context
            include_technical_details: Whether to include technical error details
        
        Returns:
            str: Formatted error message
        """
        classification = self.classify_error(error)
        response = self.generate_error_response(error, classification, context)
        
        if include_technical_details and classification.technical_details:
            response += f"\n\n*Technical details: {classification.technical_details}*"
        
        return response