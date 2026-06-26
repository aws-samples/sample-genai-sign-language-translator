"""
Conversational ASL Agent

Main agent class that provides conversational capabilities for ASL translation,
building upon the existing SignLanguageAgent patterns.
"""

import logging
import time
from typing import Dict, Any, Optional, List
from datetime import datetime

# Import existing SignLanguageAgent components
import sys
from pathlib import Path

# Add parent directory to path for imports
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir))

from signlanguageagent.utils import setup_logging, validate_payload, extract_response_content
from signlanguageagent.config import config
from signlanguageagent.monitoring import monitoring_manager

# Import conversational components
from .memory_manager import ConversationMemoryManager
from .data_models import ConversationContext, ConversationInteraction, TranslationResult, ConversationIntent
from .nlu_engine import NaturalLanguageUnderstandingEngine
from .response_formatter import ConversationResponseFormatter
from .error_handler import ConversationErrorHandler
from .alternative_suggestions import AlternativeApproachSuggester
from .error_recovery import GracefulErrorRecovery

# Configure logging
logger = setup_logging(config.agent.log_level)

class ConversationalASLAgent:
    """
    Enhanced ASL Agent with conversational capabilities
    
    This agent extends the existing SignLanguageAgent functionality with:
    - Natural conversation flow management
    - Context-aware interactions using AgentCore Memory
    - Enhanced response formatting
    - Session persistence across invocations
    """
    
    def __init__(self, memory_manager: Optional[ConversationMemoryManager] = None):
        """
        Initialize the conversational ASL agent
        
        Args:
            memory_manager: Optional memory manager instance. If None, creates a new one.
        """
        self.memory_manager = memory_manager or ConversationMemoryManager()
        self.nlu_engine = NaturalLanguageUnderstandingEngine()
        self.response_formatter = ConversationResponseFormatter()
        self.error_handler = ConversationErrorHandler()
        self.alternative_suggester = AlternativeApproachSuggester()
        self.error_recovery = GracefulErrorRecovery(self.error_handler, self.alternative_suggester)
        self.logger = logger
        
        # Initialize agent capabilities
        self.capabilities = {
            'text_to_asl': True,
            'audio_to_asl': True,
            'asl_to_text': True,
            'conversational_context': True,
            'session_persistence': True,
            'multi_modal_input': True,
            'intent_classification': True,
            'parameter_extraction': True,
            'context_aware_analysis': True
        }
        
        logger.info("ConversationalASLAgent initialized with NLU engine and AgentCore Memory integration")
    
    def handle_conversation(self, user_input: str, session_id: Optional[str] = None,
                          user_id: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Handle a conversational interaction with the user
        
        Args:
            user_input: The user's message or input
            session_id: Optional session identifier for context persistence
            user_id: Optional user identifier
            metadata: Optional additional context and parameters
        
        Returns:
            str: Conversational response to the user
        """
        operation_id = None
        try:
            # Start monitoring the conversation
            operation_id = monitoring_manager.log_request_start(
                session_id or "anonymous",
                user_id or "anonymous",
                "conversation",
                user_input
            )
            
            # Get or create conversation context
            context = self.memory_manager.get_conversation_context(session_id, user_id)
            
            # Perform natural language understanding
            nlu_result = self.nlu_engine.understand(user_input, metadata, context)
            
            # Create interaction record with classified intent
            interaction = ConversationInteraction(
                timestamp=datetime.now(),
                user_input=user_input,
                intent=nlu_result.intent,
                agent_response="",  # Will be filled after processing
                translation_result=None,
                metadata=metadata or {}
            )
            
            # Store the interaction (will be updated with response later)
            context.conversation_history.append(interaction)
            
            # Update context in memory
            self.memory_manager.update_conversation_context(session_id, context)
            
            # Generate response based on NLU result
            response = self._generate_response_from_nlu(nlu_result, context)
            
            # Update interaction with response
            interaction.agent_response = response
            
            # Update context with final interaction
            self.memory_manager.update_conversation_context(session_id, context)
            
            # Add proactive tips if appropriate
            proactive_tip = self.response_formatter.generate_proactive_tips(context)
            if proactive_tip:
                response += f"\n\n{proactive_tip}"
            
            # Log successful completion
            if operation_id:
                monitoring_manager.log_request_success(
                    operation_id,
                    session_id or "anonymous",
                    len(response)
                )
            
            logger.info(f"Conversation handled successfully for session: {session_id}")
            return response
            
        except Exception as e:
            error_msg = f"Error handling conversation: {str(e)}"
            logger.error(error_msg, exc_info=True)
            
            # Log error
            if operation_id:
                monitoring_manager.log_request_failure(
                    operation_id,
                    session_id or "anonymous",
                    e,
                    "conversation_error"
                )
            
            # Use enhanced error handling with recovery
            return self._handle_conversation_error(e, context, session_id)
    
    def _generate_response_from_nlu(self, nlu_result, context: ConversationContext) -> str:
        """
        Generate response based on NLU result
        
        Args:
            nlu_result: Natural language understanding result
            context: Current conversation context
        
        Returns:
            str: Generated response message
        """
        intent = nlu_result.intent
        parameters = nlu_result.parameters
        confidence = nlu_result.confidence
        
        # Handle different intents
        if intent == ConversationIntent.GREETING:
            return self._generate_greeting_response(parameters, context)
        
        elif intent == ConversationIntent.HELP_REQUEST:
            return self._generate_help_response_from_nlu(parameters, context)
        
        elif intent == ConversationIntent.TEXT_TO_ASL:
            return self._generate_text_to_asl_response(parameters, context)
        
        elif intent == ConversationIntent.AUDIO_TO_ASL:
            return self._generate_audio_to_asl_response(parameters, context)
        
        elif intent == ConversationIntent.ASL_TO_TEXT:
            return self._generate_asl_to_text_response(parameters, context)
        
        elif intent == ConversationIntent.STATUS_CHECK:
            return self._generate_status_response(parameters, context)
        
        elif intent == ConversationIntent.RETRY_REQUEST:
            return self._generate_retry_response(parameters, context)
        
        elif intent == ConversationIntent.CONTEXT_REFERENCE:
            return self._generate_context_reference_response(parameters, context)
        
        elif intent == ConversationIntent.UNKNOWN:
            return self._generate_unknown_intent_response(nlu_result, context)
        
        else:
            return self._generate_default_response(nlu_result, context)
    
    def _generate_greeting_response(self, parameters: Dict[str, Any], context: ConversationContext) -> str:
        """Generate greeting response"""
        greeting_type = parameters.get('greeting_type', 'general')
        
        if not context.conversation_history or len(context.conversation_history) <= 1:
            return ("Hello! I'm your conversational ASL translation assistant. "
                   "I can help you translate text to ASL, process audio files, "
                   "and analyze ASL videos. What would you like to do today?")
        else:
            return "Hello again! How can I help you with ASL translation today?"
    
    def _generate_help_response_from_nlu(self, parameters: Dict[str, Any], context: ConversationContext) -> str:
        """Generate help response based on NLU parameters using response formatter"""
        help_topic = parameters.get('help_topic', 'general')
        return self.response_formatter.format_help_response(help_topic, context)
    
    def _generate_text_to_asl_response(self, parameters: Dict[str, Any], context: ConversationContext) -> str:
        """Generate response for text-to-ASL intent"""
        text_content = parameters.get('text')
        
        if not text_content:
            return ("I understand you want to translate text to ASL, but I couldn't identify "
                   "the specific text to translate. Could you please provide the text you'd like "
                   "to convert to ASL? For example: 'Translate \"Hello, how are you?\" to ASL'")
        
        # Create a mock translation result for demonstration
        # In the full implementation, this would call the actual translation orchestrator
        from .data_models import create_text_translation_result, InputType
        
        mock_result = create_text_translation_result(
            input_text=text_content,
            gloss="HELLO HOW YOU",  # Mock gloss
            video_urls={
                'pose': 'https://example.com/pose_video.mp4',
                'sign': 'https://example.com/sign_video.mp4',
                'avatar': 'https://example.com/avatar_video.mp4'
            },
            processing_time=2.5,
            success=True
        )
        
        # Use response formatter to create conversational response
        detail_level = self.response_formatter.determine_appropriate_detail_level(mock_result, context)
        formatted_response = self.response_formatter.format_translation_response(
            mock_result, context, detail_level
        )
        
        # Add note about mock implementation
        formatted_response += ("\n\n*Note: This is a demonstration response. "
                             "Full translation functionality will be implemented "
                             "in the conversation orchestrator task.*")
        
        return formatted_response
    
    def _generate_audio_to_asl_response(self, parameters: Dict[str, Any], context: ConversationContext) -> str:
        """Generate response for audio-to-ASL intent"""
        has_audio_file = 'audio_file' in parameters or 'audio_filename' in parameters
        
        if not has_audio_file:
            return ("I understand you want to translate audio to ASL, but I don't see "
                   "an audio file attached. Please upload an audio file or provide "
                   "a reference to the audio you'd like to translate.")
        
        return ("I can see you want to translate audio to ASL. In the full implementation, "
               "I would now transcribe your audio file and then convert the text to ASL. "
               "This functionality will be added in the conversation orchestrator task.")
    
    def _generate_asl_to_text_response(self, parameters: Dict[str, Any], context: ConversationContext) -> str:
        """Generate response for ASL-to-text intent"""
        has_video = 'video_file' in parameters or 'video_filename' in parameters
        analysis_mode = parameters.get('analysis_mode', 'file')
        
        if not has_video and analysis_mode == 'file':
            return ("I understand you want to analyze ASL video, but I don't see "
                   "a video file attached. Please upload an ASL video file or "
                   "let me know if you want to use live camera analysis.")
        
        if analysis_mode == 'stream':
            return ("I can help you analyze ASL from a live video stream. "
                   "In the full implementation, I would now start the video analysis "
                   "process and interpret the ASL signs to English text.")
        else:
            return ("I can analyze your ASL video and interpret it to English text. "
                   "In the full implementation, I would now process your video file "
                   "and provide the interpreted text.")
    
    def _generate_status_response(self, parameters: Dict[str, Any], context: ConversationContext) -> str:
        """Generate status check response"""
        if not context.current_operations:
            return ("I don't currently have any active operations running. "
                   "If you've submitted a translation request, it may have already completed. "
                   "Would you like me to help you with a new translation?")
        
        return (f"I have {len(context.current_operations)} operations currently running. "
               f"In the full implementation, I would provide detailed status updates "
               f"for each operation.")
    
    def _generate_retry_response(self, parameters: Dict[str, Any], context: ConversationContext) -> str:
        """Generate retry request response"""
        if not context.last_translation:
            return ("I don't see a previous translation to retry. "
                   "Would you like to start a new translation instead?")
        
        wants_alternative = parameters.get('wants_alternative', False)
        
        if wants_alternative:
            return ("I understand you'd like to try a different approach for the translation. "
                   "In the full implementation, I would retry the translation with "
                   "alternative methods or settings.")
        else:
            return ("I'll retry your last translation. In the full implementation, "
                   "I would re-run the translation process with the same parameters.")
    
    def _generate_context_reference_response(self, parameters: Dict[str, Any], context: ConversationContext) -> str:
        """Generate context reference response"""
        reference_type = parameters.get('reference_type', 'general')
        referenced_item = parameters.get('referenced_item')
        
        if not referenced_item:
            return ("I understand you're referring to something from our previous conversation, "
                   "but I couldn't identify the specific item. Could you be more specific "
                   "about what you'd like me to show or explain?")
        
        return (f"I can see you're referring to a previous {reference_type}. "
               f"In the full implementation, I would retrieve and display "
               f"the specific item you're referencing.")
    
    def _generate_unknown_intent_response(self, nlu_result, context: ConversationContext) -> str:
        """Generate response for unknown intent"""
        confidence = nlu_result.confidence
        alternatives = nlu_result.alternative_intents
        
        response_parts = [
            f"I'm not entirely sure what you'd like me to do with: \"{nlu_result.parameters.get('original_input', '')}\""
        ]
        
        if alternatives:
            alt_intents = [intent.value.replace('_', ' ') for intent, _ in alternatives[:2]]
            response_parts.append(f"Did you mean to: {' or '.join(alt_intents)}?")
        
        response_parts.append("You can ask me to translate text to ASL, process audio files, "
                            "analyze ASL videos, or ask for help if you need guidance.")
        
        return " ".join(response_parts)
    
    def _generate_default_response(self, nlu_result, context: ConversationContext) -> str:
        """Generate default response for unhandled intents"""
        return (f"I recognized that you want to {nlu_result.intent.value.replace('_', ' ')}, "
               f"but this functionality is still being implemented. "
               f"Please try asking for help or try a different request.")
    
    def _generate_basic_response(self, user_input: str, context: ConversationContext) -> str:
        """
        Generate a basic conversational response (placeholder implementation)
        
        This will be enhanced in later tasks with proper intent classification,
        workflow orchestration, and response formatting.
        
        Args:
            user_input: The user's input message
            context: Current conversation context
        
        Returns:
            str: Basic response message
        """
        # Simple greeting detection
        if any(greeting in user_input.lower() for greeting in ['hello', 'hi', 'hey']):
            if not context.conversation_history or len(context.conversation_history) <= 1:
                return ("Hello! I'm your conversational ASL translation assistant. "
                       "I can help you translate text to ASL, process audio files, "
                       "and analyze ASL videos. What would you like to do today?")
            else:
                return "Hello again! How can I help you with ASL translation today?"
        
        # Simple help detection
        if any(help_word in user_input.lower() for help_word in ['help', 'what can you do']):
            return self._generate_help_response(context)
        
        # Default response acknowledging the input
        return (f"I understand you said: \"{user_input}\". "
               f"I'm still learning to have better conversations! "
               f"In future updates, I'll be able to classify your intent, "
               f"orchestrate translation workflows, and provide more helpful responses. "
               f"For now, I can remember our conversation context across sessions.")
    
    def _generate_help_response(self, context: ConversationContext) -> str:
        """Generate a help response based on conversation context"""
        help_sections = [
            "I'm your conversational ASL translation assistant! Here's what I can help you with:",
            "",
            "🔤 **Text to ASL Translation**",
            "• Convert English text to ASL gloss notation and generate videos",
            "",
            "🎵 **Audio to ASL Translation**", 
            "• Process audio files and convert speech to ASL",
            "",
            "📹 **ASL Video Analysis**",
            "• Analyze ASL videos and interpret signs back to English",
            "",
            "💬 **Conversational Context**",
            "• I remember our conversation and can build upon previous interactions",
            "",
            "Just tell me what you'd like to translate or analyze, and I'll guide you through the process!"
        ]
        
        return "\n".join(help_sections)
    
    def _generate_translation_help(self) -> str:
        """Generate help for translation features"""
        return ("**Translation Help**\n\n"
               "I can help you translate between English and ASL in several ways:\n\n"
               "• **Text to ASL**: Just tell me what text you want to translate\n"
               "  Example: 'Translate \"Good morning\" to ASL'\n\n"
               "• **Audio to ASL**: Upload an audio file and I'll transcribe and translate it\n"
               "  Example: 'Process this audio file to ASL'\n\n"
               "• **ASL to Text**: Upload an ASL video and I'll interpret it to English\n"
               "  Example: 'Analyze this ASL video'")
    
    def _generate_audio_help(self) -> str:
        """Generate help for audio features"""
        return ("**Audio Processing Help**\n\n"
               "I can process audio files and convert speech to ASL:\n\n"
               "• Supported formats: MP3, WAV, M4A, AAC, OGG\n"
               "• I'll transcribe the speech to text first\n"
               "• Then convert the text to ASL gloss and videos\n"
               "• You can upload files or reference existing audio\n\n"
               "Just say something like: 'Translate this audio file to ASL'")
    
    def _generate_video_help(self) -> str:
        """Generate help for video features"""
        return ("**ASL Video Analysis Help**\n\n"
               "I can analyze ASL videos and interpret them to English:\n\n"
               "• Supported formats: MP4, AVI, MOV, WebM\n"
               "• I can analyze uploaded files or live camera streams\n"
               "• I'll interpret the ASL signs and provide English text\n"
               "• You can request different analysis detail levels\n\n"
               "Just say: 'Analyze this ASL video' or 'What does this signing mean?'")
    
    def _generate_features_help(self) -> str:
        """Generate help for features overview"""
        return ("**My Capabilities**\n\n"
               "🔤 **Text to ASL Translation**\n"
               "• Convert English text to ASL gloss notation\n"
               "• Generate pose, sign, and avatar videos\n\n"
               "🎵 **Audio to ASL Translation**\n"
               "• Transcribe speech from audio files\n"
               "• Convert transcribed text to ASL\n\n"
               "📹 **ASL Video Analysis**\n"
               "• Interpret ASL signs from videos\n"
               "• Support for file uploads and live streams\n\n"
               "💬 **Conversational Context**\n"
               "• Remember our conversation history\n"
               "• Reference previous translations\n"
               "• Provide contextual help and suggestions")
    
    def _generate_getting_started_help(self) -> str:
        """Generate getting started help"""
        return ("**Getting Started**\n\n"
               "Welcome! Here's how to get started with ASL translation:\n\n"
               "1. **For Text Translation**: Simply tell me what you want to translate\n"
               "   Try: 'Translate \"Hello world\" to ASL'\n\n"
               "2. **For Audio Translation**: Upload an audio file and mention translation\n"
               "   Try: 'Convert this audio to ASL'\n\n"
               "3. **For ASL Analysis**: Upload an ASL video for interpretation\n"
               "   Try: 'What does this ASL video say?'\n\n"
               "4. **Need Help?**: Just ask! I can explain any feature in detail\n\n"
               "I'll remember our conversation, so you can build on previous translations!")
    
    def _generate_examples_help(self) -> str:
        """Generate examples help"""
        return ("**Usage Examples**\n\n"
               "Here are some example requests you can try:\n\n"
               "**Text Translation:**\n"
               "• 'Translate \"How are you today?\" to ASL'\n"
               "• 'Convert this text to sign language: \"Nice to meet you\"'\n"
               "• 'Turn \"Thank you very much\" into ASL video'\n\n"
               "**Audio Processing:**\n"
               "• 'Process this audio file and convert to ASL'\n"
               "• 'Transcribe and translate this recording'\n\n"
               "**ASL Analysis:**\n"
               "• 'Analyze this ASL video'\n"
               "• 'What is this person signing?'\n"
               "• 'Interpret this sign language video'\n\n"
               "**Conversation:**\n"
               "• 'Show me that last translation again'\n"
               "• 'Try that again with better quality'\n"
               "• 'What can you do?'")
    
    def _generate_general_help(self) -> str:
        """Generate general help response"""
        return self._generate_help_response(ConversationContext())
    
    def _handle_conversation_error(self, error: Exception, context: ConversationContext, 
                                 session_id: Optional[str] = None) -> str:
        """
        Handle conversation errors with enhanced error handling and recovery
        
        Args:
            error: The exception that occurred
            context: Current conversation context
            session_id: Optional session identifier
        
        Returns:
            str: Conversational error response with recovery suggestions
        """
        try:
            # Update context to track error
            context.error_count += 1
            
            # Check if we should attempt automatic recovery
            if self.error_recovery.should_attempt_recovery(error, context):
                # For now, we'll provide recovery suggestions rather than automatic retry
                # since we don't have the actual operation functions to retry
                
                # Generate error response with recovery suggestions
                error_response = self.error_handler.handle_error(
                    error, context, {'operation_type': 'conversation_handling'}
                )
                
                # Add alternative suggestions
                error_classification = self.error_handler.classify_error(error)
                suggestions = self.alternative_suggester.generate_suggestions(
                    'conversation_handling', error_classification, context
                )
                
                if suggestions:
                    suggestions_text = self.alternative_suggester.format_suggestions_for_user(
                        suggestions, context
                    )
                    error_response += f"\n\n{suggestions_text}"
                
                # Update context in memory
                if session_id:
                    self.memory_manager.update_conversation_context(session_id, context)
                
                return error_response
            
            else:
                # Simple error handling for cases where recovery isn't appropriate
                return self.error_handler.handle_error(
                    error, context, {'operation_type': 'conversation_handling'}
                )
                
        except Exception as handler_error:
            # Fallback if error handling itself fails
            logger.error(f"Error handler failed: {handler_error}", exc_info=True)
            return self._generate_fallback_error_response(str(error))
    
    def _generate_error_response(self, error_message: str) -> str:
        """Generate a user-friendly error response using response formatter"""
        # Create a dummy context for error formatting
        dummy_context = ConversationContext()
        error_exception = Exception(error_message)
        return self.error_handler.handle_error(error_exception, dummy_context)
    
    def _generate_fallback_error_response(self, error_message: str) -> str:
        """Generate a basic fallback error response"""
        return (f"I apologize, but I encountered an unexpected issue: {error_message}. "
               f"Please try again, and if the problem continues, "
               f"you might want to start a new conversation or try a simpler request.")
    
    def get_session_info(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a conversation session
        
        Args:
            session_id: The session identifier
        
        Returns:
            Dict containing session information or None if session doesn't exist
        """
        try:
            context = self.memory_manager.get_conversation_context(session_id)
            if context:
                return {
                    'session_id': context.session_id,
                    'user_id': context.user_id,
                    'session_start_time': context.session_start_time.isoformat(),
                    'last_activity_time': context.last_activity_time.isoformat(),
                    'interaction_count': len(context.conversation_history),
                    'last_translation': context.last_translation.input_text if context.last_translation else None,
                    'user_preferences': context.user_preferences
                }
            return None
        except Exception as e:
            logger.error(f"Error getting session info: {e}")
            return None
    
    def cleanup_session(self, session_id: str) -> bool:
        """
        Clean up a conversation session
        
        Args:
            session_id: The session identifier to clean up
        
        Returns:
            bool: True if cleanup was successful, False otherwise
        """
        try:
            return self.memory_manager.cleanup_session(session_id)
        except Exception as e:
            logger.error(f"Error cleaning up session {session_id}: {e}")
            return False
    
    def get_capabilities(self) -> Dict[str, Any]:
        """
        Get agent capabilities information
        
        Returns:
            Dict containing capability information
        """
        return {
            'capabilities': self.capabilities,
            'memory_integration': True,
            'session_persistence': True,
            'supported_inputs': ['text', 'audio', 'video'],
            'supported_outputs': ['text', 'gloss', 'video_urls'],
            'conversation_features': [
                'context_awareness',
                'intent_classification',
                'parameter_extraction',
                'context_aware_analysis',
                'natural_responses',
                'error_recovery',
                'help_system',
                'multi_modal_input_detection',
                'conversation_history_analysis',
                'user_pattern_recognition',
                'proactive_tips',
                'contextual_guidance',
                'next_step_suggestions',
                'follow_up_recommendations'
            ]
        }
    
    def handle_translation_error(self, error: Exception, operation: str, 
                                parameters: Dict[str, Any], context: ConversationContext) -> str:
        """
        Handle translation-specific errors with recovery suggestions
        
        Args:
            error: The translation error that occurred
            operation: The translation operation that failed
            parameters: Parameters used in the failed operation
            context: Current conversation context
        
        Returns:
            str: Conversational error response with recovery guidance
        """
        # Classify the error
        error_classification = self.error_handler.classify_error(
            error, {'operation_type': operation, 'parameters': parameters}
        )
        
        # Generate conversational error response
        error_response = self.error_handler.generate_error_response(
            error, error_classification, context, {'operation': operation}
        )
        
        # Add specific alternative suggestions for translation errors
        suggestions = self.alternative_suggester.generate_suggestions(
            operation, error_classification, context, {'parameters': parameters}
        )
        
        if suggestions:
            suggestions_text = self.alternative_suggester.format_suggestions_for_user(
                suggestions, context
            )
            error_response += f"\n\n{suggestions_text}"
        
        return error_response
    
    def suggest_input_format_corrections(self, input_type: str, error_details: str,
                                       context: ConversationContext) -> str:
        """
        Provide specific input format correction guidance
        
        Args:
            input_type: Type of input that had format issues
            error_details: Details about the format error
            context: Current conversation context
        
        Returns:
            str: Formatted guidance for input corrections
        """
        try:
            # Map string input type to enum
            input_type_enum = InputType(input_type.lower())
        except ValueError:
            input_type_enum = InputType.UNKNOWN
        
        # Get format guidance
        guidance = self.alternative_suggester.get_input_format_guidance(input_type_enum)
        
        response_parts = [
            f"I noticed an issue with your {input_type} input. Here's how to fix it:",
            "",
            f"**{guidance['title']}**",
            guidance['description'],
            "",
            "**Guidelines:**"
        ]
        
        for guideline in guidance['guidelines']:
            response_parts.append(f"• {guideline}")
        
        if guidance.get('examples'):
            response_parts.extend(["", "**Examples:**"])
            for example in guidance['examples']:
                response_parts.append(f"• {example}")
        
        response_parts.extend([
            "",
            "Once you've adjusted your input according to these guidelines, please try again!"
        ])
        
        return "\n".join(response_parts)
    
    def generate_retry_workflow(self, failed_operation: str, context: ConversationContext) -> str:
        """
        Generate step-by-step retry workflow for failed operations
        
        Args:
            failed_operation: Description of the operation that failed
            context: Current conversation context
        
        Returns:
            str: Step-by-step retry instructions
        """
        workflow_steps = self.alternative_suggester.generate_retry_workflow_suggestions(
            failed_operation, context
        )
        
        if not workflow_steps:
            return ("I don't have specific retry steps for this operation, "
                   "but you could try simplifying your request or asking for help.")
        
        response_parts = [
            f"Here's a step-by-step approach to retry your {failed_operation}:",
            ""
        ]
        
        for i, step in enumerate(workflow_steps, 1):
            response_parts.append(f"{i}. {step}")
        
        response_parts.extend([
            "",
            "Take your time with each step, and let me know if you need help with any of them!"
        ])
        
        return "\n".join(response_parts)
    
    async def attempt_error_recovery(self, error: Exception, operation: str,
                                   parameters: Dict[str, Any], context: ConversationContext) -> Tuple[bool, Optional[Any], str]:
        """
        Attempt automatic error recovery for failed operations
        
        Args:
            error: The exception that occurred
            operation: Description of the failed operation
            parameters: Parameters used in the failed operation
            context: Current conversation context
        
        Returns:
            Tuple of (success, recovered_result, conversational_message)
        """
        try:
            # Use the error recovery system
            recovery_result, recovered_data, message = await self.error_recovery.recover_from_error(
                error, operation, parameters, context
            )
            
            success = recovery_result in ['success', 'partial_success']
            return success, recovered_data, message
            
        except Exception as recovery_error:
            logger.error(f"Error recovery failed: {recovery_error}", exc_info=True)
            
            # Fallback to basic error handling
            fallback_message = self.error_handler.handle_error(error, context)
            return False, None, fallback_message
    
    def get_error_recovery_status(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get status of any ongoing error recovery operations
        
        Args:
            session_id: Session identifier
        
        Returns:
            Dict containing recovery status or None if no recovery in progress
        """
        # This would be implemented to track recovery sessions
        # For now, return None as we don't have persistent recovery tracking
        return None