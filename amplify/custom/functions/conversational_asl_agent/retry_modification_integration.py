"""
Retry and Modification Integration

This module integrates retry functionality, modification capabilities, and alternative
exploration into a cohesive system for handling translation improvements and variations.
"""

import logging
from typing import Dict, Any, List, Optional, Tuple, Union
from enum import Enum
from dataclasses import dataclass
from datetime import datetime

try:
    from .data_models import (
        ConversationContext, 
        ConversationIntent, 
        IntentResult,
        TranslationResult,
        InputType
    )
    from .memory_manager import ConversationMemoryManager
    from .retry_manager import RetryManager, RetrySession, RetryStrategy
    from .modification_detector import ModificationDetector, ModificationRequest
    from .alternative_explorer import AlternativeExplorer, AlternativeComparison
except ImportError:
    # Handle case when running as standalone module
    from data_models import (
        ConversationContext, 
        ConversationIntent, 
        IntentResult,
        TranslationResult,
        InputType
    )
    from memory_manager import ConversationMemoryManager
    from retry_manager import RetryManager, RetrySession, RetryStrategy
    from modification_detector import ModificationDetector, ModificationRequest
    from alternative_explorer import AlternativeExplorer, AlternativeComparison

logger = logging.getLogger(__name__)

class ActionType(Enum):
    """Types of actions that can be performed"""
    RETRY = "retry"
    MODIFY = "modify"
    EXPLORE_ALTERNATIVES = "explore_alternatives"
    APPLY_ALTERNATIVE = "apply_alternative"
    COMBINE_APPROACHES = "combine_approaches"

@dataclass
class ActionRequest:
    """Data class representing a user action request"""
    action_type: ActionType
    user_input: str
    context: ConversationContext
    target_translation: Optional[TranslationResult] = None
    specific_parameters: Optional[Dict[str, Any]] = None
    confidence: float = 0.0
    reasoning: str = ""

class RetryModificationIntegration:
    """
    Integrates retry, modification, and alternative exploration capabilities
    
    This class provides a unified interface for handling all types of translation
    improvements, retries, modifications, and alternative approaches with
    conversational guidance and context preservation.
    """
    
    def __init__(self, memory_manager: Optional[ConversationMemoryManager] = None):
        """Initialize the integrated retry and modification system"""
        self.memory_manager = memory_manager or ConversationMemoryManager()
        
        # Initialize component managers
        self.retry_manager = RetryManager(self.memory_manager)
        self.modification_detector = ModificationDetector(self.memory_manager)
        self.alternative_explorer = AlternativeExplorer(self.memory_manager)
        
        logger.info("RetryModificationIntegration initialized with all components")
    
    def handle_user_request(self, user_input: str, context: ConversationContext,
                          orchestrator_callback: Optional[callable] = None) -> Tuple[Optional[TranslationResult], str]:
        """
        Handle user request for retry, modification, or alternative exploration
        
        Args:
            user_input: User's input text
            context: Current conversation context
            orchestrator_callback: Optional callback to orchestrator for execution
        
        Returns:
            Tuple[Optional[TranslationResult], str]: Result and conversational response
        """
        try:
            # Analyze user request to determine action type
            action_request = self._analyze_user_request(user_input, context)
            
            if not action_request:
                return None, "I'm not sure what you'd like me to do. Could you clarify if you want to retry, modify, or try a different approach?"
            
            # Route to appropriate handler
            if action_request.action_type == ActionType.RETRY:
                return self._handle_retry_request(action_request, orchestrator_callback)
            
            elif action_request.action_type == ActionType.MODIFY:
                return self._handle_modification_request(action_request, orchestrator_callback)
            
            elif action_request.action_type == ActionType.EXPLORE_ALTERNATIVES:
                return self._handle_alternatives_request(action_request)
            
            elif action_request.action_type == ActionType.APPLY_ALTERNATIVE:
                return self._handle_apply_alternative_request(action_request, orchestrator_callback)
            
            else:
                return None, "I understand you want to make changes, but I'm not sure exactly what. Could you be more specific?"
        
        except Exception as e:
            error_msg = f"I encountered an issue while processing your request: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return None, error_msg
    
    def suggest_improvements(self, failed_result: TranslationResult,
                           context: ConversationContext) -> str:
        """
        Suggest improvements for a failed translation
        
        Args:
            failed_result: The failed translation result
            context: Current conversation context
        
        Returns:
            str: Conversational suggestions for improvement
        """
        suggestions = []
        
        # Get retry suggestions
        retry_session = self.retry_manager.create_retry_session(
            operation_id=f"failed_{int(datetime.now().timestamp())}",
            intent=self._determine_intent_from_result(failed_result),
            parameters=self._extract_parameters_from_result(failed_result),
            error=Exception(failed_result.error_message or "Translation failed"),
            context=context
        )
        
        retry_suggestions = self.retry_manager.suggest_retry_modifications(retry_session, context)
        if retry_suggestions:
            suggestions.append("**Retry Options:**")
            for i, suggestion in enumerate(retry_suggestions[:2], 1):
                suggestions.append(f"{i}. {suggestion['description']}")
        
        # Get alternative suggestions
        original_intent = self._determine_intent_from_result(failed_result)
        original_params = self._extract_parameters_from_result(failed_result)
        
        alternatives = self.alternative_explorer.explore_alternatives(
            original_intent, original_params, context, failed_result.error_message
        )
        
        if alternatives.alternatives:
            suggestions.append("\n**Alternative Approaches:**")
            for i, alt in enumerate(alternatives.alternatives[:2], 1):
                suggestions.append(f"{i}. {alt.title}: {alt.description}")
        
        # Get modification suggestions
        mod_suggestions = self.modification_detector.get_modification_suggestions(context)
        if mod_suggestions:
            suggestions.append("\n**Modification Ideas:**")
            for i, suggestion in enumerate(mod_suggestions[:2], 1):
                suggestions.append(f"{i}. {suggestion['description']}")
        
        if not suggestions:
            return "I don't have specific suggestions right now, but you could try again or ask me to explain what went wrong."
        
        suggestions.insert(0, "Here are some ways we could improve the translation:")
        suggestions.append("\nJust let me know which approach you'd like to try!")
        
        return "\n".join(suggestions)
    
    def get_active_sessions_status(self, context: ConversationContext) -> str:
        """
        Get status of active retry sessions and ongoing modifications
        
        Args:
            context: Current conversation context
        
        Returns:
            str: Status summary
        """
        status_parts = []
        
        # Check active retry sessions
        active_retries = self.retry_manager.get_active_retry_sessions(context)
        if active_retries:
            status_parts.append(f"**Active Retry Sessions:** {len(active_retries)}")
            for session in active_retries[:3]:  # Show up to 3
                attempts = session.get_attempt_count()
                remaining = session.max_attempts - attempts
                status_parts.append(f"• {session.operation_id}: {attempts} attempts, {remaining} remaining")
        
        # Check recent modifications
        recent_interactions = context.get_recent_interactions(5)
        modifications = [i for i in recent_interactions if 'modif' in i.user_input.lower()]
        if modifications:
            status_parts.append(f"\n**Recent Modifications:** {len(modifications)}")
        
        if not status_parts:
            return "No active retry sessions or recent modifications."
        
        return "\n".join(status_parts)
    
    def _analyze_user_request(self, user_input: str, context: ConversationContext) -> Optional[ActionRequest]:
        """Analyze user input to determine the type of action requested"""
        user_input_lower = user_input.lower().strip()
        
        # Check for retry keywords
        retry_keywords = ['retry', 'try again', 'again', 'once more', 'redo']
        if any(keyword in user_input_lower for keyword in retry_keywords):
            return ActionRequest(
                action_type=ActionType.RETRY,
                user_input=user_input,
                context=context,
                confidence=0.8,
                reasoning="User requested retry with keywords"
            )
        
        # Check for modification request
        modification_request = self.modification_detector.detect_modification_request(user_input, context)
        if modification_request:
            return ActionRequest(
                action_type=ActionType.MODIFY,
                user_input=user_input,
                context=context,
                target_translation=modification_request.target_translation,
                confidence=modification_request.confidence,
                reasoning=f"Detected modification: {modification_request.reasoning}"
            )
        
        # Check for alternative exploration keywords
        alternative_keywords = ['alternative', 'different', 'other way', 'another approach', 'options']
        if any(keyword in user_input_lower for keyword in alternative_keywords):
            return ActionRequest(
                action_type=ActionType.EXPLORE_ALTERNATIVES,
                user_input=user_input,
                context=context,
                confidence=0.7,
                reasoning="User requested alternatives"
            )
        
        # Check for specific alternative application
        apply_keywords = ['use', 'try', 'apply', 'go with', 'choose']
        option_keywords = ['option', 'approach', 'method', 'way']
        if any(apply in user_input_lower for apply in apply_keywords) and any(opt in user_input_lower for opt in option_keywords):
            return ActionRequest(
                action_type=ActionType.APPLY_ALTERNATIVE,
                user_input=user_input,
                context=context,
                confidence=0.6,
                reasoning="User wants to apply specific alternative"
            )
        
        return None
    
    def _handle_retry_request(self, action_request: ActionRequest,
                            orchestrator_callback: Optional[callable]) -> Tuple[Optional[TranslationResult], str]:
        """Handle retry request"""
        if not orchestrator_callback:
            return None, "I can't retry right now because the translation system isn't available."
        
        # Find the most recent failed or successful translation to retry
        recent_interactions = action_request.context.get_recent_interactions(5)
        target_interaction = None
        
        for interaction in reversed(recent_interactions):
            if interaction.translation_result:
                target_interaction = interaction
                break
        
        if not target_interaction or not target_interaction.translation_result:
            return None, "I don't see a recent translation to retry. Could you make a new translation request?"
        
        # Create retry session
        original_intent = self._determine_intent_from_result(target_interaction.translation_result)
        original_params = self._extract_parameters_from_result(target_interaction.translation_result)
        
        retry_session = self.retry_manager.create_retry_session(
            operation_id=f"retry_{int(datetime.now().timestamp())}",
            intent=original_intent,
            parameters=original_params,
            error=Exception(target_interaction.translation_result.error_message or "User requested retry"),
            context=action_request.context
        )
        
        # Execute retry
        result, response = self.retry_manager.execute_retry(
            retry_session=retry_session,
            context=action_request.context,
            orchestrator_callback=orchestrator_callback
        )
        
        return result, response
    
    def _handle_modification_request(self, action_request: ActionRequest,
                                   orchestrator_callback: Optional[callable]) -> Tuple[Optional[TranslationResult], str]:
        """Handle modification request"""
        if not orchestrator_callback:
            return None, "I can't make modifications right now because the translation system isn't available."
        
        # Detect the specific modification
        modification_request = self.modification_detector.detect_modification_request(
            action_request.user_input, action_request.context
        )
        
        if not modification_request:
            return None, "I understand you want to make changes, but I'm not sure what specifically to modify. Could you be more specific?"
        
        # Apply session preferences if applicable
        self.modification_detector.apply_session_preferences(modification_request, action_request.context)
        
        # Create intent for modified translation
        intent_result = self.modification_detector.create_modification_intent(
            modification_request, action_request.context
        )
        
        # Execute modified translation
        try:
            result = orchestrator_callback(intent_result, action_request.context)
            
            if result.success:
                response = f"Great! I've applied your modification. {modification_request.reasoning}"
                if modification_request.modification_type.value == 'text_change':
                    response += f" I translated the new text: '{intent_result.parameters.get('text', '')}'"
                elif modification_request.modification_type.value == 'format_change':
                    response += " I've changed the output format as requested."
                response += "\n\nHere are your updated results:"
            else:
                response = f"I tried to apply your modification, but it didn't work: {result.error_message}"
                
                # Suggest alternatives
                alternatives = self.alternative_explorer.explore_alternatives(
                    intent_result.intent, intent_result.parameters, action_request.context, result.error_message
                )
                if alternatives.alternatives:
                    response += f"\n\nHere are some alternatives you could try instead:"
                    for i, alt in enumerate(alternatives.alternatives[:2], 1):
                        response += f"\n{i}. {alt.title}: {alt.description}"
            
            return result, response
            
        except Exception as e:
            error_msg = f"I encountered an error while applying your modification: {str(e)}"
            return None, error_msg
    
    def _handle_alternatives_request(self, action_request: ActionRequest) -> Tuple[None, str]:
        """Handle request to explore alternatives"""
        # Find recent translation to suggest alternatives for
        recent_interactions = action_request.context.get_recent_interactions(5)
        target_interaction = None
        
        for interaction in reversed(recent_interactions):
            if interaction.translation_result:
                target_interaction = interaction
                break
        
        if not target_interaction or not target_interaction.translation_result:
            return None, "I don't see a recent translation to suggest alternatives for. Could you make a translation request first?"
        
        # Generate alternatives
        original_intent = self._determine_intent_from_result(target_interaction.translation_result)
        original_params = self._extract_parameters_from_result(target_interaction.translation_result)
        
        alternatives = self.alternative_explorer.explore_alternatives(
            original_intent, original_params, action_request.context,
            target_interaction.translation_result.error_message
        )
        
        # Format response
        response = self.alternative_explorer.format_alternatives_for_user(alternatives)
        
        return None, response
    
    def _handle_apply_alternative_request(self, action_request: ActionRequest,
                                        orchestrator_callback: Optional[callable]) -> Tuple[Optional[TranslationResult], str]:
        """Handle request to apply a specific alternative"""
        if not orchestrator_callback:
            return None, "I can't apply alternatives right now because the translation system isn't available."
        
        # This would need more sophisticated parsing to identify which specific alternative
        # For now, provide guidance
        return None, ("I understand you want to try a specific alternative. Could you be more specific? "
                     "For example, you could say 'try the fastest option' or 'use pose-only video'.")
    
    def _determine_intent_from_result(self, result: TranslationResult) -> ConversationIntent:
        """Determine original intent from translation result"""
        if result.input_type == InputType.TEXT:
            return ConversationIntent.TEXT_TO_ASL
        elif result.input_type == InputType.AUDIO:
            return ConversationIntent.AUDIO_TO_ASL
        elif result.input_type in [InputType.VIDEO, InputType.STREAM]:
            return ConversationIntent.ASL_TO_TEXT
        else:
            return ConversationIntent.TEXT_TO_ASL
    
    def _extract_parameters_from_result(self, result: TranslationResult) -> Dict[str, Any]:
        """Extract parameters from translation result"""
        params = {}
        
        if result.input_text:
            if result.input_type == InputType.TEXT:
                params['text'] = result.input_text
            elif result.input_type == InputType.STREAM:
                params['stream_name'] = result.input_text
            elif '/' in result.input_text:
                # Assume bucket/key format
                parts = result.input_text.split('/', 1)
                if len(parts) == 2:
                    params['bucket_name'] = parts[0]
                    params['key_name'] = parts[1]
        
        # Add metadata if available
        if result.metadata:
            params.update(result.metadata)
        
        return params