"""
Intent Classification Engine

This module provides intent classification capabilities for the conversational ASL agent,
analyzing user input to determine conversation intent and extract relevant parameters.
"""

import re
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime

try:
    from .data_models import (
        ConversationIntent, 
        IntentResult, 
        InputType, 
        ConversationContext,
        ConversationInteraction
    )
except ImportError:
    from data_models import (
        ConversationIntent, 
        IntentResult, 
        InputType, 
        ConversationContext,
        ConversationInteraction
    )

logger = logging.getLogger(__name__)

class ConversationIntentClassifier:
    """
    Intent classifier that analyzes user input and determines conversation intent
    
    Uses pattern matching, keyword analysis, and context awareness to classify
    user intents and extract relevant parameters for translation workflows.
    """
    
    def __init__(self):
        """Initialize the intent classifier with pattern definitions"""
        self.intent_patterns = self._initialize_intent_patterns()
        self.confidence_threshold = 0.6
        self.context_boost = 0.2  # Boost confidence when context supports intent
        
        logger.info("ConversationIntentClassifier initialized")
    
    def _initialize_intent_patterns(self) -> Dict[ConversationIntent, List[Dict[str, Any]]]:
        """
        Initialize intent classification patterns
        
        Returns:
            Dict mapping intents to their classification patterns
        """
        return {
            ConversationIntent.TEXT_TO_ASL: [
                {
                    'patterns': [
                        r'translate\s+(?:this\s+)?(?:text\s+)?["\'](.+?)["\']',
                        r'convert\s+(?:this\s+)?(?:text\s+)?["\'](.+?)["\']',
                        r'turn\s+(?:this\s+)?(?:into\s+)?(?:asl\s+)?["\'](.+?)["\']',
                        r'(?:can\s+you\s+)?translate\s+["\'](.+?)["\'](?:\s+(?:to\s+)?(?:asl|sign\s+language))?',
                        r'(?:please\s+)?(?:help\s+me\s+)?translate\s+(.+?)(?:\s+to\s+asl|\s+to\s+sign\s+language|$)',
                        r'(?:i\s+want\s+to\s+)?(?:translate\s+)?["\'](.+?)["\'](?:\s+to\s+asl)?',
                        r'how\s+do\s+(?:i\s+|you\s+)?sign\s+["\'](.+?)["\']',
                        r'what\s+is\s+["\'](.+?)["\'](?:\s+in\s+asl|\s+in\s+sign\s+language)?'
                    ],
                    'keywords': ['translate', 'convert', 'asl', 'sign language', 'gloss', 'video'],
                    'confidence_base': 0.8,
                    'parameter_extraction': 'text_content'
                },
                {
                    'patterns': [
                        r'(?:translate|convert|turn)\s+(?:this\s+)?(?:text\s+)?(.+?)(?:\s+(?:to\s+)?(?:asl|sign\s+language)|$)',
                        r'(?:can\s+you\s+)?(?:please\s+)?(?:help\s+me\s+)?(?:translate|convert)\s+(.+)',
                        r'(?:i\s+(?:want\s+to\s+|need\s+to\s+|would\s+like\s+to\s+))?(?:translate|convert)\s+(.+)',
                        r'make\s+(?:this\s+)?(?:into\s+)?(?:asl\s+)?(?:video\s+)?(?:for\s+)?(.+)'
                    ],
                    'keywords': ['translate', 'convert', 'make', 'create'],
                    'confidence_base': 0.7,
                    'parameter_extraction': 'text_content'
                }
            ],
            
            ConversationIntent.AUDIO_TO_ASL: [
                {
                    'patterns': [
                        r'(?:translate|convert|process)\s+(?:this\s+)?(?:audio|sound|recording|voice)',
                        r'(?:i\s+have\s+)?(?:an\s+)?audio\s+(?:file|recording)(?:\s+(?:to\s+)?(?:translate|convert))?',
                        r'(?:can\s+you\s+)?(?:process|analyze|transcribe)\s+(?:this\s+)?audio',
                        r'(?:from\s+)?(?:audio|voice|speech)\s+(?:to\s+)?(?:asl|sign\s+language)',
                        r'(?:transcribe\s+and\s+)?translate\s+(?:this\s+)?(?:audio|recording)',
                        r'(?:i\s+)?(?:uploaded|have)\s+(?:an\s+)?audio\s+file'
                    ],
                    'keywords': ['audio', 'voice', 'speech', 'recording', 'sound', 'transcribe', 'upload'],
                    'confidence_base': 0.9,
                    'parameter_extraction': 'audio_metadata'
                }
            ],
            
            ConversationIntent.ASL_TO_TEXT: [
                {
                    'patterns': [
                        r'(?:analyze|interpret|read|translate)\s+(?:this\s+)?(?:asl\s+)?(?:video|signing)',
                        r'(?:what\s+(?:does|is)\s+)?(?:this\s+)?(?:asl\s+)?(?:video|sign|signing)\s+(?:saying|mean)',
                        r'(?:can\s+you\s+)?(?:interpret|understand|read)\s+(?:this\s+)?(?:asl|sign\s+language)',
                        r'(?:from\s+)?(?:asl|sign\s+language|video)\s+(?:to\s+)?(?:text|english)',
                        r'(?:i\s+have\s+)?(?:an\s+)?(?:asl\s+)?video\s+(?:to\s+)?(?:analyze|interpret)',
                        r'(?:uploaded|have)\s+(?:an\s+)?(?:asl\s+)?video'
                    ],
                    'keywords': ['asl', 'video', 'analyze', 'interpret', 'read', 'signing', 'sign language'],
                    'confidence_base': 0.9,
                    'parameter_extraction': 'video_metadata'
                }
            ],
            
            ConversationIntent.HELP_REQUEST: [
                {
                    'patterns': [
                        r'(?:help|assistance|guide|instructions)',
                        r'(?:what\s+can\s+you\s+do|how\s+(?:does\s+this\s+work|do\s+i\s+use\s+this))',
                        r'(?:i\s+(?:need\s+help|don\'t\s+know|am\s+confused))',
                        r'(?:how\s+(?:to|do\s+i))\s+(?:use|work\s+with|operate)',
                        r'(?:what\s+(?:are\s+)?(?:your\s+)?(?:capabilities|features|functions))',
                        r'(?:show\s+me\s+)?(?:examples?|how\s+to)',
                        r'(?:i\s+(?:am\s+)?(?:new|beginner)|getting\s+started)'
                    ],
                    'keywords': ['help', 'how', 'what', 'guide', 'example', 'tutorial', 'instructions'],
                    'confidence_base': 0.8,
                    'parameter_extraction': 'help_topic'
                }
            ],
            
            ConversationIntent.STATUS_CHECK: [
                {
                    'patterns': [
                        r'(?:status|progress)\s+(?:of\s+)?(?:my\s+)?(?:translation|request|job)',
                        r'(?:is\s+(?:my\s+)?(?:translation|request|job)\s+)?(?:done|ready|complete|finished)',
                        r'(?:how\s+(?:long|much\s+time))\s+(?:will\s+(?:this|it)\s+take|left)',
                        r'(?:what\s+(?:is\s+)?(?:happening|going\s+on))\s+(?:with\s+)?(?:my\s+)?(?:request|translation)',
                        r'(?:check\s+)?(?:status|progress)',
                        r'(?:still\s+)?(?:processing|working|running)'
                    ],
                    'keywords': ['status', 'progress', 'done', 'ready', 'complete', 'finished', 'time'],
                    'confidence_base': 0.8,
                    'parameter_extraction': 'status_query'
                }
            ],
            
            ConversationIntent.RETRY_REQUEST: [
                {
                    'patterns': [
                        r'(?:try\s+again|retry|redo)\s+(?:that\s+)?(?:translation|request)?',
                        r'(?:that\s+)?(?:didn\'t\s+work|failed|was\s+wrong)',
                        r'(?:can\s+you\s+)?(?:try\s+)?(?:again|once\s+more)',
                        r'(?:let\'s\s+)?(?:try\s+)?(?:a\s+different\s+)?(?:approach|method|way)',
                        r'(?:do\s+(?:that\s+)?(?:again|over))',
                        r'(?:repeat|redo)\s+(?:that\s+)?(?:last\s+)?(?:translation|action)'
                    ],
                    'keywords': ['retry', 'again', 'redo', 'repeat', 'failed', 'wrong', 'different'],
                    'confidence_base': 0.8,
                    'parameter_extraction': 'retry_context'
                }
            ],
            
            ConversationIntent.CONTEXT_REFERENCE: [
                {
                    'patterns': [
                        r'(?:that\s+)?(?:last\s+)?(?:translation|result|video)',
                        r'(?:the\s+)?(?:previous|earlier)\s+(?:one|translation|result)',
                        r'(?:from\s+)?(?:before|earlier|previously)',
                        r'(?:that\s+)?(?:one\s+)?(?:you\s+just\s+(?:did|made|showed))',
                        r'(?:the\s+)?(?:first|second|third)\s+(?:translation|result|video)',
                        r'(?:can\s+you\s+)?(?:show\s+me\s+)?(?:that\s+)?(?:again|once\s+more)'
                    ],
                    'keywords': ['that', 'last', 'previous', 'earlier', 'before', 'first', 'second'],
                    'confidence_base': 0.7,
                    'parameter_extraction': 'context_reference'
                }
            ],
            
            ConversationIntent.GREETING: [
                {
                    'patterns': [
                        r'^(?:hi|hello|hey|greetings)(?:\s+there)?(?:\s*[!.])?$',
                        r'^(?:good\s+(?:morning|afternoon|evening))(?:\s*[!.])?$',
                        r'^(?:how\s+are\s+you|how\'s\s+it\s+going)(?:\s*[?!.])?$',
                        r'^(?:nice\s+to\s+meet\s+you)(?:\s*[!.])?$'
                    ],
                    'keywords': ['hi', 'hello', 'hey', 'good morning', 'good afternoon', 'good evening'],
                    'confidence_base': 0.9,
                    'parameter_extraction': 'greeting_type'
                }
            ]
        }
    
    def classify_intent(self, user_input: str, context: Optional[ConversationContext] = None) -> IntentResult:
        """
        Classify user intent from input text
        
        Args:
            user_input: The user's input message
            context: Optional conversation context for context-aware classification
        
        Returns:
            IntentResult: Classification result with intent, confidence, and parameters
        """
        try:
            # Normalize input for pattern matching
            normalized_input = user_input.lower().strip()
            
            # Track all potential intents with confidence scores
            intent_scores = []
            
            # Check each intent pattern
            for intent, pattern_groups in self.intent_patterns.items():
                for pattern_group in pattern_groups:
                    confidence = self._calculate_pattern_confidence(
                        normalized_input, pattern_group, context
                    )
                    
                    if confidence > 0:
                        intent_scores.append((intent, confidence, pattern_group))
            
            # Sort by confidence and get the best match
            intent_scores.sort(key=lambda x: x[1], reverse=True)
            
            if not intent_scores or intent_scores[0][1] < self.confidence_threshold:
                # No confident match found
                return IntentResult(
                    intent=ConversationIntent.UNKNOWN,
                    confidence=0.0,
                    input_type=self._detect_input_type_from_text(user_input),
                    alternative_intents=[(intent, conf) for intent, conf, _ in intent_scores[:3]]
                )
            
            # Get the best match
            best_intent, best_confidence, best_pattern_group = intent_scores[0]
            
            # Extract parameters based on the matched pattern
            parameters = self._extract_parameters(
                user_input, normalized_input, best_intent, best_pattern_group
            )
            
            # Detect input type
            input_type = self._detect_input_type(parameters, context)
            
            # Determine if context is required
            requires_context = self._requires_context(best_intent, parameters, context)
            
            # Create alternative intents list
            alternative_intents = [(intent, conf) for intent, conf, _ in intent_scores[1:4]]
            
            return IntentResult(
                intent=best_intent,
                confidence=best_confidence,
                parameters=parameters,
                input_type=input_type,
                requires_context=requires_context,
                alternative_intents=alternative_intents,
                reasoning=f"Matched pattern with {best_confidence:.2f} confidence"
            )
            
        except Exception as e:
            logger.error(f"Error classifying intent: {e}", exc_info=True)
            return IntentResult(
                intent=ConversationIntent.UNKNOWN,
                confidence=0.0,
                input_type=InputType.UNKNOWN,
                reasoning=f"Classification error: {str(e)}"
            )
    
    def _calculate_pattern_confidence(self, normalized_input: str, 
                                    pattern_group: Dict[str, Any],
                                    context: Optional[ConversationContext] = None) -> float:
        """
        Calculate confidence score for a pattern group match
        
        Args:
            normalized_input: Normalized user input
            pattern_group: Pattern group to match against
            context: Optional conversation context
        
        Returns:
            float: Confidence score (0.0 to 1.0)
        """
        confidence = 0.0
        
        # Check regex patterns
        pattern_matches = 0
        for pattern in pattern_group['patterns']:
            if re.search(pattern, normalized_input, re.IGNORECASE):
                pattern_matches += 1
        
        if pattern_matches > 0:
            # Base confidence from pattern match
            confidence = pattern_group['confidence_base']
            
            # Boost confidence for multiple pattern matches
            if pattern_matches > 1:
                confidence = min(1.0, confidence + 0.1 * (pattern_matches - 1))
        
        # Check keyword presence
        keyword_matches = 0
        for keyword in pattern_group['keywords']:
            if keyword.lower() in normalized_input:
                keyword_matches += 1
        
        if keyword_matches > 0:
            # Add keyword confidence boost
            keyword_boost = min(0.3, 0.1 * keyword_matches)
            confidence += keyword_boost
        
        # Context-aware confidence boost
        if context and confidence > 0:
            context_boost = self._calculate_context_boost(pattern_group, context)
            confidence = min(1.0, confidence + context_boost)
        
        return confidence
    
    def _calculate_context_boost(self, pattern_group: Dict[str, Any],
                               context: ConversationContext) -> float:
        """
        Calculate confidence boost based on conversation context
        
        Args:
            pattern_group: The pattern group being evaluated
            context: Conversation context
        
        Returns:
            float: Context boost value
        """
        boost = 0.0
        
        # Check recent interaction patterns
        recent_interactions = context.get_recent_interactions(3)
        
        for interaction in recent_interactions:
            # Boost confidence if user has been doing similar actions
            if any(keyword in interaction.user_input.lower() 
                   for keyword in pattern_group['keywords']):
                boost += 0.05
        
        # Boost confidence if user has established preferences
        if context.user_preferences:
            # Example: if user prefers certain video formats, boost video-related intents
            if 'preferred_video_format' in context.user_preferences:
                if any(keyword in ['video', 'asl', 'sign'] for keyword in pattern_group['keywords']):
                    boost += 0.1
        
        return min(self.context_boost, boost)
    
    def _extract_parameters(self, original_input: str, normalized_input: str,
                          intent: ConversationIntent, pattern_group: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract parameters from user input based on intent and matched patterns
        
        Args:
            original_input: Original user input
            normalized_input: Normalized user input
            intent: Classified intent
            pattern_group: Matched pattern group
        
        Returns:
            Dict containing extracted parameters
        """
        parameters = {}
        extraction_type = pattern_group.get('parameter_extraction', 'none')
        
        if extraction_type == 'text_content':
            # Extract text content for translation
            text_content = self._extract_text_content(original_input, pattern_group['patterns'])
            if text_content:
                parameters['text'] = text_content
                parameters['original_input'] = original_input
        
        elif extraction_type == 'audio_metadata':
            # Extract audio-related parameters
            parameters.update(self._extract_audio_parameters(original_input))
        
        elif extraction_type == 'video_metadata':
            # Extract video-related parameters
            parameters.update(self._extract_video_parameters(original_input))
        
        elif extraction_type == 'help_topic':
            # Extract help topic
            help_topic = self._extract_help_topic(normalized_input)
            if help_topic:
                parameters['help_topic'] = help_topic
        
        elif extraction_type == 'status_query':
            # Extract status query details
            parameters.update(self._extract_status_parameters(normalized_input))
        
        elif extraction_type == 'retry_context':
            # Extract retry context
            parameters.update(self._extract_retry_parameters(normalized_input))
        
        elif extraction_type == 'context_reference':
            # Extract context reference details
            parameters.update(self._extract_context_reference(normalized_input))
        
        elif extraction_type == 'greeting_type':
            # Extract greeting type
            parameters['greeting_type'] = self._extract_greeting_type(normalized_input)
        
        return parameters
    
    def _extract_text_content(self, input_text: str, patterns: List[str]) -> Optional[str]:
        """Extract text content from translation requests"""
        for pattern in patterns:
            match = re.search(pattern, input_text, re.IGNORECASE)
            if match and match.groups():
                # Return the first captured group (the text to translate)
                return match.group(1).strip().strip('"\'')
        
        # If no pattern captured text, try to extract it heuristically
        # Remove common command words and return the remainder
        command_words = ['translate', 'convert', 'turn', 'make', 'create', 'please', 'can you', 'help me']
        text = input_text
        
        for word in command_words:
            text = re.sub(rf'\b{re.escape(word)}\b', '', text, flags=re.IGNORECASE)
        
        # Clean up and return if substantial text remains
        text = text.strip().strip('"\'').strip()
        if len(text) > 3:  # Minimum meaningful text length
            return text
        
        return None
    
    def _extract_audio_parameters(self, input_text: str) -> Dict[str, Any]:
        """Extract audio-related parameters"""
        parameters = {}
        
        # Look for file references
        file_patterns = [
            r'(?:file|audio|recording)\s+(?:named|called)\s+["\']?([^"\']+)["\']?',
            r'["\']?([^"\']+\.(?:mp3|wav|m4a|aac|ogg))["\']?'
        ]
        
        for pattern in file_patterns:
            match = re.search(pattern, input_text, re.IGNORECASE)
            if match:
                parameters['audio_file'] = match.group(1)
                break
        
        # Look for format preferences
        if re.search(r'\b(?:mp3|wav|m4a|aac|ogg)\b', input_text, re.IGNORECASE):
            format_match = re.search(r'\b(mp3|wav|m4a|aac|ogg)\b', input_text, re.IGNORECASE)
            if format_match:
                parameters['preferred_format'] = format_match.group(1).lower()
        
        return parameters
    
    def _extract_video_parameters(self, input_text: str) -> Dict[str, Any]:
        """Extract video-related parameters"""
        parameters = {}
        
        # Look for video file references
        video_patterns = [
            r'(?:video|file)\s+(?:named|called)\s+["\']?([^"\']+)["\']?',
            r'["\']?([^"\']+\.(?:mp4|avi|mov|mkv|webm))["\']?'
        ]
        
        for pattern in video_patterns:
            match = re.search(pattern, input_text, re.IGNORECASE)
            if match:
                parameters['video_file'] = match.group(1)
                break
        
        # Look for analysis preferences
        if re.search(r'\b(?:stream|live|real-time)\b', input_text, re.IGNORECASE):
            parameters['analysis_type'] = 'stream'
        else:
            parameters['analysis_type'] = 'file'
        
        return parameters
    
    def _extract_help_topic(self, normalized_input: str) -> Optional[str]:
        """Extract specific help topic from help requests"""
        help_topics = {
            'translation': ['translate', 'translation', 'convert'],
            'audio': ['audio', 'voice', 'speech', 'sound'],
            'video': ['video', 'asl', 'sign language', 'signing'],
            'features': ['features', 'capabilities', 'functions', 'what can you do'],
            'getting_started': ['getting started', 'new', 'beginner', 'how to use'],
            'examples': ['example', 'examples', 'show me', 'demonstrate']
        }
        
        for topic, keywords in help_topics.items():
            if any(keyword in normalized_input for keyword in keywords):
                return topic
        
        return 'general'
    
    def _extract_status_parameters(self, normalized_input: str) -> Dict[str, Any]:
        """Extract status query parameters"""
        parameters = {}
        
        if 'translation' in normalized_input:
            parameters['query_type'] = 'translation'
        elif 'job' in normalized_input or 'request' in normalized_input:
            parameters['query_type'] = 'job'
        else:
            parameters['query_type'] = 'general'
        
        if any(word in normalized_input for word in ['time', 'long', 'when']):
            parameters['wants_eta'] = True
        
        return parameters
    
    def _extract_retry_parameters(self, normalized_input: str) -> Dict[str, Any]:
        """Extract retry-related parameters"""
        parameters = {}
        
        if 'different' in normalized_input or 'another' in normalized_input:
            parameters['wants_alternative'] = True
        
        if 'failed' in normalized_input or 'wrong' in normalized_input:
            parameters['previous_failed'] = True
        
        return parameters
    
    def _extract_context_reference(self, normalized_input: str) -> Dict[str, Any]:
        """Extract context reference parameters"""
        parameters = {}
        
        # Determine what they're referring to
        if 'translation' in normalized_input:
            parameters['reference_type'] = 'translation'
        elif 'video' in normalized_input:
            parameters['reference_type'] = 'video'
        elif 'result' in normalized_input:
            parameters['reference_type'] = 'result'
        else:
            parameters['reference_type'] = 'general'
        
        # Determine which one (first, last, etc.)
        if 'last' in normalized_input or 'previous' in normalized_input:
            parameters['reference_index'] = 'last'
        elif 'first' in normalized_input:
            parameters['reference_index'] = 'first'
        elif 'second' in normalized_input:
            parameters['reference_index'] = 'second'
        else:
            parameters['reference_index'] = 'last'  # Default to last
        
        return parameters
    
    def _extract_greeting_type(self, normalized_input: str) -> str:
        """Extract greeting type"""
        if 'morning' in normalized_input:
            return 'morning'
        elif 'afternoon' in normalized_input:
            return 'afternoon'
        elif 'evening' in normalized_input:
            return 'evening'
        elif any(word in normalized_input for word in ['how are you', 'how\'s it going']):
            return 'inquiry'
        else:
            return 'general'
    
    def _detect_input_type_from_text(self, user_input: str) -> InputType:
        """Detect input type from text analysis"""
        normalized = user_input.lower()
        
        if any(word in normalized for word in ['audio', 'voice', 'speech', 'sound', 'recording']):
            return InputType.AUDIO
        elif any(word in normalized for word in ['video', 'asl', 'sign language', 'signing']):
            return InputType.VIDEO
        elif any(word in normalized for word in ['stream', 'live', 'real-time']):
            return InputType.STREAM
        else:
            return InputType.TEXT
    
    def _detect_input_type(self, parameters: Dict[str, Any], 
                         context: Optional[ConversationContext] = None) -> InputType:
        """
        Detect input type from parameters and context
        
        Args:
            parameters: Extracted parameters
            context: Optional conversation context
        
        Returns:
            InputType: Detected input type
        """
        # Check parameters for explicit type indicators
        if 'audio_file' in parameters or 'preferred_format' in parameters:
            return InputType.AUDIO
        elif 'video_file' in parameters:
            return InputType.VIDEO
        elif parameters.get('analysis_type') == 'stream':
            return InputType.STREAM
        elif 'text' in parameters:
            return InputType.TEXT
        
        # Default to text for most intents
        return InputType.TEXT
    
    def _requires_context(self, intent: ConversationIntent, parameters: Dict[str, Any],
                        context: Optional[ConversationContext] = None) -> bool:
        """
        Determine if the intent requires conversation context
        
        Args:
            intent: Classified intent
            parameters: Extracted parameters
            context: Optional conversation context
        
        Returns:
            bool: True if context is required
        """
        # Context reference intents always require context
        if intent == ConversationIntent.CONTEXT_REFERENCE:
            return True
        
        # Retry requests require context to know what to retry
        if intent == ConversationIntent.RETRY_REQUEST:
            return True
        
        # Status checks may require context to know what to check
        if intent == ConversationIntent.STATUS_CHECK:
            return True
        
        # Check if parameters indicate context dependency
        if parameters.get('wants_alternative') or parameters.get('previous_failed'):
            return True
        
        return False