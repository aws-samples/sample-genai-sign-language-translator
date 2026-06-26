"""
Alternative Approach Suggestions

This module provides intelligent suggestions for alternative translation methods
when primary approaches fail, including input format guidance and step-by-step
retry workflow suggestions with conversational explanations.
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
from enum import Enum
from dataclasses import dataclass

try:
    from .data_models import (
        ConversationContext, ConversationInteraction, TranslationResult, 
        InputType, ConversationIntent
    )
    from .error_handler import ErrorType, ErrorClassification
except ImportError:
    # Handle case when running as standalone module
    from data_models import (
        ConversationContext, ConversationInteraction, TranslationResult, 
        InputType, ConversationIntent
    )
    from error_handler import ErrorType, ErrorClassification

# Configure logging
logger = logging.getLogger(__name__)

class AlternativeType(Enum):
    """Types of alternative approaches"""
    INPUT_METHOD = "input_method"          # Different input type (text vs audio vs video)
    PROCESSING_APPROACH = "processing_approach"  # Different processing method
    FORMAT_ADJUSTMENT = "format_adjustment"      # File format or input format changes
    PARAMETER_MODIFICATION = "parameter_modification"  # Different parameters or settings
    WORKFLOW_SIMPLIFICATION = "workflow_simplification"  # Simpler approach
    STEP_BY_STEP = "step_by_step"         # Break down into smaller steps

class SuggestionPriority(Enum):
    """Priority levels for suggestions"""
    HIGH = "high"       # Most likely to succeed
    MEDIUM = "medium"   # Worth trying
    LOW = "low"         # Last resort options

@dataclass
class AlternativeSuggestion:
    """Data class for alternative approach suggestions"""
    suggestion_type: AlternativeType
    priority: SuggestionPriority
    title: str
    description: str
    instructions: List[str]
    expected_outcome: str
    prerequisites: List[str] = None
    estimated_success_rate: float = 0.0  # 0.0 to 1.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'suggestion_type': self.suggestion_type.value,
            'priority': self.priority.value,
            'title': self.title,
            'description': self.description,
            'instructions': self.instructions,
            'expected_outcome': self.expected_outcome,
            'prerequisites': self.prerequisites or [],
            'estimated_success_rate': self.estimated_success_rate
        }

class AlternativeApproachSuggester:
    """
    Generates intelligent alternative approach suggestions when primary
    translation methods fail, with conversational explanations and guidance.
    """
    
    def __init__(self):
        """Initialize the alternative approach suggester"""
        self.logger = logger
        
        # Success rate mappings based on error types and alternatives
        self.success_rate_mappings = {
            (ErrorType.TRANSLATION_ERROR, AlternativeType.WORKFLOW_SIMPLIFICATION): 0.8,
            (ErrorType.TRANSLATION_ERROR, AlternativeType.INPUT_METHOD): 0.7,
            (ErrorType.USER_INPUT_ERROR, AlternativeType.FORMAT_ADJUSTMENT): 0.9,
            (ErrorType.USER_INPUT_ERROR, AlternativeType.STEP_BY_STEP): 0.8,
            (ErrorType.NETWORK_ERROR, AlternativeType.WORKFLOW_SIMPLIFICATION): 0.6,
            (ErrorType.TIMEOUT_ERROR, AlternativeType.PARAMETER_MODIFICATION): 0.7,
            (ErrorType.SYSTEM_ERROR, AlternativeType.INPUT_METHOD): 0.5,
        }
        
        logger.info("AlternativeApproachSuggester initialized")
    
    def generate_suggestions(self, failed_operation: str, error_classification: ErrorClassification,
                           context: ConversationContext, 
                           operation_context: Optional[Dict[str, Any]] = None) -> List[AlternativeSuggestion]:
        """
        Generate alternative approach suggestions based on failed operation and context
        
        Args:
            failed_operation: Description of the operation that failed
            error_classification: Classification of the error that occurred
            context: Current conversation context
            operation_context: Optional context about the failed operation
        
        Returns:
            List[AlternativeSuggestion]: Prioritized list of alternative suggestions
        """
        suggestions = []
        
        # Generate suggestions based on error type
        error_type = error_classification.error_type
        
        if error_type == ErrorType.TRANSLATION_ERROR:
            suggestions.extend(self._generate_translation_error_alternatives(
                failed_operation, context, operation_context
            ))
        
        elif error_type == ErrorType.USER_INPUT_ERROR:
            suggestions.extend(self._generate_input_error_alternatives(
                failed_operation, context, operation_context
            ))
        
        elif error_type in [ErrorType.NETWORK_ERROR, ErrorType.TIMEOUT_ERROR]:
            suggestions.extend(self._generate_network_error_alternatives(
                failed_operation, context, operation_context
            ))
        
        elif error_type == ErrorType.SYSTEM_ERROR:
            suggestions.extend(self._generate_system_error_alternatives(
                failed_operation, context, operation_context
            ))
        
        elif error_type == ErrorType.CONTEXT_ERROR:
            suggestions.extend(self._generate_context_error_alternatives(
                failed_operation, context, operation_context
            ))
        
        # Add general fallback suggestions
        suggestions.extend(self._generate_general_alternatives(
            failed_operation, context, operation_context
        ))
        
        # Calculate success rates and sort by priority
        for suggestion in suggestions:
            suggestion.estimated_success_rate = self._calculate_success_rate(
                suggestion, error_type, context
            )
        
        # Sort by priority and success rate
        suggestions.sort(key=lambda s: (
            s.priority.value == "high",
            s.priority.value == "medium", 
            s.estimated_success_rate
        ), reverse=True)
        
        # Limit to top 5 suggestions to avoid overwhelming the user
        return suggestions[:5]
    
    def _generate_translation_error_alternatives(self, failed_operation: str,
                                               context: ConversationContext,
                                               operation_context: Optional[Dict[str, Any]] = None) -> List[AlternativeSuggestion]:
        """Generate alternatives for translation errors"""
        suggestions = []
        
        # Workflow simplification
        suggestions.append(AlternativeSuggestion(
            suggestion_type=AlternativeType.WORKFLOW_SIMPLIFICATION,
            priority=SuggestionPriority.HIGH,
            title="Try with simpler input",
            description="Break down your request into smaller, simpler parts that are easier to translate.",
            instructions=[
                "Use shorter sentences (under 10 words each)",
                "Avoid complex grammar or technical terms",
                "Try translating one sentence at a time",
                "Use common, everyday words when possible"
            ],
            expected_outcome="Simpler input is more likely to translate successfully and produce clearer ASL videos."
        ))
        
        # Input method alternatives
        current_input_type = self._determine_current_input_type(operation_context)
        if current_input_type == InputType.TEXT:
            suggestions.append(AlternativeSuggestion(
                suggestion_type=AlternativeType.INPUT_METHOD,
                priority=SuggestionPriority.MEDIUM,
                title="Try audio input instead",
                description="Sometimes speaking your message naturally can work better than typing it.",
                instructions=[
                    "Record yourself saying the message clearly",
                    "Speak at a normal pace with clear pronunciation",
                    "Upload the audio file and ask me to translate it",
                    "I'll transcribe the speech and then convert it to ASL"
                ],
                expected_outcome="Audio input can capture natural speech patterns that may translate better to ASL."
            ))
        
        elif current_input_type == InputType.AUDIO:
            suggestions.append(AlternativeSuggestion(
                suggestion_type=AlternativeType.INPUT_METHOD,
                priority=SuggestionPriority.MEDIUM,
                title="Try typing the text instead",
                description="If audio processing failed, typing the text directly might work better.",
                instructions=[
                    "Type out exactly what you want to translate",
                    "Use clear, simple sentences",
                    "Check for any typos or unusual characters",
                    "Ask me to translate the text to ASL"
                ],
                expected_outcome="Direct text input bypasses audio processing and may be more reliable."
            ))
        
        # Parameter modification
        suggestions.append(AlternativeSuggestion(
            suggestion_type=AlternativeType.PARAMETER_MODIFICATION,
            priority=SuggestionPriority.MEDIUM,
            title="Request specific video format",
            description="Try asking for a specific type of ASL video that might work better.",
            instructions=[
                "Ask specifically for 'pose video' if you want to see the skeletal movements",
                "Request 'sign video' if you want to see realistic signing",
                "Try 'avatar video' for a 3D animated version",
                "You can also ask for just the ASL gloss text without videos"
            ],
            expected_outcome="Different video formats use different processing methods and one might succeed where others fail."
        ))
        
        return suggestions
    
    def _generate_input_error_alternatives(self, failed_operation: str,
                                         context: ConversationContext,
                                         operation_context: Optional[Dict[str, Any]] = None) -> List[AlternativeSuggestion]:
        """Generate alternatives for input errors"""
        suggestions = []
        
        # Format adjustment
        suggestions.append(AlternativeSuggestion(
            suggestion_type=AlternativeType.FORMAT_ADJUSTMENT,
            priority=SuggestionPriority.HIGH,
            title="Check and fix input format",
            description="Make sure your input meets the required format specifications.",
            instructions=[
                "For audio: Use MP3, WAV, M4A, AAC, or OGG format",
                "For video: Use MP4, AVI, MOV, or WebM format", 
                "Keep file sizes under 10MB when possible",
                "Make sure files aren't corrupted or empty",
                "Check that text input isn't empty or contains only special characters"
            ],
            expected_outcome="Properly formatted input should process without errors."
        ))
        
        # Step-by-step approach
        suggestions.append(AlternativeSuggestion(
            suggestion_type=AlternativeType.STEP_BY_STEP,
            priority=SuggestionPriority.HIGH,
            title="Start with a simple test",
            description="Let's start with something simple to make sure everything is working.",
            instructions=[
                "Try translating a simple phrase like 'Hello' or 'Thank you'",
                "If that works, gradually try longer or more complex content",
                "Upload a small test file first (under 1MB)",
                "Once the simple test works, try your original request again"
            ],
            expected_outcome="Starting simple helps identify if the issue is with your specific input or the system in general."
        ))
        
        # Input method alternatives
        suggestions.append(AlternativeSuggestion(
            suggestion_type=AlternativeType.INPUT_METHOD,
            priority=SuggestionPriority.MEDIUM,
            title="Try a different input method",
            description="If one type of input isn't working, try another approach.",
            instructions=[
                "If file upload failed, try typing the content directly",
                "If text input had issues, try recording audio instead",
                "For video analysis, try uploading a different video file",
                "Consider using a different device or browser if problems persist"
            ],
            expected_outcome="Different input methods use different processing paths and may avoid the current issue."
        ))
        
        return suggestions
    
    def _generate_network_error_alternatives(self, failed_operation: str,
                                           context: ConversationContext,
                                           operation_context: Optional[Dict[str, Any]] = None) -> List[AlternativeSuggestion]:
        """Generate alternatives for network and timeout errors"""
        suggestions = []
        
        # Workflow simplification for network issues
        suggestions.append(AlternativeSuggestion(
            suggestion_type=AlternativeType.WORKFLOW_SIMPLIFICATION,
            priority=SuggestionPriority.HIGH,
            title="Try with smaller or simpler input",
            description="Network issues are often resolved by reducing the processing load.",
            instructions=[
                "Use shorter text (under 50 words)",
                "Upload smaller files (under 5MB)",
                "Try one sentence at a time instead of paragraphs",
                "Avoid complex or technical language that requires more processing"
            ],
            expected_outcome="Smaller requests are less likely to timeout and more likely to complete successfully."
        ))
        
        # Parameter modification for timeouts
        suggestions.append(AlternativeSuggestion(
            suggestion_type=AlternativeType.PARAMETER_MODIFICATION,
            priority=SuggestionPriority.MEDIUM,
            title="Request faster processing options",
            description="Some processing options are faster and less likely to timeout.",
            instructions=[
                "Ask for just the ASL gloss text without videos",
                "Request only one video format instead of all three",
                "Try 'quick translation' or mention you need a fast result",
                "Skip optional features and focus on the core translation"
            ],
            expected_outcome="Faster processing options are less likely to encounter network timeouts."
        ))
        
        # Step-by-step approach
        suggestions.append(AlternativeSuggestion(
            suggestion_type=AlternativeType.STEP_BY_STEP,
            priority=SuggestionPriority.MEDIUM,
            title="Wait and retry",
            description="Network issues are often temporary and resolve themselves.",
            instructions=[
                "Wait 30-60 seconds before trying again",
                "Check your internet connection",
                "Try the same request again without changes",
                "If it fails again, wait a few minutes and retry once more"
            ],
            expected_outcome="Temporary network issues often resolve themselves with a brief wait."
        ))
        
        return suggestions
    
    def _generate_system_error_alternatives(self, failed_operation: str,
                                          context: ConversationContext,
                                          operation_context: Optional[Dict[str, Any]] = None) -> List[AlternativeSuggestion]:
        """Generate alternatives for system errors"""
        suggestions = []
        
        # Input method alternatives
        suggestions.append(AlternativeSuggestion(
            suggestion_type=AlternativeType.INPUT_METHOD,
            priority=SuggestionPriority.HIGH,
            title="Try a different translation approach",
            description="If one translation method is having issues, another might work fine.",
            instructions=[
                "If text-to-ASL failed, try uploading audio of the same content",
                "If audio processing failed, try typing the text directly",
                "If video generation failed, ask for just the ASL gloss text",
                "Try a completely different phrase to see if the issue is content-specific"
            ],
            expected_outcome="Different translation methods use different system components, so alternatives may work."
        ))
        
        # Workflow simplification
        suggestions.append(AlternativeSuggestion(
            suggestion_type=AlternativeType.WORKFLOW_SIMPLIFICATION,
            priority=SuggestionPriority.MEDIUM,
            title="Start with basic functionality",
            description="Test basic features first to isolate the system issue.",
            instructions=[
                "Try a very simple translation like 'Hello'",
                "Ask for help or information about my capabilities",
                "Test with minimal input to see what's working",
                "Once basic functions work, gradually try more complex requests"
            ],
            expected_outcome="Basic functionality testing helps identify which system components are working."
        ))
        
        return suggestions
    
    def _generate_context_error_alternatives(self, failed_operation: str,
                                           context: ConversationContext,
                                           operation_context: Optional[Dict[str, Any]] = None) -> List[AlternativeSuggestion]:
        """Generate alternatives for context errors"""
        suggestions = []
        
        # Step-by-step approach
        suggestions.append(AlternativeSuggestion(
            suggestion_type=AlternativeType.STEP_BY_STEP,
            priority=SuggestionPriority.HIGH,
            title="Start a fresh conversation",
            description="Context issues can be resolved by starting over with a clean session.",
            instructions=[
                "Begin a new conversation session",
                "Provide all the context and information again",
                "Don't reference previous interactions",
                "State your request clearly and completely"
            ],
            expected_outcome="A fresh session eliminates context-related issues and gives us a clean start."
        ))
        
        # Workflow simplification
        suggestions.append(AlternativeSuggestion(
            suggestion_type=AlternativeType.WORKFLOW_SIMPLIFICATION,
            priority=SuggestionPriority.MEDIUM,
            title="Make self-contained requests",
            description="Avoid referencing previous interactions until context is restored.",
            instructions=[
                "Include all necessary information in each request",
                "Don't say 'that last translation' or 'the previous result'",
                "Provide complete context for what you want to do",
                "Treat each request as if it's the first in our conversation"
            ],
            expected_outcome="Self-contained requests don't rely on conversation history and are more likely to succeed."
        ))
        
        return suggestions
    
    def _generate_general_alternatives(self, failed_operation: str,
                                     context: ConversationContext,
                                     operation_context: Optional[Dict[str, Any]] = None) -> List[AlternativeSuggestion]:
        """Generate general fallback alternatives"""
        suggestions = []
        
        # Help and guidance
        suggestions.append(AlternativeSuggestion(
            suggestion_type=AlternativeType.STEP_BY_STEP,
            priority=SuggestionPriority.LOW,
            title="Get help and examples",
            description="Learn about my capabilities and see examples of what works well.",
            instructions=[
                "Ask me 'What can you do?' to see all my features",
                "Request examples: 'Show me how to translate text to ASL'",
                "Ask for help with specific features: 'How do I upload audio?'",
                "Try the examples I provide to make sure everything is working"
            ],
            expected_outcome="Understanding my capabilities helps you use the features more effectively."
        ))
        
        return suggestions
    
    def _determine_current_input_type(self, operation_context: Optional[Dict[str, Any]] = None) -> InputType:
        """Determine the input type from operation context"""
        if not operation_context:
            return InputType.UNKNOWN
        
        # Check for explicit input type
        if 'input_type' in operation_context:
            try:
                return InputType(operation_context['input_type'])
            except ValueError:
                pass
        
        # Infer from operation context
        if 'audio_file' in operation_context or 'audio_filename' in operation_context:
            return InputType.AUDIO
        elif 'video_file' in operation_context or 'video_filename' in operation_context:
            return InputType.VIDEO
        elif 'text' in operation_context or 'input_text' in operation_context:
            return InputType.TEXT
        
        return InputType.UNKNOWN
    
    def _calculate_success_rate(self, suggestion: AlternativeSuggestion, 
                              error_type: ErrorType, context: ConversationContext) -> float:
        """Calculate estimated success rate for a suggestion"""
        # Base success rate from mappings
        base_rate = self.success_rate_mappings.get(
            (error_type, suggestion.suggestion_type), 0.5
        )
        
        # Adjust based on conversation history
        if context.error_count > 3:
            base_rate *= 0.8  # Lower success rate if many errors
        
        successful_translations = context.get_successful_translations()
        if successful_translations:
            base_rate *= 1.1  # Slightly higher if user has had success before
        
        # Adjust based on suggestion type
        if suggestion.suggestion_type == AlternativeType.STEP_BY_STEP:
            base_rate *= 1.2  # Step-by-step approaches tend to work better
        elif suggestion.suggestion_type == AlternativeType.WORKFLOW_SIMPLIFICATION:
            base_rate *= 1.1  # Simplification often helps
        
        return min(1.0, base_rate)  # Cap at 1.0
    
    def format_suggestions_for_user(self, suggestions: List[AlternativeSuggestion],
                                  context: ConversationContext) -> str:
        """
        Format alternative suggestions into a conversational response
        
        Args:
            suggestions: List of alternative suggestions
            context: Current conversation context
        
        Returns:
            str: Formatted conversational response with suggestions
        """
        if not suggestions:
            return "I don't have any specific alternative suggestions right now, but you could try asking for help or starting with a simpler request."
        
        response_parts = []
        
        # Introduction
        if len(suggestions) == 1:
            response_parts.append("Here's an alternative approach you can try:")
        else:
            response_parts.append("Here are some alternative approaches you can try:")
        
        # Format each suggestion
        for i, suggestion in enumerate(suggestions, 1):
            response_parts.append(f"\n**{i}. {suggestion.title}**")
            response_parts.append(suggestion.description)
            
            if suggestion.instructions:
                response_parts.append("Steps:")
                for step in suggestion.instructions:
                    response_parts.append(f"• {step}")
            
            if suggestion.expected_outcome:
                response_parts.append(f"*Expected result: {suggestion.expected_outcome}*")
            
            if i < len(suggestions):
                response_parts.append("")  # Add spacing between suggestions
        
        # Add encouraging closing
        response_parts.append("\nWhich approach would you like to try first? I'm here to help guide you through any of these options!")
        
        return "\n".join(response_parts)
    
    def get_input_format_guidance(self, input_type: InputType) -> Dict[str, Any]:
        """
        Get specific input format guidance for different input types
        
        Args:
            input_type: The type of input needing guidance
        
        Returns:
            Dict containing format guidance information
        """
        guidance = {
            InputType.TEXT: {
                'title': 'Text Input Guidelines',
                'description': 'Tips for providing text that translates well to ASL',
                'guidelines': [
                    'Use clear, simple sentences',
                    'Avoid overly complex grammar',
                    'Keep sentences under 15 words when possible',
                    'Use common, everyday vocabulary',
                    'Avoid excessive punctuation or special characters',
                    'Write in natural, conversational language'
                ],
                'examples': [
                    'Good: "Hello, how are you today?"',
                    'Good: "Thank you for your help."',
                    'Avoid: "Salutations! I would be most grateful if you could provide assistance regarding..."'
                ]
            },
            
            InputType.AUDIO: {
                'title': 'Audio Input Guidelines',
                'description': 'Requirements for audio files that can be processed successfully',
                'guidelines': [
                    'Supported formats: MP3, WAV, M4A, AAC, OGG',
                    'Keep files under 10MB when possible',
                    'Speak clearly and at a normal pace',
                    'Minimize background noise',
                    'Use good quality recording equipment if available',
                    'Avoid very long recordings (under 5 minutes works best)'
                ],
                'examples': [
                    'Good: Clear speech, minimal background noise',
                    'Good: Standard recording quality from phone or computer',
                    'Avoid: Very noisy environments, mumbled speech, very long recordings'
                ]
            },
            
            InputType.VIDEO: {
                'title': 'Video Input Guidelines', 
                'description': 'Requirements for ASL videos that can be analyzed',
                'guidelines': [
                    'Supported formats: MP4, AVI, MOV, WebM',
                    'Keep files under 25MB when possible',
                    'Ensure good lighting on the signer',
                    'Frame the signer from waist up',
                    'Use a plain, contrasting background',
                    'Avoid shaky camera movement'
                ],
                'examples': [
                    'Good: Well-lit signer against plain background',
                    'Good: Stable camera showing hands and face clearly',
                    'Avoid: Dark lighting, cluttered background, partial view of signer'
                ]
            }
        }
        
        return guidance.get(input_type, {
            'title': 'General Input Guidelines',
            'description': 'General tips for providing input',
            'guidelines': [
                'Make sure your input is clear and complete',
                'Provide all necessary context',
                'Use supported file formats',
                'Keep file sizes reasonable'
            ],
            'examples': []
        })
    
    def generate_retry_workflow_suggestions(self, failed_operation: str,
                                          context: ConversationContext) -> List[str]:
        """
        Generate step-by-step retry workflow suggestions
        
        Args:
            failed_operation: Description of the operation that failed
            context: Current conversation context
        
        Returns:
            List[str]: Step-by-step retry instructions
        """
        workflow_steps = []
        
        # Determine the type of operation that failed
        if 'text' in failed_operation.lower() and 'asl' in failed_operation.lower():
            workflow_steps = [
                "Start with a simple test phrase like 'Hello' or 'Thank you'",
                "If that works, try a short sentence (5-8 words)",
                "Gradually increase complexity until you find what works",
                "Once you know the system is working, try your original text",
                "If your original text still fails, break it into shorter sentences",
                "Try each sentence separately, then combine the results"
            ]
        
        elif 'audio' in failed_operation.lower():
            workflow_steps = [
                "First, check that your audio file is in a supported format (MP3, WAV, M4A)",
                "Try uploading a very short audio clip (under 30 seconds) as a test",
                "If the test works, try your original audio file",
                "If it still fails, try converting your audio to MP3 format",
                "As an alternative, type out what the audio says and translate that text instead",
                "You can also try recording the audio again with clearer speech"
            ]
        
        elif 'video' in failed_operation.lower() or 'asl' in failed_operation.lower():
            workflow_steps = [
                "Check that your video file is in a supported format (MP4, MOV, AVI)",
                "Make sure the video shows the signer clearly from waist up",
                "Try uploading a shorter video clip (under 1 minute) as a test",
                "Ensure good lighting and a plain background in the video",
                "If analysis still fails, try a different video with clearer signing",
                "You can also describe what the video shows and I'll help interpret it"
            ]
        
        else:
            # General retry workflow
            workflow_steps = [
                "Start with the simplest version of your request",
                "Make sure all required information is provided",
                "Check that any files are in supported formats",
                "Try the request again with minimal changes",
                "If it still fails, try a completely different approach",
                "Ask for help if you're not sure what to try next"
            ]
        
        return workflow_steps