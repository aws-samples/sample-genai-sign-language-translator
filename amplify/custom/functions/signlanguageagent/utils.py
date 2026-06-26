"""
Utility functions for the GenASL Sign Language Agent

This module provides common utility functions used across the agent
implementation, including error handling, logging, and helper functions.
"""

import logging
import time
import functools
from typing import Any, Callable, Dict, Optional, TypeVar, Union
from pathlib import Path

# Type variable for generic functions
T = TypeVar('T')

def setup_logging(log_level: str = 'INFO') -> logging.Logger:
    """
    Set up logging configuration for the agent
    
    Args:
        log_level: The logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    
    Returns:
        Configured logger instance
    """
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    logger = logging.getLogger('genasl_agent')
    logger.info(f"Logging configured with level: {log_level}")
    return logger

def retry_with_backoff(
    max_retries: int = 3,
    delay: float = 1.0,
    backoff_factor: float = 2.0,
    exceptions: tuple = (Exception,)
) -> Callable:
    """
    Decorator to retry function calls with exponential backoff
    
    Args:
        max_retries: Maximum number of retry attempts
        delay: Initial delay between retries in seconds
        backoff_factor: Factor to multiply delay by after each retry
        exceptions: Tuple of exception types to catch and retry on
    
    Returns:
        Decorated function with retry logic
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            current_delay = delay
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt == max_retries:
                        break
                    
                    logger = logging.getLogger('genasl_agent')
                    logger.warning(
                        f"Attempt {attempt + 1} failed for {func.__name__}: {e}. "
                        f"Retrying in {current_delay:.2f} seconds..."
                    )
                    
                    time.sleep(current_delay)
                    current_delay *= backoff_factor
            
            # If we get here, all retries failed
            raise last_exception
        
        return wrapper
    return decorator

def validate_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate and normalize the incoming payload
    
    Args:
        payload: The raw payload from the agent invocation
    
    Returns:
        Normalized payload with default values
    
    Raises:
        ValueError: If payload is invalid
    """
    if not isinstance(payload, dict):
        raise ValueError("Payload must be a dictionary")
    
    # Extract message from either 'message' or 'prompt' field
    message = payload.get('message', '') or payload.get('prompt', '') or payload.get('text', '')
    
    # Set defaults
    normalized = {
        'message': message,
        'type': payload.get('type', 'text'),
        'metadata': payload.get('metadata', {}),
        'session_id': payload.get('session_id'),
        'user_id': payload.get('user_id')
    }
    
    # Validate message
    if not normalized['message']:
        raise ValueError("Message cannot be empty. Please provide 'message', 'prompt', or 'text' field.")
    
    # Validate type
    valid_types = ['text', 'audio', 'video']
    if normalized['type'] not in valid_types:
        raise ValueError(f"Type must be one of: {', '.join(valid_types)}")
    
    return normalized

def format_response(
    content: str,
    success: bool = True,
    metadata: Optional[Dict[str, Any]] = None,
    error: Optional[str] = None
) -> Dict[str, Any]:
    """
    Format the agent response in a consistent structure
    
    Args:
        content: The main response content
        success: Whether the operation was successful
        metadata: Additional metadata to include
        error: Error message if operation failed
    
    Returns:
        Formatted response dictionary
    """
    response = {
        'content': content,
        'success': success,
        'timestamp': time.time(),
        'metadata': metadata or {}
    }
    
    if error:
        response['error'] = error
    
    return response

def extract_response_content(response: Any) -> str:
    """
    Extract text content from various response formats
    
    Args:
        response: The response object from the agent
    
    Returns:
        Extracted text content
    """
    try:
        # Handle Strands agent response format
        if hasattr(response, 'message') and 'content' in response.message:
            content = response.message['content']
            if isinstance(content, list) and len(content) > 0:
                return content[0].get('text', str(response))
            else:
                return str(content)
        
        # Handle direct string responses
        if isinstance(response, str):
            return response
        
        # Handle dictionary responses
        if isinstance(response, dict):
            if 'content' in response:
                return str(response['content'])
            elif 'text' in response:
                return str(response['text'])
            elif 'message' in response:
                return str(response['message'])
        
        # Fallback to string conversion
        return str(response)
        
    except Exception as e:
        logger = logging.getLogger('genasl_agent')
        logger.error(f"Error extracting response content: {e}")
        return f"Error processing response: {str(e)}"

def safe_path_join(*parts: str) -> Path:
    """
    Safely join path components and resolve the path
    
    Args:
        *parts: Path components to join
    
    Returns:
        Resolved Path object
    """
    return Path(*parts).resolve()

def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """
    Truncate text to a maximum length with optional suffix
    
    Args:
        text: Text to truncate
        max_length: Maximum length of the result
        suffix: Suffix to add if text is truncated
    
    Returns:
        Truncated text
    """
    if len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)] + suffix

def sanitize_filename(filename: str) -> str:
    """
    Sanitize a filename by removing or replacing invalid characters
    
    Args:
        filename: The filename to sanitize
    
    Returns:
        Sanitized filename
    """
    import re
    
    # Remove or replace invalid characters
    sanitized = re.sub(r'[<>:"/\\|?*]', '_', filename)
    
    # Remove leading/trailing whitespace and dots
    sanitized = sanitized.strip(' .')
    
    # Ensure filename is not empty
    if not sanitized:
        sanitized = 'unnamed_file'
    
    return sanitized

def get_file_size_mb(file_path: Union[str, Path]) -> float:
    """
    Get file size in megabytes
    
    Args:
        file_path: Path to the file
    
    Returns:
        File size in MB
    """
    try:
        size_bytes = Path(file_path).stat().st_size
        return size_bytes / (1024 * 1024)
    except (OSError, FileNotFoundError):
        return 0.0

def format_response_for_api(agent_response: Any, request_params: Dict[str, Any], response_format: str = "rest_api") -> Dict[str, Any]:
    """
    Format agent response for different API endpoints using response formatters
    
    Args:
        agent_response: Raw agent response
        request_params: Original request parameters
        response_format: Target format ("rest_api", "websocket", "legacy", "enhanced")
        
    Returns:
        dict: Formatted response data
    """
    try:
        from response_formatters import (
            format_rest_api_response,
            format_websocket_response,
            format_legacy_response,
            format_enhanced_response
        )
        
        if response_format == "rest_api":
            return format_rest_api_response(agent_response, request_params)
        elif response_format == "websocket":
            connection_id = request_params.get('connection_id', 'default')
            return format_websocket_response(agent_response, request_params, connection_id)
        elif response_format == "legacy":
            execution_arn = request_params.get('execution_arn')
            return format_legacy_response(agent_response, execution_arn)
        elif response_format == "enhanced":
            return format_enhanced_response(agent_response, request_params)
        else:
            logger = logging.getLogger('genasl_agent')
            logger.warning(f"Unknown response format: {response_format}")
            return {"message": str(agent_response), "status": "completed"}
            
    except ImportError:
        logger = logging.getLogger('genasl_agent')
        logger.warning("Response formatters not available, using basic formatting")
        return {"message": str(agent_response), "status": "completed"}
    except Exception as e:
        logger = logging.getLogger('genasl_agent')
        logger.error(f"Error formatting response: {e}")
        return {"error": str(e), "status": "failed"}

def parse_structured_response(response_text: str) -> Dict[str, Any]:
    """
    Parse structured data from agent response text
    
    Args:
        response_text: Agent response as text
        
    Returns:
        dict: Parsed structured data
    """
    import re
    
    parsed_data = {}
    
    # Extract URLs
    url_pattern = re.compile(r'https?://[^\s<>"{}|\\^`\[\]]+')
    urls = url_pattern.findall(response_text)
    
    if urls:
        for i, url in enumerate(urls):
            if 'pose' in url.lower():
                parsed_data['PoseURL'] = url
            elif 'sign' in url.lower():
                parsed_data['SignURL'] = url
            elif 'avatar' in url.lower():
                parsed_data['AvatarURL'] = url
            elif i == 0 and 'PoseURL' not in parsed_data:
                parsed_data['PoseURL'] = url
            elif i == 1 and 'SignURL' not in parsed_data:
                parsed_data['SignURL'] = url
            elif i == 2 and 'AvatarURL' not in parsed_data:
                parsed_data['AvatarURL'] = url
    
    # Extract gloss
    gloss_pattern = re.compile(r'(?:ASL Gloss|Gloss):\s*([^\n]+)', re.IGNORECASE)
    gloss_match = gloss_pattern.search(response_text)
    if gloss_match:
        parsed_data['Gloss'] = gloss_match.group(1).strip()
    
    # Extract text
    text_pattern = re.compile(r'(?:Original text|Text):\s*"([^"]+)"', re.IGNORECASE)
    text_match = text_pattern.search(response_text)
    if text_match:
        parsed_data['Text'] = text_match.group(1).strip()
    
    # If no structured data found, include the full response
    if not parsed_data:
        parsed_data['message'] = response_text
    
    return parsed_data