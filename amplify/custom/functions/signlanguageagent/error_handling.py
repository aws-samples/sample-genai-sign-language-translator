"""
Error handling and retry mechanisms for the GenASL Sign Language Agent

This module provides comprehensive error handling capabilities including:
- Exponential backoff retry logic for AWS service calls
- Circuit breaker patterns for dependent services
- Fallback strategies for service unavailability
- Error classification and recovery strategies
"""

import time
import logging
import functools
import threading
from typing import Any, Callable, Dict, List, Optional, Tuple, Type, Union
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import boto3
from botocore.exceptions import ClientError, BotoCoreError, NoCredentialsError

logger = logging.getLogger(__name__)


class ErrorType(Enum):
    """Classification of error types for handling strategies"""
    TRANSIENT = "transient"  # Temporary errors that can be retried
    PERMANENT = "permanent"  # Errors that should not be retried
    THROTTLING = "throttling"  # Rate limiting errors
    AUTHENTICATION = "authentication"  # Auth/permission errors
    VALIDATION = "validation"  # Input validation errors
    TIMEOUT = "timeout"  # Timeout errors
    RESOURCE_NOT_FOUND = "resource_not_found"  # Missing resources
    SERVICE_UNAVAILABLE = "service_unavailable"  # Service outages


class CircuitBreakerState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, rejecting requests
    HALF_OPEN = "half_open"  # Testing if service recovered


@dataclass
class RetryConfig:
    """Configuration for retry behavior"""
    max_retries: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    backoff_factor: float = 2.0
    jitter: bool = True
    retryable_errors: List[ErrorType] = field(default_factory=lambda: [
        ErrorType.TRANSIENT, ErrorType.THROTTLING, ErrorType.TIMEOUT
    ])


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker behavior"""
    failure_threshold: int = 5  # Number of failures before opening
    recovery_timeout: int = 60  # Seconds before trying half-open
    success_threshold: int = 3  # Successes needed to close from half-open
    timeout: float = 30.0  # Request timeout in seconds


@dataclass
class ErrorContext:
    """Context information for error handling"""
    operation: str
    attempt: int
    total_attempts: int
    error: Exception
    error_type: ErrorType
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


class CircuitBreaker:
    """Circuit breaker implementation for service protection"""
    
    def __init__(self, name: str, config: CircuitBreakerConfig):
        self.name = name
        self.config = config
        self.state = CircuitBreakerState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
        self.lock = threading.Lock()
        
    def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with circuit breaker protection"""
        with self.lock:
            if self.state == CircuitBreakerState.OPEN:
                if self._should_attempt_reset():
                    self.state = CircuitBreakerState.HALF_OPEN
                    logger.info(f"Circuit breaker {self.name} moving to HALF_OPEN")
                else:
                    raise CircuitBreakerOpenError(f"Circuit breaker {self.name} is OPEN")
        
        try:
            # Set timeout for the operation
            result = self._execute_with_timeout(func, *args, **kwargs)
            self._on_success()
            return result
            
        except Exception as e:
            self._on_failure(e)
            raise
    
    def _execute_with_timeout(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with timeout"""
        import signal
        
        def timeout_handler(signum, frame):
            raise TimeoutError(f"Operation timed out after {self.config.timeout} seconds")
        
        # Set up timeout (Unix systems only)
        try:
            old_handler = signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(int(self.config.timeout))
            result = func(*args, **kwargs)
            signal.alarm(0)  # Cancel alarm
            signal.signal(signal.SIGALRM, old_handler)
            return result
        except AttributeError:
            # Windows doesn't support SIGALRM, just execute normally
            return func(*args, **kwargs)
    
    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset"""
        if self.last_failure_time is None:
            return True
        return (datetime.now() - self.last_failure_time).seconds >= self.config.recovery_timeout
    
    def _on_success(self):
        """Handle successful operation"""
        with self.lock:
            if self.state == CircuitBreakerState.HALF_OPEN:
                self.success_count += 1
                if self.success_count >= self.config.success_threshold:
                    self.state = CircuitBreakerState.CLOSED
                    self.failure_count = 0
                    self.success_count = 0
                    logger.info(f"Circuit breaker {self.name} CLOSED after recovery")
            elif self.state == CircuitBreakerState.CLOSED:
                self.failure_count = 0  # Reset failure count on success
    
    def _on_failure(self, error: Exception):
        """Handle failed operation"""
        with self.lock:
            self.failure_count += 1
            self.last_failure_time = datetime.now()
            
            if self.state == CircuitBreakerState.HALF_OPEN:
                self.state = CircuitBreakerState.OPEN
                self.success_count = 0
                logger.warning(f"Circuit breaker {self.name} OPEN after failure in HALF_OPEN")
            elif (self.state == CircuitBreakerState.CLOSED and 
                  self.failure_count >= self.config.failure_threshold):
                self.state = CircuitBreakerState.OPEN
                logger.warning(f"Circuit breaker {self.name} OPEN after {self.failure_count} failures")


class CircuitBreakerOpenError(Exception):
    """Exception raised when circuit breaker is open"""
    pass


class ErrorClassifier:
    """Classifies errors for appropriate handling strategies"""
    
    # AWS error code mappings
    TRANSIENT_ERRORS = {
        'InternalServerError', 'ServiceUnavailable', 'SlowDown', 'RequestTimeout',
        'InternalError', 'ServiceException', 'ThrottlingException'
    }
    
    THROTTLING_ERRORS = {
        'Throttling', 'ThrottlingException', 'ProvisionedThroughputExceededException',
        'RequestLimitExceeded', 'TooManyRequestsException'
    }
    
    AUTHENTICATION_ERRORS = {
        'AccessDenied', 'AccessDeniedException', 'UnauthorizedOperation',
        'InvalidUserID.NotFound', 'SignatureDoesNotMatch', 'TokenRefreshRequired'
    }
    
    VALIDATION_ERRORS = {
        'ValidationException', 'InvalidParameterValue', 'InvalidParameter',
        'MalformedInput', 'InvalidInput', 'BadRequest'
    }
    
    RESOURCE_NOT_FOUND_ERRORS = {
        'ResourceNotFound', 'NoSuchBucket', 'NoSuchKey', 'ItemNotFound',
        'ResourceNotFoundException', 'NotFound'
    }
    
    @classmethod
    def classify_error(cls, error: Exception) -> ErrorType:
        """Classify an error into an ErrorType"""
        if isinstance(error, TimeoutError):
            return ErrorType.TIMEOUT
        
        if isinstance(error, NoCredentialsError):
            return ErrorType.AUTHENTICATION
        
        if isinstance(error, (ClientError, BotoCoreError)):
            error_code = getattr(error, 'response', {}).get('Error', {}).get('Code', '')
            
            if error_code in cls.TRANSIENT_ERRORS:
                return ErrorType.TRANSIENT
            elif error_code in cls.THROTTLING_ERRORS:
                return ErrorType.THROTTLING
            elif error_code in cls.AUTHENTICATION_ERRORS:
                return ErrorType.AUTHENTICATION
            elif error_code in cls.VALIDATION_ERRORS:
                return ErrorType.VALIDATION
            elif error_code in cls.RESOURCE_NOT_FOUND_ERRORS:
                return ErrorType.RESOURCE_NOT_FOUND
        
        # Check for specific error types
        if isinstance(error, (ConnectionError, OSError)):
            return ErrorType.SERVICE_UNAVAILABLE
        
        if isinstance(error, ValueError):
            return ErrorType.VALIDATION
        
        # Default to permanent for unknown errors
        return ErrorType.PERMANENT


class FallbackStrategy:
    """Defines fallback strategies for different error scenarios"""
    
    @staticmethod
    def text_to_gloss_fallback(text: str) -> str:
        """Fallback strategy for text-to-gloss conversion"""
        logger.warning(f"Using fallback strategy for text-to-gloss: {text}")
        # Simple word-to-gloss mapping as fallback
        words = text.upper().split()
        gloss_words = []
        
        # Basic fallback mappings
        fallback_mappings = {
            'I': 'IX-1P', 'YOU': 'IX-2P', 'HE': 'IX-3P', 'SHE': 'IX-3P',
            'AM': '', 'IS': '', 'ARE': '', 'BE': '', 'BEING': '',
            'THE': '', 'A': '', 'AN': '', 'AND': '', 'OF': '',
            'LOVE': 'LIKE', 'THANKS': 'THANK-YOU', 'THANK': 'THANK-YOU',
            'VIDEO': 'MOVIE', 'IMAGE': 'PICTURE', 'PHOTO': 'PICTURE'
        }
        
        for word in words:
            clean_word = word.strip('.,!?')
            gloss_words.append(fallback_mappings.get(clean_word, clean_word))
        
        return ' '.join(filter(None, gloss_words))
    
    @staticmethod
    def gloss_to_video_fallback(gloss: str, text: str = None) -> Dict[str, Any]:
        """Fallback strategy for gloss-to-video conversion"""
        logger.warning(f"Using fallback strategy for gloss-to-video: {gloss}")
        return {
            'PoseURL': 'https://fallback-pose-url.example.com/placeholder.webm',
            'SignURL': 'https://fallback-sign-url.example.com/placeholder.webm',
            'AvatarURL': 'https://fallback-avatar-url.example.com/placeholder.webm',
            'Gloss': gloss,
            'Text': text,
            'Fallback': True,
            'Message': 'Video generation service temporarily unavailable. Placeholder URLs provided.'
        }
    
    @staticmethod
    def audio_processing_fallback(bucket_name: str, key_name: str) -> str:
        """Fallback strategy for audio processing"""
        logger.warning(f"Using fallback strategy for audio processing: {bucket_name}/{key_name}")
        return f"Audio transcription service temporarily unavailable for {key_name}"
    
    @staticmethod
    def asl_analysis_fallback(input_source: str) -> str:
        """Fallback strategy for ASL analysis"""
        logger.warning(f"Using fallback strategy for ASL analysis: {input_source}")
        return "ASL analysis service temporarily unavailable. Please try again later."


def with_retry_and_circuit_breaker(
    operation_name: str,
    retry_config: Optional[RetryConfig] = None,
    circuit_breaker_config: Optional[CircuitBreakerConfig] = None,
    fallback_func: Optional[Callable] = None
):
    """Decorator that adds retry logic and circuit breaker protection to functions"""
    
    if retry_config is None:
        retry_config = RetryConfig()
    
    # Global circuit breakers registry
    if not hasattr(with_retry_and_circuit_breaker, 'circuit_breakers'):
        with_retry_and_circuit_breaker.circuit_breakers = {}
    
    def decorator(func: Callable) -> Callable:
        # Create circuit breaker if config provided
        circuit_breaker = None
        if circuit_breaker_config:
            cb_name = f"{operation_name}_{func.__name__}"
            if cb_name not in with_retry_and_circuit_breaker.circuit_breakers:
                with_retry_and_circuit_breaker.circuit_breakers[cb_name] = CircuitBreaker(
                    cb_name, circuit_breaker_config
                )
            circuit_breaker = with_retry_and_circuit_breaker.circuit_breakers[cb_name]
        
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            def execute_function():
                return func(*args, **kwargs)
            
            # Use circuit breaker if available
            if circuit_breaker:
                try:
                    return circuit_breaker.call(execute_function)
                except CircuitBreakerOpenError:
                    if fallback_func:
                        logger.info(f"Circuit breaker open for {operation_name}, using fallback")
                        return fallback_func(*args, **kwargs)
                    raise
            
            # Execute with retry logic
            last_error = None
            
            for attempt in range(retry_config.max_retries + 1):
                try:
                    return execute_function()
                    
                except Exception as e:
                    last_error = e
                    error_type = ErrorClassifier.classify_error(e)
                    
                    # Create error context
                    error_context = ErrorContext(
                        operation=operation_name,
                        attempt=attempt + 1,
                        total_attempts=retry_config.max_retries + 1,
                        error=e,
                        error_type=error_type,
                        metadata={'function': func.__name__, 'args': str(args)[:100]}
                    )
                    
                    # Check if error is retryable
                    if error_type not in retry_config.retryable_errors:
                        logger.error(f"Non-retryable error in {operation_name}: {error_type.value} - {str(e)}")
                        if fallback_func:
                            logger.info(f"Using fallback for {operation_name}")
                            return fallback_func(*args, **kwargs)
                        raise e
                    
                    # Don't retry on last attempt
                    if attempt == retry_config.max_retries:
                        logger.error(f"Max retries exceeded for {operation_name}: {str(e)}")
                        if fallback_func:
                            logger.info(f"Using fallback for {operation_name} after max retries")
                            return fallback_func(*args, **kwargs)
                        break
                    
                    # Calculate delay with exponential backoff and jitter
                    delay = min(
                        retry_config.base_delay * (retry_config.backoff_factor ** attempt),
                        retry_config.max_delay
                    )
                    
                    if retry_config.jitter:
                        import random
                        delay *= (0.5 + random.random() * 0.5)  # Add 0-50% jitter
                    
                    logger.warning(
                        f"Attempt {attempt + 1}/{retry_config.max_retries + 1} failed for {operation_name}: "
                        f"{error_type.value} - {str(e)}. Retrying in {delay:.2f}s"
                    )
                    
                    time.sleep(delay)
            
            # If we get here, all retries failed
            raise last_error
        
        return wrapper
    return decorator


def create_aws_service_client(service_name: str, region_name: str = None, **kwargs) -> Any:
    """Create AWS service client with error handling and retry configuration"""
    
    @with_retry_and_circuit_breaker(
        operation_name=f"create_{service_name}_client",
        retry_config=RetryConfig(max_retries=2, base_delay=0.5),
        circuit_breaker_config=CircuitBreakerConfig(failure_threshold=3, recovery_timeout=30)
    )
    def _create_client():
        return boto3.client(service_name, region_name=region_name, **kwargs)
    
    return _create_client()


def handle_tool_error(operation: str, error: Exception, context: Dict[str, Any] = None) -> Dict[str, Any]:
    """Centralized error handling for tool operations"""
    error_type = ErrorClassifier.classify_error(error)
    
    error_response = {
        'success': False,
        'error': str(error),
        'error_type': error_type.value,
        'operation': operation,
        'timestamp': datetime.now().isoformat(),
        'context': context or {}
    }
    
    # Add specific guidance based on error type
    if error_type == ErrorType.AUTHENTICATION:
        error_response['guidance'] = "Please check AWS credentials and permissions"
    elif error_type == ErrorType.THROTTLING:
        error_response['guidance'] = "Request rate exceeded. Please try again in a few moments"
    elif error_type == ErrorType.RESOURCE_NOT_FOUND:
        error_response['guidance'] = "Required resource not found. Please verify configuration"
    elif error_type == ErrorType.VALIDATION:
        error_response['guidance'] = "Invalid input parameters. Please check your request"
    elif error_type == ErrorType.SERVICE_UNAVAILABLE:
        error_response['guidance'] = "Service temporarily unavailable. Please try again later"
    else:
        error_response['guidance'] = "An unexpected error occurred. Please contact support if the issue persists"
    
    logger.error(f"Tool error in {operation}: {error_response}")
    return error_response


# Pre-configured decorators for common operations
bedrock_retry = with_retry_and_circuit_breaker(
    "bedrock_operation",
    retry_config=RetryConfig(max_retries=3, base_delay=1.0, backoff_factor=2.0),
    circuit_breaker_config=CircuitBreakerConfig(failure_threshold=5, recovery_timeout=60)
)

dynamodb_retry = with_retry_and_circuit_breaker(
    "dynamodb_operation", 
    retry_config=RetryConfig(max_retries=3, base_delay=0.5, backoff_factor=2.0),
    circuit_breaker_config=CircuitBreakerConfig(failure_threshold=5, recovery_timeout=30)
)

s3_retry = with_retry_and_circuit_breaker(
    "s3_operation",
    retry_config=RetryConfig(max_retries=3, base_delay=1.0, backoff_factor=2.0),
    circuit_breaker_config=CircuitBreakerConfig(failure_threshold=5, recovery_timeout=60)
)

transcribe_retry = with_retry_and_circuit_breaker(
    "transcribe_operation",
    retry_config=RetryConfig(max_retries=3, base_delay=2.0, backoff_factor=2.0),
    circuit_breaker_config=CircuitBreakerConfig(failure_threshold=3, recovery_timeout=120)
)