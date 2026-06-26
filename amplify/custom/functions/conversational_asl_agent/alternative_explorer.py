"""
Alternative Explorer

This module provides alternative translation method suggestions, parameter exploration
for different video formats and approaches, and comparative result presentation.
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
from enum import Enum
from dataclasses import dataclass, field
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

logger = logging.getLogger(__name__)

class AlternativeType(Enum):
    """Types of alternatives that can be explored"""
    INPUT_METHOD = "input_method"           # Different input methods (text vs audio vs video)
    OUTPUT_FORMAT = "output_format"         # Different output formats (pose, sign, avatar)
    PROCESSING_APPROACH = "processing_approach"  # Different processing approaches
    PARAMETER_VARIATION = "parameter_variation"  # Different parameter combinations
    TOOL_SELECTION = "tool_selection"       # Different tool selections
    QUALITY_TRADEOFF = "quality_tradeoff"   # Quality vs speed tradeoffs

class AlternativeCategory(Enum):
    """Categories for organizing alternatives"""
    FASTER = "faster"                       # Faster alternatives
    HIGHER_QUALITY = "higher_quality"       # Higher quality alternatives
    MORE_RELIABLE = "more_reliable"         # More reliable alternatives
    DIFFERENT_FORMAT = "different_format"   # Different format alternatives
    SIMPLER = "simpler"                     # Simpler alternatives
    MORE_DETAILED = "more_detailed"         # More detailed alternatives

@dataclass
class AlternativeOption:
    """Data class representing an alternative translation option"""
    option_id: str
    alternative_type: AlternativeType
    category: AlternativeCategory
    title: str
    description: str
    parameters: Dict[str, Any]
    intent: ConversationIntent
    estimated_time: float = 0.0
    estimated_quality: str = "medium"  # low, medium, high
    reliability_score: float = 0.8     # 0.0 to 1.0
    pros: List[str] = field(default_factory=list)
    cons: List[str] = field(default_factory=list)
    use_cases: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'option_id': self.option_id,
            'alternative_type': self.alternative_type.value,
            'category': self.category.value,
            'title': self.title,
            'description': self.description,
            'parameters': self.parameters,
            'intent': self.intent.value,
            'estimated_time': self.estimated_time,
            'estimated_quality': self.estimated_quality,
            'reliability_score': self.reliability_score,
            'pros': self.pros,
            'cons': self.cons,
            'use_cases': self.use_cases
        }

@dataclass
class AlternativeComparison:
    """Data class for comparing multiple alternatives"""
    original_request: Dict[str, Any]
    alternatives: List[AlternativeOption]
    recommendations: List[str] = field(default_factory=list)
    comparison_criteria: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)
    
    def get_by_category(self, category: AlternativeCategory) -> List[AlternativeOption]:
        """Get alternatives by category"""
        return [alt for alt in self.alternatives if alt.category == category]
    
    def get_fastest(self) -> Optional[AlternativeOption]:
        """Get the fastest alternative"""
        if not self.alternatives:
            return None
        return min(self.alternatives, key=lambda x: x.estimated_time)
    
    def get_highest_quality(self) -> Optional[AlternativeOption]:
        """Get the highest quality alternative"""
        quality_order = {'low': 1, 'medium': 2, 'high': 3}
        if not self.alternatives:
            return None
        return max(self.alternatives, key=lambda x: quality_order.get(x.estimated_quality, 2))
    
    def get_most_reliable(self) -> Optional[AlternativeOption]:
        """Get the most reliable alternative"""
        if not self.alternatives:
            return None
        return max(self.alternatives, key=lambda x: x.reliability_score)

class AlternativeExplorer:
    """
    Explores and suggests alternative translation methods and parameters
    
    This class provides alternative translation method suggestions, implements
    parameter exploration for different video formats and approaches, and creates
    comparative result presentation for multiple translation approaches.
    """
    
    def __init__(self, memory_manager: Optional[ConversationMemoryManager] = None):
        """Initialize the alternative explorer"""
        self.memory_manager = memory_manager or ConversationMemoryManager()
        
        # Alternative option templates
        self.alternative_templates = self._initialize_alternative_templates()
        
        logger.info("AlternativeExplorer initialized with comprehensive alternatives")
    
    def explore_alternatives(self, original_intent: ConversationIntent,
                           original_parameters: Dict[str, Any],
                           context: ConversationContext,
                           failure_reason: Optional[str] = None) -> AlternativeComparison:
        """
        Explore alternative approaches for a translation request
        
        Args:
            original_intent: Original conversation intent
            original_parameters: Original parameters that failed or need alternatives
            context: Current conversation context
            failure_reason: Optional reason for failure to guide alternatives
        
        Returns:
            AlternativeComparison: Comprehensive comparison of alternatives
        """
        alternatives = []
        
        # Generate alternatives based on original intent
        if original_intent == ConversationIntent.TEXT_TO_ASL:
            alternatives.extend(self._generate_text_to_asl_alternatives(original_parameters, failure_reason))
        elif original_intent == ConversationIntent.AUDIO_TO_ASL:
            alternatives.extend(self._generate_audio_to_asl_alternatives(original_parameters, failure_reason))
        elif original_intent == ConversationIntent.ASL_TO_TEXT:
            alternatives.extend(self._generate_asl_to_text_alternatives(original_parameters, failure_reason))
        
        # Add cross-modal alternatives
        alternatives.extend(self._generate_cross_modal_alternatives(original_intent, original_parameters))
        
        # Add parameter variation alternatives
        alternatives.extend(self._generate_parameter_variations(original_intent, original_parameters))
        
        # Generate recommendations
        recommendations = self._generate_recommendations(alternatives, context, failure_reason)
        
        # Define comparison criteria
        criteria = self._get_comparison_criteria(original_intent, failure_reason)
        
        return AlternativeComparison(
            original_request={'intent': original_intent.value, 'parameters': original_parameters},
            alternatives=alternatives,
            recommendations=recommendations,
            comparison_criteria=criteria
        )
    
    def suggest_parameter_variations(self, intent: ConversationIntent,
                                   base_parameters: Dict[str, Any]) -> List[AlternativeOption]:
        """
        Suggest parameter variations for the same translation approach
        
        Args:
            intent: Conversation intent
            base_parameters: Base parameters to vary
        
        Returns:
            List[AlternativeOption]: List of parameter variations
        """
        variations = []
        
        if intent == ConversationIntent.TEXT_TO_ASL:
            # Text processing variations
            text = base_parameters.get('text', '')
            
            # Simplified text version
            if len(text.split()) > 5:
                simplified_text = ' '.join(text.split()[:5])
                variations.append(AlternativeOption(
                    option_id="text_simplified",
                    alternative_type=AlternativeType.PARAMETER_VARIATION,
                    category=AlternativeCategory.SIMPLER,
                    title="Simplified Text",
                    description="Use shorter, simpler text for better translation accuracy",
                    parameters={**base_parameters, 'text': simplified_text},
                    intent=intent,
                    estimated_time=3.0,
                    estimated_quality="medium",
                    reliability_score=0.9,
                    pros=["More reliable", "Faster processing", "Better accuracy"],
                    cons=["Less complete message"],
                    use_cases=["When full text fails", "For testing purposes"]
                ))
            
            # Pose-only variation
            variations.append(AlternativeOption(
                option_id="pose_only",
                alternative_type=AlternativeType.OUTPUT_FORMAT,
                category=AlternativeCategory.FASTER,
                title="Pose-Only Video",
                description="Generate only pose video (faster, more reliable)",
                parameters={**base_parameters, 'pose_only': True},
                intent=intent,
                estimated_time=2.0,
                estimated_quality="medium",
                reliability_score=0.95,
                pros=["Very fast", "Highly reliable", "Good for basic communication"],
                cons=["Less expressive", "No facial expressions"],
                use_cases=["Quick translations", "When full video fails"]
            ))
            
            # High quality variation
            variations.append(AlternativeOption(
                option_id="high_quality",
                alternative_type=AlternativeType.QUALITY_TRADEOFF,
                category=AlternativeCategory.HIGHER_QUALITY,
                title="High Quality Video",
                description="Generate with enhanced quality settings",
                parameters={**base_parameters, 'quality': 'high', 'enhance_video': True},
                intent=intent,
                estimated_time=8.0,
                estimated_quality="high",
                reliability_score=0.85,
                pros=["Best visual quality", "More detailed signing", "Professional appearance"],
                cons=["Slower processing", "Higher resource usage"],
                use_cases=["Important presentations", "Educational content"]
            ))
        
        elif intent == ConversationIntent.AUDIO_TO_ASL:
            # Audio processing variations
            variations.append(AlternativeOption(
                option_id="enhanced_audio",
                alternative_type=AlternativeType.PROCESSING_APPROACH,
                category=AlternativeCategory.HIGHER_QUALITY,
                title="Enhanced Audio Processing",
                description="Use advanced audio processing for better transcription",
                parameters={**base_parameters, 'enhance_audio': True, 'noise_reduction': True},
                intent=intent,
                estimated_time=12.0,
                estimated_quality="high",
                reliability_score=0.8,
                pros=["Better transcription accuracy", "Handles noisy audio"],
                cons=["Slower processing"],
                use_cases=["Poor quality audio", "Background noise"]
            ))
            
            # Fast transcription variation
            variations.append(AlternativeOption(
                option_id="fast_transcription",
                alternative_type=AlternativeType.PROCESSING_APPROACH,
                category=AlternativeCategory.FASTER,
                title="Fast Transcription",
                description="Use faster transcription model with basic processing",
                parameters={**base_parameters, 'fast_mode': True},
                intent=intent,
                estimated_time=6.0,
                estimated_quality="medium",
                reliability_score=0.85,
                pros=["Much faster", "Good for clear audio"],
                cons=["Less accurate with unclear speech"],
                use_cases=["Clear audio", "Quick results needed"]
            ))
        
        elif intent == ConversationIntent.ASL_TO_TEXT:
            # ASL analysis variations
            variations.append(AlternativeOption(
                option_id="high_sensitivity",
                alternative_type=AlternativeType.PARAMETER_VARIATION,
                category=AlternativeCategory.HIGHER_QUALITY,
                title="High Sensitivity Analysis",
                description="Use high sensitivity for subtle sign detection",
                parameters={**base_parameters, 'sensitivity': 'high', 'frame_rate': 'high'},
                intent=intent,
                estimated_time=15.0,
                estimated_quality="high",
                reliability_score=0.75,
                pros=["Catches subtle signs", "More detailed analysis"],
                cons=["Slower processing", "May over-interpret"],
                use_cases=["Complex signing", "Subtle expressions"]
            ))
            
            # Fast analysis variation
            variations.append(AlternativeOption(
                option_id="fast_analysis",
                alternative_type=AlternativeType.PROCESSING_APPROACH,
                category=AlternativeCategory.FASTER,
                title="Fast Analysis",
                description="Quick analysis for basic sign recognition",
                parameters={**base_parameters, 'fast_mode': True, 'basic_signs_only': True},
                intent=intent,
                estimated_time=5.0,
                estimated_quality="medium",
                reliability_score=0.9,
                pros=["Very fast", "Good for basic signs"],
                cons=["May miss complex signs"],
                use_cases=["Simple signing", "Quick feedback"]
            ))
        
        return variations
    
    def compare_alternatives(self, alternatives: List[AlternativeOption],
                           criteria: List[str] = None) -> Dict[str, Any]:
        """
        Create a detailed comparison of alternatives
        
        Args:
            alternatives: List of alternatives to compare
            criteria: Optional specific criteria to focus on
        
        Returns:
            Dict[str, Any]: Detailed comparison results
        """
        if not alternatives:
            return {'error': 'No alternatives to compare'}
        
        comparison = {
            'total_alternatives': len(alternatives),
            'categories': {},
            'fastest': None,
            'highest_quality': None,
            'most_reliable': None,
            'recommendations': [],
            'comparison_table': []
        }
        
        # Group by category
        for alt in alternatives:
            category = alt.category.value
            if category not in comparison['categories']:
                comparison['categories'][category] = []
            comparison['categories'][category].append(alt.to_dict())
        
        # Find best options
        if alternatives:
            comparison['fastest'] = min(alternatives, key=lambda x: x.estimated_time).to_dict()
            
            quality_order = {'low': 1, 'medium': 2, 'high': 3}
            comparison['highest_quality'] = max(
                alternatives, 
                key=lambda x: quality_order.get(x.estimated_quality, 2)
            ).to_dict()
            
            comparison['most_reliable'] = max(alternatives, key=lambda x: x.reliability_score).to_dict()
        
        # Create comparison table
        for alt in alternatives:
            comparison['comparison_table'].append({
                'title': alt.title,
                'time': f"{alt.estimated_time:.1f}s",
                'quality': alt.estimated_quality,
                'reliability': f"{alt.reliability_score:.1%}",
                'category': alt.category.value,
                'pros': alt.pros[:2],  # Limit to top 2 pros
                'best_for': alt.use_cases[0] if alt.use_cases else "General use"
            })
        
        # Generate recommendations
        comparison['recommendations'] = self._generate_comparison_recommendations(alternatives)
        
        return comparison
    
    def format_alternatives_for_user(self, comparison: AlternativeComparison) -> str:
        """
        Format alternatives comparison for user presentation
        
        Args:
            comparison: Alternative comparison to format
        
        Returns:
            str: User-friendly formatted comparison
        """
        if not comparison.alternatives:
            return "I don't have any alternative approaches to suggest right now."
        
        response_parts = []
        
        # Introduction
        response_parts.append(f"I found {len(comparison.alternatives)} alternative approaches you could try:")
        
        # Group alternatives by category for better presentation
        categories = {}
        for alt in comparison.alternatives:
            category = alt.category.value.replace('_', ' ').title()
            if category not in categories:
                categories[category] = []
            categories[category].append(alt)
        
        # Present each category
        for category, alts in categories.items():
            response_parts.append(f"\n**{category} Options:**")
            for i, alt in enumerate(alts[:2], 1):  # Limit to 2 per category
                response_parts.append(f"{i}. **{alt.title}**")
                response_parts.append(f"   {alt.description}")
                response_parts.append(f"   ⏱️ ~{alt.estimated_time:.1f}s | 🎯 {alt.estimated_quality} quality | 📊 {alt.reliability_score:.0%} reliable")
                if alt.pros:
                    response_parts.append(f"   ✅ {alt.pros[0]}")
        
        # Add recommendations
        if comparison.recommendations:
            response_parts.append(f"\n**My Recommendations:**")
            for i, rec in enumerate(comparison.recommendations[:3], 1):
                response_parts.append(f"{i}. {rec}")
        
        # Add quick selection guide
        fastest = comparison.get_fastest()
        highest_quality = comparison.get_highest_quality()
        most_reliable = comparison.get_most_reliable()
        
        response_parts.append(f"\n**Quick Selection Guide:**")
        if fastest:
            response_parts.append(f"• **Fastest**: {fastest.title} (~{fastest.estimated_time:.1f}s)")
        if highest_quality:
            response_parts.append(f"• **Best Quality**: {highest_quality.title}")
        if most_reliable:
            response_parts.append(f"• **Most Reliable**: {most_reliable.title} ({most_reliable.reliability_score:.0%})")
        
        response_parts.append(f"\nWhich approach would you like to try? You can say something like 'try the fastest option' or 'use high quality'.")
        
        return "\n".join(response_parts)    def 
_initialize_alternative_templates(self) -> Dict[str, List[Dict[str, Any]]]:
        """Initialize templates for common alternative options"""
        return {
            'text_to_asl': [
                {
                    'type': AlternativeType.OUTPUT_FORMAT,
                    'category': AlternativeCategory.FASTER,
                    'title': 'Pose-Only Video',
                    'description': 'Generate skeletal pose video only (faster)',
                    'params': {'pose_only': True},
                    'time': 2.0,
                    'quality': 'medium',
                    'reliability': 0.95
                },
                {
                    'type': AlternativeType.OUTPUT_FORMAT,
                    'category': AlternativeCategory.HIGHER_QUALITY,
                    'title': 'Full Avatar Video',
                    'description': 'Generate complete avatar with facial expressions',
                    'params': {'include_avatar': True, 'facial_expressions': True},
                    'time': 10.0,
                    'quality': 'high',
                    'reliability': 0.8
                }
            ],
            'audio_to_asl': [
                {
                    'type': AlternativeType.INPUT_METHOD,
                    'category': AlternativeCategory.MORE_RELIABLE,
                    'title': 'Manual Text Input',
                    'description': 'Type the text instead of using audio',
                    'params': {'input_method': 'text'},
                    'time': 3.0,
                    'quality': 'high',
                    'reliability': 0.95
                }
            ],
            'asl_to_text': [
                {
                    'type': AlternativeType.PROCESSING_APPROACH,
                    'category': AlternativeCategory.FASTER,
                    'title': 'Basic Sign Recognition',
                    'description': 'Focus on common signs for faster processing',
                    'params': {'basic_signs_only': True},
                    'time': 5.0,
                    'quality': 'medium',
                    'reliability': 0.9
                }
            ]
        }
    
    def _generate_text_to_asl_alternatives(self, parameters: Dict[str, Any], 
                                         failure_reason: Optional[str]) -> List[AlternativeOption]:
        """Generate alternatives for text-to-ASL translation"""
        alternatives = []
        text = parameters.get('text', '')
        
        # Pose-only alternative (faster, more reliable)
        alternatives.append(AlternativeOption(
            option_id="text_pose_only",
            alternative_type=AlternativeType.OUTPUT_FORMAT,
            category=AlternativeCategory.FASTER,
            title="Pose-Only Video",
            description="Generate skeletal pose video without avatar (faster and more reliable)",
            parameters={**parameters, 'pose_only': True, 'pre_sign': False},
            intent=ConversationIntent.TEXT_TO_ASL,
            estimated_time=2.0,
            estimated_quality="medium",
            reliability_score=0.95,
            pros=["Very fast", "Highly reliable", "Good for basic communication"],
            cons=["Less expressive", "No facial expressions"],
            use_cases=["Quick translations", "When full video fails", "Basic communication"]
        ))
        
        # Simplified text alternative
        if len(text.split()) > 5:
            simplified = ' '.join(text.split()[:5])
            alternatives.append(AlternativeOption(
                option_id="text_simplified",
                alternative_type=AlternativeType.PARAMETER_VARIATION,
                category=AlternativeCategory.SIMPLER,
                title="Simplified Text",
                description=f"Translate shorter version: '{simplified}'",
                parameters={**parameters, 'text': simplified},
                intent=ConversationIntent.TEXT_TO_ASL,
                estimated_time=3.0,
                estimated_quality="medium",
                reliability_score=0.9,
                pros=["More reliable", "Better accuracy", "Easier to understand"],
                cons=["Incomplete message"],
                use_cases=["When full text fails", "Testing translation", "Key points only"]
            ))
        
        # Sentence-by-sentence alternative
        sentences = [s.strip() for s in text.split('.') if s.strip()]
        if len(sentences) > 1:
            first_sentence = sentences[0]
            alternatives.append(AlternativeOption(
                option_id="text_sentence_by_sentence",
                alternative_type=AlternativeType.PROCESSING_APPROACH,
                category=AlternativeCategory.MORE_RELIABLE,
                title="Sentence-by-Sentence",
                description=f"Start with first sentence: '{first_sentence}'",
                parameters={**parameters, 'text': first_sentence},
                intent=ConversationIntent.TEXT_TO_ASL,
                estimated_time=4.0,
                estimated_quality="high",
                reliability_score=0.85,
                pros=["Better accuracy per sentence", "Easier to follow", "Can build up gradually"],
                cons=["Need multiple requests for full text"],
                use_cases=["Complex text", "Educational purposes", "Step-by-step learning"]
            ))
        
        return alternatives
    
    def _generate_audio_to_asl_alternatives(self, parameters: Dict[str, Any],
                                          failure_reason: Optional[str]) -> List[AlternativeOption]:
        """Generate alternatives for audio-to-ASL translation"""
        alternatives = []
        
        # Manual text input alternative
        alternatives.append(AlternativeOption(
            option_id="audio_to_text_manual",
            alternative_type=AlternativeType.INPUT_METHOD,
            category=AlternativeCategory.MORE_RELIABLE,
            title="Manual Text Input",
            description="Type what you wanted to say instead of using audio",
            parameters={'text': '[Please type what you wanted to say]'},
            intent=ConversationIntent.TEXT_TO_ASL,
            estimated_time=3.0,
            estimated_quality="high",
            reliability_score=0.95,
            pros=["No transcription errors", "Full control", "Very reliable"],
            cons=["Requires typing", "No audio convenience"],
            use_cases=["Audio quality issues", "Transcription failures", "Precise control"]
        ))
        
        # Enhanced audio processing
        alternatives.append(AlternativeOption(
            option_id="audio_enhanced",
            alternative_type=AlternativeType.PROCESSING_APPROACH,
            category=AlternativeCategory.HIGHER_QUALITY,
            title="Enhanced Audio Processing",
            description="Use advanced audio processing with noise reduction",
            parameters={**parameters, 'enhance_audio': True, 'noise_reduction': True},
            intent=ConversationIntent.AUDIO_TO_ASL,
            estimated_time=12.0,
            estimated_quality="high",
            reliability_score=0.8,
            pros=["Better transcription", "Handles background noise", "More accurate"],
            cons=["Slower processing", "Higher resource usage"],
            use_cases=["Noisy audio", "Poor quality recordings", "Accented speech"]
        ))
        
        # Different audio format suggestion
        alternatives.append(AlternativeOption(
            option_id="audio_format_change",
            alternative_type=AlternativeType.PARAMETER_VARIATION,
            category=AlternativeCategory.MORE_RELIABLE,
            title="Different Audio Format",
            description="Try converting audio to WAV or MP3 format",
            parameters={**parameters, 'preferred_format': 'wav'},
            intent=ConversationIntent.AUDIO_TO_ASL,
            estimated_time=8.0,
            estimated_quality="medium",
            reliability_score=0.85,
            pros=["Better compatibility", "Cleaner processing", "Standard format"],
            cons=["Requires file conversion", "Extra step"],
            use_cases=["Unsupported formats", "Processing errors", "Compatibility issues"]
        ))
        
        return alternatives
    
    def _generate_asl_to_text_alternatives(self, parameters: Dict[str, Any],
                                         failure_reason: Optional[str]) -> List[AlternativeOption]:
        """Generate alternatives for ASL-to-text translation"""
        alternatives = []
        
        # High sensitivity analysis
        alternatives.append(AlternativeOption(
            option_id="asl_high_sensitivity",
            alternative_type=AlternativeType.PARAMETER_VARIATION,
            category=AlternativeCategory.HIGHER_QUALITY,
            title="High Sensitivity Analysis",
            description="Use maximum sensitivity to catch subtle signs",
            parameters={**parameters, 'sensitivity': 'high', 'frame_rate': 'high'},
            intent=ConversationIntent.ASL_TO_TEXT,
            estimated_time=15.0,
            estimated_quality="high",
            reliability_score=0.75,
            pros=["Catches subtle movements", "More detailed analysis", "Better for complex signing"],
            cons=["Slower processing", "May over-interpret", "Higher resource usage"],
            use_cases=["Complex signing", "Subtle expressions", "Professional interpretation"]
        ))
        
        # Basic signs only
        alternatives.append(AlternativeOption(
            option_id="asl_basic_signs",
            alternative_type=AlternativeType.PROCESSING_APPROACH,
            category=AlternativeCategory.FASTER,
            title="Basic Signs Recognition",
            description="Focus on common, basic signs for faster processing",
            parameters={**parameters, 'basic_signs_only': True, 'common_vocabulary': True},
            intent=ConversationIntent.ASL_TO_TEXT,
            estimated_time=5.0,
            estimated_quality="medium",
            reliability_score=0.9,
            pros=["Very fast", "Reliable for basic signs", "Good accuracy"],
            cons=["Limited vocabulary", "May miss complex signs"],
            use_cases=["Simple conversations", "Basic communication", "Quick feedback"]
        ))
        
        # Alternative input method (S3 vs Stream)
        if parameters.get('stream_name'):
            alternatives.append(AlternativeOption(
                option_id="asl_s3_upload",
                alternative_type=AlternativeType.INPUT_METHOD,
                category=AlternativeCategory.MORE_RELIABLE,
                title="Upload Video File",
                description="Upload your video file instead of using live stream",
                parameters={'bucket_name': '[upload_bucket]', 'key_name': '[your_video_file]'},
                intent=ConversationIntent.ASL_TO_TEXT,
                estimated_time=10.0,
                estimated_quality="high",
                reliability_score=0.85,
                pros=["More thorough analysis", "Better quality control", "Can replay"],
                cons=["Requires file upload", "Not real-time"],
                use_cases=["Pre-recorded videos", "Better quality needed", "Detailed analysis"]
            ))
        elif parameters.get('bucket_name'):
            alternatives.append(AlternativeOption(
                option_id="asl_stream_analysis",
                alternative_type=AlternativeType.INPUT_METHOD,
                category=AlternativeCategory.FASTER,
                title="Live Stream Analysis",
                description="Use live stream analysis for real-time feedback",
                parameters={'stream_name': '[your_stream_name]'},
                intent=ConversationIntent.ASL_TO_TEXT,
                estimated_time=3.0,
                estimated_quality="medium",
                reliability_score=0.8,
                pros=["Real-time feedback", "Interactive", "Immediate results"],
                cons=["Less thorough", "Network dependent"],
                use_cases=["Live conversations", "Real-time feedback", "Interactive sessions"]
            ))
        
        return alternatives
    
    def _generate_cross_modal_alternatives(self, original_intent: ConversationIntent,
                                         parameters: Dict[str, Any]) -> List[AlternativeOption]:
        """Generate alternatives that use different input/output modalities"""
        alternatives = []
        
        if original_intent == ConversationIntent.AUDIO_TO_ASL:
            # Suggest text-to-ASL as alternative
            alternatives.append(AlternativeOption(
                option_id="cross_audio_to_text",
                alternative_type=AlternativeType.INPUT_METHOD,
                category=AlternativeCategory.MORE_RELIABLE,
                title="Text Input Instead",
                description="Type your message instead of using audio",
                parameters={'text': '[Type your message here]'},
                intent=ConversationIntent.TEXT_TO_ASL,
                estimated_time=3.0,
                estimated_quality="high",
                reliability_score=0.95,
                pros=["No transcription errors", "Full control", "Very reliable"],
                cons=["Manual typing required"],
                use_cases=["Audio issues", "Precise control", "Complex text"]
            ))
        
        return alternatives
    
    def _generate_parameter_variations(self, intent: ConversationIntent,
                                     parameters: Dict[str, Any]) -> List[AlternativeOption]:
        """Generate parameter variations for the same approach"""
        return self.suggest_parameter_variations(intent, parameters)
    
    def _generate_recommendations(self, alternatives: List[AlternativeOption],
                                context: ConversationContext,
                                failure_reason: Optional[str]) -> List[str]:
        """Generate recommendations based on alternatives and context"""
        recommendations = []
        
        if not alternatives:
            return recommendations
        
        # Analyze user's history for preferences
        successful_translations = context.get_successful_translations()
        user_prefers_speed = len([t for t in successful_translations 
                                if t.translation_result and t.translation_result.processing_time < 5.0]) > len(successful_translations) / 2
        
        # Recommend based on failure reason
        if failure_reason:
            if 'timeout' in failure_reason.lower():
                fastest = min(alternatives, key=lambda x: x.estimated_time)
                recommendations.append(f"Since you experienced a timeout, I'd recommend trying '{fastest.title}' which is much faster")
            elif 'quality' in failure_reason.lower():
                highest_quality = max(alternatives, key=lambda x: {'low': 1, 'medium': 2, 'high': 3}.get(x.estimated_quality, 2))
                recommendations.append(f"For better quality, try '{highest_quality.title}'")
        
        # Recommend based on user preferences
        if user_prefers_speed:
            fastest = min(alternatives, key=lambda x: x.estimated_time)
            recommendations.append(f"Based on your preferences, '{fastest.title}' would be the quickest option")
        
        # General recommendations
        most_reliable = max(alternatives, key=lambda x: x.reliability_score)
        recommendations.append(f"'{most_reliable.title}' has the highest success rate ({most_reliable.reliability_score:.0%})")
        
        return recommendations[:3]  # Limit to 3 recommendations
    
    def _get_comparison_criteria(self, intent: ConversationIntent,
                               failure_reason: Optional[str]) -> List[str]:
        """Get relevant comparison criteria"""
        criteria = ['Speed', 'Quality', 'Reliability']
        
        if intent in [ConversationIntent.TEXT_TO_ASL, ConversationIntent.AUDIO_TO_ASL]:
            criteria.append('Video Format Options')
        
        if failure_reason:
            if 'timeout' in failure_reason.lower():
                criteria.insert(0, 'Processing Time')
            elif 'quality' in failure_reason.lower():
                criteria.insert(0, 'Output Quality')
        
        return criteria
    
    def _generate_comparison_recommendations(self, alternatives: List[AlternativeOption]) -> List[str]:
        """Generate recommendations for comparing alternatives"""
        recommendations = []
        
        if not alternatives:
            return recommendations
        
        # Find best in each category
        fastest = min(alternatives, key=lambda x: x.estimated_time)
        most_reliable = max(alternatives, key=lambda x: x.reliability_score)
        
        recommendations.append(f"For speed: Choose '{fastest.title}' (~{fastest.estimated_time:.1f}s)")
        recommendations.append(f"For reliability: Choose '{most_reliable.title}' ({most_reliable.reliability_score:.0%} success rate)")
        
        # Category-specific recommendations
        categories = set(alt.category for alt in alternatives)
        if AlternativeCategory.SIMPLER in categories:
            recommendations.append("If you're having issues, try the 'Simpler' options first")
        
        return recommendations