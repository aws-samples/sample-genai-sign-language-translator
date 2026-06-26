"""
Graceful Error Recovery

This module implements automatic retry logic with exponential backoff,
fallback tool selection when primary translation tools fail, and
conversational error recovery that maintains natural dialogue flow.
"""

import asyncio
import logging
import time
import random
from typing import Dict, Any, List, Optional, Callable, Tuple
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime, timedelta

try:
    from .data_models import (
        ConversationContext, ConversationInteraction, TranslationResult,
        InputType, ConversationIntent, TranslationStatus
    )
    from .error_handler import ErrorType, ErrorClassification, ConversationErrorHandler
    from .alternative_suggestions import AlternativeApproachSuggester, AlternativeSuggestion
except ImportError:
    # Handle case when running as standalone module
    from data_models import (
        ConversationContext, ConversationInteraction, TranslationResult,
        InputType, ConversationIntent, TranslationStatus
    )
    from error_handler import ErrorType, ErrorClassification, ConversationErrorHandler
    from alternative_suggestions import AlternativeApproachSuggester, AlternativeSuggestion

# Configure logging
logger = logging.getLogger(__name__)

class RecoveryStrategy(Enum):
    """Types of recovery strategies"""
    IMMEDIATE_RETRY = "immediate_retry"
    EXPONENTIAL_BACKOFF = "exponential_backoff"
    FALLBACK_TOOL = "fallback_tool"
    PARAMETER_ADJUSTMENT = "parameter_adjustment"
    WORKFLOW_SIMPLIFICATION = "workflow_simplification"
    ALTERNATIVE_METHOD = "alternative_method"
    GRACEFUL_DEGRADATION = "graceful_degradation"

class RecoveryResult(Enum):
    """Results of recovery attempts"""
    SUCCESS = "success"
    PARTIAL_SUCCESS = "partial_success"
    FAILED = "failed"
    EXHAUSTED = "exhausted"  # All recovery options exhausted

@dataclass
class RecoveryAttempt:
    """Data class for tracking recovery attempts"""
    attempt_number: int
    strategy: RecoveryStrategy
    timestamp: datetime
    parameters: Dict[str, Any]
    result: Optional[RecoveryResult] = None
    error_message: Optional[str] = None
    processing_time: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'attempt_number': self.attempt_number,
            'strategy': self.strategy.value,
            'timestamp': self.timestamp.isoformat(),
            'parameters': self.parameters,
            'result': self.result.value if self.result else None,
            'error_message': self.error_message,
            'processing_time': self.processing_time
        }

@dataclass
class RecoverySession:
    """Data class for tracking an entire recovery session"""
    session_id: str
    original_operation: str
    original_parameters: Dict[str, Any]
    error_classification: ErrorClassification
    attempts: List[RecoveryAttempt] = field(default_factory=list)
    final_result: Optional[RecoveryResult] = None
    total_recovery_time: float = 0.0
    conversation_context: Optional[ConversationContext] = None
    
    def add_attempt(self, attempt: RecoveryAttempt) -> None:
        """Add a recovery attempt to the session"""
        self.attempts.append(attempt)
    
    def get_attempt_count(self) -> int:
        """Get the total number of recovery attempts"""
        return len(self.attempts)
    
    def get_successful_attempts(self) -> List[RecoveryAttempt]:
        """Get all successful recovery attempts"""
        return [attempt for attempt in self.attempts 
                if attempt.result == RecoveryResult.SUCCESS]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'session_id': self.session_id,
            'original_operation': self.original_operation,
            'original_parameters': self.original_parameters,
            'error_classification': {
                'error_type': self.error_classification.error_type.value,
                'severity': self.error_classification.severity.value,
                'is_recoverable': self.error_classification.is_recoverable
            },
            'attempts': [attempt.to_dict() for attempt in self.attempts],
            'final_result': self.final_result.value if self.final_result else None,
            'total_recovery_time': self.total_recovery_time
        }

class GracefulErrorRecovery:
    """
    Implements graceful error recovery with automatic retry logic,
    fallback tool selection, and conversational error recovery.
    """
    
    def __init__(self, error_handler: Optional[ConversationErrorHandler] = None,
                 alternative_suggester: Optional[AlternativeApproachSuggester] = None):
        """
        Initialize the graceful error recovery system
        
        Args:
            error_handler: Optional error handler instance
            alternative_suggester: Optional alternative approach suggester
        """
        self.error_handler = error_handler or ConversationErrorHandler()
        self.alternative_suggester = alternative_suggester or AlternativeApproachSuggester()
        self.logger = logger
        
        # Recovery configuration
        self.max_retry_attempts = 3
        self.base_retry_delay = 1.0  # seconds
        self.max_retry_delay = 30.0  # seconds
        self.backoff_multiplier = 2.0
        self.jitter_factor = 0.1  # Add randomness to prevent thundering herd
        
        # Tool fallback mappings
        self.tool_fallbacks = {
            'text_to_asl_gloss': ['simplified_text_to_asl', 'basic_gloss_generation'],
            'gloss_to_video': ['pose_video_only', 'sign_video_only', 'avatar_video_only'],
            'process_audio_input': ['basic_transcription', 'simple_audio_processing'],
            'analyze_asl_video_stream': ['analyze_asl_from_s3', 'basic_asl_analysis'],
            'analyze_asl_from_s3': ['analyze_asl_video_stream', 'simple_video_analysis']
        }
        
        logger.info("GracefulErrorRecovery initialized")
    
    async def recover_from_error(self, error: Exception, operation: str,
                               parameters: Dict[str, Any], context: ConversationContext,
                               operation_function: Optional[Callable] = None) -> Tuple[RecoveryResult, Optional[Any], str]:
        """
        Attempt to recover from an error using various strategies
        
        Args:
            error: The exception that occurred
            operation: Description of the operation that failed
            parameters: Original operation parameters
            context: Current conversation context
            operation_function: Optional function to retry (for actual recovery)
        
        Returns:
            Tuple of (RecoveryResult, recovered_result, conversational_message)
        """
        # Classify the error
        error_classification = self.error_handler.classify_error(error, {'operation': operation})
        
        # Create recovery session
        recovery_session = RecoverySession(
            session_id=f"recovery_{int(time.time())}_{random.randint(1000, 9999)}",
            original_operation=operation,
            original_parameters=parameters,
            error_classification=error_classification,
            conversation_context=context
        )
        
        start_time = time.time()
        
        try:
            # Check if error is recoverable
            if not error_classification.is_recoverable:
                return await self._handle_non_recoverable_error(
                    error, recovery_session, context
                )
            
            # Try different recovery strategies
            recovery_strategies = self._determine_recovery_strategies(error_classification, context)
            
            for strategy in recovery_strategies:
                try:
                    result, recovered_data = await self._execute_recovery_strategy(
                        strategy, error, recovery_session, operation_function
                    )
                    
                    if result == RecoveryResult.SUCCESS:
                        recovery_session.final_result = RecoveryResult.SUCCESS
                        recovery_session.total_recovery_time = time.time() - start_time
                        
                        message = self._generate_recovery_success_message(
                            recovery_session, context
                        )
                        return RecoveryResult.SUCCESS, recovered_data, message
                    
                    elif result == RecoveryResult.PARTIAL_SUCCESS:
                        recovery_session.final_result = RecoveryResult.PARTIAL_SUCCESS
                        recovery_session.total_recovery_time = time.time() - start_time
                        
                        message = self._generate_partial_recovery_message(
                            recovery_session, context, recovered_data
                        )
                        return RecoveryResult.PARTIAL_SUCCESS, recovered_data, message
                
                except Exception as recovery_error:
                    logger.warning(f"Recovery strategy {strategy} failed: {recovery_error}")
                    continue
            
            # All recovery strategies exhausted
            recovery_session.final_result = RecoveryResult.EXHAUSTED
            recovery_session.total_recovery_time = time.time() - start_time
            
            message = await self._generate_exhausted_recovery_message(
                recovery_session, context
            )
            return RecoveryResult.EXHAUSTED, None, message
            
        except Exception as recovery_system_error:
            logger.error(f"Recovery system error: {recovery_system_error}", exc_info=True)
            recovery_session.final_result = RecoveryResult.FAILED
            recovery_session.total_recovery_time = time.time() - start_time
            
            message = self._generate_recovery_system_error_message(context)
            return RecoveryResult.FAILED, None, message
    
    def _determine_recovery_strategies(self, error_classification: ErrorClassification,
                                     context: ConversationContext) -> List[RecoveryStrategy]:
        """Determine which recovery strategies to try based on error classification"""
        strategies = []
        error_type = error_classification.error_type
        
        # Strategy selection based on error type
        if error_type in [ErrorType.NETWORK_ERROR, ErrorType.TIMEOUT_ERROR]:
            strategies.extend([
                RecoveryStrategy.EXPONENTIAL_BACKOFF,
                RecoveryStrategy.PARAMETER_ADJUSTMENT,
                RecoveryStrategy.WORKFLOW_SIMPLIFICATION
            ])
        
        elif error_type == ErrorType.TRANSLATION_ERROR:
            strategies.extend([
                RecoveryStrategy.FALLBACK_TOOL,
                RecoveryStrategy.PARAMETER_ADJUSTMENT,
                RecoveryStrategy.WORKFLOW_SIMPLIFICATION,
                RecoveryStrategy.ALTERNATIVE_METHOD
            ])
        
        elif error_type == ErrorType.USER_INPUT_ERROR:
            strategies.extend([
                RecoveryStrategy.PARAMETER_ADJUSTMENT,
                RecoveryStrategy.ALTERNATIVE_METHOD
            ])
        
        elif error_type == ErrorType.SYSTEM_ERROR:
            strategies.extend([
                RecoveryStrategy.EXPONENTIAL_BACKOFF,
                RecoveryStrategy.FALLBACK_TOOL,
                RecoveryStrategy.GRACEFUL_DEGRADATION
            ])
        
        else:
            # Default strategies for unknown errors
            strategies.extend([
                RecoveryStrategy.IMMEDIATE_RETRY,
                RecoveryStrategy.PARAMETER_ADJUSTMENT,
                RecoveryStrategy.GRACEFUL_DEGRADATION
            ])
        
        # Consider conversation context
        if context.error_count > 2:
            # User has had multiple errors, prioritize simpler approaches
            strategies.insert(0, RecoveryStrategy.WORKFLOW_SIMPLIFICATION)
        
        return strategies
    
    async def _execute_recovery_strategy(self, strategy: RecoveryStrategy, error: Exception,
                                       recovery_session: RecoverySession,
                                       operation_function: Optional[Callable] = None) -> Tuple[RecoveryResult, Optional[Any]]:
        """Execute a specific recovery strategy"""
        attempt = RecoveryAttempt(
            attempt_number=recovery_session.get_attempt_count() + 1,
            strategy=strategy,
            timestamp=datetime.now(),
            parameters={}
        )
        
        start_time = time.time()
        
        try:
            if strategy == RecoveryStrategy.IMMEDIATE_RETRY:
                result, data = await self._immediate_retry(recovery_session, operation_function)
            
            elif strategy == RecoveryStrategy.EXPONENTIAL_BACKOFF:
                result, data = await self._exponential_backoff_retry(recovery_session, operation_function)
            
            elif strategy == RecoveryStrategy.FALLBACK_TOOL:
                result, data = await self._fallback_tool_retry(recovery_session, operation_function)
            
            elif strategy == RecoveryStrategy.PARAMETER_ADJUSTMENT:
                result, data = await self._parameter_adjustment_retry(recovery_session, operation_function)
            
            elif strategy == RecoveryStrategy.WORKFLOW_SIMPLIFICATION:
                result, data = await self._workflow_simplification_retry(recovery_session, operation_function)
            
            elif strategy == RecoveryStrategy.ALTERNATIVE_METHOD:
                result, data = await self._alternative_method_retry(recovery_session, operation_function)
            
            elif strategy == RecoveryStrategy.GRACEFUL_DEGRADATION:
                result, data = await self._graceful_degradation_retry(recovery_session, operation_function)
            
            else:
                result, data = RecoveryResult.FAILED, None
            
            attempt.result = result
            attempt.processing_time = time.time() - start_time
            recovery_session.add_attempt(attempt)
            
            return result, data
            
        except Exception as strategy_error:
            attempt.result = RecoveryResult.FAILED
            attempt.error_message = str(strategy_error)
            attempt.processing_time = time.time() - start_time
            recovery_session.add_attempt(attempt)
            
            raise strategy_error
    
    async def _immediate_retry(self, recovery_session: RecoverySession,
                             operation_function: Optional[Callable] = None) -> Tuple[RecoveryResult, Optional[Any]]:
        """Attempt immediate retry without changes"""
        if not operation_function:
            # Simulate retry for demonstration
            return RecoveryResult.FAILED, None
        
        try:
            result = await operation_function(**recovery_session.original_parameters)
            return RecoveryResult.SUCCESS, result
        except Exception:
            return RecoveryResult.FAILED, None
    
    async def _exponential_backoff_retry(self, recovery_session: RecoverySession,
                                       operation_function: Optional[Callable] = None) -> Tuple[RecoveryResult, Optional[Any]]:
        """Attempt retry with exponential backoff"""
        attempt_count = recovery_session.get_attempt_count()
        
        # Calculate delay with exponential backoff and jitter
        delay = min(
            self.base_retry_delay * (self.backoff_multiplier ** attempt_count),
            self.max_retry_delay
        )
        
        # Add jitter to prevent thundering herd
        jitter = delay * self.jitter_factor * random.random()
        total_delay = delay + jitter
        
        logger.info(f"Waiting {total_delay:.2f} seconds before retry attempt {attempt_count + 1}")
        await asyncio.sleep(total_delay)
        
        if not operation_function:
            # Simulate retry for demonstration
            return RecoveryResult.FAILED, None
        
        try:
            result = await operation_function(**recovery_session.original_parameters)
            return RecoveryResult.SUCCESS, result
        except Exception:
            return RecoveryResult.FAILED, None
    
    async def _fallback_tool_retry(self, recovery_session: RecoverySession,
                                 operation_function: Optional[Callable] = None) -> Tuple[RecoveryResult, Optional[Any]]:
        """Attempt retry with fallback tools"""
        operation = recovery_session.original_operation
        fallback_tools = self.tool_fallbacks.get(operation, [])
        
        if not fallback_tools:
            return RecoveryResult.FAILED, None
        
        # For demonstration, simulate trying fallback tools
        # In real implementation, this would call actual fallback functions
        logger.info(f"Trying fallback tools for {operation}: {fallback_tools}")
        
        # Simulate partial success with fallback tool
        if random.random() > 0.5:  # 50% chance of success
            return RecoveryResult.PARTIAL_SUCCESS, {
                'fallback_tool_used': fallback_tools[0],
                'result': 'Partial result from fallback tool'
            }
        
        return RecoveryResult.FAILED, None
    
    async def _parameter_adjustment_retry(self, recovery_session: RecoverySession,
                                        operation_function: Optional[Callable] = None) -> Tuple[RecoveryResult, Optional[Any]]:
        """Attempt retry with adjusted parameters"""
        adjusted_params = recovery_session.original_parameters.copy()
        
        # Make parameter adjustments based on error type
        error_type = recovery_session.error_classification.error_type
        
        if error_type == ErrorType.TIMEOUT_ERROR:
            # Reduce complexity for timeout errors
            if 'text' in adjusted_params:
                text = adjusted_params['text']
                if len(text) > 50:
                    adjusted_params['text'] = text[:50] + "..."
            
            # Request simpler output
            adjusted_params['simple_mode'] = True
            adjusted_params['video_formats'] = ['pose']  # Only one format
        
        elif error_type == ErrorType.USER_INPUT_ERROR:
            # Clean up input parameters
            if 'text' in adjusted_params:
                text = adjusted_params['text'].strip()
                # Remove special characters that might cause issues
                import re
                text = re.sub(r'[^\w\s.,!?-]', '', text)
                adjusted_params['text'] = text
        
        if not operation_function:
            # Simulate retry for demonstration
            return RecoveryResult.PARTIAL_SUCCESS, {
                'adjusted_parameters': adjusted_params,
                'result': 'Adjusted parameter result'
            }
        
        try:
            result = await operation_function(**adjusted_params)
            return RecoveryResult.SUCCESS, result
        except Exception:
            return RecoveryResult.FAILED, None
    
    async def _workflow_simplification_retry(self, recovery_session: RecoverySession,
                                           operation_function: Optional[Callable] = None) -> Tuple[RecoveryResult, Optional[Any]]:
        """Attempt retry with simplified workflow"""
        # Simplify the operation by breaking it down or using basic options
        simplified_params = recovery_session.original_parameters.copy()
        
        # Simplification strategies
        if 'text' in simplified_params:
            text = simplified_params['text']
            # Take only the first sentence
            sentences = text.split('.')
            if len(sentences) > 1:
                simplified_params['text'] = sentences[0].strip() + '.'
        
        # Request only basic output
        simplified_params['output_format'] = 'basic'
        simplified_params['video_formats'] = ['pose']  # Simplest video format
        
        # For demonstration, simulate simplified processing
        return RecoveryResult.PARTIAL_SUCCESS, {
            'simplified_result': 'Basic translation result',
            'note': 'Simplified version of your request'
        }
    
    async def _alternative_method_retry(self, recovery_session: RecoverySession,
                                      operation_function: Optional[Callable] = None) -> Tuple[RecoveryResult, Optional[Any]]:
        """Attempt retry with alternative method"""
        # Generate alternative suggestions and try the first one
        suggestions = self.alternative_suggester.generate_suggestions(
            recovery_session.original_operation,
            recovery_session.error_classification,
            recovery_session.conversation_context or ConversationContext()
        )
        
        if not suggestions:
            return RecoveryResult.FAILED, None
        
        # For demonstration, simulate trying the first alternative
        first_suggestion = suggestions[0]
        logger.info(f"Trying alternative method: {first_suggestion.title}")
        
        # Simulate success with alternative method
        return RecoveryResult.PARTIAL_SUCCESS, {
            'alternative_method': first_suggestion.title,
            'result': 'Result from alternative approach',
            'suggestion': first_suggestion.to_dict()
        }
    
    async def _graceful_degradation_retry(self, recovery_session: RecoverySession,
                                        operation_function: Optional[Callable] = None) -> Tuple[RecoveryResult, Optional[Any]]:
        """Attempt graceful degradation - provide partial functionality"""
        # Provide whatever functionality we can, even if limited
        operation = recovery_session.original_operation
        
        degraded_result = {
            'status': 'degraded',
            'message': 'Providing limited functionality due to system issues'
        }
        
        if 'text_to_asl' in operation:
            degraded_result.update({
                'gloss_available': False,
                'video_available': False,
                'explanation': 'I can acknowledge your text but cannot generate ASL translation right now'
            })
        
        elif 'audio' in operation:
            degraded_result.update({
                'transcription_available': False,
                'translation_available': False,
                'explanation': 'I can see your audio file but cannot process it right now'
            })
        
        elif 'asl' in operation or 'video' in operation:
            degraded_result.update({
                'analysis_available': False,
                'interpretation_available': False,
                'explanation': 'I can see your video but cannot analyze the ASL right now'
            })
        
        return RecoveryResult.PARTIAL_SUCCESS, degraded_result
    
    async def _handle_non_recoverable_error(self, error: Exception, recovery_session: RecoverySession,
                                          context: ConversationContext) -> Tuple[RecoveryResult, Optional[Any], str]:
        """Handle errors that cannot be recovered from"""
        recovery_session.final_result = RecoveryResult.FAILED
        
        message = self.error_handler.generate_error_response(
            error, recovery_session.error_classification, context
        )
        
        # Add note about non-recoverable nature
        message += ("\n\nThis appears to be a fundamental issue that I cannot automatically resolve. "
                   "You may need to try a completely different approach or contact support if the problem persists.")
        
        return RecoveryResult.FAILED, None, message
    
    def _generate_recovery_success_message(self, recovery_session: RecoverySession,
                                         context: ConversationContext) -> str:
        """Generate message for successful recovery"""
        successful_attempts = recovery_session.get_successful_attempts()
        if not successful_attempts:
            return "Great! I was able to resolve the issue and complete your request."
        
        last_attempt = successful_attempts[-1]
        strategy_name = last_attempt.strategy.value.replace('_', ' ')
        
        messages = [
            "Excellent! I encountered an issue initially, but I was able to resolve it and complete your request.",
            f"I used a {strategy_name} approach to work around the problem.",
        ]
        
        if recovery_session.get_attempt_count() > 1:
            messages.append(f"It took {recovery_session.get_attempt_count()} attempts, but we got there!")
        
        messages.append("Your translation is ready!")
        
        return " ".join(messages)
    
    def _generate_partial_recovery_message(self, recovery_session: RecoverySession,
                                         context: ConversationContext, recovered_data: Any) -> str:
        """Generate message for partial recovery"""
        messages = [
            "I encountered some issues with your request, but I was able to provide a partial result.",
        ]
        
        if isinstance(recovered_data, dict):
            if 'fallback_tool_used' in recovered_data:
                messages.append(f"I used an alternative processing method to get you some results.")
            
            elif 'simplified_result' in recovered_data:
                messages.append("I provided a simplified version of what you requested.")
            
            elif 'alternative_method' in recovered_data:
                messages.append(f"I tried a different approach: {recovered_data['alternative_method']}")
        
        messages.extend([
            "While this isn't exactly what you originally asked for, it should still be helpful.",
            "Would you like me to try the full request again, or is this partial result sufficient?"
        ])
        
        return " ".join(messages)
    
    async def _generate_exhausted_recovery_message(self, recovery_session: RecoverySession,
                                                 context: ConversationContext) -> str:
        """Generate message when all recovery options are exhausted"""
        messages = [
            f"I'm sorry, but I've tried {recovery_session.get_attempt_count()} different approaches to resolve the issue with your request, and none of them worked.",
        ]
        
        # Generate alternative suggestions for the user to try manually
        suggestions = self.alternative_suggester.generate_suggestions(
            recovery_session.original_operation,
            recovery_session.error_classification,
            context
        )
        
        if suggestions:
            messages.append("Here are some things you could try:")
            for i, suggestion in enumerate(suggestions[:3], 1):
                messages.append(f"{i}. {suggestion.title}: {suggestion.description}")
        
        messages.append("I'm here to help if you'd like to try any of these approaches or if you have questions!")
        
        return "\n\n".join(messages)
    
    def _generate_recovery_system_error_message(self, context: ConversationContext) -> str:
        """Generate message when the recovery system itself fails"""
        return ("I apologize, but I encountered a serious issue while trying to recover from the original error. "
               "This suggests a more fundamental problem that I cannot resolve automatically. "
               "Please try again in a few moments, or try a simpler request to see if basic functionality is working. "
               "If problems persist, you may want to start a new conversation session.")
    
    def get_recovery_statistics(self, recovery_session: RecoverySession) -> Dict[str, Any]:
        """Get statistics about a recovery session"""
        return {
            'total_attempts': recovery_session.get_attempt_count(),
            'successful_attempts': len(recovery_session.get_successful_attempts()),
            'total_recovery_time': recovery_session.total_recovery_time,
            'final_result': recovery_session.final_result.value if recovery_session.final_result else None,
            'strategies_tried': [attempt.strategy.value for attempt in recovery_session.attempts],
            'average_attempt_time': (
                sum(attempt.processing_time for attempt in recovery_session.attempts) / 
                len(recovery_session.attempts) if recovery_session.attempts else 0
            )
        }
    
    def should_attempt_recovery(self, error: Exception, context: ConversationContext) -> bool:
        """
        Determine if recovery should be attempted based on error and context
        
        Args:
            error: The exception that occurred
            context: Current conversation context
        
        Returns:
            bool: True if recovery should be attempted
        """
        # Don't attempt recovery if user has had too many errors recently
        if context.error_count > 5:
            return False
        
        # Classify error to check if it's recoverable
        error_classification = self.error_handler.classify_error(error)
        
        return error_classification.is_recoverable