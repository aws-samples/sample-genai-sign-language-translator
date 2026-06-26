"""
Context-Aware Intent Analysis Module

This module provides context-aware intent analysis capabilities, including
conversation history analysis, user pattern recognition, and confidence scoring
for intent classification results.
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from collections import Counter, defaultdict

try:
    from .data_models import (
        ConversationIntent, 
        IntentResult, 
        InputType, 
        ConversationContext,
        ConversationInteraction,
        TranslationResult
    )
except ImportError:
    from data_models import (
        ConversationIntent, 
        IntentResult, 
        InputType, 
        ConversationContext,
        ConversationInteraction,
        TranslationResult
    )

logger = logging.getLogger(__name__)

class ContextAwareIntentAnalyzer:
    """
    Context-aware intent analyzer that uses conversation history and user patterns
    to improve intent classification accuracy and provide confidence scoring.
    """
    
    def __init__(self):
        """Initialize the context-aware intent analyzer"""
        self.pattern_weights = {
            'recent_intent_similarity': 0.3,
            'user_preference_alignment': 0.2,
            'session_context_relevance': 0.25,
            'error_recovery_context': 0.15,
            'temporal_patterns': 0.1
        }
        
        self.confidence_adjustments = {
            'strong_context_support': 0.2,
            'moderate_context_support': 0.1,
            'weak_context_support': 0.05,
            'context_contradiction': -0.15,
            'insufficient_context': 0.0
        }
        
        logger.info("ContextAwareIntentAnalyzer initialized")
    
    def analyze_intent_with_context(self, base_intent_result: IntentResult,
                                   user_input: str, context: Optional[ConversationContext] = None) -> IntentResult:
        """
        Enhance intent classification with context-aware analysis
        
        Args:
            base_intent_result: Initial intent classification result
            user_input: The user's input message
            context: Optional conversation context
        
        Returns:
            IntentResult: Enhanced intent result with context-aware adjustments
        """
        try:
            if not context:
                # No context available, return base result
                return base_intent_result
            
            # Analyze conversation history for patterns
            history_analysis = self._analyze_conversation_history(context)
            
            # Analyze user patterns and preferences
            user_patterns = self._analyze_user_patterns(context)
            
            # Calculate context-based confidence adjustments
            context_confidence = self._calculate_context_confidence(
                base_intent_result, user_input, context, history_analysis, user_patterns
            )
            
            # Determine if context suggests alternative intents
            alternative_suggestions = self._suggest_context_alternatives(
                base_intent_result, context, history_analysis, user_patterns
            )
            
            # Create enhanced intent result
            enhanced_result = IntentResult(
                intent=base_intent_result.intent,
                confidence=min(1.0, max(0.0, base_intent_result.confidence + context_confidence)),
                parameters=base_intent_result.parameters.copy(),
                input_type=base_intent_result.input_type,
                requires_context=base_intent_result.requires_context,
                alternative_intents=alternative_suggestions,
                reasoning=self._generate_context_reasoning(
                    base_intent_result, context_confidence, history_analysis, user_patterns
                )
            )
            
            # Add context-derived parameters
            context_params = self._extract_context_parameters(
                base_intent_result.intent, context, history_analysis, user_patterns
            )
            enhanced_result.parameters.update(context_params)
            
            logger.debug(f"Enhanced intent {base_intent_result.intent.value} with context: "
                        f"confidence {base_intent_result.confidence:.2f} -> {enhanced_result.confidence:.2f}")
            
            return enhanced_result
            
        except Exception as e:
            logger.error(f"Error in context-aware intent analysis: {e}", exc_info=True)
            # Return base result if context analysis fails
            base_intent_result.reasoning = f"Context analysis failed: {str(e)}"
            return base_intent_result
    
    def _analyze_conversation_history(self, context: ConversationContext) -> Dict[str, Any]:
        """
        Analyze conversation history for patterns and trends
        
        Args:
            context: Conversation context with history
        
        Returns:
            Dict containing history analysis results
        """
        analysis = {
            'total_interactions': len(context.conversation_history),
            'recent_intents': [],
            'intent_frequency': Counter(),
            'success_rate': 0.0,
            'error_patterns': [],
            'temporal_patterns': {},
            'interaction_flow': []
        }
        
        if not context.conversation_history:
            return analysis
        
        # Analyze recent interactions (last 5)
        recent_interactions = context.get_recent_interactions(5)
        analysis['recent_intents'] = [interaction.intent for interaction in recent_interactions]
        
        # Count intent frequencies
        for interaction in context.conversation_history:
            analysis['intent_frequency'][interaction.intent] += 1
        
        # Calculate success rate
        successful_interactions = sum(1 for interaction in context.conversation_history
                                    if interaction.translation_result and interaction.translation_result.success)
        if context.conversation_history:
            analysis['success_rate'] = successful_interactions / len(context.conversation_history)
        
        # Identify error patterns
        error_interactions = [interaction for interaction in context.conversation_history
                            if interaction.error_occurred or 
                            (interaction.translation_result and not interaction.translation_result.success)]
        
        if error_interactions:
            error_intents = [interaction.intent for interaction in error_interactions]
            analysis['error_patterns'] = list(Counter(error_intents).most_common(3))
        
        # Analyze temporal patterns
        analysis['temporal_patterns'] = self._analyze_temporal_patterns(context.conversation_history)
        
        # Analyze interaction flow
        analysis['interaction_flow'] = self._analyze_interaction_flow(recent_interactions)
        
        return analysis
    
    def _analyze_user_patterns(self, context: ConversationContext) -> Dict[str, Any]:
        """
        Analyze user patterns and preferences from conversation context
        
        Args:
            context: Conversation context
        
        Returns:
            Dict containing user pattern analysis
        """
        patterns = {
            'preferred_intents': [],
            'preferred_input_types': [],
            'usage_frequency': {},
            'time_preferences': {},
            'quality_preferences': {},
            'interaction_style': 'unknown'
        }
        
        if not context.conversation_history:
            return patterns
        
        # Analyze preferred intents
        intent_counts = Counter(interaction.intent for interaction in context.conversation_history)
        patterns['preferred_intents'] = [intent for intent, _ in intent_counts.most_common(3)]
        
        # Analyze preferred input types
        input_type_counts = Counter()
        for interaction in context.conversation_history:
            if interaction.translation_result:
                input_type_counts[interaction.translation_result.input_type] += 1
        patterns['preferred_input_types'] = [input_type for input_type, _ in input_type_counts.most_common(3)]
        
        # Analyze usage frequency patterns
        patterns['usage_frequency'] = self._calculate_usage_frequency(context)
        
        # Analyze time preferences
        patterns['time_preferences'] = self._analyze_time_preferences(context.conversation_history)
        
        # Extract quality preferences from user preferences
        if context.user_preferences:
            patterns['quality_preferences'] = {
                key: value for key, value in context.user_preferences.items()
                if 'quality' in key.lower() or 'format' in key.lower()
            }
        
        # Determine interaction style
        patterns['interaction_style'] = self._determine_interaction_style(context.conversation_history)
        
        return patterns
    
    def _calculate_context_confidence(self, base_result: IntentResult, user_input: str,
                                    context: ConversationContext, history_analysis: Dict[str, Any],
                                    user_patterns: Dict[str, Any]) -> float:
        """
        Calculate confidence adjustment based on context analysis
        
        Args:
            base_result: Base intent classification result
            user_input: User's input message
            context: Conversation context
            history_analysis: Results from history analysis
            user_patterns: Results from user pattern analysis
        
        Returns:
            float: Confidence adjustment value (-1.0 to 1.0)
        """
        total_adjustment = 0.0
        
        # Recent intent similarity boost
        recent_intent_boost = self._calculate_recent_intent_boost(
            base_result.intent, history_analysis['recent_intents']
        )
        total_adjustment += recent_intent_boost * self.pattern_weights['recent_intent_similarity']
        
        # User preference alignment boost
        preference_boost = self._calculate_preference_alignment_boost(
            base_result.intent, user_patterns['preferred_intents']
        )
        total_adjustment += preference_boost * self.pattern_weights['user_preference_alignment']
        
        # Session context relevance
        context_relevance = self._calculate_session_context_relevance(
            base_result, context, history_analysis
        )
        total_adjustment += context_relevance * self.pattern_weights['session_context_relevance']
        
        # Error recovery context
        error_recovery_boost = self._calculate_error_recovery_boost(
            base_result.intent, history_analysis['error_patterns'], context
        )
        total_adjustment += error_recovery_boost * self.pattern_weights['error_recovery_context']
        
        # Temporal pattern alignment
        temporal_boost = self._calculate_temporal_pattern_boost(
            base_result.intent, history_analysis['temporal_patterns']
        )
        total_adjustment += temporal_boost * self.pattern_weights['temporal_patterns']
        
        # Clamp the adjustment to reasonable bounds
        return max(-0.3, min(0.3, total_adjustment))
    
    def _suggest_context_alternatives(self, base_result: IntentResult, context: ConversationContext,
                                    history_analysis: Dict[str, Any], user_patterns: Dict[str, Any]) -> List[Tuple[ConversationIntent, float]]:
        """
        Suggest alternative intents based on context analysis
        
        Args:
            base_result: Base intent classification result
            context: Conversation context
            history_analysis: Results from history analysis
            user_patterns: Results from user pattern analysis
        
        Returns:
            List of (intent, confidence) tuples for alternative suggestions
        """
        alternatives = []
        
        # Start with base alternatives
        alternatives.extend(base_result.alternative_intents)
        
        # Add context-suggested alternatives
        
        # If user frequently uses certain intents, suggest them
        for preferred_intent in user_patterns['preferred_intents'][:2]:
            if preferred_intent != base_result.intent:
                # Calculate confidence based on usage frequency
                intent_frequency = history_analysis['intent_frequency'].get(preferred_intent, 0)
                total_interactions = history_analysis['total_interactions']
                if total_interactions > 0:
                    frequency_confidence = min(0.8, intent_frequency / total_interactions)
                    alternatives.append((preferred_intent, frequency_confidence))
        
        # If recent interactions suggest a pattern, add related intents
        recent_intents = history_analysis['recent_intents']
        if len(recent_intents) >= 2:
            # Look for intent sequences
            if recent_intents[-1] == ConversationIntent.TEXT_TO_ASL and base_result.intent != ConversationIntent.RETRY_REQUEST:
                alternatives.append((ConversationIntent.RETRY_REQUEST, 0.6))
            elif recent_intents[-1] == ConversationIntent.HELP_REQUEST and base_result.intent != ConversationIntent.TEXT_TO_ASL:
                alternatives.append((ConversationIntent.TEXT_TO_ASL, 0.7))
        
        # If there were recent errors, suggest help or retry
        if history_analysis['error_patterns'] and base_result.intent not in [ConversationIntent.HELP_REQUEST, ConversationIntent.RETRY_REQUEST]:
            alternatives.append((ConversationIntent.HELP_REQUEST, 0.5))
            alternatives.append((ConversationIntent.RETRY_REQUEST, 0.6))
        
        # Remove duplicates and sort by confidence
        seen_intents = set()
        unique_alternatives = []
        for intent, confidence in alternatives:
            if intent not in seen_intents:
                seen_intents.add(intent)
                unique_alternatives.append((intent, confidence))
        
        # Sort by confidence and return top alternatives
        unique_alternatives.sort(key=lambda x: x[1], reverse=True)
        return unique_alternatives[:5]  # Return top 5 alternatives
    
    def _generate_context_reasoning(self, base_result: IntentResult, context_confidence: float,
                                  history_analysis: Dict[str, Any], user_patterns: Dict[str, Any]) -> str:
        """Generate reasoning explanation for context-aware classification"""
        reasoning_parts = [base_result.reasoning or "Base classification"]
        
        if context_confidence > 0.1:
            reasoning_parts.append(f"Context analysis increased confidence by {context_confidence:.2f}")
        elif context_confidence < -0.1:
            reasoning_parts.append(f"Context analysis decreased confidence by {abs(context_confidence):.2f}")
        
        # Add specific context insights
        if history_analysis['recent_intents']:
            recent_intent_str = ", ".join([intent.value for intent in history_analysis['recent_intents'][-3:]])
            reasoning_parts.append(f"Recent intents: {recent_intent_str}")
        
        if user_patterns['preferred_intents']:
            preferred_str = ", ".join([intent.value for intent in user_patterns['preferred_intents'][:2]])
            reasoning_parts.append(f"User preferences: {preferred_str}")
        
        if history_analysis['success_rate'] < 0.5:
            reasoning_parts.append("Low success rate suggests user may need help")
        
        return "; ".join(reasoning_parts)
    
    def _extract_context_parameters(self, intent: ConversationIntent, context: ConversationContext,
                                  history_analysis: Dict[str, Any], user_patterns: Dict[str, Any]) -> Dict[str, Any]:
        """Extract additional parameters from context analysis"""
        context_params = {}
        
        # Add user preference parameters
        if context.user_preferences:
            context_params['user_preferences'] = context.user_preferences
        
        # Add session context
        context_params['session_context'] = {
            'total_interactions': history_analysis['total_interactions'],
            'success_rate': history_analysis['success_rate'],
            'session_duration': context.get_session_duration(),
            'interaction_style': user_patterns['interaction_style']
        }
        
        # Add relevant previous results for context-dependent intents
        if intent in [ConversationIntent.RETRY_REQUEST, ConversationIntent.CONTEXT_REFERENCE]:
            if context.last_translation:
                context_params['last_translation'] = context.last_translation.to_dict()
        
        # Add error context if relevant
        if history_analysis['error_patterns']:
            context_params['recent_errors'] = history_analysis['error_patterns']
        
        return context_params
    
    def _analyze_temporal_patterns(self, interactions: List[ConversationInteraction]) -> Dict[str, Any]:
        """Analyze temporal patterns in user interactions"""
        patterns = {
            'interaction_intervals': [],
            'peak_usage_times': [],
            'session_lengths': []
        }
        
        if len(interactions) < 2:
            return patterns
        
        # Calculate intervals between interactions
        for i in range(1, len(interactions)):
            interval = (interactions[i].timestamp - interactions[i-1].timestamp).total_seconds()
            patterns['interaction_intervals'].append(interval)
        
        # Analyze usage times (hour of day)
        usage_hours = [interaction.timestamp.hour for interaction in interactions]
        hour_counts = Counter(usage_hours)
        patterns['peak_usage_times'] = [hour for hour, _ in hour_counts.most_common(3)]
        
        return patterns
    
    def _analyze_interaction_flow(self, recent_interactions: List[ConversationInteraction]) -> List[str]:
        """Analyze the flow of recent interactions"""
        if not recent_interactions:
            return []
        
        flow = []
        for interaction in recent_interactions:
            flow_item = f"{interaction.intent.value}"
            if interaction.translation_result:
                if interaction.translation_result.success:
                    flow_item += "_success"
                else:
                    flow_item += "_failed"
            flow.append(flow_item)
        
        return flow
    
    def _calculate_usage_frequency(self, context: ConversationContext) -> Dict[str, float]:
        """Calculate usage frequency patterns"""
        frequency = {}
        
        if not context.conversation_history:
            return frequency
        
        # Calculate interactions per day
        session_duration_days = context.get_session_duration() / (24 * 3600)
        if session_duration_days > 0:
            frequency['interactions_per_day'] = len(context.conversation_history) / session_duration_days
        
        # Calculate average time between interactions
        if len(context.conversation_history) > 1:
            total_time = (context.last_activity_time - context.session_start_time).total_seconds()
            frequency['avg_interval_seconds'] = total_time / (len(context.conversation_history) - 1)
        
        return frequency
    
    def _analyze_time_preferences(self, interactions: List[ConversationInteraction]) -> Dict[str, Any]:
        """Analyze user's time-based preferences"""
        preferences = {}
        
        if not interactions:
            return preferences
        
        # Analyze preferred hours
        hours = [interaction.timestamp.hour for interaction in interactions]
        hour_counts = Counter(hours)
        preferences['preferred_hours'] = [hour for hour, _ in hour_counts.most_common(3)]
        
        # Analyze preferred days of week
        days = [interaction.timestamp.weekday() for interaction in interactions]
        day_counts = Counter(days)
        preferences['preferred_days'] = [day for day, _ in day_counts.most_common(3)]
        
        return preferences
    
    def _determine_interaction_style(self, interactions: List[ConversationInteraction]) -> str:
        """Determine user's interaction style"""
        if not interactions:
            return 'unknown'
        
        # Analyze input lengths
        input_lengths = [len(interaction.user_input) for interaction in interactions]
        avg_length = sum(input_lengths) / len(input_lengths)
        
        # Analyze interaction frequency
        if len(interactions) > 10:
            style = 'frequent_user'
        elif len(interactions) > 5:
            style = 'regular_user'
        else:
            style = 'occasional_user'
        
        # Modify based on input style
        if avg_length > 100:
            style += '_verbose'
        elif avg_length < 20:
            style += '_concise'
        
        return style
    
    def _calculate_recent_intent_boost(self, current_intent: ConversationIntent,
                                     recent_intents: List[ConversationIntent]) -> float:
        """Calculate confidence boost based on recent intent similarity"""
        if not recent_intents:
            return 0.0
        
        # Count occurrences of current intent in recent history
        recent_count = recent_intents.count(current_intent)
        
        # Boost confidence if intent appears frequently in recent history
        if recent_count >= 2:
            return 0.2
        elif recent_count == 1:
            return 0.1
        
        return 0.0
    
    def _calculate_preference_alignment_boost(self, current_intent: ConversationIntent,
                                           preferred_intents: List[ConversationIntent]) -> float:
        """Calculate confidence boost based on user preference alignment"""
        if not preferred_intents:
            return 0.0
        
        if current_intent in preferred_intents[:2]:  # Top 2 preferences
            position = preferred_intents.index(current_intent)
            return 0.15 - (position * 0.05)  # Higher boost for more preferred intents
        
        return 0.0
    
    def _calculate_session_context_relevance(self, base_result: IntentResult,
                                           context: ConversationContext,
                                           history_analysis: Dict[str, Any]) -> float:
        """Calculate relevance boost based on session context"""
        relevance = 0.0
        
        # Boost help requests if success rate is low
        if (base_result.intent == ConversationIntent.HELP_REQUEST and 
            history_analysis['success_rate'] < 0.5):
            relevance += 0.15
        
        # Boost retry requests if there were recent failures
        if (base_result.intent == ConversationIntent.RETRY_REQUEST and
            context.last_translation and not context.last_translation.success):
            relevance += 0.2
        
        # Boost context references if there are recent successful translations
        if (base_result.intent == ConversationIntent.CONTEXT_REFERENCE and
            context.last_translation and context.last_translation.success):
            relevance += 0.1
        
        return relevance
    
    def _calculate_error_recovery_boost(self, current_intent: ConversationIntent,
                                      error_patterns: List[Tuple[ConversationIntent, int]],
                                      context: ConversationContext) -> float:
        """Calculate boost for error recovery scenarios"""
        if not error_patterns:
            return 0.0
        
        # Boost help requests if user has been experiencing errors
        if current_intent == ConversationIntent.HELP_REQUEST:
            total_errors = sum(count for _, count in error_patterns)
            if total_errors > 2:
                return 0.1
        
        # Boost retry requests if the last interaction failed
        if (current_intent == ConversationIntent.RETRY_REQUEST and
            context.conversation_history and
            context.conversation_history[-1].error_occurred):
            return 0.15
        
        return 0.0
    
    def _calculate_temporal_pattern_boost(self, current_intent: ConversationIntent,
                                        temporal_patterns: Dict[str, Any]) -> float:
        """Calculate boost based on temporal usage patterns"""
        # This could be enhanced with more sophisticated temporal analysis
        # For now, provide a small boost for consistency
        if temporal_patterns.get('interaction_intervals'):
            # If user has consistent interaction patterns, slightly boost confidence
            intervals = temporal_patterns['interaction_intervals']
            if len(intervals) > 3:
                # Calculate consistency (lower variance = more consistent)
                avg_interval = sum(intervals) / len(intervals)
                variance = sum((x - avg_interval) ** 2 for x in intervals) / len(intervals)
                if variance < avg_interval * 0.5:  # Relatively consistent
                    return 0.05
        
        return 0.0