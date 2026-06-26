"""
Conversation Router

This module provides the main conversation routing functionality for the conversational ASL agent,
handling user interactions, session management, and coordinating intent classification with response generation.
"""

import logging
import time
import uuid
from typing import Dict, Any, Optional, Tuple, List
from datetime import datetime

try:
    from .data_models import (
        ConversationContext, 
        ConversationInteraction, 
        ConversationIntent,
        TranslationResult,
        InputType
    )
    from .memory_manager import ConversationMemoryManager
    from .intent_classifier import ConversationIntentClassifier
    from .nlu_engine import NaturalLanguageUnderstandingEngine
    from .conversation_orchestrator import ConversationOrchestrator
    from .response_formatter import ConversationResponseFormatter
except ImportError:
    from data_models import (
        ConversationContext, 
        ConversationInteraction, 
        ConversationIntent,
        TranslationResult,
        InputType
    )
    from memory_manager import ConversationMemoryManager
    from intent_classifier import ConversationIntentClassifier
    from nlu_engine import NaturalLanguageUnderstandingEngine
    from conversation_orchestrator import ConversationOrchestrator
    from response_formatter import ConversationResponseFormatter
try:
    from .error_handler import ConversationErrorHandler
except ImportError:
    from error_handler import ConversationErrorHandler

logger = logging.getLogger(__name__)

class ConversationSession:
    """
    Data class representing a conversation session
    
    Contains session metadata and configuration for conversation management.
    """
    
    def __init__(self, session_id: str, user_id: Optional[str] = None, 
                 metadata: Optional[Dict[str, Any]] = None):
        """
        Initialize a conversation session
        
        Args:
            session_id: Unique session identifier
            user_id: Optional user identifier
            metadata: Optional session metadata
        """
        self.session_id = session_id
        self.user_id = user_id
        self.metadata = metadata or {}
        self.created_at = datetime.now()
        self.last_activity = datetime.now()
        self.is_active = True
        
    def update_activity(self):
        """Update last activity timestamp"""
        self.last_activity = datetime.now()
    
    def get_session_duration(self) -> float:
        """Get session duration in seconds"""
        return (self.last_activity - self.created_at).total_seconds()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert session to dictionary"""
        return {
            'session_id': self.session_id,
            'user_id': self.user_id,
            'metadata': self.metadata,
            'created_at': self.created_at.isoformat(),
            'last_activity': self.last_activity.isoformat(),
            'is_active': self.is_active,
            'duration_seconds': self.get_session_duration()
        }

class ConversationResponse:
    """
    Data class representing a conversation response
    
    Contains the response message and metadata about the conversation interaction.
    """
    
    def __init__(self, message: str, session_id: str, 
                 translation_result: Optional[TranslationResult] = None,
                 metadata: Optional[Dict[str, Any]] = None):
        """
        Initialize a conversation response
        
        Args:
            message: Response message to send to user
            session_id: Session identifier
            translation_result: Optional translation result
            metadata: Optional response metadata
        """
        self.message = message
        self.session_id = session_id
        self.translation_result = translation_result
        self.metadata = metadata or {}
        self.timestamp = datetime.now()
        self.response_id = f"resp_{int(time.time())}_{str(uuid.uuid4())[:8]}"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert response to dictionary"""
        return {
            'response_id': self.response_id,
            'message': self.message,
            'session_id': self.session_id,
            'translation_result': self.translation_result.to_dict() if self.translation_result else None,
            'metadata': self.metadata,
            'timestamp': self.timestamp.isoformat()
        }

class ConversationRouter:
    """
    Main conversation router that handles all user interactions
    
    This class serves as the primary entry point for conversational interactions,
    coordinating between intent classification, session management, workflow orchestration,
    and response generation using AgentCore Memory integration.
    """
    
    def __init__(self, memory_manager: Optional[ConversationMemoryManager] = None):
        """
        Initialize the conversation router
        
        Args:
            memory_manager: Optional memory manager instance. If None, creates a new one.
        """
        self.memory_manager = memory_manager or ConversationMemoryManager()
        self.intent_classifier = ConversationIntentClassifier()
        self.nlu_engine = NaturalLanguageUnderstandingEngine()
        self.orchestrator = ConversationOrchestrator(self.memory_manager)
        self.response_formatter = ConversationResponseFormatter()
        self.error_handler = ConversationErrorHandler()
        
        # Session management
        self.active_sessions: Dict[str, ConversationSession] = {}
        self.session_timeout = 24 * 60 * 60  # 24 hours in seconds
        self.cleanup_interval = 60 * 60  # 1 hour in seconds
        self.last_cleanup = time.time()
        
        logger.info("ConversationRouter initialized with AgentCore Memory integration")
    
    def handle_conversation(self, user_input: str, session_id: Optional[str] = None,
                          user_id: Optional[str] = None, 
                          metadata: Optional[Dict[str, Any]] = None) -> ConversationResponse:
        """
        Handle a conversational interaction with the user
        
        This is the main entry point for processing user interactions. It coordinates
        session management, intent classification, workflow orchestration, and response generation.
        
        Args:
            user_input: The user's message or input
            session_id: Optional session identifier for context persistence
            user_id: Optional user identifier
            metadata: Optional additional context and parameters
        
        Returns:
            ConversationResponse: Complete response with message and metadata
        """
        start_time = time.time()
        
        try:
            # Initialize or retrieve session
            session = self.initialize_session(session_id, user_id, metadata)
            session_id = session.session_id
            
            # Get conversation context from memory
            context = self.memory_manager.get_conversation_context(session_id, user_id)
            
            # Perform periodic cleanup if needed
            self._perform_periodic_cleanup()
            
            # Classify user intent using NLU engine
            nlu_result = self.nlu_engine.understand(user_input, metadata, context)
            
            logger.info(f"Classified intent: {nlu_result.intent.value} (confidence: {nlu_result.confidence:.2f})")
            
            # Create interaction record
            interaction = ConversationInteraction(
                timestamp=datetime.now(),
                user_input=user_input,
                intent=nlu_result.intent,
                agent_response="",  # Will be filled after processing
                translation_result=None,
                metadata=metadata or {}
            )
            
            # Route to appropriate handler based on intent
            response_message, translation_result = self._route_intent(
                nlu_result, context, session_id
            )
            
            # Update interaction with response and result
            interaction.agent_response = response_message
            interaction.translation_result = translation_result
            interaction.processing_time = time.time() - start_time
            
            # Add interaction to context and update memory using enhanced session management
            context.add_interaction(interaction)
            update_success = self.memory_manager.update_session(session_id, context)
            
            if not update_success:
                logger.warning(f"Failed to update session {session_id}, session may have expired")
            
            # Update session activity
            session.update_activity()
            
            # Create response object
            response = ConversationResponse(
                message=response_message,
                session_id=session_id,
                translation_result=translation_result,
                metadata={
                    'intent': nlu_result.intent.value,
                    'confidence': nlu_result.confidence,
                    'processing_time': time.time() - start_time,
                    'session_duration': session.get_session_duration()
                }
            )
            
            logger.info(f"Conversation handled successfully for session: {session_id}")
            return response
            
        except Exception as e:
            error_msg = f"Error handling conversation: {str(e)}"
            logger.error(error_msg, exc_info=True)
            
            # Create error response
            error_response = self._create_error_response(
                error_msg, session_id or "unknown", user_input, metadata
            )
            
            return error_response
    
    def initialize_session(self, session_id: Optional[str] = None, 
                         user_id: Optional[str] = None,
                         metadata: Optional[Dict[str, Any]] = None) -> ConversationSession:
        """
        Initialize a new conversation session or retrieve an existing one with enhanced lifecycle management
        
        Args:
            session_id: Optional session identifier
            user_id: Optional user identifier
            metadata: Optional session metadata
        
        Returns:
            ConversationSession: Initialized or existing session
        """
        # Generate session ID if not provided
        if not session_id:
            session_id = f"session_{int(time.time())}_{str(uuid.uuid4())[:8]}"
        
        # Check if session already exists in memory
        if session_id in self.active_sessions:
            session = self.active_sessions[session_id]
            
            # Check if session should be cleaned up based on timeout policies
            should_cleanup, cleanup_reason = self._evaluate_session_timeout(session)
            if should_cleanup:
                logger.info(f"Session {session_id} expired: {cleanup_reason}, creating new session")
                self.cleanup_session(session_id)
                # Continue to create new session below
            else:
                session.update_activity()
                logger.debug(f"Retrieved existing session: {session_id}")
                return session
        
        # Create new session with enhanced lifecycle management
        session = ConversationSession(
            session_id=session_id,
            user_id=user_id,
            metadata=metadata
        )
        
        # Store in active sessions
        self.active_sessions[session_id] = session
        
        # Create conversation context using memory manager's enhanced session creation
        try:
            initial_preferences = metadata.get('user_preferences') if metadata else None
            self.memory_manager.create_session(session_id, user_id, initial_preferences)
            logger.info(f"Initialized new conversation session with enhanced lifecycle: {session_id}")
        except Exception as e:
            logger.error(f"Error creating session context for {session_id}: {e}")
            # Continue with basic session even if context creation fails
        
        return session
    
    def cleanup_session(self, session_id: str) -> bool:
        """
        Clean up a conversation session with enhanced lifecycle management
        
        Args:
            session_id: The session identifier to clean up
        
        Returns:
            bool: True if cleanup was successful, False otherwise
        """
        try:
            # Remove from active sessions
            session_removed = False
            if session_id in self.active_sessions:
                del self.active_sessions[session_id]
                session_removed = True
            
            # Clean up memory data using enhanced cleanup
            cleanup_success = self.memory_manager.cleanup_session(session_id)
            
            logger.info(f"Cleaned up session: {session_id} "
                       f"(local session removed: {session_removed}, memory cleanup: {cleanup_success})")
            return cleanup_success
            
        except Exception as e:
            logger.error(f"Error cleaning up session {session_id}: {e}")
            return False
    
    def _route_intent(self, nlu_result, context: ConversationContext, 
                     session_id: str) -> Tuple[str, Optional[TranslationResult]]:
        """
        Route intent to appropriate handler and generate response
        
        Args:
            nlu_result: Natural language understanding result
            context: Conversation context
            session_id: Session identifier
        
        Returns:
            Tuple of (response_message, translation_result)
        """
        intent = nlu_result.intent
        parameters = nlu_result.parameters
        
        try:
            # Handle translation intents through orchestrator
            if intent in [ConversationIntent.TEXT_TO_ASL, 
                         ConversationIntent.AUDIO_TO_ASL, 
                         ConversationIntent.ASL_TO_TEXT]:
                
                # Execute translation workflow
                translation_result = self.orchestrator.execute_translation_flow(
                    nlu_result, context
                )
                
                # Format response using response formatter
                response_message = self.response_formatter.format_translation_response(
                    translation_result, context
                )
                
                return response_message, translation_result
            
            # Handle non-translation intents directly
            elif intent == ConversationIntent.HELP_REQUEST:
                help_topic = parameters.get('help_topic', 'general')
                response_message = self.response_formatter.format_help_response(
                    help_topic, context
                )
                return response_message, None
            
            elif intent == ConversationIntent.STATUS_CHECK:
                response_message = self._handle_status_check(parameters, context, session_id)
                return response_message, None
            
            elif intent == ConversationIntent.RETRY_REQUEST:
                response_message, translation_result = self._handle_retry_request(
                    parameters, context, session_id
                )
                return response_message, translation_result
            
            elif intent == ConversationIntent.CONTEXT_REFERENCE:
                response_message = self._handle_context_reference(parameters, context)
                return response_message, None
            
            elif intent == ConversationIntent.GREETING:
                response_message = self._handle_greeting(parameters, context)
                return response_message, None
            
            elif intent == ConversationIntent.UNKNOWN:
                response_message = self._handle_unknown_intent(nlu_result, context)
                return response_message, None
            
            else:
                # Default handler for unhandled intents
                response_message = self._handle_default_intent(nlu_result, context)
                return response_message, None
                
        except Exception as e:
            logger.error(f"Error routing intent {intent.value}: {e}", exc_info=True)
            
            # Use error handler to generate recovery response
            error_response = self.error_handler.handle_error(e, context, {
                'intent': intent.value,
                'parameters': parameters,
                'session_id': session_id
            })
            
            return error_response, None
    
    def _handle_status_check(self, parameters: Dict[str, Any], 
                           context: ConversationContext, session_id: str) -> str:
        """Handle status check requests"""
        # Get active operations for the session
        active_operations = self.orchestrator.get_active_operations(session_id)
        
        if not active_operations:
            return ("I don't currently have any active operations running for your session. "
                   "If you've submitted a translation request, it may have already completed. "
                   "Would you like me to help you with a new translation?")
        
        # Format status information
        status_parts = [f"I have {len(active_operations)} operations currently running:"]
        
        for i, operation in enumerate(active_operations, 1):
            progress_percent = int(operation.progress * 100)
            status_parts.append(
                f"{i}. {operation.operation_type.replace('_', ' ').title()}: "
                f"{progress_percent}% complete"
            )
            
            if operation.current_step:
                status_parts.append(f"   Current step: {operation.current_step}")
        
        return "\n".join(status_parts)
    
    def _handle_retry_request(self, parameters: Dict[str, Any], 
                            context: ConversationContext, session_id: str) -> Tuple[str, Optional[TranslationResult]]:
        """Handle retry requests"""
        if not context.last_translation:
            return ("I don't see a previous translation to retry. "
                   "Would you like to start a new translation instead?"), None
        
        wants_alternative = parameters.get('wants_alternative', False)
        
        if wants_alternative:
            return ("I understand you'd like to try a different approach for the translation. "
                   "In the full implementation, I would retry the translation with "
                   "alternative methods or settings."), None
        else:
            # For now, return a placeholder response
            # In full implementation, this would re-execute the last translation
            return ("I'll retry your last translation. In the full implementation, "
                   "I would re-run the translation process with the same parameters."), None
    
    def _handle_context_reference(self, parameters: Dict[str, Any], 
                                context: ConversationContext) -> str:
        """Handle context reference requests"""
        reference_type = parameters.get('reference_type', 'general')
        reference_index = parameters.get('reference_index', 'last')
        
        if reference_type == 'translation' and context.last_translation:
            # Show information about the last translation
            last_translation = context.last_translation
            
            if last_translation.success:
                response_parts = [
                    f"Here's information about your {reference_index} translation:",
                    f"• Input: {last_translation.input_text}",
                ]
                
                if last_translation.gloss:
                    response_parts.append(f"• ASL Gloss: {last_translation.gloss}")
                
                if last_translation.interpreted_text:
                    response_parts.append(f"• Interpreted Text: {last_translation.interpreted_text}")
                
                if last_translation.video_urls:
                    response_parts.append("• Generated Videos:")
                    for video_type, url in last_translation.video_urls.items():
                        response_parts.append(f"  - {video_type.title()}: {url}")
                
                return "\n".join(response_parts)
            else:
                return (f"Your {reference_index} translation attempt failed with error: "
                       f"{last_translation.error_message}")
        
        return ("I understand you're referring to something from our previous conversation, "
               "but I couldn't identify the specific item. Could you be more specific "
               "about what you'd like me to show or explain?")
    
    def _handle_greeting(self, parameters: Dict[str, Any], 
                        context: ConversationContext) -> str:
        """Handle greeting messages"""
        greeting_type = parameters.get('greeting_type', 'general')
        
        if not context.conversation_history or len(context.conversation_history) <= 1:
            # First interaction
            return ("Hello! I'm your conversational ASL translation assistant. "
                   "I can help you translate text to ASL, process audio files, "
                   "and analyze ASL videos. What would you like to do today?")
        else:
            # Returning user
            return "Hello again! How can I help you with ASL translation today?"
    
    def _handle_unknown_intent(self, nlu_result, context: ConversationContext) -> str:
        """Handle unknown intents"""
        confidence = nlu_result.confidence
        alternatives = nlu_result.alternative_intents
        original_input = nlu_result.parameters.get('original_input', '')
        
        response_parts = [
            f"I'm not entirely sure what you'd like me to do with: \"{original_input}\""
        ]
        
        if alternatives:
            alt_intents = [intent.value.replace('_', ' ') for intent, _ in alternatives[:2]]
            response_parts.append(f"Did you mean to: {' or '.join(alt_intents)}?")
        
        response_parts.append("You can ask me to translate text to ASL, process audio files, "
                            "analyze ASL videos, or ask for help if you need guidance.")
        
        return " ".join(response_parts)
    
    def _handle_default_intent(self, nlu_result, context: ConversationContext) -> str:
        """Handle default/unhandled intents"""
        return (f"I recognized that you want to {nlu_result.intent.value.replace('_', ' ')}, "
               f"but this functionality is still being implemented. "
               f"Please try asking for help or try a different request.")
    
    def _create_error_response(self, error_message: str, session_id: str, 
                             user_input: str, metadata: Optional[Dict[str, Any]]) -> ConversationResponse:
        """Create an error response"""
        error_response_message = (
            f"I apologize, but I encountered an unexpected issue: {error_message}. "
            f"Please try again, and if the problem continues, "
            f"you might want to start a new conversation or try a simpler request."
        )
        
        return ConversationResponse(
            message=error_response_message,
            session_id=session_id,
            metadata={
                'error': True,
                'error_message': error_message,
                'user_input': user_input,
                'original_metadata': metadata
            }
        )
    
    def _perform_periodic_cleanup(self):
        """Perform periodic cleanup of expired sessions with enhanced lifecycle management"""
        current_time = time.time()
        
        # Only run cleanup if enough time has passed
        if current_time - self.last_cleanup < self.cleanup_interval:
            return
        
        self.last_cleanup = current_time
        expired_sessions = []
        
        # Find expired sessions using enhanced timeout evaluation
        for session_id, session in self.active_sessions.items():
            should_cleanup, cleanup_reason = self._evaluate_session_timeout(session)
            if should_cleanup:
                expired_sessions.append((session_id, cleanup_reason))
        
        # Clean up expired sessions
        for session_id, reason in expired_sessions:
            logger.debug(f"Cleaning up session {session_id}: {reason}")
            self.cleanup_session(session_id)
        
        if expired_sessions:
            logger.info(f"Cleaned up {len(expired_sessions)} expired sessions")
        
        # Trigger memory manager's comprehensive cleanup
        memory_cleaned = self.memory_manager.cleanup_expired_sessions()
        if memory_cleaned > 0:
            logger.info(f"Memory manager cleaned up {memory_cleaned} additional sessions")
    
    def _evaluate_session_timeout(self, session: ConversationSession) -> tuple[bool, str]:
        """
        Evaluate whether a session should be cleaned up based on timeout policies
        
        Args:
            session: ConversationSession to evaluate
        
        Returns:
            Tuple of (should_cleanup: bool, reason: str)
        """
        try:
            current_time = datetime.now()
            
            # Check inactive timeout (use memory manager's timeout settings)
            inactive_timeout = getattr(self.memory_manager, 'inactive_session_timeout', self.session_timeout)
            inactive_duration = (current_time - session.last_activity).total_seconds()
            if inactive_duration > inactive_timeout:
                return True, f"Inactive for {inactive_duration:.0f}s (limit: {inactive_timeout}s)"
            
            # Check absolute session timeout
            absolute_timeout = getattr(self.memory_manager, 'session_ttl', 24 * 60 * 60)
            session_duration = session.get_session_duration()
            if session_duration > absolute_timeout:
                return True, f"Session age {session_duration:.0f}s (limit: {absolute_timeout}s)"
            
            return False, "Session within timeout limits"
            
        except Exception as e:
            logger.error(f"Error evaluating session timeout for {session.session_id}: {e}")
            return True, f"Evaluation error: {str(e)}"
    
    def get_session_info(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a conversation session
        
        Args:
            session_id: The session identifier
        
        Returns:
            Dict containing session information or None if session doesn't exist
        """
        try:
            # Get session from active sessions
            session = self.active_sessions.get(session_id)
            if not session:
                return None
            
            # Get context from memory
            context = self.memory_manager.get_conversation_context(session_id)
            
            session_info = session.to_dict()
            
            if context:
                session_info.update({
                    'interaction_count': len(context.conversation_history),
                    'last_translation': context.last_translation.input_text if context.last_translation else None,
                    'user_preferences': context.user_preferences,
                    'error_count': context.error_count,
                    'error_rate': context.get_error_rate()
                })
            
            return session_info
            
        except Exception as e:
            logger.error(f"Error getting session info for {session_id}: {e}")
            return None
    
    def get_active_sessions(self) -> List[Dict[str, Any]]:
        """
        Get information about all active sessions
        
        Returns:
            List of active session information
        """
        try:
            return [session.to_dict() for session in self.active_sessions.values()]
        except Exception as e:
            logger.error(f"Error getting active sessions: {e}")
            return []
    
    def migrate_session(self, session_id: str, from_version: str = "1.0", 
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
            return self.memory_manager.migrate_session_data(session_id, from_version, to_version)
        except Exception as e:
            logger.error(f"Error migrating session {session_id}: {e}")
            return False
    
    def get_router_status(self) -> Dict[str, Any]:
        """
        Get overall router status and metrics with enhanced session lifecycle information
        
        Returns:
            Dict containing comprehensive router status information
        """
        try:
            # Get basic router status
            basic_status = {
                'active_sessions_count': len(self.active_sessions),
                'active_session_ids': list(self.active_sessions.keys()),
                'session_timeout_seconds': self.session_timeout,
                'cleanup_interval_seconds': self.cleanup_interval,
                'last_cleanup_time': self.last_cleanup,
                'memory_manager_available': self.memory_manager is not None,
                'timestamp': datetime.now().isoformat()
            }
            
            # Add orchestrator status if available
            try:
                basic_status['orchestrator_status'] = self.orchestrator.get_orchestrator_status()
            except Exception as e:
                basic_status['orchestrator_status'] = {'error': str(e)}
            
            # Get enhanced session lifecycle stats from memory manager
            try:
                lifecycle_stats = self.memory_manager.get_session_lifecycle_stats()
                basic_status.update(lifecycle_stats)
            except Exception as e:
                basic_status['session_lifecycle_error'] = str(e)
            
            return basic_status
            
        except Exception as e:
            logger.error(f"Error getting router status: {e}")
            return {'error': str(e)}