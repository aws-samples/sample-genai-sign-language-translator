"""
Natural Language Understanding Engine

This module provides a comprehensive NLU engine that integrates intent classification,
parameter extraction, and context-aware analysis for conversational ASL agent interactions.
"""

import logging
from typing import Dict, Any, Optional, List

try:
    from .data_models import (
        ConversationIntent, 
        IntentResult, 
        InputType, 
        ConversationContext
    )
    from .intent_classifier import ConversationIntentClassifier
    from .parameter_extractor import ParameterExtractor
    from .context_analyzer import ContextAwareIntentAnalyzer
except ImportError:
    from data_models import (
        ConversationIntent, 
        IntentResult, 
        InputType, 
        ConversationContext
    )
    from intent_classifier import ConversationIntentClassifier
    from parameter_extractor import ParameterExtractor
    from context_analyzer import ContextAwareIntentAnalyzer

logger = logging.getLogger(__name__)

class NaturalLanguageUnderstandingEngine:
    """
    Comprehensive NLU engine that combines intent classification, parameter extraction,
    and context-aware analysis to provide complete natural language understanding
    for conversational ASL agent interactions.
    """
    
    def __init__(self):
        """Initialize the NLU engine with all components"""
        self.intent_classifier = ConversationIntentClassifier()
        self.parameter_extractor = ParameterExtractor()
        self.context_analyzer = ContextAwareIntentAnalyzer()
        
        logger.info("NaturalLanguageUnderstandingEngine initialized")
    
    def understand(self, user_input: str, metadata: Optional[Dict[str, Any]] = None,
                  context: Optional[ConversationContext] = None) -> IntentResult:
        """
        Perform complete natural language understanding on user input
        
        Args:
            user_input: The user's input message
            metadata: Optional metadata containing file information, session data, etc.
            context: Optional conversation context for context-aware analysis
        
        Returns:
            IntentResult: Complete understanding result with intent, parameters, and confidence
        """
        try:
            logger.debug(f"Processing user input: '{user_input[:100]}...' with context: {context is not None}")
            
            # Step 1: Basic intent classification
            base_intent_result = self.intent_classifier.classify_intent(user_input, context)
            logger.debug(f"Base intent classification: {base_intent_result.intent.value} "
                        f"(confidence: {base_intent_result.confidence:.2f})")
            
            # Step 2: Extract parameters for the classified intent
            extracted_parameters = self.parameter_extractor.extract_parameters(
                user_input, base_intent_result.intent, metadata, context
            )
            
            # Merge extracted parameters with base parameters
            base_intent_result.parameters.update(extracted_parameters)
            
            # Update input type from parameter extraction if more specific
            if 'input_type' in extracted_parameters:
                base_intent_result.input_type = extracted_parameters['input_type']
            
            logger.debug(f"Extracted {len(extracted_parameters)} parameters")
            
            # Step 3: Context-aware analysis and enhancement
            if context:
                enhanced_result = self.context_analyzer.analyze_intent_with_context(
                    base_intent_result, user_input, context
                )
                logger.debug(f"Context-enhanced confidence: {base_intent_result.confidence:.2f} -> "
                           f"{enhanced_result.confidence:.2f}")
            else:
                enhanced_result = base_intent_result
                enhanced_result.reasoning = (enhanced_result.reasoning or "") + "; No context available"
            
            # Step 4: Final validation and cleanup
            final_result = self._validate_and_finalize_result(enhanced_result, user_input, metadata, context)
            
            logger.info(f"NLU complete: {final_result.intent.value} "
                       f"(confidence: {final_result.confidence:.2f}, "
                       f"parameters: {len(final_result.parameters)})")
            
            return final_result
            
        except Exception as e:
            logger.error(f"Error in NLU processing: {e}", exc_info=True)
            
            # Return a fallback result
            return IntentResult(
                intent=ConversationIntent.UNKNOWN,
                confidence=0.0,
                parameters={'original_input': user_input, 'error': str(e)},
                input_type=InputType.TEXT,
                requires_context=False,
                reasoning=f"NLU processing failed: {str(e)}"
            )
    
    def _validate_and_finalize_result(self, result: IntentResult, user_input: str,
                                    metadata: Optional[Dict[str, Any]], 
                                    context: Optional[ConversationContext]) -> IntentResult:
        """
        Validate and finalize the NLU result
        
        Args:
            result: The intent result to validate
            user_input: Original user input
            metadata: Optional metadata
            context: Optional conversation context
        
        Returns:
            IntentResult: Validated and finalized result
        """
        # Ensure minimum required parameters are present
        if 'original_input' not in result.parameters:
            result.parameters['original_input'] = user_input
        
        # Validate intent-specific requirements
        validation_result = self._validate_intent_requirements(result, context)
        if not validation_result['valid']:
            # Adjust intent or confidence based on validation
            if validation_result['suggested_intent']:
                logger.debug(f"Validation suggests changing intent from {result.intent.value} "
                           f"to {validation_result['suggested_intent'].value}")
                result.intent = validation_result['suggested_intent']
                result.confidence = max(0.5, result.confidence - 0.2)
                result.reasoning += f"; Adjusted based on validation: {validation_result['reason']}"
        
        # Ensure confidence is within valid bounds
        result.confidence = max(0.0, min(1.0, result.confidence))
        
        # Add processing metadata
        result.parameters['nlu_metadata'] = {
            'processing_timestamp': self._get_current_timestamp(),
            'has_context': context is not None,
            'has_metadata': metadata is not None,
            'parameter_count': len(result.parameters),
            'validation_passed': validation_result['valid']
        }
        
        return result
    
    def _validate_intent_requirements(self, result: IntentResult, 
                                    context: Optional[ConversationContext]) -> Dict[str, Any]:
        """
        Validate that the intent result meets requirements for the classified intent
        
        Args:
            result: Intent result to validate
            context: Optional conversation context
        
        Returns:
            Dict containing validation results
        """
        validation = {
            'valid': True,
            'reason': '',
            'suggested_intent': None
        }
        
        intent = result.intent
        parameters = result.parameters
        
        # Validate TEXT_TO_ASL requirements
        if intent == ConversationIntent.TEXT_TO_ASL:
            if 'text' not in parameters or not parameters['text']:
                validation['valid'] = False
                validation['reason'] = 'No text content found for translation'
                validation['suggested_intent'] = ConversationIntent.HELP_REQUEST
        
        # Validate AUDIO_TO_ASL requirements
        elif intent == ConversationIntent.AUDIO_TO_ASL:
            has_audio = ('audio_file' in parameters or 
                        'audio_filename' in parameters or
                        result.input_type == InputType.AUDIO)
            if not has_audio:
                validation['valid'] = False
                validation['reason'] = 'No audio input detected for audio translation'
                validation['suggested_intent'] = ConversationIntent.HELP_REQUEST
        
        # Validate ASL_TO_TEXT requirements
        elif intent == ConversationIntent.ASL_TO_TEXT:
            has_video = ('video_file' in parameters or 
                        'video_filename' in parameters or
                        result.input_type in [InputType.VIDEO, InputType.STREAM])
            if not has_video:
                validation['valid'] = False
                validation['reason'] = 'No video input detected for ASL analysis'
                validation['suggested_intent'] = ConversationIntent.HELP_REQUEST
        
        # Validate CONTEXT_REFERENCE requirements
        elif intent == ConversationIntent.CONTEXT_REFERENCE:
            if not context or not context.conversation_history:
                validation['valid'] = False
                validation['reason'] = 'No conversation context available for reference'
                validation['suggested_intent'] = ConversationIntent.HELP_REQUEST
        
        # Validate RETRY_REQUEST requirements
        elif intent == ConversationIntent.RETRY_REQUEST:
            if not context or not context.last_translation:
                validation['valid'] = False
                validation['reason'] = 'No previous translation to retry'
                validation['suggested_intent'] = ConversationIntent.HELP_REQUEST
        
        # Validate STATUS_CHECK requirements
        elif intent == ConversationIntent.STATUS_CHECK:
            if not context or not context.current_operations:
                # Status check without active operations might be valid, but lower confidence
                if result.confidence > 0.7:
                    result.confidence = 0.6
                validation['reason'] = 'No active operations to check status for'
        
        return validation
    
    def get_understanding_summary(self, result: IntentResult) -> Dict[str, Any]:
        """
        Generate a summary of the understanding result for debugging/monitoring
        
        Args:
            result: Intent result to summarize
        
        Returns:
            Dict containing understanding summary
        """
        summary = {
            'intent': result.intent.value,
            'confidence': result.confidence,
            'input_type': result.input_type.value,
            'requires_context': result.requires_context,
            'parameter_count': len(result.parameters),
            'has_alternatives': len(result.alternative_intents) > 0,
            'reasoning': result.reasoning
        }
        
        # Add parameter summary (without sensitive data)
        parameter_summary = {}
        for key, value in result.parameters.items():
            if key in ['original_input', 'text']:
                parameter_summary[key] = f"<{len(str(value))} chars>"
            elif isinstance(value, dict):
                parameter_summary[key] = f"<dict with {len(value)} keys>"
            elif isinstance(value, list):
                parameter_summary[key] = f"<list with {len(value)} items>"
            else:
                parameter_summary[key] = str(value)[:50]
        
        summary['parameters'] = parameter_summary
        
        # Add alternative intents summary
        if result.alternative_intents:
            summary['alternatives'] = [
                {'intent': intent.value, 'confidence': conf}
                for intent, conf in result.alternative_intents[:3]
            ]
        
        return summary
    
    def _get_current_timestamp(self) -> str:
        """Get current timestamp as ISO string"""
        from datetime import datetime
        return datetime.now().isoformat()
    
    def update_confidence_threshold(self, threshold: float) -> None:
        """
        Update the confidence threshold for intent classification
        
        Args:
            threshold: New confidence threshold (0.0 to 1.0)
        """
        if 0.0 <= threshold <= 1.0:
            self.intent_classifier.confidence_threshold = threshold
            logger.info(f"Updated confidence threshold to {threshold}")
        else:
            logger.warning(f"Invalid confidence threshold: {threshold}. Must be between 0.0 and 1.0")
    
    def get_supported_intents(self) -> List[str]:
        """
        Get list of supported conversation intents
        
        Returns:
            List of supported intent names
        """
        return [intent.value for intent in ConversationIntent]
    
    def get_supported_input_types(self) -> List[str]:
        """
        Get list of supported input types
        
        Returns:
            List of supported input type names
        """
        return [input_type.value for input_type in InputType]
    
    def analyze_input_complexity(self, user_input: str) -> Dict[str, Any]:
        """
        Analyze the complexity of user input for processing optimization
        
        Args:
            user_input: User's input message
        
        Returns:
            Dict containing complexity analysis
        """
        analysis = {
            'length': len(user_input),
            'word_count': len(user_input.split()),
            'sentence_count': len([s for s in user_input.split('.') if s.strip()]),
            'has_quotes': '"' in user_input or "'" in user_input,
            'has_questions': '?' in user_input,
            'has_commands': any(cmd in user_input.lower() for cmd in ['translate', 'convert', 'help', 'show']),
            'complexity_score': 0.0
        }
        
        # Calculate complexity score
        score = 0.0
        score += min(1.0, analysis['length'] / 100)  # Length factor
        score += min(1.0, analysis['word_count'] / 20)  # Word count factor
        score += 0.2 if analysis['has_quotes'] else 0.0  # Quoted content
        score += 0.1 if analysis['has_questions'] else 0.0  # Questions
        score += 0.1 if analysis['has_commands'] else 0.0  # Commands
        
        analysis['complexity_score'] = min(1.0, score)
        
        return analysis