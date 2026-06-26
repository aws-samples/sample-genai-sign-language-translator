"""
Modification Detector

This module provides modification detection from user input, parameter extraction
for translation modifications, and modified translation execution with context preservation.
"""

import logging
import re
from typing import Dict, Any, List, Optional, Tuple, Set
from enum import Enum
from dataclasses import dataclass
from datetime import datetime

try:
    from .data_models import (
        ConversationContext, 
        ConversationIntent, 
        IntentResult,
        TranslationResult,
        InputType,
        ConversationInteraction
    )
    from .memory_manager import ConversationMemoryManager
except ImportError:
    # Handle case when running as standalone module
    from data_models import (
        ConversationContext, 
        ConversationIntent, 
        IntentResult,
        TranslationResult,
        InputType,
        ConversationInteraction
    )
    from memory_manager import ConversationMemoryManager

logger = logging.getLogger(__name__)

class ModificationType(Enum):
    """Types of modifications that can be detected"""
    TEXT_CHANGE = "text_change"                    # Change the input text
    PARAMETER_ADJUSTMENT = "parameter_adjustment"   # Adjust translation parameters
    FORMAT_CHANGE = "format_change"                # Change output format (pose-only, etc.)
    STYLE_CHANGE = "style_change"                  # Change translation style
    SPEED_CHANGE = "speed_change"                  # Change video speed
    QUALITY_CHANGE = "quality_change"              # Change quality settings
    PARTIAL_RETRY = "partial_retry"                # Retry part of previous translation
    COMPLETE_REDO = "complete_redo"                # Completely redo translation
    ENHANCEMENT = "enhancement"                    # Add enhancements to existing result

class ModificationScope(Enum):
    """Scope of the modification"""
    CURRENT_TRANSLATION = "current_translation"    # Modify the most recent translation
    SPECIFIC_TRANSLATION = "specific_translation"  # Modify a specific past translation
    ALL_TRANSLATIONS = "all_translations"          # Apply to all future translations
    SESSION_PREFERENCE = "session_preference"      # Set preference for session

@dataclass
class ModificationRequest:
    """Data class representing a modification request"""
    modification_type: ModificationType
    scope: ModificationScope
    target_translation: Optional[TranslationResult] = None
    original_parameters: Dict[str, Any] = None
    modified_parameters: Dict[str, Any] = None
    user_input: str = ""
    confidence: float = 0.0
    reasoning: str = ""
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
        if self.original_parameters is None:
            self.original_parameters = {}
        if self.modified_parameters is None:
            self.modified_parameters = {}

class ModificationDetector:
    """
    Detects modification requests from user input and extracts parameters
    
    This class analyzes user input to determine if they want to modify a previous
    translation, extracts the specific modifications requested, and prepares
    parameters for re-execution with context preservation.
    """
    
    def __init__(self, memory_manager: Optional[ConversationMemoryManager] = None):
        """Initialize the modification detector"""
        self.memory_manager = memory_manager or ConversationMemoryManager()
        
        # Modification detection patterns
        self.modification_patterns = {
            # Text change patterns
            ModificationType.TEXT_CHANGE: [
                r"change (?:the )?text to (.+)",
                r"instead of .+ use (.+)",
                r"replace .+ with (.+)",
                r"try (?:with )?(.+) instead",
                r"use (.+) as the text",
                r"translate (.+) instead"
            ],
            
            # Parameter adjustment patterns
            ModificationType.PARAMETER_ADJUSTMENT: [
                r"make it (faster|slower)",
                r"use (high|low|medium) quality",
                r"with (more|less) detail",
                r"adjust the (speed|quality|sensitivity)",
                r"set .+ to (.+)"
            ],
            
            # Format change patterns
            ModificationType.FORMAT_CHANGE: [
                r"(?:just|only) (?:the )?pose(?:s)?",
                r"pose[- ]?only",
                r"without (?:the )?avatar",
                r"include (?:the )?avatar",
                r"with (?:full )?signing",
                r"(?:add|include) (?:the )?sign(?:ing)? video"
            ],
            
            # Style change patterns
            ModificationType.STYLE_CHANGE: [
                r"more (formal|casual|expressive)",
                r"less (formal|casual|expressive)",
                r"change (?:the )?style to (.+)",
                r"make it more (.+)",
                r"use (.+) style"
            ],
            
            # Speed change patterns
            ModificationType.SPEED_CHANGE: [
                r"make it (faster|slower)",
                r"speed it up",
                r"slow it down",
                r"change (?:the )?speed",
                r"at (.+) speed"
            ],
            
            # Quality change patterns
            ModificationType.QUALITY_CHANGE: [
                r"(?:higher|better) quality",
                r"(?:lower|worse) quality",
                r"improve (?:the )?quality",
                r"with (high|medium|low) quality",
                r"enhance (?:the )?video"
            ],
            
            # Partial retry patterns
            ModificationType.PARTIAL_RETRY: [
                r"just (?:the )?(?:first|last) (?:part|sentence|word)",
                r"only (?:the )?(.+) part",
                r"redo (?:the )?(.+) section",
                r"retry (?:the )?(.+) portion"
            ],
            
            # Complete redo patterns
            ModificationType.COMPLETE_REDO: [
                r"start over",
                r"do it again",
                r"redo (?:the )?(?:whole )?(?:thing|translation)",
                r"try again (?:from )?(?:the )?(?:beginning|start)",
                r"completely redo"
            ],
            
            # Enhancement patterns
            ModificationType.ENHANCEMENT: [
                r"add (.+)",
                r"include (.+)",
                r"with (.+) added",
                r"enhance (?:with|by) (.+)",
                r"improve (?:by|with) (.+)"
            ]
        }
        
        # Scope detection patterns
        self.scope_patterns = {
            ModificationScope.CURRENT_TRANSLATION: [
                r"(?:the )?(?:last|most recent|current|this) (?:translation|one)",
                r"(?:that|this) (?:translation|result)",
                r"(?:the )?previous (?:translation|result)"
            ],
            
            ModificationScope.SPECIFIC_TRANSLATION: [
                r"(?:the )?(?:first|second|third|\d+(?:st|nd|rd|th)) (?:translation|one)",
                r"(?:the )?translation (?:of|with|about) (.+)",
                r"when I (?:said|asked|translated) (.+)"
            ],
            
            ModificationScope.ALL_TRANSLATIONS: [
                r"(?:all|every) (?:future )?translations?",
                r"from now on",
                r"for (?:all|every) (?:future )?requests?",
                r"as (?:the )?default"
            ],
            
            ModificationScope.SESSION_PREFERENCE: [
                r"for (?:this|the) (?:session|conversation)",
                r"(?:remember|save) (?:this|that) (?:setting|preference)",
                r"use (?:this|that) (?:setting|preference) (?:going forward|from now on)"
            ]
        }
        
        # Reference detection patterns
        self.reference_patterns = [
            r"(?:the )?(?:last|most recent|previous) (?:translation|result|one)",
            r"(?:that|this) (?:translation|result)",
            r"(?:the )?(?:first|second|third|\d+(?:st|nd|rd|th)) (?:translation|one)",
            r"when I (?:said|asked|translated) ['\"](.+)['\"]",
            r"(?:the )?translation (?:of|with|about) ['\"](.+)['\"]"
        ]
        
        logger.info("ModificationDetector initialized with pattern matching")
    
    def detect_modification_request(self, user_input: str, 
                                  context: ConversationContext) -> Optional[ModificationRequest]:
        """
        Detect if user input contains a modification request
        
        Args:
            user_input: User's input text
            context: Current conversation context
        
        Returns:
            ModificationRequest or None if no modification detected
        """
        user_input_lower = user_input.lower().strip()
        
        # Check if this looks like a modification request
        if not self._is_modification_request(user_input_lower, context):
            return None
        
        # Detect modification type
        modification_type, extracted_value, confidence = self._detect_modification_type(user_input_lower)
        
        if modification_type is None:
            return None
        
        # Detect scope
        scope = self._detect_modification_scope(user_input_lower, context)
        
        # Find target translation
        target_translation = self._find_target_translation(user_input_lower, context, scope)
        
        if target_translation is None and scope != ModificationScope.ALL_TRANSLATIONS:
            logger.warning("Could not find target translation for modification")
            return None
        
        # Extract parameters
        original_parameters, modified_parameters = self._extract_modification_parameters(
            modification_type, extracted_value, target_translation, user_input_lower
        )
        
        # Generate reasoning
        reasoning = self._generate_modification_reasoning(
            modification_type, scope, extracted_value, target_translation
        )
        
        return ModificationRequest(
            modification_type=modification_type,
            scope=scope,
            target_translation=target_translation,
            original_parameters=original_parameters,
            modified_parameters=modified_parameters,
            user_input=user_input,
            confidence=confidence,
            reasoning=reasoning
        )
    
    def extract_modification_parameters(self, modification_request: ModificationRequest,
                                      context: ConversationContext) -> Dict[str, Any]:
        """
        Extract complete parameters for executing the modification
        
        Args:
            modification_request: The modification request to process
            context: Current conversation context
        
        Returns:
            Dict[str, Any]: Complete parameters for re-execution
        """
        if not modification_request.target_translation:
            return modification_request.modified_parameters.copy()
        
        # Start with original parameters from target translation
        base_parameters = self._extract_original_parameters(modification_request.target_translation)
        
        # Apply modifications
        final_parameters = base_parameters.copy()
        final_parameters.update(modification_request.modified_parameters)
        
        # Apply type-specific parameter extraction
        if modification_request.modification_type == ModificationType.TEXT_CHANGE:
            final_parameters = self._apply_text_change(final_parameters, modification_request)
        
        elif modification_request.modification_type == ModificationType.FORMAT_CHANGE:
            final_parameters = self._apply_format_change(final_parameters, modification_request)
        
        elif modification_request.modification_type == ModificationType.PARAMETER_ADJUSTMENT:
            final_parameters = self._apply_parameter_adjustment(final_parameters, modification_request)
        
        elif modification_request.modification_type == ModificationType.SPEED_CHANGE:
            final_parameters = self._apply_speed_change(final_parameters, modification_request)
        
        elif modification_request.modification_type == ModificationType.QUALITY_CHANGE:
            final_parameters = self._apply_quality_change(final_parameters, modification_request)
        
        elif modification_request.modification_type == ModificationType.ENHANCEMENT:
            final_parameters = self._apply_enhancement(final_parameters, modification_request)
        
        return final_parameters
    
    def create_modification_intent(self, modification_request: ModificationRequest,
                                 context: ConversationContext) -> IntentResult:
        """
        Create an IntentResult for executing the modification
        
        Args:
            modification_request: The modification request
            context: Current conversation context
        
        Returns:
            IntentResult: Intent result for orchestrator execution
        """
        # Extract complete parameters
        parameters = self.extract_modification_parameters(modification_request, context)
        
        # Determine intent based on target translation or parameters
        if modification_request.target_translation:
            original_intent = self._determine_original_intent(modification_request.target_translation)
        else:
            original_intent = self._determine_intent_from_parameters(parameters)
        
        # Determine input type
        input_type = self._determine_input_type(parameters)
        
        return IntentResult(
            intent=original_intent,
            confidence=modification_request.confidence,
            parameters=parameters,
            input_type=input_type,
            requires_context=True,
            reasoning=f"Modification request: {modification_request.reasoning}"
        )
    
    def apply_session_preferences(self, modification_request: ModificationRequest,
                                context: ConversationContext) -> None:
        """
        Apply modification as a session preference for future translations
        
        Args:
            modification_request: The modification request
            context: Current conversation context
        """
        if modification_request.scope not in [ModificationScope.SESSION_PREFERENCE, ModificationScope.ALL_TRANSLATIONS]:
            return
        
        # Extract preference settings
        preferences = {}
        
        if modification_request.modification_type == ModificationType.FORMAT_CHANGE:
            if 'pose_only' in modification_request.modified_parameters:
                preferences['default_pose_only'] = modification_request.modified_parameters['pose_only']
            if 'include_avatar' in modification_request.modified_parameters:
                preferences['default_include_avatar'] = modification_request.modified_parameters['include_avatar']
        
        elif modification_request.modification_type == ModificationType.QUALITY_CHANGE:
            if 'quality' in modification_request.modified_parameters:
                preferences['default_quality'] = modification_request.modified_parameters['quality']
        
        elif modification_request.modification_type == ModificationType.SPEED_CHANGE:
            if 'speed' in modification_request.modified_parameters:
                preferences['default_speed'] = modification_request.modified_parameters['speed']
        
        # Store preferences in context
        for key, value in preferences.items():
            context.update_user_preference(key, value)
        
        # Store in memory for persistence
        if context.session_id:
            memory_key = f"session_preferences:{context.session_id}"
            self.memory_manager.store_data(memory_key, context.user_preferences)
        
        logger.info(f"Applied session preferences: {preferences}")
    
    def get_modification_suggestions(self, context: ConversationContext) -> List[Dict[str, Any]]:
        """
        Get suggestions for possible modifications based on conversation history
        
        Args:
            context: Current conversation context
        
        Returns:
            List[Dict[str, Any]]: List of modification suggestions
        """
        suggestions = []
        
        # Get recent successful translations
        successful_translations = context.get_successful_translations()
        if not successful_translations:
            return suggestions
        
        last_translation = successful_translations[-1]
        if not last_translation.translation_result:
            return suggestions
        
        result = last_translation.translation_result
        
        # Suggest format modifications
        if result.video_urls:
            if 'pose' in result.video_urls and 'sign' in result.video_urls:
                suggestions.append({
                    'type': 'format_change',
                    'description': 'Show only the pose video (simpler, faster)',
                    'example': 'Just show the pose video',
                    'parameters': {'pose_only': True}
                })
            
            if 'pose' in result.video_urls and 'avatar' not in result.video_urls:
                suggestions.append({
                    'type': 'format_change',
                    'description': 'Add avatar video for better visualization',
                    'example': 'Include the avatar video',
                    'parameters': {'include_avatar': True}
                })
        
        # Suggest text modifications for text-based translations
        if result.input_type == InputType.TEXT and result.input_text:
            text = result.input_text
            if len(text.split()) > 5:
                suggestions.append({
                    'type': 'text_change',
                    'description': 'Try with shorter, simpler text',
                    'example': f'Use "{text.split()[0]} {text.split()[1]}" instead',
                    'parameters': {'text': ' '.join(text.split()[:3])}
                })
        
        # Suggest quality improvements
        suggestions.append({
            'type': 'quality_change',
            'description': 'Generate with higher quality',
            'example': 'Make it higher quality',
            'parameters': {'quality': 'high'}
        })
        
        # Suggest speed adjustments
        suggestions.append({
            'type': 'speed_change',
            'description': 'Adjust the signing speed',
            'example': 'Make it slower',
            'parameters': {'speed': 'slow'}
        })
        
        return suggestions[:4]  # Limit to 4 suggestions
    
    def _is_modification_request(self, user_input: str, context: ConversationContext) -> bool:
        """Check if user input appears to be a modification request"""
        # Must have some conversation history to modify
        if not context.conversation_history:
            return False
        
        # Check for modification keywords
        modification_keywords = [
            'change', 'modify', 'adjust', 'alter', 'update', 'fix',
            'instead', 'rather', 'different', 'better', 'improve',
            'redo', 'retry', 'again', 'over', 'replace', 'substitute'
        ]
        
        # Check for reference to previous translations
        reference_keywords = [
            'last', 'previous', 'that', 'this', 'recent', 'earlier',
            'before', 'above', 'translation', 'result', 'video'
        ]
        
        has_modification = any(keyword in user_input for keyword in modification_keywords)
        has_reference = any(keyword in user_input for keyword in reference_keywords)
        
        return has_modification or has_reference
    
    def _detect_modification_type(self, user_input: str) -> Tuple[Optional[ModificationType], str, float]:
        """Detect the type of modification requested"""
        best_match = None
        best_value = ""
        best_confidence = 0.0
        
        for mod_type, patterns in self.modification_patterns.items():
            for pattern in patterns:
                match = re.search(pattern, user_input, re.IGNORECASE)
                if match:
                    confidence = 0.8  # Base confidence for pattern match
                    
                    # Extract value if captured
                    value = match.group(1) if match.groups() else ""
                    
                    # Adjust confidence based on match quality
                    if len(match.group(0)) > len(user_input) * 0.5:
                        confidence += 0.1  # Bonus for covering most of input
                    
                    if confidence > best_confidence:
                        best_match = mod_type
                        best_value = value
                        best_confidence = confidence
        
        return best_match, best_value, best_confidence
    
    def _detect_modification_scope(self, user_input: str, context: ConversationContext) -> ModificationScope:
        """Detect the scope of the modification"""
        for scope, patterns in self.scope_patterns.items():
            for pattern in patterns:
                if re.search(pattern, user_input, re.IGNORECASE):
                    return scope
        
        # Default to current translation if we have recent history
        if context.conversation_history:
            return ModificationScope.CURRENT_TRANSLATION
        
        return ModificationScope.ALL_TRANSLATIONS
    
    def _find_target_translation(self, user_input: str, context: ConversationContext,
                               scope: ModificationScope) -> Optional[TranslationResult]:
        """Find the target translation for modification"""
        if scope == ModificationScope.ALL_TRANSLATIONS:
            return None
        
        successful_translations = context.get_successful_translations()
        if not successful_translations:
            return None
        
        if scope == ModificationScope.CURRENT_TRANSLATION:
            # Return most recent successful translation
            return successful_translations[-1].translation_result
        
        elif scope == ModificationScope.SPECIFIC_TRANSLATION:
            # Try to find specific translation by reference
            for pattern in self.reference_patterns:
                match = re.search(pattern, user_input, re.IGNORECASE)
                if match and match.groups():
                    reference_text = match.group(1).lower()
                    
                    # Find translation with matching input text
                    for interaction in reversed(successful_translations):
                        if interaction.translation_result and interaction.translation_result.input_text:
                            if reference_text in interaction.translation_result.input_text.lower():
                                return interaction.translation_result
            
            # Fallback to most recent if specific not found
            return successful_translations[-1].translation_result
        
        return None
    
    def _extract_modification_parameters(self, modification_type: ModificationType,
                                       extracted_value: str, target_translation: Optional[TranslationResult],
                                       user_input: str) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """Extract original and modified parameters"""
        original_params = {}
        modified_params = {}
        
        if target_translation:
            original_params = self._extract_original_parameters(target_translation)
        
        # Apply type-specific parameter extraction
        if modification_type == ModificationType.TEXT_CHANGE:
            modified_params['text'] = extracted_value.strip()
        
        elif modification_type == ModificationType.FORMAT_CHANGE:
            if 'pose' in user_input and 'only' in user_input:
                modified_params['pose_only'] = True
            elif 'avatar' in user_input:
                if 'without' in user_input or 'no' in user_input:
                    modified_params['include_avatar'] = False
                else:
                    modified_params['include_avatar'] = True
        
        elif modification_type == ModificationType.SPEED_CHANGE:
            if 'faster' in user_input or 'speed up' in user_input:
                modified_params['speed'] = 'fast'
            elif 'slower' in user_input or 'slow down' in user_input:
                modified_params['speed'] = 'slow'
            elif extracted_value:
                modified_params['speed'] = extracted_value
        
        elif modification_type == ModificationType.QUALITY_CHANGE:
            if 'high' in user_input or 'better' in user_input:
                modified_params['quality'] = 'high'
            elif 'low' in user_input or 'worse' in user_input:
                modified_params['quality'] = 'low'
            elif extracted_value:
                modified_params['quality'] = extracted_value
        
        return original_params, modified_params
    
    def _extract_original_parameters(self, translation_result: TranslationResult) -> Dict[str, Any]:
        """Extract original parameters from a translation result"""
        params = {}
        
        if translation_result.input_text:
            params['text'] = translation_result.input_text
        
        if translation_result.input_type == InputType.AUDIO:
            # Try to extract bucket/key from metadata or input_text
            if translation_result.metadata:
                params.update(translation_result.metadata)
            elif '/' in translation_result.input_text:
                parts = translation_result.input_text.split('/')
                if len(parts) >= 2:
                    params['bucket_name'] = parts[0]
                    params['key_name'] = '/'.join(parts[1:])
        
        elif translation_result.input_type == InputType.VIDEO:
            # Similar extraction for video
            if translation_result.metadata:
                params.update(translation_result.metadata)
            elif '/' in translation_result.input_text:
                parts = translation_result.input_text.split('/')
                if len(parts) >= 2:
                    params['bucket_name'] = parts[0]
                    params['key_name'] = '/'.join(parts[1:])
        
        elif translation_result.input_type == InputType.STREAM:
            params['stream_name'] = translation_result.input_text
        
        return params
    
    def _apply_text_change(self, parameters: Dict[str, Any], 
                          modification_request: ModificationRequest) -> Dict[str, Any]:
        """Apply text change modification"""
        if 'text' in modification_request.modified_parameters:
            parameters['text'] = modification_request.modified_parameters['text']
        return parameters
    
    def _apply_format_change(self, parameters: Dict[str, Any],
                           modification_request: ModificationRequest) -> Dict[str, Any]:
        """Apply format change modification"""
        parameters.update(modification_request.modified_parameters)
        return parameters
    
    def _apply_parameter_adjustment(self, parameters: Dict[str, Any],
                                  modification_request: ModificationRequest) -> Dict[str, Any]:
        """Apply parameter adjustment modification"""
        parameters.update(modification_request.modified_parameters)
        return parameters
    
    def _apply_speed_change(self, parameters: Dict[str, Any],
                          modification_request: ModificationRequest) -> Dict[str, Any]:
        """Apply speed change modification"""
        parameters.update(modification_request.modified_parameters)
        return parameters
    
    def _apply_quality_change(self, parameters: Dict[str, Any],
                            modification_request: ModificationRequest) -> Dict[str, Any]:
        """Apply quality change modification"""
        parameters.update(modification_request.modified_parameters)
        return parameters
    
    def _apply_enhancement(self, parameters: Dict[str, Any],
                         modification_request: ModificationRequest) -> Dict[str, Any]:
        """Apply enhancement modification"""
        parameters.update(modification_request.modified_parameters)
        return parameters
    
    def _determine_original_intent(self, translation_result: TranslationResult) -> ConversationIntent:
        """Determine original intent from translation result"""
        if translation_result.input_type == InputType.TEXT:
            return ConversationIntent.TEXT_TO_ASL
        elif translation_result.input_type == InputType.AUDIO:
            return ConversationIntent.AUDIO_TO_ASL
        elif translation_result.input_type in [InputType.VIDEO, InputType.STREAM]:
            return ConversationIntent.ASL_TO_TEXT
        else:
            return ConversationIntent.TEXT_TO_ASL  # Default
    
    def _determine_intent_from_parameters(self, parameters: Dict[str, Any]) -> ConversationIntent:
        """Determine intent from parameters"""
        if 'text' in parameters:
            return ConversationIntent.TEXT_TO_ASL
        elif 'bucket_name' in parameters and 'key_name' in parameters:
            # Could be audio or video - default to audio
            return ConversationIntent.AUDIO_TO_ASL
        elif 'stream_name' in parameters:
            return ConversationIntent.ASL_TO_TEXT
        else:
            return ConversationIntent.TEXT_TO_ASL
    
    def _determine_input_type(self, parameters: Dict[str, Any]) -> InputType:
        """Determine input type from parameters"""
        if 'text' in parameters:
            return InputType.TEXT
        elif 'stream_name' in parameters:
            return InputType.STREAM
        elif 'bucket_name' in parameters and 'key_name' in parameters:
            # Check file extension for type
            key_name = parameters.get('key_name', '').lower()
            if any(ext in key_name for ext in ['.mp3', '.wav', '.m4a', '.aac']):
                return InputType.AUDIO
            else:
                return InputType.VIDEO
        else:
            return InputType.UNKNOWN
    
    def _generate_modification_reasoning(self, modification_type: ModificationType,
                                       scope: ModificationScope, extracted_value: str,
                                       target_translation: Optional[TranslationResult]) -> str:
        """Generate reasoning for the modification request"""
        reasoning_parts = []
        
        # Add modification type reasoning
        type_descriptions = {
            ModificationType.TEXT_CHANGE: "changing the input text",
            ModificationType.FORMAT_CHANGE: "changing the output format",
            ModificationType.PARAMETER_ADJUSTMENT: "adjusting translation parameters",
            ModificationType.SPEED_CHANGE: "changing the video speed",
            ModificationType.QUALITY_CHANGE: "changing the quality settings",
            ModificationType.ENHANCEMENT: "adding enhancements",
            ModificationType.PARTIAL_RETRY: "retrying part of the translation",
            ModificationType.COMPLETE_REDO: "completely redoing the translation"
        }
        
        reasoning_parts.append(f"User requested {type_descriptions.get(modification_type, 'modification')}")
        
        # Add scope reasoning
        if scope == ModificationScope.CURRENT_TRANSLATION:
            reasoning_parts.append("for the most recent translation")
        elif scope == ModificationScope.SPECIFIC_TRANSLATION:
            reasoning_parts.append("for a specific previous translation")
        elif scope == ModificationScope.ALL_TRANSLATIONS:
            reasoning_parts.append("for all future translations")
        elif scope == ModificationScope.SESSION_PREFERENCE:
            reasoning_parts.append("as a session preference")
        
        # Add extracted value if available
        if extracted_value:
            reasoning_parts.append(f"with value: {extracted_value}")
        
        return "; ".join(reasoning_parts)