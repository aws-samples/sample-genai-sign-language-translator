"""
Conversational Response Formatter

This module provides natural language generation and response formatting capabilities
for the conversational ASL agent, creating user-friendly responses with clear
explanations and next step suggestions.
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from enum import Enum

try:
    from .data_models import (
        ConversationContext, 
        ConversationInteraction, 
        TranslationResult, 
        ConversationIntent,
        InputType,
        TranslationStatus
    )
except ImportError:
    # Fallback for direct execution
    from data_models import (
        ConversationContext, 
        ConversationInteraction, 
        TranslationResult, 
        ConversationIntent,
        InputType,
        TranslationStatus
    )

logger = logging.getLogger(__name__)

class ResponseTemplate(Enum):
    """Enumeration of response template types"""
    TRANSLATION_SUCCESS = "translation_success"
    TRANSLATION_PARTIAL = "translation_partial"
    TRANSLATION_ERROR = "translation_error"
    HELP_GENERAL = "help_general"
    HELP_SPECIFIC = "help_specific"
    STATUS_UPDATE = "status_update"
    GREETING = "greeting"
    ACKNOWLEDGMENT = "acknowledgment"
    ERROR_RECOVERY = "error_recovery"
    NEXT_STEPS = "next_steps"

class ConversationResponseFormatter:
    """
    Conversational response formatter that generates natural language responses
    for translation results, help requests, and other agent interactions.
    """
    
    def __init__(self):
        """Initialize the response formatter with templates and patterns"""
        self.templates = self._initialize_templates()
        self.response_patterns = self._initialize_response_patterns()
        
    def _initialize_templates(self) -> Dict[ResponseTemplate, Dict[str, Any]]:
        """Initialize response templates for different interaction types"""
        return {
            ResponseTemplate.TRANSLATION_SUCCESS: {
                'intro_phrases': [
                    "Great! I've successfully translated your {input_type}.",
                    "Perfect! Here's your {input_type} translation:",
                    "Done! I've converted your {input_type} to ASL:",
                    "Excellent! Your {input_type} has been translated:"
                ],
                'result_intro': [
                    "Here are the results:",
                    "Here's what I generated:",
                    "Your translation results:",
                    "Here's your ASL translation:"
                ]
            },
            ResponseTemplate.TRANSLATION_PARTIAL: {
                'intro_phrases': [
                    "I was able to partially process your {input_type}.",
                    "I've made some progress on your {input_type} translation:",
                    "Here's what I could translate from your {input_type}:"
                ],
                'explanation': [
                    "Some parts couldn't be processed completely.",
                    "There were some challenges with certain sections.",
                    "I encountered some difficulties with parts of the input."
                ]
            },
            ResponseTemplate.TRANSLATION_ERROR: {
                'intro_phrases': [
                    "I encountered an issue while translating your {input_type}.",
                    "Unfortunately, I couldn't complete the {input_type} translation.",
                    "There was a problem processing your {input_type}:"
                ],
                'recovery_suggestions': [
                    "Let me suggest some alternatives:",
                    "Here are some things you could try:",
                    "Would you like to try one of these options:"
                ]
            },
            ResponseTemplate.HELP_GENERAL: {
                'intro_phrases': [
                    "I'm happy to help! Here's what I can do:",
                    "Great question! Let me explain my capabilities:",
                    "I'd love to help you understand what I can do:"
                ]
            },
            ResponseTemplate.GREETING: {
                'first_time': [
                    "Hello! I'm your conversational ASL translation assistant.",
                    "Hi there! I'm here to help you with ASL translation.",
                    "Welcome! I'm your friendly ASL translation agent."
                ],
                'returning': [
                    "Hello again! Good to see you back.",
                    "Hi! Welcome back to our conversation.",
                    "Great to have you back! How can I help today?"
                ]
            }
        }
    
    def _initialize_response_patterns(self) -> Dict[str, List[str]]:
        """Initialize common response patterns and phrases"""
        return {
            'transition_phrases': [
                "Now,", "Next,", "Additionally,", "Also,", "Furthermore,"
            ],
            'encouragement': [
                "You're doing great!", "Perfect!", "Excellent choice!", 
                "That's exactly right!", "Good thinking!"
            ],
            'clarification_requests': [
                "Could you clarify", "I'd like to understand better",
                "Can you help me understand", "Would you mind explaining"
            ],
            'next_step_intros': [
                "What would you like to do next?",
                "Here are some things you might want to try:",
                "You could also:",
                "Some other options:"
            ]
        }
    
    def format_translation_response(self, result: TranslationResult, 
                                  context: ConversationContext,
                                  detail_level: str = "standard") -> str:
        """
        Format a translation result into a conversational response
        
        Args:
            result: The translation result to format
            context: Current conversation context
            detail_level: Level of detail ("brief", "standard", "detailed")
            
        Returns:
            str: Formatted conversational response
        """
        try:
            if result.success:
                return self._format_successful_translation(result, context, detail_level)
            else:
                return self._format_failed_translation(result, context)
                
        except Exception as e:
            logger.error(f"Error formatting translation response: {e}")
            return self._format_error_fallback(result, str(e))
    
    def determine_appropriate_detail_level(self, result: TranslationResult, 
                                         context: ConversationContext) -> str:
        """
        Determine appropriate detail level based on context
        
        Args:
            result: The translation result
            context: Current conversation context
            
        Returns:
            str: Appropriate detail level ("brief", "standard", "detailed")
        """
        # Use detailed for first interaction or complex results
        if len(context.conversation_history) <= 1:
            return "detailed"
        
        # Use brief for repeated similar operations
        recent_interactions = context.get_recent_interactions(3)
        similar_operations = [
            interaction for interaction in recent_interactions
            if (interaction.translation_result and 
                interaction.translation_result.input_type == result.input_type)
        ]
        
        if len(similar_operations) >= 2:
            return "brief"
        
        # Use detailed for complex results (multiple videos, metadata)
        if (len(result.video_urls) > 2 or 
            (result.metadata and len(result.metadata) > 2)):
            return "detailed"
        
        # Default to standard
        return "standard"
    
    def _format_successful_translation(self, result: TranslationResult, 
                                     context: ConversationContext,
                                     detail_level: str = "standard") -> str:
        """Format a successful translation result with appropriate detail level"""
        response_parts = []
        
        # Get input type for personalization
        input_type_name = self._get_input_type_display_name(result.input_type)
        
        # Choose intro phrase based on detail level
        if detail_level == "brief":
            intro = f"✅ {input_type_name.title()} translated successfully!"
        else:
            intro_template = self.templates[ResponseTemplate.TRANSLATION_SUCCESS]
            intro = self._select_phrase(intro_template['intro_phrases']).format(
                input_type=input_type_name
            )
        
        response_parts.append(intro)
        
        # Add result details based on detail level
        if detail_level == "brief":
            result_section = self._format_brief_translation_details(result)
        elif detail_level == "detailed":
            result_section = self._format_detailed_translation_details(result)
        else:  # standard
            result_section = self._format_translation_details(result)
        
        if result_section:
            response_parts.append(result_section)
        
        # Add processing time if significant and not brief
        if detail_level != "brief" and result.processing_time > 1.0:
            response_parts.append(f"⏱️ Processing completed in {result.processing_time:.1f} seconds.")
        
        # Add next steps suggestions based on detail level
        if detail_level != "brief":
            next_steps = self._generate_next_steps_suggestions(result, context)
            if next_steps:
                response_parts.append(next_steps)
        
        return "\n\n".join(response_parts)
    
    def _format_brief_translation_details(self, result: TranslationResult) -> str:
        """Format translation details in brief format"""
        details = []
        
        # Show only the most important information
        if result.gloss:
            details.append(f"**ASL Gloss:** {result.gloss}")
        
        if result.interpreted_text and result.input_type in [InputType.VIDEO, InputType.STREAM]:
            details.append(f"**Interpreted:** \"{result.interpreted_text}\"")
        
        # Show only the best video if available
        if result.video_urls:
            best_video = self._get_best_video_url(result.video_urls)
            if best_video:
                video_type, url = best_video
                details.append(f"**Video:** {url}")
        
        return "\n".join(details) if details else ""
    
    def _format_detailed_translation_details(self, result: TranslationResult) -> str:
        """Format translation details in detailed format with extra context"""
        # Start with standard details
        details = self._format_translation_details(result)
        
        # Add extra detailed information
        extra_details = []
        
        # Add quality indicators
        if result.video_urls:
            video_count = len(result.video_urls)
            extra_details.append(f"**Generated {video_count} video format{'s' if video_count != 1 else ''}** for different viewing preferences")
        
        # Add technical details if available
        if result.metadata:
            tech_details = self._format_technical_details(result.metadata)
            if tech_details:
                extra_details.append(tech_details)
        
        # Add usage tips
        usage_tips = self._generate_usage_tips(result)
        if usage_tips:
            extra_details.append(usage_tips)
        
        if extra_details:
            details += "\n\n" + "\n\n".join(extra_details)
        
        return details
    
    def _format_technical_details(self, metadata: Dict[str, Any]) -> str:
        """Format technical details from metadata"""
        tech_lines = []
        
        # Model information
        if 'model_version' in metadata:
            tech_lines.append(f"Model Version: {metadata['model_version']}")
        
        # Processing statistics
        if 'frames_processed' in metadata:
            tech_lines.append(f"Frames Processed: {metadata['frames_processed']}")
        
        if 'gloss_tokens' in metadata:
            tech_lines.append(f"Gloss Tokens: {metadata['gloss_tokens']}")
        
        # Quality metrics
        if 'quality_score' in metadata:
            score = metadata['quality_score']
            if isinstance(score, (int, float)):
                tech_lines.append(f"Quality Score: {score:.2f}")
        
        if tech_lines:
            return "**Technical Details:**\n" + "\n".join([f"• {line}" for line in tech_lines])
        
        return ""
    
    def _generate_usage_tips(self, result: TranslationResult) -> str:
        """Generate usage tips based on the translation result"""
        tips = []
        
        if result.input_type == InputType.TEXT and result.gloss:
            tips.append("💡 **Tip:** The gloss notation shows the conceptual structure of ASL signs")
            
        if len(result.video_urls) > 1:
            tips.append("💡 **Tip:** Try different video formats to see which works best for your needs")
            
        if result.input_type == InputType.AUDIO:
            tips.append("💡 **Tip:** For better accuracy, use clear audio with minimal background noise")
            
        if result.input_type in [InputType.VIDEO, InputType.STREAM]:
            tips.append("💡 **Tip:** Good lighting and clear hand visibility improve analysis accuracy")
        
        if tips:
            return "\n".join(tips)
        
        return ""
    
    def _get_best_video_url(self, video_urls: Dict[str, str]) -> Optional[Tuple[str, str]]:
        """Get the best video URL based on quality preference"""
        # Preference order: blended > avatar > sign > pose
        preference_order = ['blended', 'avatar', 'sign', 'pose']
        
        for video_type in preference_order:
            if video_type in video_urls:
                return (video_type, video_urls[video_type])
        
        # If none of the preferred types, return the first available
        if video_urls:
            first_type = next(iter(video_urls))
            return (first_type, video_urls[first_type])
        
        return None
    
    def _format_failed_translation(self, result: TranslationResult, 
                                 context: ConversationContext) -> str:
        """Format a failed translation result with recovery suggestions"""
        response_parts = []
        
        # Get input type for personalization
        input_type_name = self._get_input_type_display_name(result.input_type)
        
        # Choose intro phrase
        intro_template = self.templates[ResponseTemplate.TRANSLATION_ERROR]
        intro = self._select_phrase(intro_template['intro_phrases']).format(
            input_type=input_type_name
        )
        response_parts.append(intro)
        
        # Add error explanation if available
        if result.error_message:
            error_explanation = self._format_error_explanation(result.error_message)
            response_parts.append(error_explanation)
        
        # Add recovery suggestions
        recovery_suggestions = self._generate_recovery_suggestions(result, context)
        if recovery_suggestions:
            response_parts.append(recovery_suggestions)
        
        return "\n\n".join(response_parts)
    
    def _format_translation_details(self, result: TranslationResult) -> str:
        """Format the detailed translation results with organized presentation"""
        details = []
        
        # Add original input with context-appropriate formatting
        if result.input_text:
            if result.input_type == InputType.TEXT:
                details.append(f"**Original Text:** \"{result.input_text}\"")
            elif result.input_type == InputType.AUDIO:
                # For audio, input_text might be the file reference
                if result.interpreted_text:  # This would be the transcribed text
                    details.append(f"**Transcribed Text:** \"{result.interpreted_text}\"")
                details.append(f"**Audio Source:** {result.input_text}")
            elif result.input_type in [InputType.VIDEO, InputType.STREAM]:
                details.append(f"**Video Source:** {result.input_text}")
        
        # Add ASL gloss with explanation for text/audio to ASL translations
        if result.gloss:
            gloss_section = self._format_gloss_notation(result.gloss)
            details.append(gloss_section)
        
        # Add interpreted text for ASL-to-text translations
        if result.interpreted_text and result.input_type in [InputType.VIDEO, InputType.STREAM]:
            details.append(f"**Interpreted English:** \"{result.interpreted_text}\"")
        
        # Add video URLs with organized presentation
        if result.video_urls:
            video_section = self._format_video_urls(result.video_urls)
            details.append(video_section)
        
        # Add metadata if relevant
        metadata_section = self._format_relevant_metadata(result)
        if metadata_section:
            details.append(metadata_section)
        
        return "\n\n".join(details) if details else ""
    
    def _format_gloss_notation(self, gloss: str) -> str:
        """Format ASL gloss notation with explanation"""
        gloss_lines = [
            f"**ASL Gloss Notation:** {gloss}",
            "",
            "*Gloss notation shows the conceptual structure of ASL signs.*",
            "*Words in CAPS represent signs, and the order reflects ASL grammar.*"
        ]
        
        # Add brief explanation if gloss contains common patterns
        if any(pattern in gloss.upper() for pattern in ['IX', 'CL:', 'FS:']):
            gloss_lines.append("*Special notations: IX (indexing/pointing), CL: (classifiers), FS: (fingerspelling)*")
        
        return "\n".join(gloss_lines)
    
    def _format_relevant_metadata(self, result: TranslationResult) -> str:
        """Format relevant metadata information"""
        if not result.metadata:
            return ""
        
        metadata_lines = []
        
        # Format transcription confidence for audio translations
        if 'transcription_confidence' in result.metadata:
            confidence = result.metadata['transcription_confidence']
            if isinstance(confidence, (int, float)):
                confidence_pct = confidence * 100 if confidence <= 1.0 else confidence
                metadata_lines.append(f"**Transcription Confidence:** {confidence_pct:.1f}%")
        
        # Format video analysis details
        if 'detected_signs' in result.metadata:
            sign_count = result.metadata['detected_signs']
            metadata_lines.append(f"**Signs Detected:** {sign_count}")
        
        if 'analysis_confidence' in result.metadata:
            confidence = result.metadata['analysis_confidence']
            if isinstance(confidence, (int, float)):
                confidence_pct = confidence * 100 if confidence <= 1.0 else confidence
                metadata_lines.append(f"**Analysis Confidence:** {confidence_pct:.1f}%")
        
        # Format processing details
        if 'video_duration' in result.metadata:
            duration = result.metadata['video_duration']
            metadata_lines.append(f"**Video Duration:** {duration:.1f} seconds")
        
        if 'audio_duration' in result.metadata:
            duration = result.metadata['audio_duration']
            metadata_lines.append(f"**Audio Duration:** {duration:.1f} seconds")
        
        if metadata_lines:
            return "**Processing Details:**\n" + "\n".join([f"• {line}" for line in metadata_lines])
        
        return ""
    
    def _format_video_urls(self, video_urls: Dict[str, str]) -> str:
        """Format video URLs with clear labels and organized presentation"""
        if not video_urls:
            return ""
        
        video_lines = ["**Generated Videos:**"]
        
        # Define display names and descriptions for video types
        video_type_info = {
            'pose': {
                'icon': '🎭',
                'name': 'Pose Video',
                'description': 'Skeletal representation showing hand and body positions'
            },
            'sign': {
                'icon': '👤',
                'name': 'Sign Video', 
                'description': 'Avatar demonstrating the actual signs'
            },
            'avatar': {
                'icon': '🤖',
                'name': 'Avatar Video',
                'description': '3D character performing the signs'
            },
            'blended': {
                'icon': '✨',
                'name': 'Blended Video',
                'description': 'Enhanced quality with smoothed transitions'
            }
        }
        
        # Sort video types by preference order
        preferred_order = ['blended', 'avatar', 'sign', 'pose']
        sorted_videos = []
        
        # Add videos in preferred order
        for video_type in preferred_order:
            if video_type in video_urls:
                sorted_videos.append((video_type, video_urls[video_type]))
        
        # Add any remaining videos not in preferred order
        for video_type, url in video_urls.items():
            if video_type not in preferred_order:
                sorted_videos.append((video_type, url))
        
        # Format each video with detailed information
        for video_type, url in sorted_videos:
            if video_type in video_type_info:
                info = video_type_info[video_type]
                video_lines.append(
                    f"• {info['icon']} **{info['name']}**: {info['description']}\n"
                    f"  📎 {url}"
                )
            else:
                # Fallback for unknown video types
                video_lines.append(f"• 📹 **{video_type.title()} Video**: {url}")
        
        return "\n".join(video_lines)
    
    def _format_error_explanation(self, error_message: str) -> str:
        """Format error message in a user-friendly way"""
        # Clean up technical error messages
        user_friendly_message = self._make_error_user_friendly(error_message)
        return f"**Issue:** {user_friendly_message}"
    
    def _make_error_user_friendly(self, error_message: str) -> str:
        """Convert technical error messages to user-friendly explanations"""
        error_lower = error_message.lower()
        
        # Common error patterns and their user-friendly explanations
        error_mappings = {
            'timeout': "The processing took longer than expected and timed out.",
            'file not found': "The file you referenced couldn't be found.",
            'invalid format': "The file format isn't supported or the file is corrupted.",
            'network error': "There was a network connectivity issue.",
            'service unavailable': "The translation service is temporarily unavailable.",
            'quota exceeded': "The service usage limit has been reached.",
            'authentication': "There was an authentication issue with the service.",
            'permission denied': "Access to the requested resource was denied.",
            'out of memory': "The system ran out of memory while processing.",
            'invalid input': "The input provided wasn't in the expected format."
        }
        
        for pattern, explanation in error_mappings.items():
            if pattern in error_lower:
                return explanation
        
        # If no pattern matches, return a cleaned version of the original
        return error_message.replace('_', ' ').capitalize()
    
    def _generate_recovery_suggestions(self, result: TranslationResult, 
                                     context: ConversationContext) -> str:
        """Generate recovery suggestions based on the error type"""
        suggestions = []
        
        if result.error_message:
            error_lower = result.error_message.lower()
            
            if 'timeout' in error_lower:
                suggestions.extend([
                    "Try breaking longer text into smaller chunks",
                    "Check your internet connection",
                    "Try again in a few moments"
                ])
            elif 'file not found' in error_lower or 'invalid format' in error_lower:
                suggestions.extend([
                    "Make sure the file is properly uploaded",
                    "Check that the file format is supported (MP4, AVI, MOV for videos; MP3, WAV for audio)",
                    "Try uploading the file again"
                ])
            elif 'network' in error_lower or 'service unavailable' in error_lower:
                suggestions.extend([
                    "Check your internet connection",
                    "Try again in a few minutes",
                    "The service might be temporarily down"
                ])
            else:
                # Generic suggestions
                suggestions.extend([
                    "Try rephrasing your request",
                    "Check that all required information is provided",
                    "Try a different approach or input method"
                ])
        
        if suggestions:
            intro = self._select_phrase(
                self.templates[ResponseTemplate.TRANSLATION_ERROR]['recovery_suggestions']
            )
            suggestion_list = "\n".join([f"• {suggestion}" for suggestion in suggestions])
            return f"{intro}\n{suggestion_list}"
        
        return ""
    
    def _generate_next_steps_suggestions(self, result: TranslationResult, 
                                       context: ConversationContext) -> str:
        """Generate contextual next step suggestions based on translation type and user patterns"""
        suggestions = self._get_contextual_suggestions(result, context)
        
        if not suggestions:
            return ""
        
        # Select appropriate intro based on context
        intro = self._select_next_steps_intro(result, context)
        
        # Format suggestions with appropriate icons and descriptions
        formatted_suggestions = self._format_suggestion_list(suggestions)
        
        return f"{intro}\n{formatted_suggestions}"
    
    def _get_contextual_suggestions(self, result: TranslationResult, 
                                  context: ConversationContext) -> List[Dict[str, str]]:
        """Get contextual suggestions based on result and conversation history"""
        suggestions = []
        
        # Base suggestions by translation type
        if result.input_type == InputType.TEXT and result.success:
            suggestions.extend([
                {
                    'action': 'Try translating another phrase',
                    'icon': '🔤',
                    'description': 'Translate more text to ASL'
                },
                {
                    'action': 'Ask me to explain the ASL gloss notation',
                    'icon': '📝',
                    'description': 'Learn about gloss symbols and structure'
                },
                {
                    'action': 'Upload an audio file to translate speech to ASL',
                    'icon': '🎵',
                    'description': 'Try audio-to-ASL translation'
                }
            ])
        elif result.input_type == InputType.AUDIO and result.success:
            suggestions.extend([
                {
                    'action': 'Try uploading another audio file',
                    'icon': '🎵',
                    'description': 'Process more audio content'
                },
                {
                    'action': 'Ask me to show you the transcribed text again',
                    'icon': '📝',
                    'description': 'Review the speech-to-text conversion'
                },
                {
                    'action': 'Try translating some text directly',
                    'icon': '🔤',
                    'description': 'Compare with direct text translation'
                }
            ])
        elif result.input_type in [InputType.VIDEO, InputType.STREAM] and result.success:
            suggestions.extend([
                {
                    'action': 'Upload another ASL video to analyze',
                    'icon': '📹',
                    'description': 'Analyze more ASL content'
                },
                {
                    'action': 'Try translating the interpreted text back to ASL',
                    'icon': '🔄',
                    'description': 'See the round-trip translation'
                },
                {
                    'action': 'Ask me to explain what signs were detected',
                    'icon': '🔍',
                    'description': 'Get detailed analysis breakdown'
                }
            ])
        
        # Add contextual suggestions based on conversation patterns
        contextual_suggestions = self._get_pattern_based_suggestions(result, context)
        suggestions.extend(contextual_suggestions)
        
        # Add learning and exploration suggestions
        learning_suggestions = self._get_learning_suggestions(result, context)
        suggestions.extend(learning_suggestions)
        
        # Limit and prioritize suggestions
        return self._prioritize_suggestions(suggestions, result, context)
    
    def _get_pattern_based_suggestions(self, result: TranslationResult, 
                                     context: ConversationContext) -> List[Dict[str, str]]:
        """Get suggestions based on user interaction patterns"""
        suggestions = []
        
        # First-time user suggestions
        if len(context.conversation_history) <= 1:
            suggestions.append({
                'action': 'Ask me "What can you do?" to learn about all my features',
                'icon': '❓',
                'description': 'Discover all available capabilities'
            })
        
        # Suggestions based on previous successful translations
        successful_translations = context.get_successful_translations()
        if successful_translations:
            used_types = {t.translation_result.input_type for t in successful_translations}
            
            # Suggest trying different input types
            if InputType.TEXT in used_types and InputType.AUDIO not in used_types:
                suggestions.append({
                    'action': 'Try uploading an audio file for speech-to-ASL',
                    'icon': '🎤',
                    'description': 'Experience audio translation'
                })
            
            if InputType.AUDIO in used_types and InputType.VIDEO not in used_types:
                suggestions.append({
                    'action': 'Upload an ASL video for interpretation',
                    'icon': '📹',
                    'description': 'Try ASL-to-text analysis'
                })
            
            if (InputType.TEXT in used_types or InputType.AUDIO in used_types) and InputType.VIDEO not in used_types:
                suggestions.append({
                    'action': 'Try the reverse: upload ASL video for interpretation',
                    'icon': '🔄',
                    'description': 'Experience bidirectional translation'
                })
        
        # Suggestions based on error patterns
        if context.get_error_rate() > 20:  # If user has had some errors
            suggestions.append({
                'action': 'Ask for help with troubleshooting',
                'icon': '🛠️',
                'description': 'Get tips for better results'
            })
        
        return suggestions
    
    def _get_learning_suggestions(self, result: TranslationResult, 
                                context: ConversationContext) -> List[Dict[str, str]]:
        """Get learning and educational suggestions"""
        suggestions = []
        
        # Educational suggestions based on result type
        if result.gloss and 'IX' in result.gloss.upper():
            suggestions.append({
                'action': 'Ask me about indexing (IX) in ASL grammar',
                'icon': '👉',
                'description': 'Learn about ASL pointing and reference'
            })
        
        if result.gloss and 'CL:' in result.gloss.upper():
            suggestions.append({
                'action': 'Ask me about classifiers (CL:) in ASL',
                'icon': '🏷️',
                'description': 'Understand ASL classifier usage'
            })
        
        if len(result.video_urls) > 1:
            suggestions.append({
                'action': 'Ask me about the different video formats',
                'icon': '🎬',
                'description': 'Learn when to use each video type'
            })
        
        # General learning suggestions
        if len(context.conversation_history) > 3:  # Experienced user
            suggestions.append({
                'action': 'Ask me about advanced ASL features',
                'icon': '🎓',
                'description': 'Explore advanced capabilities'
            })
        
        return suggestions
    
    def _prioritize_suggestions(self, suggestions: List[Dict[str, str]], 
                              result: TranslationResult, 
                              context: ConversationContext) -> List[Dict[str, str]]:
        """Prioritize and limit suggestions based on context"""
        if not suggestions:
            return []
        
        # Remove duplicates while preserving order
        seen_actions = set()
        unique_suggestions = []
        for suggestion in suggestions:
            if suggestion['action'] not in seen_actions:
                unique_suggestions.append(suggestion)
                seen_actions.add(suggestion['action'])
        
        # Prioritize based on user experience level
        if len(context.conversation_history) <= 1:
            # New users: prioritize exploration and learning
            priority_keywords = ['learn', 'discover', 'features', 'help']
        elif len(context.conversation_history) <= 5:
            # Intermediate users: prioritize trying different types
            priority_keywords = ['try', 'upload', 'another', 'different']
        else:
            # Experienced users: prioritize advanced features
            priority_keywords = ['advanced', 'explain', 'detailed', 'troubleshooting']
        
        # Sort suggestions by priority
        def suggestion_priority(suggestion):
            action_lower = suggestion['action'].lower()
            for i, keyword in enumerate(priority_keywords):
                if keyword in action_lower:
                    return i
            return len(priority_keywords)  # Lower priority for non-matching
        
        unique_suggestions.sort(key=suggestion_priority)
        
        # Limit to 3-4 suggestions to avoid overwhelming
        max_suggestions = 3 if len(context.conversation_history) <= 1 else 4
        return unique_suggestions[:max_suggestions]
    
    def _select_next_steps_intro(self, result: TranslationResult, 
                               context: ConversationContext) -> str:
        """Select appropriate intro for next steps based on context"""
        if len(context.conversation_history) <= 1:
            return "🌟 **Here are some things you might want to explore:**"
        elif result.success:
            return "✨ **What would you like to try next?**"
        else:
            return "🔄 **Here are some alternatives you could try:**"
    
    def _format_suggestion_list(self, suggestions: List[Dict[str, str]]) -> str:
        """Format suggestions into a readable list"""
        if not suggestions:
            return ""
        
        formatted_lines = []
        for suggestion in suggestions:
            icon = suggestion.get('icon', '•')
            action = suggestion['action']
            description = suggestion.get('description', '')
            
            if description:
                formatted_lines.append(f"{icon} **{action}**\n   {description}")
            else:
                formatted_lines.append(f"{icon} {action}")
        
        return "\n".join(formatted_lines)
    
    def generate_proactive_tips(self, context: ConversationContext) -> Optional[str]:
        """
        Generate proactive tips based on user interaction patterns
        
        Args:
            context: Current conversation context
            
        Returns:
            Optional[str]: Proactive tip message or None
        """
        if not context.conversation_history:
            return None
        
        # Analyze user patterns
        recent_interactions = context.get_recent_interactions(5)
        
        # Tip for users who only use one input type
        used_input_types = {
            interaction.translation_result.input_type 
            for interaction in recent_interactions 
            if interaction.translation_result
        }
        
        if len(used_input_types) == 1 and len(recent_interactions) >= 3:
            current_type = next(iter(used_input_types))
            if current_type == InputType.TEXT:
                return ("💡 **Pro Tip:** Did you know I can also process audio files and analyze ASL videos? "
                       "Try uploading an audio recording or ASL video for a different experience!")
            elif current_type == InputType.AUDIO:
                return ("💡 **Pro Tip:** You can also upload ASL videos for interpretation, "
                       "or simply type text for direct translation to ASL!")
            elif current_type in [InputType.VIDEO, InputType.STREAM]:
                return ("💡 **Pro Tip:** I can also translate text and audio to ASL! "
                       "Try typing a message or uploading an audio file.")
        
        # Tip for users with high error rates
        if context.get_error_rate() > 30 and len(recent_interactions) >= 3:
            return ("💡 **Helpful Tip:** If you're experiencing issues, try using clear, simple sentences "
                   "for text translation, or ensure good lighting and hand visibility for video analysis.")
        
        # Tip for users who haven't explored video formats
        successful_translations = [
            interaction for interaction in recent_interactions
            if interaction.translation_result and interaction.translation_result.success
        ]
        
        if (len(successful_translations) >= 2 and 
            all(len(t.translation_result.video_urls) > 1 for t in successful_translations)):
            return ("💡 **Did You Know?** I generate multiple video formats for each translation. "
                   "Try asking 'What's the difference between the video formats?' to learn more!")
        
        return None
    
    def generate_follow_up_recommendations(self, result: TranslationResult, 
                                         context: ConversationContext) -> Optional[str]:
        """
        Generate follow-up action recommendations based on completed translation
        
        Args:
            result: The completed translation result
            context: Current conversation context
            
        Returns:
            Optional[str]: Follow-up recommendation message or None
        """
        recommendations = []
        
        # Recommendations based on translation success and type
        if result.success:
            if result.input_type == InputType.TEXT:
                recommendations.extend([
                    "Practice the signs by watching the generated videos",
                    "Try translating related phrases to build vocabulary",
                    "Ask me to explain any unfamiliar gloss notation"
                ])
            elif result.input_type == InputType.AUDIO:
                recommendations.extend([
                    "Review the transcribed text for accuracy",
                    "Try the same content as direct text input to compare",
                    "Practice the resulting ASL signs"
                ])
            elif result.input_type in [InputType.VIDEO, InputType.STREAM]:
                recommendations.extend([
                    "Try translating the interpreted text back to ASL",
                    "Ask for clarification on any unclear interpretations",
                    "Upload another video to continue practicing"
                ])
        else:
            # Recommendations for failed translations
            recommendations.extend([
                "Try simplifying your input",
                "Check file formats and quality",
                "Ask for help with troubleshooting"
            ])
        
        # Add contextual recommendations
        if len(context.conversation_history) >= 3:
            successful_count = len(context.get_successful_translations())
            if successful_count >= 2:
                recommendations.append("Explore advanced features like live video analysis")
        
        if recommendations:
            intro = "🎯 **Recommended next actions:**"
            rec_list = "\n".join([f"• {rec}" for rec in recommendations[:3]])
            return f"{intro}\n{rec_list}"
        
        return None
    
    def generate_contextual_guidance(self, intent: ConversationIntent, 
                                   context: ConversationContext) -> Optional[str]:
        """
        Generate contextual guidance based on user intent and conversation history
        
        Args:
            intent: The user's current intent
            context: Current conversation context
            
        Returns:
            Optional[str]: Contextual guidance message or None
        """
        guidance_messages = {
            ConversationIntent.TEXT_TO_ASL: [
                "For best results, use clear, simple sentences",
                "I can handle complex phrases, but shorter text often translates more accurately",
                "Try everyday phrases like greetings, questions, or common expressions"
            ],
            ConversationIntent.AUDIO_TO_ASL: [
                "Speak clearly and at a moderate pace for better transcription",
                "Minimize background noise for optimal results",
                "Audio files under 2 minutes work best"
            ],
            ConversationIntent.ASL_TO_TEXT: [
                "Ensure good lighting and clear hand visibility",
                "Sign at a natural pace - not too fast or slow",
                "Keep hands within the camera frame throughout the video"
            ]
        }
        
        if intent in guidance_messages:
            # Select guidance based on user experience
            messages = guidance_messages[intent]
            if len(context.conversation_history) <= 1:
                # New users get more detailed guidance
                return f"📋 **Tips for {intent.value.replace('_', ' ')}:**\n" + \
                       "\n".join([f"• {msg}" for msg in messages])
            elif context.get_error_rate() > 20:
                # Users with errors get targeted help
                return f"💡 **To improve results:** {messages[0]}"
        
        return None
    
    def format_help_response(self, help_topic: str, context: ConversationContext) -> str:
        """
        Format a help response based on the requested topic
        
        Args:
            help_topic: The specific help topic requested
            context: Current conversation context
            
        Returns:
            str: Formatted help response
        """
        if help_topic == 'general':
            return self._format_general_help(context)
        elif help_topic == 'translation':
            return self._format_translation_help()
        elif help_topic == 'audio':
            return self._format_audio_help()
        elif help_topic == 'video':
            return self._format_video_help()
        elif help_topic == 'features':
            return self._format_features_help()
        elif help_topic == 'examples':
            return self._format_examples_help()
        else:
            return self._format_general_help(context)
    
    def _format_general_help(self, context: ConversationContext) -> str:
        """Format general help response"""
        intro = self._select_phrase(
            self.templates[ResponseTemplate.HELP_GENERAL]['intro_phrases']
        )
        
        help_sections = [
            intro,
            "",
            "🔤 **Text to ASL Translation**",
            "Convert English text to ASL gloss notation and generate videos",
            "Example: 'Translate \"Hello world\" to ASL'",
            "",
            "🎵 **Audio to ASL Translation**", 
            "Process audio files and convert speech to ASL",
            "Example: 'Convert this audio file to ASL'",
            "",
            "📹 **ASL Video Analysis**",
            "Analyze ASL videos and interpret signs back to English",
            "Example: 'What does this ASL video say?'",
            "",
            "💬 **Conversational Context**",
            "I remember our conversation and can build upon previous interactions",
            "Example: 'Show me that last translation again'",
            "",
            "Just tell me what you'd like to translate or analyze, and I'll guide you through the process!"
        ]
        
        return "\n".join(help_sections)
    
    def _format_translation_help(self) -> str:
        """Format translation-specific help"""
        return ("**Translation Help**\n\n"
               "I can help you translate between English and ASL in several ways:\n\n"
               "• **Text to ASL**: Just tell me what text you want to translate\n"
               "  Example: 'Translate \"Good morning\" to ASL'\n"
               "  I'll provide ASL gloss notation and generate video demonstrations\n\n"
               "• **Audio to ASL**: Upload an audio file and I'll transcribe and translate it\n"
               "  Example: 'Process this audio file to ASL'\n"
               "  Supported formats: MP3, WAV, M4A, AAC, OGG\n\n"
               "• **ASL to Text**: Upload an ASL video and I'll interpret it to English\n"
               "  Example: 'Analyze this ASL video'\n"
               "  Supported formats: MP4, AVI, MOV, WebM")
    
    def _format_audio_help(self) -> str:
        """Format audio-specific help"""
        return ("**Audio Processing Help**\n\n"
               "I can process audio files and convert speech to ASL:\n\n"
               "📁 **Supported Formats**: MP3, WAV, M4A, AAC, OGG\n"
               "🎯 **Process**: I'll transcribe the speech to text first, then convert to ASL\n"
               "📹 **Output**: You'll get ASL gloss notation and video demonstrations\n"
               "⏱️ **Time**: Processing typically takes 10-30 seconds depending on audio length\n\n"
               "**Example requests:**\n"
               "• 'Translate this audio file to ASL'\n"
               "• 'Convert this recording to sign language'\n"
               "• 'Process this speech and show me the ASL'")
    
    def _format_video_help(self) -> str:
        """Format video-specific help"""
        return ("**ASL Video Analysis Help**\n\n"
               "I can analyze ASL videos and interpret them to English:\n\n"
               "📁 **Supported Formats**: MP4, AVI, MOV, WebM\n"
               "📹 **Input Types**: Uploaded files or live camera streams\n"
               "🎯 **Analysis**: I'll interpret the ASL signs and provide English text\n"
               "📊 **Detail Levels**: I can provide basic or detailed analysis\n\n"
               "**Example requests:**\n"
               "• 'Analyze this ASL video'\n"
               "• 'What does this person signing?'\n"
               "• 'Interpret this sign language video'\n"
               "• 'What is being signed here?'")
    
    def _format_features_help(self) -> str:
        """Format features overview help"""
        return ("**My Capabilities Overview**\n\n"
               "🔤 **Text to ASL Translation**\n"
               "• Convert English text to ASL gloss notation\n"
               "• Generate pose, sign, and avatar videos\n"
               "• Handle complex sentences and phrases\n\n"
               "🎵 **Audio to ASL Translation**\n"
               "• Transcribe speech from audio files\n"
               "• Convert transcribed text to ASL\n"
               "• Support multiple audio formats\n\n"
               "📹 **ASL Video Analysis**\n"
               "• Interpret ASL signs from videos\n"
               "• Support for file uploads and live streams\n"
               "• Provide detailed sign analysis\n\n"
               "💬 **Conversational Context**\n"
               "• Remember our conversation history\n"
               "• Reference previous translations\n"
               "• Provide contextual help and suggestions\n"
               "• Learn from your preferences over time")
    
    def _format_examples_help(self) -> str:
        """Format examples help"""
        return ("**Usage Examples**\n\n"
               "Here are some example requests you can try:\n\n"
               "**Text Translation:**\n"
               "• 'Translate \"How are you today?\" to ASL'\n"
               "• 'Convert this text to sign language: \"Nice to meet you\"'\n"
               "• 'Turn \"Thank you very much\" into ASL video'\n\n"
               "**Audio Processing:**\n"
               "• 'Process this audio file and convert to ASL'\n"
               "• 'Transcribe and translate this recording'\n"
               "• 'Convert this speech to sign language'\n\n"
               "**ASL Analysis:**\n"
               "• 'Analyze this ASL video'\n"
               "• 'What is this person signing?'\n"
               "• 'Interpret this sign language video'\n"
               "• 'What does this signing mean?'\n\n"
               "**Conversation:**\n"
               "• 'Show me that last translation again'\n"
               "• 'Try that again with better quality'\n"
               "• 'What other video formats do you have?'\n"
               "• 'Can you explain the gloss notation?'")
    
    def format_status_response(self, status_info: Dict[str, Any], 
                             context: ConversationContext) -> str:
        """
        Format a status update response
        
        Args:
            status_info: Dictionary containing status information
            context: Current conversation context
            
        Returns:
            str: Formatted status response
        """
        response_parts = []
        
        # Current operations
        current_ops = status_info.get('current_operations', [])
        if current_ops:
            response_parts.append(f"I currently have {len(current_ops)} operations running:")
            for i, op in enumerate(current_ops, 1):
                response_parts.append(f"{i}. {op}")
        else:
            response_parts.append("I don't have any operations currently running.")
        
        # Session information
        if context.session_id:
            session_duration = context.get_session_duration()
            interaction_count = len(context.conversation_history)
            
            response_parts.append(
                f"\n**Session Info:**\n"
                f"• Duration: {session_duration/60:.1f} minutes\n"
                f"• Interactions: {interaction_count}\n"
                f"• Success rate: {100 - context.get_error_rate():.1f}%"
            )
        
        # Recent activity
        if context.last_translation:
            last_type = self._get_input_type_display_name(context.last_translation.input_type)
            response_parts.append(f"• Last translation: {last_type}")
        
        return "\n".join(response_parts)
    
    def format_error_response(self, error: Exception, context: ConversationContext) -> str:
        """
        Format an error response with helpful guidance
        
        Args:
            error: The exception that occurred
            context: Current conversation context
            
        Returns:
            str: Formatted error response
        """
        error_message = str(error)
        user_friendly_error = self._make_error_user_friendly(error_message)
        
        response_parts = [
            "I apologize, but I encountered an issue while processing your request.",
            f"**Issue:** {user_friendly_error}"
        ]
        
        # Add recovery suggestions
        recovery_suggestions = self._generate_generic_recovery_suggestions(error_message)
        if recovery_suggestions:
            response_parts.append(recovery_suggestions)
        
        # Add encouragement
        response_parts.append("Please don't hesitate to try again or ask for help if you need it!")
        
        return "\n\n".join(response_parts)
    
    def _generate_generic_recovery_suggestions(self, error_message: str) -> str:
        """Generate generic recovery suggestions for errors"""
        suggestions = [
            "Try rephrasing your request",
            "Make sure all required information is provided",
            "Check that any uploaded files are in supported formats"
        ]
        
        error_lower = error_message.lower()
        if 'network' in error_lower or 'timeout' in error_lower:
            suggestions.insert(0, "Check your internet connection and try again")
        
        suggestion_list = "\n".join([f"• {suggestion}" for suggestion in suggestions])
        return f"Here are some things you could try:\n{suggestion_list}"
    
    def _get_input_type_display_name(self, input_type: InputType) -> str:
        """Get user-friendly display name for input type"""
        display_names = {
            InputType.TEXT: "text",
            InputType.AUDIO: "audio file",
            InputType.VIDEO: "video",
            InputType.STREAM: "video stream",
            InputType.IMAGE: "image",
            InputType.UNKNOWN: "input"
        }
        return display_names.get(input_type, "input")
    
    def _select_phrase(self, phrases: List[str]) -> str:
        """Select a phrase from a list (for now, just return the first one)"""
        # In a more advanced implementation, this could use randomization
        # or context-based selection for variety
        return phrases[0] if phrases else ""
    
    def _format_error_fallback(self, result: TranslationResult, error: str) -> str:
        """Fallback error response when formatting fails"""
        return (f"I encountered an issue while formatting the response for your "
               f"{self._get_input_type_display_name(result.input_type)} translation. "
               f"The translation may have completed, but I couldn't present it properly. "
               f"Error: {error}")