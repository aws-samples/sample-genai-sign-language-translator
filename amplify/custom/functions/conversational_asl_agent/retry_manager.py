"""
Retry Manager

This module provides retry functionality for failed translations with conversational guidance,
parameter modification capabilities for retry attempts, and alternative tool selection.
"""

import logging
import time
import uuid
from typing import Dict, Any, List, Optional, Callable, Tuple
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass, field

try:
    from .data_models import (
        ConversationContext, 
        ConversationIntent, 
        IntentResult,
        TranslationResult,
        TranslationStatus,
        InputType,
        OperationStatus
    )
    from .memory_manager import ConversationMemoryManager
    from .error_handler import ErrorType, ErrorClassification, ConversationErrorHandler
except ImportError:
    # Handle case when running as standalone module
    from data_models import (
        ConversationContext, 
        ConversationIntent, 
        IntentResult,
        TranslationResult,
        TranslationStatus,
        InputType,
        OperationStatus
    )
    from memory_manager import ConversationMemoryManager
    from error_handler import ErrorType, ErrorClassification, ConversationErrorHandler

logger = logging.getLogger(__name__)

class RetryStrategy(Enum):
    """Enumeration of retry strategies"""
    IMMEDIATE = "immediate"           # Retry immediately with same parameters
    EXPONENTIAL_BACKOFF = "exponential_backoff"  # Retry with increasing delays
    ALTERNATIVE_TOOL = "alternative_tool"        # Try different tool/approach
    PARAMETER_MODIFICATION = "parameter_modification"  # Modify parameters and retry
    USER_GUIDED = "user_guided"       # Wait for user input before retry
    FALLBACK_CHAIN = "fallback_chain" # Try multiple fallback approaches

class RetryReason(Enum):
    """Enumeration of retry reasons"""
    TRANSLATION_FAILED = "translation_failed"
    TIMEOUT_ERROR = "timeout_error"
    NETWORK_ERROR = "network_error"
    SYSTEM_ERROR = "system_error"
    USER_REQUESTED = "user_requested"
    PARAMETER_ADJUSTMENT = "parameter_adjustment"
    ALTERNATIVE_APPROACH = "alternative_approach"

@dataclass
class RetryAttempt:
    """Data class representing a retry attempt"""
    attempt_number: int
    timestamp: datetime
    strategy: RetryStrategy
    reason: RetryReason
    original_parameters: Dict[str, Any]
    modified_parameters: Dict[str, Any]
    result: Optional[TranslationResult] = None
    error_message: Optional[str] = None
    processing_time: float = 0.0
    success: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'attempt_number': self.attempt_number,
            'timestamp': self.timestamp.isoformat(),
            'strategy': self.strategy.value,
            'reason': self.reason.value,
            'original_parameters': self.original_parameters,
            'modified_parameters': self.modified_parameters,
            'result': self.result.to_dict() if self.result else None,
            'error_message': self.error_message,
            'processing_time': self.processing_time,
            'success': self.success
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'RetryAttempt':
        """Create from dictionary for deserialization"""
        data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        data['strategy'] = RetryStrategy(data['strategy'])
        data['reason'] = RetryReason(data['reason'])
        if data.get('result'):
            data['result'] = TranslationResult.from_dict(data['result'])
        return cls(**data)

@dataclass
class RetrySession:
    """Data class representing a retry session for a specific operation"""
    session_id: str
    operation_id: str
    original_intent: ConversationIntent
    original_parameters: Dict[str, Any]
    original_error: Optional[str] = None
    attempts: List[RetryAttempt] = field(default_factory=list)
    max_attempts: int = 3
    current_strategy: RetryStrategy = RetryStrategy.IMMEDIATE
    created_at: datetime = field(default_factory=datetime.now)
    last_attempt_at: Optional[datetime] = None
    is_active: bool = True
    final_result: Optional[TranslationResult] = None
    
    def add_attempt(self, attempt: RetryAttempt) -> None:
        """Add a retry attempt to the session"""
        self.attempts.append(attempt)
        self.last_attempt_at = attempt.timestamp
        if attempt.success and attempt.result:
            self.final_result = attempt.result
            self.is_active = False
    
    def get_attempt_count(self) -> int:
        """Get the number of retry attempts made"""
        return len(self.attempts)
    
    def has_attempts_remaining(self) -> bool:
        """Check if there are retry attempts remaining"""
        return self.get_attempt_count() < self.max_attempts and self.is_active
    
    def get_last_attempt(self) -> Optional[RetryAttempt]:
        """Get the most recent retry attempt"""
        return self.attempts[-1] if self.attempts else None
    
    def get_successful_attempts(self) -> List[RetryAttempt]:
        """Get all successful retry attempts"""
        return [attempt for attempt in self.attempts if attempt.success]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'session_id': self.session_id,
            'operation_id': self.operation_id,
            'original_intent': self.original_intent.value,
            'original_parameters': self.original_parameters,
            'original_error': self.original_error,
            'attempts': [attempt.to_dict() for attempt in self.attempts],
            'max_attempts': self.max_attempts,
            'current_strategy': self.current_strategy.value,
            'created_at': self.created_at.isoformat(),
            'last_attempt_at': self.last_attempt_at.isoformat() if self.last_attempt_at else None,
            'is_active': self.is_active,
            'final_result': self.final_result.to_dict() if self.final_result else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'RetrySession':
        """Create from dictionary for deserialization"""
        data['original_intent'] = ConversationIntent(data['original_intent'])
        data['current_strategy'] = RetryStrategy(data['current_strategy'])
        data['created_at'] = datetime.fromisoformat(data['created_at'])
        if data.get('last_attempt_at'):
            data['last_attempt_at'] = datetime.fromisoformat(data['last_attempt_at'])
        if data.get('attempts'):
            data['attempts'] = [RetryAttempt.from_dict(attempt_data) for attempt_data in data['attempts']]
        if data.get('final_result'):
            data['final_result'] = TranslationResult.from_dict(data['final_result'])
        return cls(**data)

class RetryManager:
    """
    Manages retry functionality for failed translations with conversational guidance
    
    This class provides retry logic for failed translations with user-friendly explanations,
    parameter modification capabilities for retry attempts, and alternative tool selection.
    """
    
    def __init__(self, memory_manager: Optional[ConversationMemoryManager] = None):
        """Initialize the retry manager"""
        self.memory_manager = memory_manager or ConversationMemoryManager()
        self.error_handler = ConversationErrorHandler()
        
        # Retry configuration
        self.default_max_attempts = 3
        self.exponential_backoff_base = 2.0
        self.max_backoff_delay = 60.0  # Maximum delay in seconds
        
        # Strategy selection rules
        self.strategy_rules = {
            ErrorType.NETWORK_ERROR: [RetryStrategy.EXPONENTIAL_BACKOFF, RetryStrategy.ALTERNATIVE_TOOL],
            ErrorType.TIMEOUT_ERROR: [RetryStrategy.EXPONENTIAL_BACKOFF, RetryStrategy.PARAMETER_MODIFICATION],
            ErrorType.TRANSLATION_ERROR: [RetryStrategy.PARAMETER_MODIFICATION, RetryStrategy.ALTERNATIVE_TOOL],
            ErrorType.SYSTEM_ERROR: [RetryStrategy.EXPONENTIAL_BACKOFF, RetryStrategy.ALTERNATIVE_TOOL],
            ErrorType.USER_INPUT_ERROR: [RetryStrategy.USER_GUIDED, RetryStrategy.PARAMETER_MODIFICATION],
            ErrorType.RESOURCE_ERROR: [RetryStrategy.EXPONENTIAL_BACKOFF, RetryStrategy.PARAMETER_MODIFICATION]
        }
        
        logger.info("RetryManager initialized with conversational guidance")
    
    def create_retry_session(self, operation_id: str, intent: ConversationIntent,
                           parameters: Dict[str, Any], error: Optional[Exception] = None,
                           context: Optional[ConversationContext] = None) -> RetrySession:
        """
        Create a new retry session for a failed operation
        
        Args:
            operation_id: Unique identifier for the operation
            intent: Original conversation intent
            parameters: Original operation parameters
            error: Optional error that caused the failure
            context: Optional conversation context
        
        Returns:
            RetrySession: New retry session
        """
        session_id = f"retry_{int(time.time())}_{str(uuid.uuid4())[:8]}"
        
        retry_session = RetrySession(
            session_id=session_id,
            operation_id=operation_id,
            original_intent=intent,
            original_parameters=parameters.copy(),
            original_error=str(error) if error else None,
            max_attempts=self.default_max_attempts
        )
        
        # Store retry session in memory
        if context and context.session_id:
            memory_key = f"retry_session:{context.session_id}:{session_id}"
            self.memory_manager.store_data(memory_key, retry_session.to_dict())
        
        logger.info(f"Created retry session {session_id} for operation {operation_id}")
        return retry_session
    
    def execute_retry(self, retry_session: RetrySession, context: ConversationContext,
                     orchestrator_callback: Callable[[IntentResult, ConversationContext], TranslationResult],
                     modified_parameters: Optional[Dict[str, Any]] = None,
                     strategy: Optional[RetryStrategy] = None) -> Tuple[TranslationResult, str]:
        """
        Execute a retry attempt with conversational guidance
        
        Args:
            retry_session: The retry session to execute
            context: Current conversation context
            orchestrator_callback: Callback to orchestrator for executing translation
            modified_parameters: Optional modified parameters for the retry
            strategy: Optional specific retry strategy to use
        
        Returns:
            Tuple[TranslationResult, str]: Translation result and conversational response
        """
        if not retry_session.has_attempts_remaining():
            return self._handle_max_attempts_reached(retry_session, context)
        
        # Determine retry strategy
        if strategy:
            retry_strategy = strategy
        else:
            retry_strategy = self._select_retry_strategy(retry_session, context)
        
        # Prepare parameters for retry
        retry_parameters = self._prepare_retry_parameters(
            retry_session, modified_parameters, retry_strategy
        )
        
        # Create retry attempt record
        attempt_number = retry_session.get_attempt_count() + 1
        retry_attempt = RetryAttempt(
            attempt_number=attempt_number,
            timestamp=datetime.now(),
            strategy=retry_strategy,
            reason=self._determine_retry_reason(retry_session, modified_parameters),
            original_parameters=retry_session.original_parameters.copy(),
            modified_parameters=retry_parameters.copy()
        )
        
        # Apply retry delay if needed
        delay = self._calculate_retry_delay(retry_strategy, attempt_number)
        if delay > 0:
            logger.info(f"Applying retry delay of {delay} seconds")
            time.sleep(delay)
        
        # Execute the retry
        start_time = time.time()
        try:
            # Create intent result for retry
            intent_result = IntentResult(
                intent=retry_session.original_intent,
                confidence=1.0,  # High confidence for retry
                parameters=retry_parameters,
                input_type=self._determine_input_type(retry_parameters),
                requires_context=True
            )
            
            # Execute translation through orchestrator
            result = orchestrator_callback(intent_result, context)
            
            # Record successful retry
            retry_attempt.result = result
            retry_attempt.success = result.success
            retry_attempt.processing_time = time.time() - start_time
            
            if not result.success:
                retry_attempt.error_message = result.error_message
            
        except Exception as e:
            # Record failed retry
            retry_attempt.error_message = str(e)
            retry_attempt.success = False
            retry_attempt.processing_time = time.time() - start_time
            
            # Create error result
            result = TranslationResult(
                input_text=retry_parameters.get('text', 'Retry attempt'),
                input_type=self._determine_input_type(retry_parameters),
                success=False,
                error_message=str(e),
                status=TranslationStatus.FAILED,
                processing_time=retry_attempt.processing_time
            )
            retry_attempt.result = result
        
        # Add attempt to session
        retry_session.add_attempt(retry_attempt)
        
        # Update retry session in memory
        if context.session_id:
            memory_key = f"retry_session:{context.session_id}:{retry_session.session_id}"
            self.memory_manager.store_data(memory_key, retry_session.to_dict())
        
        # Generate conversational response
        response = self._generate_retry_response(retry_attempt, retry_session, context)
        
        logger.info(f"Retry attempt {attempt_number} completed: success={retry_attempt.success}")
        return result, response
    
    def suggest_retry_modifications(self, retry_session: RetrySession, 
                                  context: ConversationContext) -> List[Dict[str, Any]]:
        """
        Suggest parameter modifications for retry attempts
        
        Args:
            retry_session: Current retry session
            context: Conversation context
        
        Returns:
            List[Dict[str, Any]]: List of suggested modifications
        """
        suggestions = []
        original_params = retry_session.original_parameters
        intent = retry_session.original_intent
        
        # Text-to-ASL modifications
        if intent == ConversationIntent.TEXT_TO_ASL:
            text = original_params.get('text', '')
            if text:
                # Suggest text simplification
                if len(text.split()) > 10:
                    suggestions.append({
                        'type': 'text_simplification',
                        'description': 'Break your text into shorter, simpler sentences',
                        'parameters': {'text': self._simplify_text(text)},
                        'explanation': 'Shorter sentences often translate more accurately to ASL'
                    })
                
                # Suggest removing special characters
                if any(char in text for char in '!@#$%^&*()[]{}|\\:";\'<>?,./'):
                    clean_text = self._clean_text(text)
                    suggestions.append({
                        'type': 'text_cleaning',
                        'description': 'Remove special characters that might cause issues',
                        'parameters': {'text': clean_text},
                        'explanation': 'Special characters can sometimes interfere with translation'
                    })
        
        # Audio-to-ASL modifications
        elif intent == ConversationIntent.AUDIO_TO_ASL:
            # Suggest different audio processing parameters
            suggestions.append({
                'type': 'audio_quality_adjustment',
                'description': 'Try with enhanced audio processing',
                'parameters': {**original_params, 'enhance_audio': True},
                'explanation': 'Enhanced processing can help with unclear audio'
            })
            
            suggestions.append({
                'type': 'transcription_model_change',
                'description': 'Use a different transcription model',
                'parameters': {**original_params, 'model_variant': 'enhanced'},
                'explanation': 'Different models work better for different types of speech'
            })
        
        # ASL-to-text modifications
        elif intent == ConversationIntent.ASL_TO_TEXT:
            # Suggest different analysis parameters
            suggestions.append({
                'type': 'analysis_sensitivity',
                'description': 'Adjust analysis sensitivity',
                'parameters': {**original_params, 'sensitivity': 'high'},
                'explanation': 'Higher sensitivity can catch more subtle sign movements'
            })
            
            suggestions.append({
                'type': 'frame_rate_adjustment',
                'description': 'Process more frames for better accuracy',
                'parameters': {**original_params, 'frame_rate': 'high'},
                'explanation': 'Processing more frames can improve sign recognition'
            })
        
        # Add general suggestions based on previous attempts
        if retry_session.attempts:
            last_attempt = retry_session.get_last_attempt()
            if last_attempt and last_attempt.strategy == RetryStrategy.IMMEDIATE:
                suggestions.append({
                    'type': 'wait_and_retry',
                    'description': 'Wait a moment before trying again',
                    'parameters': original_params,
                    'explanation': 'Sometimes a brief wait can help with temporary issues'
                })
        
        return suggestions[:4]  # Limit to 4 most relevant suggestions
    
    def get_alternative_tools(self, intent: ConversationIntent, 
                            failed_parameters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Get alternative tool suggestions for retry attempts
        
        Args:
            intent: Original conversation intent
            failed_parameters: Parameters that failed
        
        Returns:
            List[Dict[str, Any]]: List of alternative tool suggestions
        """
        alternatives = []
        
        if intent == ConversationIntent.TEXT_TO_ASL:
            # Suggest pose-only video generation if full video failed
            alternatives.append({
                'tool': 'pose_only_generation',
                'description': 'Generate pose-only video (faster, more reliable)',
                'parameters': {**failed_parameters, 'pose_only': True},
                'explanation': 'Pose-only videos are simpler and less likely to fail'
            })
            
            # Suggest breaking text into parts
            text = failed_parameters.get('text', '')
            if text and len(text.split()) > 5:
                sentences = text.split('.')
                if len(sentences) > 1:
                    alternatives.append({
                        'tool': 'sentence_by_sentence',
                        'description': 'Translate one sentence at a time',
                        'parameters': {'text': sentences[0].strip()},
                        'explanation': 'Translating shorter segments often works better'
                    })
        
        elif intent == ConversationIntent.AUDIO_TO_ASL:
            # Suggest manual text input if audio processing failed
            alternatives.append({
                'tool': 'manual_text_input',
                'description': 'Type the text instead of using audio',
                'parameters': {'text': '[Please type what you wanted to say]'},
                'explanation': 'Manual text input bypasses audio processing issues'
            })
            
            # Suggest different audio format
            alternatives.append({
                'tool': 'audio_format_conversion',
                'description': 'Try converting your audio to a different format',
                'parameters': failed_parameters,
                'explanation': 'Some audio formats work better than others'
            })
        
        elif intent == ConversationIntent.ASL_TO_TEXT:
            # Suggest different analysis approach
            if failed_parameters.get('stream_name'):
                alternatives.append({
                    'tool': 's3_upload_analysis',
                    'description': 'Upload your video file instead of using live stream',
                    'parameters': {'bucket_name': '[upload_bucket]', 'key_name': '[your_video]'},
                    'explanation': 'Uploaded videos can be analyzed more thoroughly'
                })
            elif failed_parameters.get('bucket_name'):
                alternatives.append({
                    'tool': 'stream_analysis',
                    'description': 'Try live stream analysis instead',
                    'parameters': {'stream_name': '[your_stream]'},
                    'explanation': 'Live stream analysis uses different processing methods'
                })
        
        return alternatives
    
    def get_retry_session(self, session_id: str, context: ConversationContext) -> Optional[RetrySession]:
        """
        Retrieve a retry session from memory
        
        Args:
            session_id: Retry session ID
            context: Conversation context
        
        Returns:
            RetrySession or None if not found
        """
        if not context.session_id:
            return None
        
        memory_key = f"retry_session:{context.session_id}:{session_id}"
        session_data = self.memory_manager.retrieve_data(memory_key)
        
        if session_data:
            return RetrySession.from_dict(session_data)
        
        return None
    
    def get_active_retry_sessions(self, context: ConversationContext) -> List[RetrySession]:
        """
        Get all active retry sessions for a conversation
        
        Args:
            context: Conversation context
        
        Returns:
            List[RetrySession]: List of active retry sessions
        """
        if not context.session_id:
            return []
        
        # Get all retry session keys for this conversation
        pattern = f"retry_session:{context.session_id}:*"
        session_keys = self.memory_manager.get_keys_by_pattern(pattern)
        
        active_sessions = []
        for key in session_keys:
            session_data = self.memory_manager.retrieve_data(key)
            if session_data:
                retry_session = RetrySession.from_dict(session_data)
                if retry_session.is_active:
                    active_sessions.append(retry_session)
        
        return active_sessions
    
    def _select_retry_strategy(self, retry_session: RetrySession, 
                             context: ConversationContext) -> RetryStrategy:
        """Select appropriate retry strategy based on error and context"""
        # Classify the original error if available
        if retry_session.original_error:
            try:
                error = Exception(retry_session.original_error)
                classification = self.error_handler.classify_error(error)
                error_type = classification.error_type
            except Exception:
                error_type = ErrorType.UNKNOWN_ERROR
        else:
            error_type = ErrorType.UNKNOWN_ERROR
        
        # Get strategies for this error type
        strategies = self.strategy_rules.get(error_type, [RetryStrategy.IMMEDIATE])
        
        # Select strategy based on attempt number
        attempt_number = retry_session.get_attempt_count()
        if attempt_number < len(strategies):
            return strategies[attempt_number]
        else:
            return strategies[-1]  # Use last strategy for remaining attempts
    
    def _prepare_retry_parameters(self, retry_session: RetrySession,
                                modified_parameters: Optional[Dict[str, Any]],
                                strategy: RetryStrategy) -> Dict[str, Any]:
        """Prepare parameters for retry based on strategy"""
        base_parameters = retry_session.original_parameters.copy()
        
        # Apply user modifications first
        if modified_parameters:
            base_parameters.update(modified_parameters)
        
        # Apply strategy-specific modifications
        if strategy == RetryStrategy.PARAMETER_MODIFICATION:
            # Apply automatic parameter modifications
            if retry_session.original_intent == ConversationIntent.TEXT_TO_ASL:
                text = base_parameters.get('text', '')
                if text and len(text.split()) > 10:
                    # Simplify text for retry
                    base_parameters['text'] = self._simplify_text(text)
            
            elif retry_session.original_intent == ConversationIntent.AUDIO_TO_ASL:
                # Add audio enhancement parameters
                base_parameters['enhance_audio'] = True
                base_parameters['noise_reduction'] = True
        
        elif strategy == RetryStrategy.ALTERNATIVE_TOOL:
            # Modify parameters for alternative tool usage
            if retry_session.original_intent == ConversationIntent.TEXT_TO_ASL:
                base_parameters['pose_only'] = True  # Use pose-only generation
                base_parameters['pre_sign'] = False  # Disable pre-signing
        
        return base_parameters
    
    def _determine_retry_reason(self, retry_session: RetrySession,
                              modified_parameters: Optional[Dict[str, Any]]) -> RetryReason:
        """Determine the reason for this retry attempt"""
        if modified_parameters:
            return RetryReason.PARAMETER_ADJUSTMENT
        
        if retry_session.original_error:
            error_msg = retry_session.original_error.lower()
            if 'timeout' in error_msg:
                return RetryReason.TIMEOUT_ERROR
            elif 'network' in error_msg or 'connection' in error_msg:
                return RetryReason.NETWORK_ERROR
            elif 'system' in error_msg or 'internal' in error_msg:
                return RetryReason.SYSTEM_ERROR
            else:
                return RetryReason.TRANSLATION_FAILED
        
        return RetryReason.USER_REQUESTED
    
    def _determine_input_type(self, parameters: Dict[str, Any]) -> InputType:
        """Determine input type from parameters"""
        if 'text' in parameters:
            return InputType.TEXT
        elif 'bucket_name' in parameters and 'key_name' in parameters:
            # Check if it's audio or video based on file extension or other hints
            key_name = parameters.get('key_name', '').lower()
            if any(ext in key_name for ext in ['.mp3', '.wav', '.m4a', '.aac']):
                return InputType.AUDIO
            else:
                return InputType.VIDEO
        elif 'stream_name' in parameters:
            return InputType.STREAM
        else:
            return InputType.UNKNOWN
    
    def _calculate_retry_delay(self, strategy: RetryStrategy, attempt_number: int) -> float:
        """Calculate delay before retry based on strategy"""
        if strategy == RetryStrategy.EXPONENTIAL_BACKOFF:
            delay = min(
                self.exponential_backoff_base ** (attempt_number - 1),
                self.max_backoff_delay
            )
            return delay
        elif strategy == RetryStrategy.USER_GUIDED:
            return 0.0  # No automatic delay for user-guided retries
        else:
            return 1.0  # Small delay for other strategies
    
    def _simplify_text(self, text: str) -> str:
        """Simplify text for better translation success"""
        # Split into sentences and take the first one
        sentences = text.split('.')
        if sentences:
            first_sentence = sentences[0].strip()
            if first_sentence:
                return first_sentence
        
        # If no sentences, take first 50 characters
        return text[:50].strip()
    
    def _clean_text(self, text: str) -> str:
        """Clean text by removing special characters"""
        import re
        # Remove special characters but keep basic punctuation
        cleaned = re.sub(r'[^\w\s.,!?-]', '', text)
        return cleaned.strip()
    
    def _generate_retry_response(self, attempt: RetryAttempt, retry_session: RetrySession,
                               context: ConversationContext) -> str:
        """Generate conversational response for retry attempt"""
        response_parts = []
        
        if attempt.success:
            # Successful retry
            response_parts.append(f"Great! The retry was successful on attempt {attempt.attempt_number}.")
            
            if attempt.strategy == RetryStrategy.PARAMETER_MODIFICATION:
                response_parts.append("The parameter adjustments helped resolve the issue.")
            elif attempt.strategy == RetryStrategy.ALTERNATIVE_TOOL:
                response_parts.append("Using an alternative approach worked better this time.")
            elif attempt.strategy == RetryStrategy.EXPONENTIAL_BACKOFF:
                response_parts.append("Waiting a bit before retrying did the trick.")
            
            response_parts.append("Here are your translation results:")
            
        else:
            # Failed retry
            response_parts.append(f"I tried again (attempt {attempt.attempt_number}), but unfortunately it still didn't work.")
            
            if attempt.error_message:
                response_parts.append(f"The issue was: {attempt.error_message}")
            
            if retry_session.has_attempts_remaining():
                remaining = retry_session.max_attempts - retry_session.get_attempt_count()
                response_parts.append(f"I have {remaining} more attempt{'s' if remaining != 1 else ''} available.")
                
                # Suggest modifications for next attempt
                suggestions = self.suggest_retry_modifications(retry_session, context)
                if suggestions:
                    response_parts.append("Here are some adjustments we could try:")
                    for i, suggestion in enumerate(suggestions[:2], 1):
                        response_parts.append(f"{i}. {suggestion['description']}")
                
                response_parts.append("Would you like me to try again with one of these adjustments, or would you prefer a different approach?")
            else:
                response_parts.append("I've used all available retry attempts.")
                
                # Suggest alternatives
                alternatives = self.get_alternative_tools(retry_session.original_intent, retry_session.original_parameters)
                if alternatives:
                    response_parts.append("Here are some alternative approaches you could try:")
                    for i, alt in enumerate(alternatives[:2], 1):
                        response_parts.append(f"{i}. {alt['description']}")
        
        return "\n\n".join(response_parts)
    
    def _handle_max_attempts_reached(self, retry_session: RetrySession,
                                   context: ConversationContext) -> Tuple[TranslationResult, str]:
        """Handle case when maximum retry attempts have been reached"""
        # Create final failure result
        result = TranslationResult(
            input_text=retry_session.original_parameters.get('text', 'Max retries reached'),
            input_type=self._determine_input_type(retry_session.original_parameters),
            success=False,
            error_message=f"Maximum retry attempts ({retry_session.max_attempts}) reached",
            status=TranslationStatus.FAILED
        )
        
        # Generate conversational response
        response_parts = [
            f"I've tried {retry_session.max_attempts} times, but I wasn't able to complete your translation successfully.",
            "This might be due to a temporary issue with the system or the specific content you're trying to translate."
        ]
        
        # Suggest alternatives
        alternatives = self.get_alternative_tools(retry_session.original_intent, retry_session.original_parameters)
        if alternatives:
            response_parts.append("Here are some alternative approaches you could try:")
            for i, alt in enumerate(alternatives[:3], 1):
                response_parts.append(f"{i}. {alt['description']}")
        
        response_parts.extend([
            "You could also:",
            "• Try again later when the system might be less busy",
            "• Start a new conversation and try with different input",
            "• Ask me for help with a specific aspect of ASL translation"
        ])
        
        response = "\n\n".join(response_parts)
        
        # Mark retry session as inactive
        retry_session.is_active = False
        if context.session_id:
            memory_key = f"retry_session:{context.session_id}:{retry_session.session_id}"
            self.memory_manager.store_data(memory_key, retry_session.to_dict())
        
        return result, response