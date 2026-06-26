"""
Conversation Memory Manager

This module provides AgentCore Memory integration for conversation data management,
including session storage, context persistence, and data serialization utilities.
"""

import json
import logging
import time
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from dataclasses import asdict

# Import AgentCore Memory
from bedrock_agentcore.runtime import BedrockAgentCoreApp

# Import data models
try:
    from .data_models import ConversationContext, ConversationInteraction, TranslationResult
except ImportError:
    from data_models import ConversationContext, ConversationInteraction, TranslationResult

logger = logging.getLogger(__name__)

class ConversationMemoryManager:
    """
    Manages conversation data using AgentCore Memory
    
    Provides utilities for:
    - Session and context storage
    - Memory key generation and management
    - Data serialization/deserialization
    - Memory cleanup and lifecycle management
    - Session timeout handling with configurable cleanup policies
    - Session data migration for backward compatibility
    """
    
    def __init__(self, app: Optional[BedrockAgentCoreApp] = None, 
                 session_config: Optional[Dict[str, Any]] = None):
        """
        Initialize the memory manager
        
        Args:
            app: Optional AgentCore app instance. If None, creates a new one.
            session_config: Optional session configuration parameters
        """
        self.app = app or BedrockAgentCoreApp()
        self.memory = self.app.memory
        
        # Session configuration with defaults
        config = session_config or {}
        self.session_ttl = config.get('session_ttl', 24 * 60 * 60)  # 24 hours in seconds
        self.history_limit = config.get('history_limit', 50)  # Maximum conversation history items
        self.cleanup_interval = config.get('cleanup_interval', 60 * 60)  # 1 hour in seconds
        self.inactive_session_timeout = config.get('inactive_session_timeout', 2 * 60 * 60)  # 2 hours
        self.max_sessions_per_user = config.get('max_sessions_per_user', 10)  # Maximum sessions per user
        self.enable_session_migration = config.get('enable_session_migration', True)
        self.data_version = config.get('data_version', '1.0')  # For backward compatibility
        
        # Session lifecycle tracking
        self.last_cleanup = time.time()
        self.cleanup_stats = {
            'total_cleanups': 0,
            'sessions_cleaned': 0,
            'last_cleanup_duration': 0.0,
            'cleanup_errors': 0
        }
        
        # Session timeout policies
        self.timeout_policies = {
            'inactive_timeout': self.inactive_session_timeout,
            'absolute_timeout': self.session_ttl,
            'cleanup_on_error': True,
            'preserve_user_preferences': True,
            'migration_enabled': self.enable_session_migration
        }
        
        logger.info(f"ConversationMemoryManager initialized with AgentCore Memory - "
                   f"Session TTL: {self.session_ttl}s, Cleanup interval: {self.cleanup_interval}s")
    
    def generate_session_key(self, session_id: str) -> str:
        """
        Generate memory key for session context
        
        Args:
            session_id: The session identifier
        
        Returns:
            str: Memory key for session context
        """
        return f"session:{session_id}:context"
    
    def generate_history_key(self, session_id: str) -> str:
        """
        Generate memory key for conversation history
        
        Args:
            session_id: The session identifier
        
        Returns:
            str: Memory key for conversation history
        """
        return f"session:{session_id}:history"
    
    def generate_preferences_key(self, session_id: str) -> str:
        """
        Generate memory key for user preferences
        
        Args:
            session_id: The session identifier
        
        Returns:
            str: Memory key for user preferences
        """
        return f"session:{session_id}:preferences"
    
    def generate_last_result_key(self, session_id: str) -> str:
        """
        Generate memory key for last translation result
        
        Args:
            session_id: The session identifier
        
        Returns:
            str: Memory key for last translation result
        """
        return f"session:{session_id}:last_result"
    
    def generate_user_global_key(self, user_id: str) -> str:
        """
        Generate memory key for cross-session user preferences
        
        Args:
            user_id: The user identifier
        
        Returns:
            str: Memory key for global user preferences
        """
        return f"user:{user_id}:global_preferences"
    
    def serialize_conversation_context(self, context: ConversationContext) -> str:
        """
        Serialize conversation context for memory storage
        
        Args:
            context: The conversation context to serialize
        
        Returns:
            str: JSON serialized context data
        """
        try:
            # Convert dataclass to dictionary
            context_dict = asdict(context)
            
            # Convert datetime objects to ISO format strings
            if 'session_start_time' in context_dict and context_dict['session_start_time']:
                context_dict['session_start_time'] = context_dict['session_start_time'].isoformat()
            if 'last_activity_time' in context_dict and context_dict['last_activity_time']:
                context_dict['last_activity_time'] = context_dict['last_activity_time'].isoformat()
            
            # Handle conversation history separately (will be stored in different key)
            conversation_history = context_dict.pop('conversation_history', [])
            
            # Serialize to JSON
            serialized = json.dumps(context_dict, default=str, ensure_ascii=False)
            logger.debug(f"Serialized context for session {context.session_id}")
            return serialized
            
        except Exception as e:
            logger.error(f"Error serializing conversation context: {e}")
            raise
    
    def deserialize_conversation_context(self, serialized_data: str) -> ConversationContext:
        """
        Deserialize conversation context from memory storage
        
        Args:
            serialized_data: JSON serialized context data
        
        Returns:
            ConversationContext: Deserialized context object
        """
        try:
            # Parse JSON
            context_dict = json.loads(serialized_data)
            
            # Convert ISO format strings back to datetime objects
            if 'session_start_time' in context_dict and context_dict['session_start_time']:
                context_dict['session_start_time'] = datetime.fromisoformat(context_dict['session_start_time'])
            if 'last_activity_time' in context_dict and context_dict['last_activity_time']:
                context_dict['last_activity_time'] = datetime.fromisoformat(context_dict['last_activity_time'])
            
            # Initialize empty conversation history (will be loaded separately)
            context_dict['conversation_history'] = []
            
            # Create ConversationContext object
            context = ConversationContext(**context_dict)
            logger.debug(f"Deserialized context for session {context.session_id}")
            return context
            
        except Exception as e:
            logger.error(f"Error deserializing conversation context: {e}")
            raise
    
    def serialize_conversation_history(self, history: List[ConversationInteraction]) -> str:
        """
        Serialize conversation history for memory storage
        
        Args:
            history: List of conversation interactions
        
        Returns:
            str: JSON serialized history data
        """
        try:
            # Convert interactions to dictionaries
            history_dicts = []
            for interaction in history:
                interaction_dict = asdict(interaction)
                
                # Convert datetime to ISO format
                if 'timestamp' in interaction_dict and interaction_dict['timestamp']:
                    interaction_dict['timestamp'] = interaction_dict['timestamp'].isoformat()
                
                # Convert enum to string
                if 'intent' in interaction_dict and interaction_dict['intent']:
                    interaction_dict['intent'] = interaction_dict['intent'].value
                
                history_dicts.append(interaction_dict)
            
            # Serialize to JSON
            serialized = json.dumps(history_dicts, default=str, ensure_ascii=False)
            logger.debug(f"Serialized {len(history)} conversation interactions")
            return serialized
            
        except Exception as e:
            logger.error(f"Error serializing conversation history: {e}")
            raise
    
    def deserialize_conversation_history(self, serialized_data: str) -> List[ConversationInteraction]:
        """
        Deserialize conversation history from memory storage
        
        Args:
            serialized_data: JSON serialized history data
        
        Returns:
            List[ConversationInteraction]: Deserialized interaction objects
        """
        try:
            # Parse JSON
            history_dicts = json.loads(serialized_data)
            
            # Convert dictionaries back to ConversationInteraction objects
            history = []
            for interaction_dict in history_dicts:
                # Convert ISO format string back to datetime
                if 'timestamp' in interaction_dict and interaction_dict['timestamp']:
                    interaction_dict['timestamp'] = datetime.fromisoformat(interaction_dict['timestamp'])
                
                # Convert string back to enum
                if 'intent' in interaction_dict and interaction_dict['intent']:
                    try:
                        from .data_models import ConversationIntent
                    except ImportError:
                        from data_models import ConversationIntent
                    interaction_dict['intent'] = ConversationIntent(interaction_dict['intent'])
                
                # Handle translation_result if present
                if 'translation_result' in interaction_dict and interaction_dict['translation_result']:
                    result_dict = interaction_dict['translation_result']
                    interaction_dict['translation_result'] = TranslationResult(**result_dict)
                
                interaction = ConversationInteraction(**interaction_dict)
                history.append(interaction)
            
            logger.debug(f"Deserialized {len(history)} conversation interactions")
            return history
            
        except Exception as e:
            logger.error(f"Error deserializing conversation history: {e}")
            raise
    
    def serialize_translation_result(self, result: TranslationResult) -> str:
        """
        Serialize translation result for memory storage
        
        Args:
            result: The translation result to serialize
        
        Returns:
            str: JSON serialized result data
        """
        try:
            result_dict = asdict(result)
            
            # Convert enum to string if present
            if 'input_type' in result_dict and result_dict['input_type']:
                result_dict['input_type'] = result_dict['input_type'].value
            
            serialized = json.dumps(result_dict, default=str, ensure_ascii=False)
            logger.debug("Serialized translation result")
            return serialized
            
        except Exception as e:
            logger.error(f"Error serializing translation result: {e}")
            raise
    
    def deserialize_translation_result(self, serialized_data: str) -> TranslationResult:
        """
        Deserialize translation result from memory storage
        
        Args:
            serialized_data: JSON serialized result data
        
        Returns:
            TranslationResult: Deserialized result object
        """
        try:
            result_dict = json.loads(serialized_data)
            
            # Convert string back to enum if present
            if 'input_type' in result_dict and result_dict['input_type']:
                try:
                    from .data_models import InputType
                except ImportError:
                    from data_models import InputType
                result_dict['input_type'] = InputType(result_dict['input_type'])
            
            result = TranslationResult(**result_dict)
            logger.debug("Deserialized translation result")
            return result
            
        except Exception as e:
            logger.error(f"Error deserializing translation result: {e}")
            raise
    
    def store_conversation_context(self, session_id: str, context: ConversationContext) -> bool:
        """
        Store conversation context in memory
        
        Args:
            session_id: The session identifier
            context: The conversation context to store
        
        Returns:
            bool: True if storage was successful, False otherwise
        """
        try:
            # Store main context (without history)
            context_key = self.generate_session_key(session_id)
            serialized_context = self.serialize_conversation_context(context)
            self.memory.store(context_key, serialized_context, ttl=self.session_ttl)
            
            # Store conversation history separately
            if context.conversation_history:
                history_key = self.generate_history_key(session_id)
                serialized_history = self.serialize_conversation_history(context.conversation_history)
                self.memory.store(history_key, serialized_history, ttl=self.session_ttl)
            
            # Store user preferences if present
            if context.user_preferences:
                preferences_key = self.generate_preferences_key(session_id)
                preferences_json = json.dumps(context.user_preferences, ensure_ascii=False)
                self.memory.store(preferences_key, preferences_json, ttl=self.session_ttl)
            
            # Store last translation result if present
            if context.last_translation:
                result_key = self.generate_last_result_key(session_id)
                serialized_result = self.serialize_translation_result(context.last_translation)
                self.memory.store(result_key, serialized_result, ttl=self.session_ttl)
            
            logger.info(f"Stored conversation context for session: {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error storing conversation context for session {session_id}: {e}")
            return False
    
    def retrieve_conversation_context(self, session_id: str) -> Optional[ConversationContext]:
        """
        Retrieve conversation context from memory
        
        Args:
            session_id: The session identifier
        
        Returns:
            ConversationContext or None if not found
        """
        try:
            # Retrieve main context
            context_key = self.generate_session_key(session_id)
            serialized_context = self.memory.retrieve(context_key)
            
            if not serialized_context:
                logger.debug(f"No context found for session: {session_id}")
                return None
            
            # Deserialize context
            context = self.deserialize_conversation_context(serialized_context)
            
            # Retrieve conversation history
            history_key = self.generate_history_key(session_id)
            serialized_history = self.memory.retrieve(history_key)
            if serialized_history:
                context.conversation_history = self.deserialize_conversation_history(serialized_history)
            
            # Retrieve user preferences
            preferences_key = self.generate_preferences_key(session_id)
            preferences_json = self.memory.retrieve(preferences_key)
            if preferences_json:
                context.user_preferences = json.loads(preferences_json)
            
            # Retrieve last translation result
            result_key = self.generate_last_result_key(session_id)
            serialized_result = self.memory.retrieve(result_key)
            if serialized_result:
                context.last_translation = self.deserialize_translation_result(serialized_result)
            
            logger.debug(f"Retrieved conversation context for session: {session_id}")
            return context
            
        except Exception as e:
            logger.error(f"Error retrieving conversation context for session {session_id}: {e}")
            return None
    
    def get_conversation_context(self, session_id: Optional[str] = None, 
                               user_id: Optional[str] = None) -> ConversationContext:
        """
        Get existing conversation context or create a new one
        
        Args:
            session_id: Optional session identifier
            user_id: Optional user identifier
        
        Returns:
            ConversationContext: Existing or new conversation context
        """
        # Generate session ID if not provided
        if not session_id:
            import uuid
            session_id = f"session_{int(time.time())}_{str(uuid.uuid4())[:8]}"
        
        # Try to retrieve existing context
        context = self.retrieve_conversation_context(session_id)
        
        if context:
            # Update last activity time
            context.last_activity_time = datetime.now()
            self.store_conversation_context(session_id, context)
            return context
        
        # Create new context
        context = ConversationContext(
            session_id=session_id,
            user_id=user_id,
            session_start_time=datetime.now(),
            last_activity_time=datetime.now(),
            conversation_history=[],
            user_preferences={},
            last_translation=None
        )
        
        # Store new context
        self.store_conversation_context(session_id, context)
        logger.info(f"Created new conversation context for session: {session_id}")
        
        return context
    
    def update_conversation_context(self, session_id: str, context: ConversationContext) -> bool:
        """
        Update conversation context in memory
        
        Args:
            session_id: The session identifier
            context: The updated conversation context
        
        Returns:
            bool: True if update was successful, False otherwise
        """
        # Update last activity time
        context.last_activity_time = datetime.now()
        
        # Limit conversation history to prevent memory bloat
        if len(context.conversation_history) > self.history_limit:
            context.conversation_history = context.conversation_history[-self.history_limit:]
        
        return self.store_conversation_context(session_id, context)
    
    def cleanup_session(self, session_id: str) -> bool:
        """
        Clean up all memory data for a session
        
        Args:
            session_id: The session identifier to clean up
        
        Returns:
            bool: True if cleanup was successful, False otherwise
        """
        try:
            # Delete all session-related keys
            keys_to_delete = [
                self.generate_session_key(session_id),
                self.generate_history_key(session_id),
                self.generate_preferences_key(session_id),
                self.generate_last_result_key(session_id)
            ]
            
            success_count = 0
            for key in keys_to_delete:
                try:
                    self.memory.delete(key)
                    success_count += 1
                except Exception as e:
                    logger.warning(f"Failed to delete memory key {key}: {e}")
            
            logger.info(f"Cleaned up {success_count}/{len(keys_to_delete)} memory keys for session: {session_id}")
            return success_count == len(keys_to_delete)
            
        except Exception as e:
            logger.error(f"Error cleaning up session {session_id}: {e}")
            return False
    
    def cleanup_expired_sessions(self) -> int:
        """
        Clean up expired sessions based on configurable timeout policies
        
        This method implements comprehensive session lifecycle management with:
        - Inactive session timeout handling
        - Absolute session timeout enforcement
        - User preference preservation
        - Session migration support
        - Configurable cleanup policies
        
        Returns:
            int: Number of sessions cleaned up
        """
        try:
            cleanup_start_time = time.time()
            current_time = cleanup_start_time
            
            # Only run cleanup if enough time has passed
            if current_time - self.last_cleanup < self.cleanup_interval:
                return 0
            
            logger.info("Starting comprehensive session cleanup with configurable policies")
            
            # Track cleanup statistics
            sessions_cleaned = 0
            errors_encountered = 0
            
            # Get all session keys for cleanup evaluation
            session_keys = self._discover_session_keys()
            
            for session_key in session_keys:
                try:
                    session_id = self._extract_session_id_from_key(session_key)
                    if not session_id:
                        continue
                    
                    # Evaluate session for cleanup based on policies
                    should_cleanup, cleanup_reason = self._evaluate_session_for_cleanup(session_id)
                    
                    if should_cleanup:
                        # Preserve user preferences if policy enabled
                        if self.timeout_policies['preserve_user_preferences']:
                            self._preserve_user_preferences_before_cleanup(session_id)
                        
                        # Perform session cleanup
                        cleanup_success = self.cleanup_session(session_id)
                        
                        if cleanup_success:
                            sessions_cleaned += 1
                            logger.debug(f"Cleaned up session {session_id}: {cleanup_reason}")
                        else:
                            errors_encountered += 1
                            logger.warning(f"Failed to cleanup session {session_id}")
                    
                except Exception as session_error:
                    errors_encountered += 1
                    logger.error(f"Error processing session {session_key}: {session_error}")
            
            # Update cleanup statistics
            cleanup_duration = time.time() - cleanup_start_time
            self.last_cleanup = current_time
            self.cleanup_stats.update({
                'total_cleanups': self.cleanup_stats['total_cleanups'] + 1,
                'sessions_cleaned': self.cleanup_stats['sessions_cleaned'] + sessions_cleaned,
                'last_cleanup_duration': cleanup_duration,
                'cleanup_errors': self.cleanup_stats['cleanup_errors'] + errors_encountered
            })
            
            if sessions_cleaned > 0 or errors_encountered > 0:
                logger.info(f"Session cleanup completed: {sessions_cleaned} sessions cleaned, "
                           f"{errors_encountered} errors, duration: {cleanup_duration:.2f}s")
            
            return sessions_cleaned
            
        except Exception as e:
            self.cleanup_stats['cleanup_errors'] += 1
            logger.error(f"Error during comprehensive session cleanup: {e}")
            return 0
    
    def _discover_session_keys(self) -> List[str]:
        """
        Discover all session-related keys in memory
        
        Returns:
            List of session keys for cleanup evaluation
        """
        try:
            # Since AgentCore Memory doesn't provide key enumeration,
            # we'll maintain a registry of active sessions
            registry_key = "session_registry"
            registry_data = self.memory.retrieve(registry_key)
            
            if registry_data:
                registry = json.loads(registry_data)
                return list(registry.get('active_sessions', {}).keys())
            
            return []
            
        except Exception as e:
            logger.error(f"Error discovering session keys: {e}")
            return []
    
    def _extract_session_id_from_key(self, session_key: str) -> Optional[str]:
        """
        Extract session ID from memory key
        
        Args:
            session_key: Memory key containing session ID
        
        Returns:
            Session ID or None if extraction fails
        """
        try:
            # Extract session ID from keys like "session:session_id:context"
            if session_key.startswith("session:") and ":context" in session_key:
                parts = session_key.split(":")
                if len(parts) >= 3:
                    return parts[1]
            return None
        except Exception:
            return None
    
    def _evaluate_session_for_cleanup(self, session_id: str) -> tuple[bool, str]:
        """
        Evaluate whether a session should be cleaned up based on timeout policies
        
        Args:
            session_id: Session identifier to evaluate
        
        Returns:
            Tuple of (should_cleanup: bool, reason: str)
        """
        try:
            # Retrieve session context to check timestamps
            context = self.retrieve_conversation_context(session_id)
            
            if not context:
                return True, "Session context not found"
            
            current_time = datetime.now()
            
            # Check inactive timeout
            inactive_duration = (current_time - context.last_activity_time).total_seconds()
            if inactive_duration > self.timeout_policies['inactive_timeout']:
                return True, f"Inactive for {inactive_duration:.0f}s (limit: {self.timeout_policies['inactive_timeout']}s)"
            
            # Check absolute timeout
            session_duration = (current_time - context.session_start_time).total_seconds()
            if session_duration > self.timeout_policies['absolute_timeout']:
                return True, f"Session age {session_duration:.0f}s (limit: {self.timeout_policies['absolute_timeout']}s)"
            
            # Check error-based cleanup
            if self.timeout_policies['cleanup_on_error'] and context.get_error_rate() > 80.0:
                return True, f"High error rate: {context.get_error_rate():.1f}%"
            
            return False, "Session within timeout limits"
            
        except Exception as e:
            logger.error(f"Error evaluating session {session_id} for cleanup: {e}")
            return True, f"Evaluation error: {str(e)}"
    
    def _preserve_user_preferences_before_cleanup(self, session_id: str) -> bool:
        """
        Preserve user preferences before session cleanup
        
        Args:
            session_id: Session identifier
        
        Returns:
            bool: True if preferences were preserved successfully
        """
        try:
            context = self.retrieve_conversation_context(session_id)
            
            if not context or not context.user_id or not context.user_preferences:
                return True  # Nothing to preserve
            
            # Store user preferences in global user key
            global_key = self.generate_user_global_key(context.user_id)
            existing_prefs = self.memory.retrieve(global_key)
            
            if existing_prefs:
                # Merge with existing preferences
                global_prefs = json.loads(existing_prefs)
                global_prefs.update(context.user_preferences)
            else:
                global_prefs = context.user_preferences.copy()
            
            # Add session metadata
            global_prefs['_last_session'] = {
                'session_id': session_id,
                'last_activity': context.last_activity_time.isoformat(),
                'total_interactions': context.total_interactions,
                'preserved_at': datetime.now().isoformat()
            }
            
            # Store with extended TTL for user preferences
            user_prefs_ttl = self.session_ttl * 7  # Keep user prefs 7x longer than sessions
            self.memory.store(global_key, json.dumps(global_prefs), ttl=user_prefs_ttl)
            
            logger.debug(f"Preserved user preferences for user {context.user_id} from session {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error preserving user preferences for session {session_id}: {e}")
            return False
    
    def _update_session_registry(self, session_id: str, action: str = 'add') -> bool:
        """
        Update the session registry for tracking active sessions
        
        Args:
            session_id: Session identifier
            action: 'add' or 'remove'
        
        Returns:
            bool: True if registry was updated successfully
        """
        try:
            registry_key = "session_registry"
            registry_data = self.memory.retrieve(registry_key) or "{}"
            registry = json.loads(registry_data)
            
            if 'active_sessions' not in registry:
                registry['active_sessions'] = {}
            
            if action == 'add':
                registry['active_sessions'][session_id] = {
                    'created_at': datetime.now().isoformat(),
                    'last_updated': datetime.now().isoformat()
                }
            elif action == 'remove':
                registry['active_sessions'].pop(session_id, None)
            
            # Update registry metadata
            registry['last_updated'] = datetime.now().isoformat()
            registry['total_sessions'] = len(registry['active_sessions'])
            
            # Store updated registry
            self.memory.store(registry_key, json.dumps(registry), ttl=self.session_ttl * 2)
            return True
            
        except Exception as e:
            logger.error(f"Error updating session registry for {session_id}: {e}")
            return False
    
    def create_session(self, session_id: str, user_id: Optional[str] = None, 
                      initial_preferences: Optional[Dict[str, Any]] = None) -> ConversationContext:
        """
        Create a new conversation session with full lifecycle management
        
        Args:
            session_id: Unique session identifier
            user_id: Optional user identifier
            initial_preferences: Optional initial user preferences
        
        Returns:
            ConversationContext: Newly created conversation context
        """
        try:
            # Check if session already exists
            existing_context = self.retrieve_conversation_context(session_id)
            if existing_context:
                logger.warning(f"Session {session_id} already exists, returning existing context")
                return existing_context
            
            # Load user preferences from global storage if user_id provided
            user_preferences = {}
            if user_id:
                global_key = self.generate_user_global_key(user_id)
                global_prefs_data = self.memory.retrieve(global_key)
                if global_prefs_data:
                    global_prefs = json.loads(global_prefs_data)
                    # Extract user preferences (exclude metadata)
                    user_preferences = {k: v for k, v in global_prefs.items() 
                                      if not k.startswith('_')}
            
            # Merge with initial preferences
            if initial_preferences:
                user_preferences.update(initial_preferences)
            
            # Create new conversation context
            context = ConversationContext(
                session_id=session_id,
                user_id=user_id,
                session_start_time=datetime.now(),
                last_activity_time=datetime.now(),
                conversation_history=[],
                user_preferences=user_preferences,
                last_translation=None,
                current_operations=[],
                error_count=0,
                total_interactions=0
            )
            
            # Store the new context
            success = self.store_conversation_context(session_id, context)
            if not success:
                raise Exception("Failed to store new session context")
            
            # Update session registry
            self._update_session_registry(session_id, 'add')
            
            logger.info(f"Created new session {session_id} for user {user_id}")
            return context
            
        except Exception as e:
            logger.error(f"Error creating session {session_id}: {e}")
            raise
    
    def update_session(self, session_id: str, context: ConversationContext, 
                      force_update: bool = False) -> bool:
        """
        Update session with enhanced lifecycle management
        
        Args:
            session_id: Session identifier
            context: Updated conversation context
            force_update: Force update even if session seems expired
        
        Returns:
            bool: True if update was successful
        """
        try:
            # Check if session should be updated based on policies
            if not force_update:
                should_cleanup, reason = self._evaluate_session_for_cleanup(session_id)
                if should_cleanup:
                    logger.warning(f"Attempted to update expired session {session_id}: {reason}")
                    return False
            
            # Update last activity time
            context.last_activity_time = datetime.now()
            
            # Apply history limit
            if len(context.conversation_history) > self.history_limit:
                context.conversation_history = context.conversation_history[-self.history_limit:]
            
            # Store updated context
            success = self.store_conversation_context(session_id, context)
            
            if success:
                # Update session registry
                self._update_session_registry(session_id, 'add')
                logger.debug(f"Updated session {session_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error updating session {session_id}: {e}")
            return False
    
    def migrate_session_data(self, session_id: str, from_version: str = "1.0", 
                           to_version: str = "1.0") -> bool:
        """
        Migrate session data for backward compatibility
        
        Args:
            session_id: Session identifier to migrate
            from_version: Source data version
            to_version: Target data version
        
        Returns:
            bool: True if migration was successful
        """
        try:
            if not self.timeout_policies['migration_enabled']:
                logger.info(f"Session migration disabled, skipping migration for {session_id}")
                return True
            
            if from_version == to_version:
                logger.debug(f"No migration needed for session {session_id} (same version)")
                return True
            
            logger.info(f"Migrating session {session_id} from version {from_version} to {to_version}")
            
            # Retrieve existing context
            context = self.retrieve_conversation_context(session_id)
            if not context:
                logger.warning(f"No context found for session {session_id}, cannot migrate")
                return False
            
            # Apply version-specific migrations
            migrated_context = self._apply_data_migrations(context, from_version, to_version)
            
            if migrated_context:
                # Store migrated context
                success = self.store_conversation_context(session_id, migrated_context)
                if success:
                    logger.info(f"Successfully migrated session {session_id} to version {to_version}")
                return success
            else:
                logger.error(f"Migration failed for session {session_id}")
                return False
            
        except Exception as e:
            logger.error(f"Error migrating session {session_id}: {e}")
            return False
    
    def _apply_data_migrations(self, context: ConversationContext, 
                             from_version: str, to_version: str) -> Optional[ConversationContext]:
        """
        Apply version-specific data migrations
        
        Args:
            context: Original conversation context
            from_version: Source version
            to_version: Target version
        
        Returns:
            Migrated context or None if migration fails
        """
        try:
            # For now, implement basic migration patterns
            # In a real implementation, this would handle specific version transitions
            
            migrated_context = context
            
            # Example migration: Add missing fields for newer versions
            if not hasattr(migrated_context, 'error_count'):
                migrated_context.error_count = 0
            
            if not hasattr(migrated_context, 'total_interactions'):
                migrated_context.total_interactions = len(migrated_context.conversation_history)
            
            # Ensure all interactions have required fields
            for interaction in migrated_context.conversation_history:
                if not hasattr(interaction, 'processing_time'):
                    interaction.processing_time = 0.0
                if not hasattr(interaction, 'error_occurred'):
                    interaction.error_occurred = False
            
            logger.debug(f"Applied data migrations from {from_version} to {to_version}")
            return migrated_context
            
        except Exception as e:
            logger.error(f"Error applying data migrations: {e}")
            return None
    
    def get_session_lifecycle_stats(self) -> Dict[str, Any]:
        """
        Get comprehensive session lifecycle statistics
        
        Returns:
            Dict containing detailed session lifecycle metrics
        """
        try:
            # Get basic memory stats
            basic_stats = self.get_memory_stats()
            
            # Add lifecycle-specific stats
            lifecycle_stats = {
                'session_lifecycle': {
                    'timeout_policies': self.timeout_policies.copy(),
                    'cleanup_stats': self.cleanup_stats.copy(),
                    'configuration': {
                        'session_ttl_seconds': self.session_ttl,
                        'inactive_session_timeout_seconds': self.inactive_session_timeout,
                        'max_sessions_per_user': self.max_sessions_per_user,
                        'history_limit': self.history_limit,
                        'cleanup_interval_seconds': self.cleanup_interval,
                        'data_version': self.data_version,
                        'migration_enabled': self.enable_session_migration
                    }
                }
            }
            
            # Get session registry stats
            try:
                registry_key = "session_registry"
                registry_data = self.memory.retrieve(registry_key)
                if registry_data:
                    registry = json.loads(registry_data)
                    lifecycle_stats['session_lifecycle']['active_sessions_count'] = len(registry.get('active_sessions', {}))
                    lifecycle_stats['session_lifecycle']['registry_last_updated'] = registry.get('last_updated')
                else:
                    lifecycle_stats['session_lifecycle']['active_sessions_count'] = 0
            except Exception:
                lifecycle_stats['session_lifecycle']['active_sessions_count'] = 'unknown'
            
            # Merge with basic stats
            basic_stats.update(lifecycle_stats)
            return basic_stats
            
        except Exception as e:
            logger.error(f"Error getting session lifecycle stats: {e}")
            return {'error': str(e)}
    
    def get_memory_stats(self) -> Dict[str, Any]:
        """
        Get memory usage statistics
        
        Returns:
            Dict containing memory statistics
        """
        try:
            # Basic statistics (AgentCore Memory doesn't expose detailed stats)
            return {
                'memory_manager_initialized': True,
                'session_ttl_seconds': self.session_ttl,
                'history_limit': self.history_limit,
                'cleanup_interval_seconds': self.cleanup_interval,
                'last_cleanup_time': self.last_cleanup,
                'agentcore_memory_available': self.memory is not None
            }
        except Exception as e:
            logger.error(f"Error getting memory stats: {e}")
            return {'error': str(e)}