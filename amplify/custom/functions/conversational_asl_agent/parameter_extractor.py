"""
Parameter Extraction Module

This module provides parameter extraction capabilities for different intent types,
including input type detection from metadata and context reference detection.
"""

import re
import logging
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
from pathlib import Path

try:
    from .data_models import (
        ConversationIntent, 
        InputType, 
        ConversationContext,
        ConversationInteraction,
        TranslationResult
    )
except ImportError:
    from data_models import (
        ConversationIntent, 
        InputType, 
        ConversationContext,
        ConversationInteraction,
        TranslationResult
    )

logger = logging.getLogger(__name__)

class ParameterExtractor:
    """
    Parameter extractor that analyzes user input and metadata to extract
    relevant parameters for different intent types and translation workflows.
    """
    
    def __init__(self):
        """Initialize the parameter extractor"""
        self.supported_audio_formats = {'.mp3', '.wav', '.m4a', '.aac', '.ogg', '.flac', '.wma'}
        self.supported_video_formats = {'.mp4', '.avi', '.mov', '.mkv', '.webm', '.flv', '.wmv'}
        self.supported_image_formats = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp'}
        
        logger.info("ParameterExtractor initialized")
    
    def extract_parameters(self, user_input: str, intent: ConversationIntent,
                         metadata: Optional[Dict[str, Any]] = None,
                         context: Optional[ConversationContext] = None) -> Dict[str, Any]:
        """
        Extract parameters for different intent types
        
        Args:
            user_input: The user's input message
            intent: The classified conversation intent
            metadata: Optional metadata containing file information, etc.
            context: Optional conversation context
        
        Returns:
            Dict containing extracted parameters
        """
        try:
            parameters = {}
            
            # Extract base parameters from input
            base_params = self._extract_base_parameters(user_input, metadata)
            parameters.update(base_params)
            
            # Extract intent-specific parameters
            if intent == ConversationIntent.TEXT_TO_ASL:
                intent_params = self._extract_text_to_asl_parameters(user_input, metadata, context)
            elif intent == ConversationIntent.AUDIO_TO_ASL:
                intent_params = self._extract_audio_to_asl_parameters(user_input, metadata, context)
            elif intent == ConversationIntent.ASL_TO_TEXT:
                intent_params = self._extract_asl_to_text_parameters(user_input, metadata, context)
            elif intent == ConversationIntent.HELP_REQUEST:
                intent_params = self._extract_help_parameters(user_input, metadata, context)
            elif intent == ConversationIntent.STATUS_CHECK:
                intent_params = self._extract_status_parameters(user_input, metadata, context)
            elif intent == ConversationIntent.RETRY_REQUEST:
                intent_params = self._extract_retry_parameters(user_input, metadata, context)
            elif intent == ConversationIntent.CONTEXT_REFERENCE:
                intent_params = self._extract_context_reference_parameters(user_input, metadata, context)
            else:
                intent_params = {}
            
            parameters.update(intent_params)
            
            # Detect and validate input type
            input_type = self.detect_input_type(metadata, parameters, user_input)
            parameters['input_type'] = input_type
            
            # Extract context references if present
            context_refs = self._detect_context_references(user_input, context)
            if context_refs:
                parameters['context_references'] = context_refs
            
            logger.debug(f"Extracted parameters for intent {intent.value}: {parameters}")
            return parameters
            
        except Exception as e:
            logger.error(f"Error extracting parameters: {e}", exc_info=True)
            return {'error': str(e)}
    
    def _extract_base_parameters(self, user_input: str, metadata: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Extract base parameters common to all intents"""
        parameters = {
            'original_input': user_input,
            'timestamp': datetime.now().isoformat(),
            'input_length': len(user_input)
        }
        
        # Add metadata if provided
        if metadata:
            parameters['metadata'] = metadata
            
            # Extract file information from metadata
            if 'files' in metadata:
                parameters['files'] = metadata['files']
            
            if 'user_id' in metadata:
                parameters['user_id'] = metadata['user_id']
            
            if 'session_id' in metadata:
                parameters['session_id'] = metadata['session_id']
        
        return parameters
    
    def _extract_text_to_asl_parameters(self, user_input: str, metadata: Optional[Dict[str, Any]],
                                      context: Optional[ConversationContext]) -> Dict[str, Any]:
        """Extract parameters for text-to-ASL translation"""
        parameters = {}
        
        # Extract text content to translate
        text_content = self._extract_translation_text(user_input)
        if text_content:
            parameters['text'] = text_content
            parameters['text_length'] = len(text_content)
        
        # Extract video format preferences
        video_prefs = self._extract_video_preferences(user_input)
        if video_prefs:
            parameters.update(video_prefs)
        
        # Extract quality preferences
        quality_prefs = self._extract_quality_preferences(user_input)
        if quality_prefs:
            parameters.update(quality_prefs)
        
        # Check for batch processing indicators
        if self._detect_batch_processing(user_input):
            parameters['batch_processing'] = True
        
        return parameters
    
    def _extract_audio_to_asl_parameters(self, user_input: str, metadata: Optional[Dict[str, Any]],
                                       context: Optional[ConversationContext]) -> Dict[str, Any]:
        """Extract parameters for audio-to-ASL translation"""
        parameters = {}
        
        # Extract audio file information
        audio_info = self._extract_audio_file_info(user_input, metadata)
        if audio_info:
            parameters.update(audio_info)
        
        # Extract transcription preferences
        transcription_prefs = self._extract_transcription_preferences(user_input)
        if transcription_prefs:
            parameters.update(transcription_prefs)
        
        # Extract language preferences
        language_prefs = self._extract_language_preferences(user_input)
        if language_prefs:
            parameters.update(language_prefs)
        
        # Check for real-time processing
        if self._detect_realtime_processing(user_input):
            parameters['realtime_processing'] = True
        
        return parameters
    
    def _extract_asl_to_text_parameters(self, user_input: str, metadata: Optional[Dict[str, Any]],
                                      context: Optional[ConversationContext]) -> Dict[str, Any]:
        """Extract parameters for ASL-to-text analysis"""
        parameters = {}
        
        # Extract video file information
        video_info = self._extract_video_file_info(user_input, metadata)
        if video_info:
            parameters.update(video_info)
        
        # Extract analysis preferences
        analysis_prefs = self._extract_analysis_preferences(user_input)
        if analysis_prefs:
            parameters.update(analysis_prefs)
        
        # Check for streaming vs file analysis
        if self._detect_streaming_analysis(user_input):
            parameters['analysis_mode'] = 'stream'
        else:
            parameters['analysis_mode'] = 'file'
        
        # Extract confidence threshold preferences
        confidence_prefs = self._extract_confidence_preferences(user_input)
        if confidence_prefs:
            parameters.update(confidence_prefs)
        
        return parameters
    
    def _extract_help_parameters(self, user_input: str, metadata: Optional[Dict[str, Any]],
                               context: Optional[ConversationContext]) -> Dict[str, Any]:
        """Extract parameters for help requests"""
        parameters = {}
        
        # Determine help topic
        help_topic = self._determine_help_topic(user_input)
        parameters['help_topic'] = help_topic
        
        # Check for specific feature requests
        feature_requests = self._extract_feature_requests(user_input)
        if feature_requests:
            parameters['requested_features'] = feature_requests
        
        # Determine user experience level
        experience_level = self._determine_experience_level(user_input, context)
        parameters['experience_level'] = experience_level
        
        return parameters
    
    def _extract_status_parameters(self, user_input: str, metadata: Optional[Dict[str, Any]],
                                 context: Optional[ConversationContext]) -> Dict[str, Any]:
        """Extract parameters for status check requests"""
        parameters = {}
        
        # Determine what status is being requested
        status_type = self._determine_status_type(user_input)
        parameters['status_type'] = status_type
        
        # Check if they want ETA information
        if self._wants_eta_info(user_input):
            parameters['wants_eta'] = True
        
        # Check if they want detailed progress
        if self._wants_detailed_progress(user_input):
            parameters['wants_details'] = True
        
        return parameters
    
    def _extract_retry_parameters(self, user_input: str, metadata: Optional[Dict[str, Any]],
                                context: Optional[ConversationContext]) -> Dict[str, Any]:
        """Extract parameters for retry requests"""
        parameters = {}
        
        # Determine what to retry
        retry_target = self._determine_retry_target(user_input, context)
        if retry_target:
            parameters['retry_target'] = retry_target
        
        # Check for modification requests
        modifications = self._extract_modification_requests(user_input)
        if modifications:
            parameters['modifications'] = modifications
        
        # Check if they want alternative approaches
        if self._wants_alternative_approach(user_input):
            parameters['wants_alternative'] = True
        
        return parameters
    
    def _extract_context_reference_parameters(self, user_input: str, metadata: Optional[Dict[str, Any]],
                                            context: Optional[ConversationContext]) -> Dict[str, Any]:
        """Extract parameters for context reference requests"""
        parameters = {}
        
        # Determine what they're referring to
        reference_type = self._determine_reference_type(user_input)
        parameters['reference_type'] = reference_type
        
        # Determine which item (first, last, etc.)
        reference_index = self._determine_reference_index(user_input)
        parameters['reference_index'] = reference_index
        
        # Extract the actual referenced item if possible
        referenced_item = self._extract_referenced_item(user_input, context, reference_type, reference_index)
        if referenced_item:
            parameters['referenced_item'] = referenced_item
        
        return parameters
    
    def detect_input_type(self, metadata: Optional[Dict[str, Any]], 
                         parameters: Dict[str, Any], user_input: str) -> InputType:
        """
        Detect input type from metadata, parameters, and user input
        
        Args:
            metadata: Optional metadata containing file information
            parameters: Extracted parameters
            user_input: User's input text
        
        Returns:
            InputType: Detected input type
        """
        # Check metadata for file information first
        if metadata and 'files' in metadata:
            for file_info in metadata['files']:
                file_type = self._detect_file_type(file_info)
                if file_type != InputType.UNKNOWN:
                    return file_type
        
        # Check parameters for file references
        if 'audio_file' in parameters or 'audio_url' in parameters:
            return InputType.AUDIO
        elif 'video_file' in parameters or 'video_url' in parameters:
            return InputType.VIDEO
        elif 'image_file' in parameters or 'image_url' in parameters:
            return InputType.IMAGE
        
        # Check for streaming indicators
        if parameters.get('realtime_processing') or parameters.get('analysis_mode') == 'stream':
            return InputType.STREAM
        
        # Analyze user input for type indicators
        normalized_input = user_input.lower()
        
        if any(word in normalized_input for word in ['audio', 'voice', 'speech', 'sound', 'recording']):
            return InputType.AUDIO
        elif any(word in normalized_input for word in ['video', 'asl', 'sign language', 'signing']):
            return InputType.VIDEO
        elif any(word in normalized_input for word in ['stream', 'live', 'real-time', 'camera']):
            return InputType.STREAM
        elif any(word in normalized_input for word in ['image', 'picture', 'photo', 'screenshot']):
            return InputType.IMAGE
        
        # Default to text if no other type detected
        return InputType.TEXT
    
    def _detect_file_type(self, file_info: Dict[str, Any]) -> InputType:
        """Detect file type from file information"""
        if 'filename' in file_info:
            filename = file_info['filename'].lower()
            file_ext = Path(filename).suffix.lower()
            
            if file_ext in self.supported_audio_formats:
                return InputType.AUDIO
            elif file_ext in self.supported_video_formats:
                return InputType.VIDEO
            elif file_ext in self.supported_image_formats:
                return InputType.IMAGE
        
        if 'content_type' in file_info:
            content_type = file_info['content_type'].lower()
            if content_type.startswith('audio/'):
                return InputType.AUDIO
            elif content_type.startswith('video/'):
                return InputType.VIDEO
            elif content_type.startswith('image/'):
                return InputType.IMAGE
        
        return InputType.UNKNOWN
    
    def _detect_context_references(self, user_input: str, 
                                 context: Optional[ConversationContext]) -> Optional[List[Dict[str, Any]]]:
        """Detect references to previous conversation elements"""
        if not context or not context.conversation_history:
            return None
        
        references = []
        normalized_input = user_input.lower()
        
        # Common reference patterns
        reference_patterns = [
            (r'\b(?:that|the)\s+(?:last|previous|earlier)\s+(\w+)', 'last'),
            (r'\b(?:that|the)\s+(?:first)\s+(\w+)', 'first'),
            (r'\b(?:that|the)\s+(?:second)\s+(\w+)', 'second'),
            (r'\b(?:that|the)\s+(\w+)\s+(?:you\s+just\s+(?:did|made|showed))', 'last'),
            (r'\b(?:from\s+)?(?:before|earlier|previously)', 'previous_general')
        ]
        
        for pattern, ref_type in reference_patterns:
            matches = re.finditer(pattern, normalized_input)
            for match in matches:
                reference = {
                    'type': ref_type,
                    'matched_text': match.group(0),
                    'position': match.span()
                }
                
                if match.groups():
                    reference['referenced_object'] = match.group(1)
                
                references.append(reference)
        
        return references if references else None
    
    def _extract_translation_text(self, user_input: str) -> Optional[str]:
        """Extract text content to translate from user input"""
        # Patterns to extract quoted text
        quote_patterns = [
            r'"([^"]+)"',  # Double quotes
            r"'([^']+)'",  # Single quotes
            r'`([^`]+)`'   # Backticks
        ]
        
        for pattern in quote_patterns:
            match = re.search(pattern, user_input)
            if match:
                return match.group(1).strip()
        
        # If no quotes, try to extract after command words
        command_patterns = [
            r'(?:translate|convert|turn)\s+(?:this\s+)?(?:text\s+)?(.+?)(?:\s+(?:to\s+)?(?:asl|sign\s+language)|$)',
            r'(?:please\s+)?(?:help\s+me\s+)?translate\s+(.+?)(?:\s+to\s+asl|\s+to\s+sign\s+language|$)',
            r'(?:can\s+you\s+)?(?:please\s+)?(?:translate|convert)\s+(.+)',
            r'how\s+do\s+(?:i\s+|you\s+)?sign\s+(.+)',
            r'what\s+is\s+(.+?)(?:\s+in\s+asl|\s+in\s+sign\s+language|$)'
        ]
        
        for pattern in command_patterns:
            match = re.search(pattern, user_input, re.IGNORECASE)
            if match:
                text = match.group(1).strip().strip('"\'')
                # Only return if it's substantial text (not just command words)
                if len(text) > 3 and not any(cmd in text.lower() for cmd in ['translate', 'convert', 'asl']):
                    return text
        
        return None
    
    def _extract_video_preferences(self, user_input: str) -> Dict[str, Any]:
        """Extract video format and quality preferences"""
        preferences = {}
        normalized = user_input.lower()
        
        # Video format preferences
        if 'pose' in normalized:
            preferences['include_pose'] = True
        if 'avatar' in normalized:
            preferences['include_avatar'] = True
        if 'sign' in normalized and 'video' in normalized:
            preferences['include_sign'] = True
        
        # Quality preferences
        if any(word in normalized for word in ['high quality', 'hd', '1080p', '720p']):
            preferences['quality'] = 'high'
        elif any(word in normalized for word in ['low quality', 'fast', 'quick']):
            preferences['quality'] = 'low'
        
        return preferences
    
    def _extract_quality_preferences(self, user_input: str) -> Dict[str, Any]:
        """Extract quality and speed preferences"""
        preferences = {}
        normalized = user_input.lower()
        
        if any(word in normalized for word in ['fast', 'quick', 'speed']):
            preferences['priority'] = 'speed'
        elif any(word in normalized for word in ['quality', 'accurate', 'precise']):
            preferences['priority'] = 'quality'
        
        return preferences
    
    def _detect_batch_processing(self, user_input: str) -> bool:
        """Detect if user wants batch processing"""
        normalized = user_input.lower()
        return any(word in normalized for word in ['batch', 'multiple', 'all', 'several'])
    
    def _extract_audio_file_info(self, user_input: str, metadata: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Extract audio file information"""
        info = {}
        
        # Extract from metadata first
        if metadata and 'files' in metadata:
            for file_info in metadata['files']:
                if self._detect_file_type(file_info) == InputType.AUDIO:
                    info['audio_file'] = file_info
                    break
        
        # Extract from user input
        file_patterns = [
            r'(?:file|audio|recording)\s+(?:named|called)\s+["\']?([^"\']+)["\']?',
            r'["\']?([^"\']+\.(?:mp3|wav|m4a|aac|ogg|flac))["\']?'
        ]
        
        for pattern in file_patterns:
            match = re.search(pattern, user_input, re.IGNORECASE)
            if match:
                info['audio_filename'] = match.group(1)
                break
        
        return info
    
    def _extract_transcription_preferences(self, user_input: str) -> Dict[str, Any]:
        """Extract transcription preferences"""
        preferences = {}
        normalized = user_input.lower()
        
        if 'accurate' in normalized or 'precise' in normalized:
            preferences['transcription_accuracy'] = 'high'
        elif 'fast' in normalized or 'quick' in normalized:
            preferences['transcription_speed'] = 'fast'
        
        return preferences
    
    def _extract_language_preferences(self, user_input: str) -> Dict[str, Any]:
        """Extract language preferences"""
        preferences = {}
        
        # For now, assume English, but could be extended
        preferences['source_language'] = 'en'
        preferences['target_language'] = 'asl'
        
        return preferences
    
    def _detect_realtime_processing(self, user_input: str) -> bool:
        """Detect if user wants real-time processing"""
        normalized = user_input.lower()
        return any(word in normalized for word in ['real-time', 'live', 'streaming', 'now'])
    
    def _extract_video_file_info(self, user_input: str, metadata: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Extract video file information"""
        info = {}
        
        # Extract from metadata first
        if metadata and 'files' in metadata:
            for file_info in metadata['files']:
                if self._detect_file_type(file_info) == InputType.VIDEO:
                    info['video_file'] = file_info
                    break
        
        # Extract from user input
        file_patterns = [
            r'(?:video|file)\s+(?:named|called)\s+["\']?([^"\']+)["\']?',
            r'["\']?([^"\']+\.(?:mp4|avi|mov|mkv|webm))["\']?'
        ]
        
        for pattern in file_patterns:
            match = re.search(pattern, user_input, re.IGNORECASE)
            if match:
                info['video_filename'] = match.group(1)
                break
        
        return info
    
    def _extract_analysis_preferences(self, user_input: str) -> Dict[str, Any]:
        """Extract ASL analysis preferences"""
        preferences = {}
        normalized = user_input.lower()
        
        if 'detailed' in normalized or 'thorough' in normalized:
            preferences['analysis_detail'] = 'high'
        elif 'quick' in normalized or 'fast' in normalized:
            preferences['analysis_detail'] = 'low'
        
        return preferences
    
    def _detect_streaming_analysis(self, user_input: str) -> bool:
        """Detect if user wants streaming analysis"""
        normalized = user_input.lower()
        return any(word in normalized for word in ['stream', 'live', 'real-time', 'camera'])
    
    def _extract_confidence_preferences(self, user_input: str) -> Dict[str, Any]:
        """Extract confidence threshold preferences"""
        preferences = {}
        
        # Could be extended to parse specific confidence values
        # For now, just detect if they want high confidence
        normalized = user_input.lower()
        if any(word in normalized for word in ['confident', 'sure', 'certain', 'accurate']):
            preferences['min_confidence'] = 0.8
        
        return preferences
    
    def _determine_help_topic(self, user_input: str) -> str:
        """Determine the specific help topic requested"""
        normalized = user_input.lower()
        
        help_topics = {
            'translation': ['translate', 'translation', 'convert'],
            'audio': ['audio', 'voice', 'speech', 'sound'],
            'video': ['video', 'asl', 'sign language', 'signing'],
            'features': ['features', 'capabilities', 'functions', 'what can you do'],
            'getting_started': ['getting started', 'new', 'beginner', 'how to use'],
            'examples': ['example', 'examples', 'show me', 'demonstrate'],
            'troubleshooting': ['problem', 'issue', 'error', 'not working', 'failed']
        }
        
        for topic, keywords in help_topics.items():
            if any(keyword in normalized for keyword in keywords):
                return topic
        
        return 'general'
    
    def _extract_feature_requests(self, user_input: str) -> List[str]:
        """Extract specific feature requests from help input"""
        features = []
        normalized = user_input.lower()
        
        feature_keywords = {
            'batch_processing': ['batch', 'multiple files', 'several'],
            'real_time': ['real-time', 'live', 'streaming'],
            'video_formats': ['video format', 'mp4', 'avi', 'formats'],
            'quality_options': ['quality', 'resolution', 'hd'],
            'api_access': ['api', 'programmatic', 'integration']
        }
        
        for feature, keywords in feature_keywords.items():
            if any(keyword in normalized for keyword in keywords):
                features.append(feature)
        
        return features
    
    def _determine_experience_level(self, user_input: str, 
                                  context: Optional[ConversationContext]) -> str:
        """Determine user's experience level"""
        normalized = user_input.lower()
        
        # Check for beginner indicators
        if any(word in normalized for word in ['new', 'beginner', 'first time', 'never used']):
            return 'beginner'
        
        # Check context for experience indicators
        if context and len(context.conversation_history) > 5:
            return 'experienced'
        elif context and len(context.conversation_history) > 1:
            return 'intermediate'
        
        return 'unknown'
    
    def _determine_status_type(self, user_input: str) -> str:
        """Determine what type of status is being requested"""
        normalized = user_input.lower()
        
        if 'translation' in normalized:
            return 'translation'
        elif any(word in normalized for word in ['job', 'request', 'task']):
            return 'job'
        elif 'progress' in normalized:
            return 'progress'
        else:
            return 'general'
    
    def _wants_eta_info(self, user_input: str) -> bool:
        """Check if user wants ETA information"""
        normalized = user_input.lower()
        return any(word in normalized for word in ['time', 'long', 'when', 'eta', 'estimate'])
    
    def _wants_detailed_progress(self, user_input: str) -> bool:
        """Check if user wants detailed progress information"""
        normalized = user_input.lower()
        return any(word in normalized for word in ['detailed', 'progress', 'step', 'stage'])
    
    def _determine_retry_target(self, user_input: str, 
                              context: Optional[ConversationContext]) -> Optional[str]:
        """Determine what the user wants to retry"""
        normalized = user_input.lower()
        
        if 'translation' in normalized:
            return 'translation'
        elif 'last' in normalized or 'previous' in normalized:
            return 'last_action'
        elif context and context.last_translation:
            return 'last_translation'
        
        return None
    
    def _extract_modification_requests(self, user_input: str) -> List[str]:
        """Extract modification requests from retry input"""
        modifications = []
        normalized = user_input.lower()
        
        modification_patterns = {
            'different_format': ['different format', 'another format', 'other format'],
            'higher_quality': ['higher quality', 'better quality', 'hd'],
            'faster_processing': ['faster', 'quicker', 'speed up'],
            'more_accurate': ['more accurate', 'better accuracy', 'precise']
        }
        
        for mod_type, keywords in modification_patterns.items():
            if any(keyword in normalized for keyword in keywords):
                modifications.append(mod_type)
        
        return modifications
    
    def _wants_alternative_approach(self, user_input: str) -> bool:
        """Check if user wants alternative approach"""
        normalized = user_input.lower()
        return any(word in normalized for word in ['different', 'alternative', 'another way', 'other method'])
    
    def _determine_reference_type(self, user_input: str) -> str:
        """Determine what type of item is being referenced"""
        normalized = user_input.lower()
        
        if 'translation' in normalized:
            return 'translation'
        elif 'video' in normalized:
            return 'video'
        elif 'result' in normalized:
            return 'result'
        elif 'file' in normalized:
            return 'file'
        else:
            return 'general'
    
    def _determine_reference_index(self, user_input: str) -> str:
        """Determine which item is being referenced (first, last, etc.)"""
        normalized = user_input.lower()
        
        if 'first' in normalized:
            return 'first'
        elif 'second' in normalized:
            return 'second'
        elif 'third' in normalized:
            return 'third'
        elif any(word in normalized for word in ['last', 'previous', 'recent']):
            return 'last'
        else:
            return 'last'  # Default to last
    
    def _extract_referenced_item(self, user_input: str, context: Optional[ConversationContext],
                               reference_type: str, reference_index: str) -> Optional[Dict[str, Any]]:
        """Extract the actual referenced item from context"""
        if not context or not context.conversation_history:
            return None
        
        try:
            if reference_index == 'last':
                # Get the most recent item of the specified type
                for interaction in reversed(context.conversation_history):
                    if reference_type == 'translation' and interaction.translation_result:
                        return {
                            'type': 'translation',
                            'interaction': interaction.to_dict(),
                            'result': interaction.translation_result.to_dict()
                        }
                    elif reference_type == 'video' and interaction.translation_result and interaction.translation_result.video_urls:
                        return {
                            'type': 'video',
                            'interaction': interaction.to_dict(),
                            'video_urls': interaction.translation_result.video_urls
                        }
            
            elif reference_index in ['first', 'second', 'third']:
                # Get item by position
                index_map = {'first': 0, 'second': 1, 'third': 2}
                target_index = index_map[reference_index]
                
                relevant_interactions = []
                for interaction in context.conversation_history:
                    if reference_type == 'translation' and interaction.translation_result:
                        relevant_interactions.append(interaction)
                    elif reference_type == 'video' and interaction.translation_result and interaction.translation_result.video_urls:
                        relevant_interactions.append(interaction)
                
                if target_index < len(relevant_interactions):
                    interaction = relevant_interactions[target_index]
                    return {
                        'type': reference_type,
                        'interaction': interaction.to_dict(),
                        'result': interaction.translation_result.to_dict() if interaction.translation_result else None
                    }
        
        except Exception as e:
            logger.error(f"Error extracting referenced item: {e}")
        
        return None