"""
Conversation management module for the GenASL Sign Language Agent

This module provides conversational capabilities including context management,
natural language understanding, and user-friendly response formatting.
"""

import logging
import time
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)

class ConversationState(Enum):
    """Enumeration of conversation states"""
    GREETING = "greeting"
    TEXT_TRANSLATION = "text_translation"
    AUDIO_PROCESSING = "audio_processing"
    VIDEO_ANALYSIS = "video_analysis"
    HELP_REQUEST = "help_request"
    ERROR_HANDLING = "error_handling"
    FOLLOWUP = "followup"

class RequestType(Enum):
    """Enumeration of request types"""
    TEXT_TO_ASL = "text_to_asl"
    AUDIO_TO_ASL = "audio_to_asl"
    ASL_TO_TEXT = "asl_to_text"
    HELP = "help"
    STATUS = "status"
    UNKNOWN = "unknown"

@dataclass
class ConversationContext:
    """Context information for ongoing conversations"""
    session_id: Optional[str] = None
    user_id: Optional[str] = None
    state: ConversationState = ConversationState.GREETING
    last_request_type: Optional[RequestType] = None
    last_translation_text: Optional[str] = None
    last_gloss: Optional[str] = None
    last_video_urls: Dict[str, str] = field(default_factory=dict)
    pending_operations: List[str] = field(default_factory=list)
    error_count: int = 0
    conversation_history: List[Dict[str, Any]] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

class ConversationManager:
    """Manages conversational interactions and context"""
    
    def __init__(self):
        self.contexts: Dict[str, ConversationContext] = {}
        logger.info("ConversationManager initialized")
    
    def get_or_create_context(self, session_id: Optional[str] = None, 
                            user_id: Optional[str] = None) -> ConversationContext:
        """Get existing context or create new one"""
        context_key = session_id or user_id or "default"
        
        if context_key not in self.contexts:
            self.contexts[context_key] = ConversationContext(
                session_id=session_id,
                user_id=user_id
            )
            logger.info(f"Created new conversation context for: {context_key}")
        else:
            # Update timestamp
            self.contexts[context_key].updated_at = time.time()
        
        return self.contexts[context_key]
    
    def analyze_user_intent(self, message: str, context: ConversationContext) -> Tuple[RequestType, Dict[str, Any]]:
        """Analyze user message to determine intent and extract parameters"""
        message_lower = message.lower().strip()
        
        # Extract potential parameters
        params = {}
        
        # Check for greeting patterns
        greeting_patterns = ['hello', 'hi', 'hey', 'good morning', 'good afternoon', 'good evening']
        if any(pattern in message_lower for pattern in greeting_patterns):
            return RequestType.HELP, params
        
        # Check for help requests
        help_patterns = ['help', 'what can you do', 'how do i', 'instructions', 'guide', 'capabilities']
        if any(pattern in message_lower for pattern in help_patterns):
            return RequestType.HELP, params
        
        # Check for status requests
        status_patterns = ['status', 'how is', 'what happened', 'progress', 'update']
        if any(pattern in message_lower for pattern in status_patterns):
            return RequestType.STATUS, params
        
        # Check for audio processing requests
        audio_patterns = ['audio', 'transcribe', 'speech', 'voice', 'sound', 'recording']
        if any(pattern in message_lower for pattern in audio_patterns):
            # Look for S3 references
            if 's3://' in message_lower or ('bucket' in message_lower and 'key' in message_lower):
                return RequestType.AUDIO_TO_ASL, params
            return RequestType.AUDIO_TO_ASL, params
        
        # Check for ASL analysis requests
        analysis_patterns = ['analyze', 'interpret', 'what does this sign mean', 'asl to text', 'reverse']
        video_patterns = ['video', 'stream', 'kinesis', 'camera']
        if (any(pattern in message_lower for pattern in analysis_patterns) or 
            any(pattern in message_lower for pattern in video_patterns)):
            return RequestType.ASL_TO_TEXT, params
        
        # Check for text translation requests (default for most text)
        translation_patterns = ['translate', 'convert', 'asl', 'sign language', 'gloss', 'video']
        if (any(pattern in message_lower for pattern in translation_patterns) or 
            len(message.split()) > 2):  # Assume longer messages are for translation
            return RequestType.TEXT_TO_ASL, params
        
        return RequestType.UNKNOWN, params
    
    def generate_contextual_response_prefix(self, context: ConversationContext, 
                                          request_type: RequestType) -> str:
        """Generate contextual response prefix based on conversation state"""
        prefixes = []
        
        # Greeting for new conversations
        if not context.conversation_history:
            prefixes.append("Hello! I'm GenASL, your AI-powered ASL translation assistant.")
        
        # Context-aware responses based on previous interactions
        if context.last_request_type == request_type and request_type == RequestType.TEXT_TO_ASL:
            prefixes.append("I'll translate another text to ASL for you.")
        elif context.last_request_type != request_type:
            if request_type == RequestType.TEXT_TO_ASL:
                prefixes.append("I'll help you translate text to American Sign Language.")
            elif request_type == RequestType.AUDIO_TO_ASL:
                prefixes.append("I'll process your audio file and convert it to ASL.")
            elif request_type == RequestType.ASL_TO_TEXT:
                prefixes.append("I'll analyze the ASL video and interpret the signs for you.")
        
        # Status updates for pending operations
        if context.pending_operations:
            prefixes.append(f"I'm currently working on: {', '.join(context.pending_operations)}.")
        
        return " ".join(prefixes)
    
    def format_translation_result(self, result: str, context: ConversationContext) -> str:
        """Format translation results with conversational context"""
        try:
            # Try to parse if result contains structured data
            import json
            if result.startswith('{') and result.endswith('}'):
                data = json.loads(result)
                return self._format_structured_result(data, context)
        except:
            pass
        
        # Handle plain text results
        formatted_response = []
        
        # Add contextual introduction
        if context.last_request_type == RequestType.TEXT_TO_ASL:
            formatted_response.append("Here's your ASL translation:")
        elif context.last_request_type == RequestType.AUDIO_TO_ASL:
            formatted_response.append("I've processed your audio and created the ASL translation:")
        
        formatted_response.append(result)
        
        # Add helpful follow-up suggestions
        follow_ups = [
            "Would you like me to translate anything else?",
            "I can also help you with audio files or analyze ASL videos if needed.",
            "Feel free to ask if you have any questions about the translation!"
        ]
        
        if len(context.conversation_history) < 3:  # Only for early conversations
            formatted_response.append(follow_ups[len(context.conversation_history) % len(follow_ups)])
        
        return "\n\n".join(formatted_response)
    
    def _format_structured_result(self, data: Dict[str, Any], context: ConversationContext) -> str:
        """Format structured result data into conversational response"""
        response_parts = []
        
        if 'Gloss' in data and 'Text' in data:
            response_parts.append(f"Original text: \"{data['Text']}\"")
            response_parts.append(f"ASL Gloss: {data['Gloss']}")
            
            # Store in context for future reference
            context.last_translation_text = data['Text']
            context.last_gloss = data['Gloss']
        
        # Format video URLs
        video_urls = {}
        for url_type in ['PoseURL', 'SignURL', 'AvatarURL']:
            if url_type in data and data[url_type]:
                video_urls[url_type.replace('URL', '').lower()] = data[url_type]
        
        if video_urls:
            response_parts.append("Generated ASL videos:")
            for video_type, url in video_urls.items():
                response_parts.append(f"• {video_type.title()} video: {url}")
            
            # Store in context
            context.last_video_urls = video_urls
        
        return "\n".join(response_parts)
    
    def handle_error_response(self, error: str, context: ConversationContext) -> str:
        """Generate user-friendly error responses with helpful guidance"""
        context.error_count += 1
        
        # Categorize errors and provide specific guidance
        error_lower = error.lower()
        
        if 'bucket' in error_lower or 's3' in error_lower:
            return self._format_s3_error_response(error, context)
        elif 'transcription' in error_lower or 'audio' in error_lower:
            return self._format_audio_error_response(error, context)
        elif 'video' in error_lower or 'stream' in error_lower:
            return self._format_video_error_response(error, context)
        elif 'gloss' in error_lower or 'translation' in error_lower:
            return self._format_translation_error_response(error, context)
        else:
            return self._format_generic_error_response(error, context)
    
    def _format_s3_error_response(self, error: str, context: ConversationContext) -> str:
        """Format S3-related error responses"""
        response = [
            "I encountered an issue accessing the S3 file.",
            f"Error details: {error}",
            "",
            "Please check:",
            "• The bucket name and file path are correct",
            "• The file exists in the specified location",
            "• I have permission to access the file",
            "",
            "You can provide the S3 location like: s3://bucket-name/path/to/file.mp3"
        ]
        return "\n".join(response)
    
    def _format_audio_error_response(self, error: str, context: ConversationContext) -> str:
        """Format audio processing error responses"""
        response = [
            "I had trouble processing the audio file.",
            f"Error details: {error}",
            "",
            "Please ensure:",
            "• The audio file is in a supported format (MP3, WAV, MP4, etc.)",
            "• The file is not corrupted or empty",
            "• The audio contains clear speech",
            "",
            "Would you like to try with a different audio file?"
        ]
        return "\n".join(response)
    
    def _format_video_error_response(self, error: str, context: ConversationContext) -> str:
        """Format video processing error responses"""
        response = [
            "I encountered an issue processing the video.",
            f"Error details: {error}",
            "",
            "Please verify:",
            "• The video stream or file is accessible",
            "• The video contains clear ASL signs",
            "• The format is supported (MP4, WebM, etc.)",
            "",
            "For Kinesis streams, make sure the stream name is correct and active."
        ]
        return "\n".join(response)
    
    def _format_translation_error_response(self, error: str, context: ConversationContext) -> str:
        """Format translation error responses"""
        response = [
            "I had difficulty with the translation process.",
            f"Error details: {error}",
            "",
            "This might help:",
            "• Try rephrasing your text in simpler terms",
            "• Check for any unusual characters or formatting",
            "• Break long sentences into shorter ones",
            "",
            "Would you like to try translating a different phrase?"
        ]
        return "\n".join(response)
    
    def _format_generic_error_response(self, error: str, context: ConversationContext) -> str:
        """Format generic error responses"""
        response = [
            "I encountered an unexpected issue while processing your request.",
            f"Error details: {error}",
            "",
            "You can try:",
            "• Rephrasing your request",
            "• Checking your input format",
            "• Trying again in a moment",
            "",
            "If the problem persists, please let me know and I'll do my best to help!"
        ]
        return "\n".join(response)
    
    def update_context(self, context: ConversationContext, request_type: RequestType, 
                      user_message: str, response: str):
        """Update conversation context with new interaction"""
        context.last_request_type = request_type
        context.updated_at = time.time()
        
        # Add to conversation history
        context.conversation_history.append({
            'timestamp': time.time(),
            'user_message': user_message,
            'request_type': request_type.value,
            'response': response[:200] + "..." if len(response) > 200 else response
        })
        
        # Keep only last 10 interactions to manage memory
        if len(context.conversation_history) > 10:
            context.conversation_history = context.conversation_history[-10:]
        
        logger.info(f"Updated context for session: {context.session_id or 'default'}")
    
    def generate_help_response(self, context: ConversationContext) -> str:
        """Generate contextual help response"""
        help_sections = []
        
        # Welcome message for new users
        if not context.conversation_history:
            help_sections.append(
                "Welcome to GenASL! I'm here to help you with American Sign Language translation."
            )
        
        help_sections.extend([
            "",
            "Here's what I can do for you:",
            "",
            "🔤 **Text to ASL Translation**",
            "• Just type any English text and I'll convert it to ASL gloss and generate videos",
            "• Example: \"Hello, how are you today?\"",
            "",
            "🎵 **Audio to ASL Translation**",
            "• Provide an S3 location of an audio file and I'll transcribe and translate it",
            "• Example: \"Please process audio from s3://my-bucket/speech.mp3\"",
            "",
            "📹 **ASL Video Analysis**",
            "• I can analyze ASL videos and interpret the signs back to English",
            "• Supports Kinesis Video Streams and S3-stored videos",
            "• Example: \"Analyze ASL video from stream my-stream-name\"",
            "",
            "💬 **Natural Conversation**",
            "• I remember our conversation context and can handle follow-up questions",
            "• Ask me about previous translations or request modifications",
            "",
            "Just tell me what you'd like to do, and I'll guide you through the process!"
        ])
        
        return "\n".join(help_sections)
    
    def cleanup_old_contexts(self, max_age_hours: int = 24):
        """Clean up old conversation contexts to manage memory"""
        current_time = time.time()
        max_age_seconds = max_age_hours * 3600
        
        old_contexts = [
            key for key, context in self.contexts.items()
            if current_time - context.updated_at > max_age_seconds
        ]
        
        for key in old_contexts:
            del self.contexts[key]
        
        if old_contexts:
            logger.info(f"Cleaned up {len(old_contexts)} old conversation contexts")

# Global conversation manager instance
conversation_manager = ConversationManager()