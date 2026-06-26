"""
Performance optimization module for the GenASL Sign Language Agent

This module provides performance enhancements including connection pooling,
request optimization, and performance monitoring.
"""

import time
import logging
import functools
from typing import Dict, Any, Optional, Callable, List
from dataclasses import dataclass
from threading import Lock
import boto3
from botocore.config import Config

from .caching import (
    gloss_pose_cache, aws_connection_pool, response_cache, 
    request_throttler, initialize_caches
)

logger = logging.getLogger(__name__)

@dataclass
class PerformanceMetrics:
    """Performance metrics tracking"""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    average_response_time: float = 0.0
    cache_hit_rate: float = 0.0
    throttled_requests: int = 0

class PerformanceMonitor:
    """Monitor and track performance metrics"""
    
    def __init__(self):
        self.metrics = PerformanceMetrics()
        self._response_times: List[float] = []
        self._lock = Lock()
    
    def record_request(self, response_time: float, success: bool, cache_hit: bool = False, throttled: bool = False):
        """Record request metrics"""
        with self._lock:
            self.metrics.total_requests += 1
            
            if success:
                self.metrics.successful_requests += 1
            else:
                self.metrics.failed_requests += 1
            
            if throttled:
                self.metrics.throttled_requests += 1
            
            # Track response times (keep last 1000)
            self._response_times.append(response_time)
            if len(self._response_times) > 1000:
                self._response_times.pop(0)
            
            # Update average response time
            if self._response_times:
                self.metrics.average_response_time = sum(self._response_times) / len(self._response_times)
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current performance metrics"""
        with self._lock:
            success_rate = 0.0
            if self.metrics.total_requests > 0:
                success_rate = self.metrics.successful_requests / self.metrics.total_requests
            
            return {
                'total_requests': self.metrics.total_requests,
                'successful_requests': self.metrics.successful_requests,
                'failed_requests': self.metrics.failed_requests,
                'success_rate': success_rate,
                'average_response_time': self.metrics.average_response_time,
                'throttled_requests': self.metrics.throttled_requests,
                'recent_response_times': self._response_times[-10:] if self._response_times else []
            }

# Global performance monitor
performance_monitor = PerformanceMonitor()

def with_performance_monitoring(func: Callable) -> Callable:
    """Decorator to add performance monitoring to functions"""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        success = False
        cache_hit = False
        throttled = False
        
        try:
            result = func(*args, **kwargs)
            success = True
            return result
        except Exception as e:
            if "throttled" in str(e).lower() or "queue" in str(e).lower():
                throttled = True
            raise
        finally:
            response_time = time.time() - start_time
            performance_monitor.record_request(response_time, success, cache_hit, throttled)
    
    return wrapper

def with_response_caching(cache_key_func: Optional[Callable] = None):
    """Decorator to add response caching to functions"""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key
            if cache_key_func:
                cache_key = cache_key_func(*args, **kwargs)
            else:
                # Default cache key generation
                cache_key = f"{func.__name__}:{hash(str(args) + str(sorted(kwargs.items())))}"
            
            # Try to get from cache
            cached_result = response_cache.cache.get(cache_key)
            if cached_result is not None:
                logger.debug(f"Cache hit for {func.__name__}")
                return cached_result
            
            # Execute function and cache result
            result = func(*args, **kwargs)
            response_cache.cache.put(cache_key, result)
            logger.debug(f"Cached result for {func.__name__}")
            
            return result
        
        return wrapper
    return decorator

def optimize_aws_client_config() -> Config:
    """Get optimized AWS client configuration"""
    return Config(
        region_name='us-west-2',  # Default region
        retries={
            'max_attempts': 3,
            'mode': 'adaptive'
        },
        max_pool_connections=50,  # Increase connection pool size
        connect_timeout=10,
        read_timeout=30
    )

def get_optimized_bedrock_client(region_name: Optional[str] = None):
    """Get optimized Bedrock client with connection pooling"""
    return aws_connection_pool.get_client('bedrock-runtime', region_name)

def get_optimized_dynamodb_resource(region_name: Optional[str] = None):
    """Get optimized DynamoDB resource with connection pooling"""
    return aws_connection_pool.get_resource('dynamodb', region_name)

def get_optimized_s3_client(region_name: Optional[str] = None):
    """Get optimized S3 client with connection pooling"""
    return aws_connection_pool.get_client('s3', region_name)

def optimize_gloss_to_sign_ids(gloss_sentence: str) -> List[str]:
    """Optimized gloss-to-sign-ID conversion using caching"""
    if not gloss_sentence or not gloss_sentence.strip():
        return []
    
    # Split and clean glosses
    glosses = []
    for gloss in gloss_sentence.split():
        cleaned_gloss = gloss.strip().upper()
        # Remove punctuation
        import re
        cleaned_gloss = re.sub(r'[,!?.]', '', cleaned_gloss)
        if cleaned_gloss:
            glosses.append(cleaned_gloss)
    
    if not glosses:
        return []
    
    # Use batch caching for better performance
    gloss_to_sign_id = gloss_pose_cache.get_sign_ids_batch(glosses)
    
    # Extract sign IDs, handling finger spelling for unknown glosses
    sign_ids = []
    for gloss in glosses:
        sign_id = gloss_to_sign_id.get(gloss)
        if sign_id:
            sign_ids.append(sign_id)
        else:
            # Try finger spelling for unknown glosses
            finger_spell_ids = _get_finger_spelling_ids(gloss)
            sign_ids.extend(finger_spell_ids)
    
    return sign_ids

def _get_finger_spelling_ids(word: str) -> List[str]:
    """Get finger spelling sign IDs for a word"""
    finger_spell_ids = []
    
    for char in word:
        if char.isalpha():
            sign_id = gloss_pose_cache.get_sign_id(char.upper())
            if sign_id:
                finger_spell_ids.append(sign_id)
    
    return finger_spell_ids

class BatchProcessor:
    """Batch processor for handling multiple requests efficiently"""
    
    def __init__(self, batch_size: int = 10, timeout_seconds: float = 5.0):
        self.batch_size = batch_size
        self.timeout_seconds = timeout_seconds
        self._batch: List[Dict[str, Any]] = []
        self._batch_lock = Lock()
        self._last_batch_time = time.time()
    
    def add_request(self, request_data: Dict[str, Any]) -> Optional[List[Any]]:
        """Add request to batch and process if batch is full or timeout reached"""
        with self._batch_lock:
            self._batch.append(request_data)
            
            # Check if we should process the batch
            should_process = (
                len(self._batch) >= self.batch_size or
                time.time() - self._last_batch_time >= self.timeout_seconds
            )
            
            if should_process:
                batch_to_process = self._batch.copy()
                self._batch.clear()
                self._last_batch_time = time.time()
                
                # Process batch outside of lock
                return self._process_batch(batch_to_process)
        
        return None
    
    def _process_batch(self, batch: List[Dict[str, Any]]) -> List[Any]:
        """Process a batch of requests"""
        results = []
        
        # Group requests by type for efficient processing
        text_requests = [req for req in batch if req.get('type') == 'text']
        audio_requests = [req for req in batch if req.get('type') == 'audio']
        video_requests = [req for req in batch if req.get('type') == 'video']
        
        # Process each type in batch
        if text_requests:
            results.extend(self._process_text_batch(text_requests))
        
        if audio_requests:
            results.extend(self._process_audio_batch(audio_requests))
        
        if video_requests:
            results.extend(self._process_video_batch(video_requests))
        
        return results
    
    def _process_text_batch(self, requests: List[Dict[str, Any]]) -> List[Any]:
        """Process batch of text requests"""
        # This could be optimized further by batching Bedrock calls
        results = []
        for request in requests:
            try:
                # Process individual text request
                # This would call the actual text processing logic
                result = {"status": "processed", "request": request}
                results.append(result)
            except Exception as e:
                results.append({"status": "error", "error": str(e), "request": request})
        
        return results
    
    def _process_audio_batch(self, requests: List[Dict[str, Any]]) -> List[Any]:
        """Process batch of audio requests"""
        # Audio requests could be batched for transcription
        results = []
        for request in requests:
            try:
                result = {"status": "processed", "request": request}
                results.append(result)
            except Exception as e:
                results.append({"status": "error", "error": str(e), "request": request})
        
        return results
    
    def _process_video_batch(self, requests: List[Dict[str, Any]]) -> List[Any]:
        """Process batch of video requests"""
        results = []
        for request in requests:
            try:
                result = {"status": "processed", "request": request}
                results.append(result)
            except Exception as e:
                results.append({"status": "error", "error": str(e), "request": request})
        
        return results

# Global batch processor
batch_processor = BatchProcessor()

def optimize_bedrock_request(model_id: str, messages: List[Dict], inference_config: Dict) -> Dict:
    """Optimize Bedrock request parameters for better performance"""
    # Use optimized client
    bedrock_client = get_optimized_bedrock_client()
    
    # Optimize inference config
    optimized_config = inference_config.copy()
    
    # Ensure reasonable token limits
    if optimized_config.get('maxTokens', 0) > 4000:
        optimized_config['maxTokens'] = 4000
    
    # Use lower temperature for more consistent results
    if optimized_config.get('temperature', 1.0) > 0.3:
        optimized_config['temperature'] = 0.1
    
    try:
        response = bedrock_client.converse(
            modelId=model_id,
            messages=messages,
            inferenceConfig=optimized_config
        )
        return response
    except Exception as e:
        logger.error(f"Optimized Bedrock request failed: {str(e)}")
        raise

def warm_up_connections():
    """Warm up AWS connections and caches"""
    logger.info("Warming up connections and caches...")
    
    try:
        # Initialize caches
        initialize_caches()
        
        # Warm up AWS connections
        get_optimized_bedrock_client()
        get_optimized_dynamodb_resource()
        get_optimized_s3_client()
        
        # Test a simple operation to warm up the connection
        dynamodb = get_optimized_dynamodb_resource()
        # This will create the connection without actually querying data
        
        logger.info("Connections and caches warmed up successfully")
        
    except Exception as e:
        logger.warning(f"Connection warm-up failed: {str(e)}")

def get_performance_report() -> Dict[str, Any]:
    """Get comprehensive performance report"""
    return {
        'performance_metrics': performance_monitor.get_metrics(),
        'cache_stats': {
            'gloss_pose_cache': gloss_pose_cache.get_stats(),
            'response_cache': response_cache.get_stats()
        },
        'throttling_stats': request_throttler.get_stats(),
        'timestamp': time.time()
    }

# Initialize performance optimizations on module load
try:
    warm_up_connections()
except Exception as e:
    logger.warning(f"Failed to initialize performance optimizations: {str(e)}")