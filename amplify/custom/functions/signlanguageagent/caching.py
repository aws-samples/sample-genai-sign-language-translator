"""
Caching module for the GenASL Sign Language Agent

This module provides caching capabilities for frequently used operations
to improve performance, including gloss-to-pose mappings, AWS service
connections, and response caching.
"""

import json
import time
import hashlib
import logging
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, asdict
from threading import Lock
from collections import OrderedDict
import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)

@dataclass
class CacheEntry:
    """Cache entry with metadata"""
    value: Any
    timestamp: float
    access_count: int = 0
    last_accessed: float = 0.0
    
    def is_expired(self, ttl_seconds: int) -> bool:
        """Check if cache entry is expired"""
        return time.time() - self.timestamp > ttl_seconds
    
    def access(self):
        """Mark entry as accessed"""
        self.access_count += 1
        self.last_accessed = time.time()


class LRUCache:
    """Thread-safe LRU cache implementation"""
    
    def __init__(self, max_size: int = 1000, ttl_seconds: int = 3600):
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._lock = Lock()
        self._hits = 0
        self._misses = 0
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        with self._lock:
            if key not in self._cache:
                self._misses += 1
                return None
            
            entry = self._cache[key]
            
            # Check if expired
            if entry.is_expired(self.ttl_seconds):
                del self._cache[key]
                self._misses += 1
                return None
            
            # Move to end (most recently used)
            self._cache.move_to_end(key)
            entry.access()
            self._hits += 1
            
            return entry.value
    
    def put(self, key: str, value: Any):
        """Put value in cache"""
        with self._lock:
            # Remove oldest entries if at capacity
            while len(self._cache) >= self.max_size:
                oldest_key = next(iter(self._cache))
                del self._cache[oldest_key]
            
            # Add new entry
            entry = CacheEntry(
                value=value,
                timestamp=time.time(),
                last_accessed=time.time()
            )
            self._cache[key] = entry
    
    def invalidate(self, key: str):
        """Remove specific key from cache"""
        with self._lock:
            self._cache.pop(key, None)
    
    def clear(self):
        """Clear all cache entries"""
        with self._lock:
            self._cache.clear()
            self._hits = 0
            self._misses = 0
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        with self._lock:
            total_requests = self._hits + self._misses
            hit_rate = self._hits / total_requests if total_requests > 0 else 0.0
            
            return {
                'size': len(self._cache),
                'max_size': self.max_size,
                'hits': self._hits,
                'misses': self._misses,
                'hit_rate': hit_rate,
                'ttl_seconds': self.ttl_seconds
            }


class GlossPoseMappingCache:
    """Specialized cache for gloss-to-pose mappings"""
    
    def __init__(self, max_size: int = 5000, ttl_seconds: int = 7200):  # 2 hours TTL
        self.cache = LRUCache(max_size, ttl_seconds)
        self._dynamodb_table = None
        self._table_name = None
    
    def _get_dynamodb_table(self):
        """Get DynamoDB table with lazy initialization"""
        if self._dynamodb_table is None:
            import os
            self._table_name = os.environ.get('TABLE_NAME', 'Pose_Data6')
            dynamodb = boto3.resource('dynamodb')
            self._dynamodb_table = dynamodb.Table(self._table_name)
        return self._dynamodb_table
    
    def get_sign_id(self, gloss: str) -> Optional[str]:
        """Get sign ID for a gloss with caching"""
        cache_key = f"gloss:{gloss.upper()}"
        
        # Try cache first
        cached_result = self.cache.get(cache_key)
        if cached_result is not None:
            logger.debug(f"Cache hit for gloss: {gloss}")
            return cached_result
        
        # Cache miss - query DynamoDB
        try:
            table = self._get_dynamodb_table()
            response = table.query(
                KeyConditionExpression=boto3.dynamodb.conditions.Key('Gloss').eq(gloss.upper())
            )
            
            sign_id = None
            if response['Count'] > 0:
                sign_id = response['Items'][0]['SignID']
            
            # Cache the result (including None for not found)
            self.cache.put(cache_key, sign_id)
            logger.debug(f"Cached gloss mapping: {gloss} -> {sign_id}")
            
            return sign_id
            
        except Exception as e:
            logger.error(f"Error querying gloss {gloss}: {str(e)}")
            return None
    
    def get_sign_ids_batch(self, glosses: List[str]) -> Dict[str, Optional[str]]:
        """Get sign IDs for multiple glosses efficiently"""
        results = {}
        uncached_glosses = []
        
        # Check cache for each gloss
        for gloss in glosses:
            cache_key = f"gloss:{gloss.upper()}"
            cached_result = self.cache.get(cache_key)
            if cached_result is not None:
                results[gloss] = cached_result
            else:
                uncached_glosses.append(gloss)
        
        # Batch query uncached glosses
        if uncached_glosses:
            try:
                table = self._get_dynamodb_table()
                
                # Use batch_get_item for better performance
                for gloss in uncached_glosses:
                    try:
                        response = table.query(
                            KeyConditionExpression=boto3.dynamodb.conditions.Key('Gloss').eq(gloss.upper())
                        )
                        
                        sign_id = None
                        if response['Count'] > 0:
                            sign_id = response['Items'][0]['SignID']
                        
                        results[gloss] = sign_id
                        
                        # Cache the result
                        cache_key = f"gloss:{gloss.upper()}"
                        self.cache.put(cache_key, sign_id)
                        
                    except Exception as e:
                        logger.error(f"Error querying gloss {gloss}: {str(e)}")
                        results[gloss] = None
                        
            except Exception as e:
                logger.error(f"Error in batch gloss query: {str(e)}")
                # Fill remaining with None
                for gloss in uncached_glosses:
                    if gloss not in results:
                        results[gloss] = None
        
        return results
    
    def preload_common_glosses(self, common_glosses: List[str]):
        """Preload commonly used glosses into cache"""
        logger.info(f"Preloading {len(common_glosses)} common glosses into cache")
        self.get_sign_ids_batch(common_glosses)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        return self.cache.get_stats()


class AWSConnectionPool:
    """Connection pool for AWS services to reduce connection overhead"""
    
    def __init__(self):
        self._clients: Dict[str, Any] = {}
        self._resources: Dict[str, Any] = {}
        self._lock = Lock()
    
    def get_client(self, service_name: str, region_name: Optional[str] = None) -> Any:
        """Get or create AWS client with connection reuse"""
        key = f"{service_name}:{region_name or 'default'}"
        
        with self._lock:
            if key not in self._clients:
                kwargs = {'service_name': service_name}
                if region_name:
                    kwargs['region_name'] = region_name
                
                self._clients[key] = boto3.client(**kwargs)
                logger.debug(f"Created new AWS client: {key}")
            
            return self._clients[key]
    
    def get_resource(self, service_name: str, region_name: Optional[str] = None) -> Any:
        """Get or create AWS resource with connection reuse"""
        key = f"{service_name}:{region_name or 'default'}"
        
        with self._lock:
            if key not in self._resources:
                kwargs = {'service_name': service_name}
                if region_name:
                    kwargs['region_name'] = region_name
                
                self._resources[key] = boto3.resource(**kwargs)
                logger.debug(f"Created new AWS resource: {key}")
            
            return self._resources[key]
    
    def clear(self):
        """Clear all cached connections"""
        with self._lock:
            self._clients.clear()
            self._resources.clear()


class ResponseCache:
    """Cache for agent responses to avoid recomputation"""
    
    def __init__(self, max_size: int = 500, ttl_seconds: int = 1800):  # 30 minutes TTL
        self.cache = LRUCache(max_size, ttl_seconds)
    
    def _generate_key(self, request_data: Dict[str, Any]) -> str:
        """Generate cache key from request data"""
        # Create a normalized representation of the request
        normalized = {
            'message': request_data.get('message', '').strip().lower(),
            'type': request_data.get('type', 'text'),
            'metadata': request_data.get('metadata', {})
        }
        
        # Create hash of the normalized request
        request_str = json.dumps(normalized, sort_keys=True)
        return hashlib.md5(request_str.encode()).hexdigest()
    
    def get_response(self, request_data: Dict[str, Any]) -> Optional[str]:
        """Get cached response for request"""
        cache_key = self._generate_key(request_data)
        return self.cache.get(cache_key)
    
    def cache_response(self, request_data: Dict[str, Any], response: str):
        """Cache response for request"""
        cache_key = self._generate_key(request_data)
        self.cache.put(cache_key, response)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        return self.cache.get_stats()


class RequestThrottler:
    """Request throttling and queuing mechanism"""
    
    def __init__(self, max_concurrent: int = 10, max_queue_size: int = 100):
        self.max_concurrent = max_concurrent
        self.max_queue_size = max_queue_size
        self._active_requests = 0
        self._queue: List[Tuple[float, str]] = []  # (timestamp, request_id)
        self._lock = Lock()
    
    def can_process_request(self, request_id: str) -> bool:
        """Check if request can be processed immediately"""
        with self._lock:
            if self._active_requests < self.max_concurrent:
                self._active_requests += 1
                return True
            
            # Add to queue if space available
            if len(self._queue) < self.max_queue_size:
                self._queue.append((time.time(), request_id))
                return False
            
            # Queue is full
            raise RuntimeError("Request queue is full. Please try again later.")
    
    def complete_request(self, request_id: str):
        """Mark request as completed"""
        with self._lock:
            if self._active_requests > 0:
                self._active_requests -= 1
            
            # Process next queued request if any
            if self._queue:
                self._queue.pop(0)  # Remove oldest queued request
    
    def get_queue_position(self, request_id: str) -> Optional[int]:
        """Get position in queue for request"""
        with self._lock:
            for i, (_, queued_id) in enumerate(self._queue):
                if queued_id == request_id:
                    return i + 1
            return None
    
    def get_stats(self) -> Dict[str, Any]:
        """Get throttling statistics"""
        with self._lock:
            return {
                'active_requests': self._active_requests,
                'max_concurrent': self.max_concurrent,
                'queue_size': len(self._queue),
                'max_queue_size': self.max_queue_size,
                'queue_utilization': len(self._queue) / self.max_queue_size
            }


# Global cache instances
gloss_pose_cache = GlossPoseMappingCache()
aws_connection_pool = AWSConnectionPool()
response_cache = ResponseCache()
request_throttler = RequestThrottler()

# Common ASL glosses for preloading
COMMON_GLOSSES = [
    'HELLO', 'GOODBYE', 'THANK-YOU', 'PLEASE', 'SORRY',
    'YES', 'NO', 'GOOD', 'BAD', 'HAPPY', 'SAD',
    'IX-1P', 'IX-2P', 'IX-3P',  # Pronouns
    'LIKE', 'WANT', 'NEED', 'HAVE', 'GO', 'COME',
    'EAT', 'DRINK', 'SLEEP', 'WORK', 'PLAY',
    'MOTHER', 'FATHER', 'FAMILY', 'FRIEND',
    'HOME', 'SCHOOL', 'WORK', 'STORE',
    'TODAY', 'TOMORROW', 'YESTERDAY', 'NOW',
    'MORNING', 'AFTERNOON', 'EVENING', 'NIGHT'
]

def initialize_caches():
    """Initialize all caches with common data"""
    logger.info("Initializing performance caches...")
    
    # Preload common glosses
    gloss_pose_cache.preload_common_glosses(COMMON_GLOSSES)
    
    logger.info("Performance caches initialized successfully")

def get_cache_stats() -> Dict[str, Any]:
    """Get statistics for all caches"""
    return {
        'gloss_pose_cache': gloss_pose_cache.get_stats(),
        'response_cache': response_cache.get_stats(),
        'request_throttler': request_throttler.get_stats()
    }

def clear_all_caches():
    """Clear all caches"""
    gloss_pose_cache.cache.clear()
    response_cache.cache.clear()
    aws_connection_pool.clear()
    logger.info("All caches cleared")