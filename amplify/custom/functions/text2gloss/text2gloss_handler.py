import json
import os
import time
import logging
from typing import Optional
import sys
from pathlib import Path

import boto3
from botocore.exceptions import ClientError, BotoCoreError
from strands import tool

# Configure logging first
logger = logging.getLogger(__name__)

# Add signlanguageagent to path for error handling imports
current_dir = Path(__file__).parent
agent_dir = current_dir.parent / 'signlanguageagent'
if agent_dir.exists():
    sys.path.insert(0, str(agent_dir))

try:
    from error_handling import (
        bedrock_retry, handle_tool_error, FallbackStrategy,
        with_retry_and_circuit_breaker, RetryConfig, CircuitBreakerConfig
    )
    ERROR_HANDLING_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Error handling module not available: {e}")
    ERROR_HANDLING_AVAILABLE = False
    # Create dummy decorator if error handling not available
    def bedrock_retry(func):
        return func

try:
    from performance import (
        with_performance_monitoring, with_response_caching,
        get_optimized_bedrock_client, optimize_bedrock_request
    )
    PERFORMANCE_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Performance module not available: {e}")
    PERFORMANCE_AVAILABLE = False
    # Create dummy decorators if performance not available
    def with_performance_monitoring(func):
        return func
    def with_response_caching(cache_key_func=None):
        def decorator(func):
            return func
        return decorator
logger.setLevel(logging.INFO)

eng_to_asl_model = os.environ.get('ENG_TO_ASL_MODEL', 'amazon.nova-lite-v1:0')


def construct_query(text: str) -> str:
    """Construct the prompt for text-to-gloss conversion"""
    return f"""

H: Here are some examples of translations from english text to ASL gloss 
Examples:
Apples ==> APPLE
you  ==> IX-2P
your  ==> IX-2P
Love ==> LIKE
My ==> IX-1P
Thanks ==> THANK-YOU
am ==> 
and ==> 
be ==>
of ==>
video ==> MOVIE
image ==> PICTURE
conversations ==> TALK
type of ==> TYPE
Watch ==> SEE

Translate the following english text to ASL Gloss and return only the gloss. Don't provide any explanation.
{text} ==>


A:"""


def lambda_handler(event, context):
    """Invoke Bedrock to convert English text to ASL Gloss
    Parameters
    ----------
    event: dict, required
        Input event to the Lambda function
    context: object, required
        Lambda Context runtime methods and attributes
    Returns
    ------
        dict: text consists of ASL Gloss
    """
    try:
        input_text = event.get("Text", "")
        if not input_text.strip():
            return {'Error': 'No text provided for translation'}
        
        gloss = text_to_asl_gloss(input_text)
        return {'Gloss': gloss, 'Text': input_text}
    except Exception as e:
        logger.error(f"Error in lambda_handler: {str(e)}")
        return {'Error': f'Translation failed: {str(e)}'}


def _text_cache_key(text: str) -> str:
    """Generate cache key for text-to-gloss conversion"""
    return f"text2gloss:{text.strip().lower()}"

@tool
@bedrock_retry
@with_performance_monitoring
@with_response_caching(cache_key_func=lambda text: _text_cache_key(text))
def text_to_asl_gloss(text: str) -> str:
    """Convert English text to ASL gloss notation with enhanced error handling
    
    Args:
        text: English text to convert to ASL gloss
        
    Returns:
        str: ASL gloss notation
        
    Raises:
        ValueError: If text is empty or invalid
        RuntimeError: If translation fails after retries
    """
    if not text or not text.strip():
        raise ValueError("Text cannot be empty")
    
    text = text.strip()
    
    try:
        return _perform_text_to_gloss_conversion(text)
    except Exception as e:
        if ERROR_HANDLING_AVAILABLE:
            error_info = handle_tool_error("text_to_asl_gloss", e, {"text": text})
            logger.error(f"Text-to-gloss conversion failed: {error_info}")
            
            # Try fallback strategy
            try:
                fallback_result = FallbackStrategy.text_to_gloss_fallback(text)
                logger.info(f"Using fallback result for text-to-gloss: {fallback_result}")
                return fallback_result
            except Exception as fallback_error:
                logger.error(f"Fallback strategy also failed: {fallback_error}")
                raise RuntimeError(f"Text-to-gloss conversion failed: {str(e)}")
        else:
            raise RuntimeError(f"Text-to-gloss conversion failed: {str(e)}")


def _perform_text_to_gloss_conversion(text: str) -> str:
    """Perform the actual text-to-gloss conversion with Bedrock"""
    try:
        # Use optimized Bedrock client if available
        if PERFORMANCE_AVAILABLE:
            bedrock_client = get_optimized_bedrock_client()
        else:
            bedrock_client = boto3.client(service_name="bedrock-runtime")
        
        # Create the prompt
        prompt_data = construct_query(text)
        conversation = [
            {
                "role": "user",
                "content": [{"text": prompt_data}],
            }
        ]
        
        inference_config = {
            "maxTokens": 3000, 
            "temperature": 0.0, 
            "topP": 0.5
        }

        logger.info(f"Performing text-to-gloss conversion for: '{text}'")
        
        # Use optimized Bedrock request if available
        if PERFORMANCE_AVAILABLE:
            response = optimize_bedrock_request(
                eng_to_asl_model,
                conversation,
                inference_config
            )
        else:
            response = bedrock_client.converse(
                modelId=eng_to_asl_model,
                messages=conversation,
                inferenceConfig=inference_config,
            )

        gloss = response["output"]["message"]["content"][0]["text"]
        
        # Clean up the gloss output
        gloss = gloss.strip()
        if gloss.startswith("==>"):
            gloss = gloss[3:].strip()
        
        if not gloss:
            raise RuntimeError("Bedrock returned empty gloss result")
        
        logger.info(f"Successfully converted text to gloss: '{text}' -> '{gloss}'")
        return gloss
        
    except (ClientError, BotoCoreError) as e:
        # Let the retry decorator handle AWS-specific errors
        raise e
    except Exception as e:
        logger.error(f"Unexpected error in text-to-gloss conversion: {str(e)}")
        raise RuntimeError(f"Text-to-gloss conversion failed: {str(e)}")


if __name__ == "__main__":
    # Test cases
    test_cases = [
        "what is your name?",
        "How are you?", 
        "She is watching a movie",
        "He wants to play",
        "Can you come with me?"
    ]
    
    for test_text in test_cases:
        try:
            result = lambda_handler({"Text": test_text}, {})
            print(f"Input: {test_text}")
            print(f"Result: {result}")
            print("-" * 50)
        except Exception as e:
            print(f"Error testing '{test_text}': {str(e)}")