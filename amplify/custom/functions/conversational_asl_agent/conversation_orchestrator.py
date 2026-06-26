"""
Conversation Orchestrator

This module provides workflow coordination and orchestration for conversational ASL translation,
managing the execution of translation workflows and coordinating between different tools.
"""

import logging
import time
import uuid
from typing import Dict, Any, Optional, Callable, List
from datetime import datetime

try:
    from .data_models import (
        ConversationContext, 
        ConversationIntent, 
        IntentResult,
        TranslationResult,
        TranslationStatus,
        InputType,
        OperationStatus,
        create_text_translation_result,
        create_audio_translation_result,
        create_asl_analysis_result
    )
except ImportError:
    from data_models import (
        ConversationContext, 
        ConversationIntent, 
        IntentResult,
        TranslationResult,
        TranslationStatus,
        InputType,
        OperationStatus,
        create_text_translation_result,
        create_audio_translation_result,
        create_asl_analysis_result
    )
try:
    from .progress_tracker import ProgressTracker, OperationQueue
    from .memory_manager import ConversationMemoryManager
except ImportError:
    from progress_tracker import ProgressTracker, OperationQueue
    from memory_manager import ConversationMemoryManager

logger = logging.getLogger(__name__)

class ConversationOrchestrator:
    """
    Orchestrates translation workflows and manages execution of translation operations
    
    This class coordinates calls to existing translation tools, manages error handling
    and fallback strategies, provides progress updates, and handles retry logic.
    """
    
    def __init__(self, memory_manager: Optional[ConversationMemoryManager] = None):
        """Initialize the conversation orchestrator"""
        self.memory_manager = memory_manager or ConversationMemoryManager()
        self.progress_tracker = ProgressTracker(self.memory_manager)
        self.operation_queue = OperationQueue(self.memory_manager)
        
        # Import existing tools (will be set up during initialization)
        self.tools = {}
        self._setup_tools()
        
        logger.info("ConversationOrchestrator initialized with progress tracking and queuing")
    
    def _setup_tools(self):
        """Set up references to existing translation tools"""
        try:
            # Import tools from the SignLanguageAgent context
            import sys
            from pathlib import Path
            
            # Add parent directory to path for imports
            parent_dir = Path(__file__).parent.parent
            sys.path.insert(0, str(parent_dir))
            
            # Import text2gloss tool
            try:
                from text2gloss_handler import text_to_asl_gloss
                self.tools['text_to_asl_gloss'] = text_to_asl_gloss
                logger.info("Successfully imported text_to_asl_gloss tool")
            except ImportError as e:
                logger.warning(f"Failed to import text2gloss tool: {e}")
                self.tools['text_to_asl_gloss'] = self._create_placeholder_text_tool()
            
            # Import gloss2pose tool
            try:
                from gloss2pose_handler import gloss_to_video
                self.tools['gloss_to_video'] = gloss_to_video
                logger.info("Successfully imported gloss_to_video tool")
            except ImportError as e:
                logger.warning(f"Failed to import gloss2pose tool: {e}")
                self.tools['gloss_to_video'] = self._create_placeholder_video_tool()
            
            # Import audio processing tools
            try:
                from audio_processing_handler import process_audio_input, get_transcription_result
                self.tools['process_audio_input'] = process_audio_input
                self.tools['get_transcription_result'] = get_transcription_result
                logger.info("Successfully imported audio processing tools")
            except ImportError as e:
                logger.warning(f"Failed to import audio processing tools: {e}")
                self.tools['process_audio_input'] = self._create_placeholder_audio_tool()
                self.tools['get_transcription_result'] = self._create_placeholder_transcription_tool()
            
            # Import ASL analysis tools
            try:
                from asl_analysis_handler import analyze_asl_video_stream, analyze_asl_from_s3
                self.tools['analyze_asl_video_stream'] = analyze_asl_video_stream
                self.tools['analyze_asl_from_s3'] = analyze_asl_from_s3
                logger.info("Successfully imported ASL analysis tools")
            except ImportError as e:
                logger.warning(f"Failed to import ASL analysis tools: {e}")
                self.tools['analyze_asl_video_stream'] = self._create_placeholder_stream_tool()
                self.tools['analyze_asl_from_s3'] = self._create_placeholder_s3_tool()
                
        except Exception as e:
            logger.error(f"Error setting up tools: {e}")
            # Create all placeholder tools
            self.tools = {
                'text_to_asl_gloss': self._create_placeholder_text_tool(),
                'gloss_to_video': self._create_placeholder_video_tool(),
                'process_audio_input': self._create_placeholder_audio_tool(),
                'get_transcription_result': self._create_placeholder_transcription_tool(),
                'analyze_asl_video_stream': self._create_placeholder_stream_tool(),
                'analyze_asl_from_s3': self._create_placeholder_s3_tool()
            }
    
    def _create_placeholder_text_tool(self):
        """Create placeholder text-to-gloss tool"""
        def placeholder_text_to_gloss(text: str) -> str:
            logger.warning("Using placeholder text_to_asl_gloss tool")
            return f"PLACEHOLDER_GLOSS_FOR_{text.upper().replace(' ', '_')}"
        return placeholder_text_to_gloss
    
    def _create_placeholder_video_tool(self):
        """Create placeholder gloss-to-video tool"""
        def placeholder_gloss_to_video(gloss_sentence: str, text: str = None, pose_only: bool = False, pre_sign: bool = True) -> dict:
            logger.warning("Using placeholder gloss_to_video tool")
            return {
                'PoseURL': 'https://placeholder-pose-url.com',
                'SignURL': 'https://placeholder-sign-url.com',
                'AvatarURL': 'https://placeholder-avatar-url.com',
                'Gloss': gloss_sentence,
                'Text': text
            }
        return placeholder_gloss_to_video
    
    def _create_placeholder_audio_tool(self):
        """Create placeholder audio processing tool"""
        def placeholder_process_audio(bucket_name: str, key_name: str) -> str:
            logger.warning("Using placeholder process_audio_input tool")
            return f"PLACEHOLDER_TRANSCRIPTION_FOR_{bucket_name}_{key_name}"
        return placeholder_process_audio
    
    def _create_placeholder_transcription_tool(self):
        """Create placeholder transcription result tool"""
        def placeholder_get_transcription(job_name: str) -> str:
            logger.warning("Using placeholder get_transcription_result tool")
            return f"PLACEHOLDER_TRANSCRIPTION_RESULT_FOR_{job_name}"
        return placeholder_get_transcription
    
    def _create_placeholder_stream_tool(self):
        """Create placeholder stream analysis tool"""
        def placeholder_analyze_stream(stream_name: str) -> str:
            logger.warning("Using placeholder analyze_asl_video_stream tool")
            return f"PLACEHOLDER_ASL_ANALYSIS_FOR_STREAM_{stream_name}"
        return placeholder_analyze_stream
    
    def _create_placeholder_s3_tool(self):
        """Create placeholder S3 analysis tool"""
        def placeholder_analyze_s3(bucket_name: str, key_name: str) -> str:
            logger.warning("Using placeholder analyze_asl_from_s3 tool")
            return f"PLACEHOLDER_ASL_ANALYSIS_FOR_{bucket_name}_{key_name}"
        return placeholder_analyze_s3
    
    def execute_translation_flow(self, intent_result: IntentResult, 
                                context: ConversationContext,
                                progress_callback: Optional[Callable[[float, str], None]] = None) -> TranslationResult:
        """
        Execute translation flow based on intent classification result
        
        Args:
            intent_result: Intent classification result with parameters
            context: Current conversation context
            progress_callback: Optional callback for progress updates
        
        Returns:
            TranslationResult: Result of the translation workflow
        """
        try:
            operation_id = f"op_{int(time.time())}_{str(uuid.uuid4())[:8]}"
            start_time = time.time()
            
            # Start operation tracking with progress tracker
            operation_status = self.progress_tracker.start_operation(
                operation_id=operation_id,
                operation_type=intent_result.intent.value,
                session_id=context.session_id,
                estimated_duration=self._estimate_operation_duration(intent_result.intent)
            )
            
            if progress_callback:
                self.progress_tracker.add_progress_callback(operation_id, progress_callback)
            
            logger.info(f"Starting translation flow for intent: {intent_result.intent.value}")
            
            # Route to appropriate workflow handler
            if intent_result.intent == ConversationIntent.TEXT_TO_ASL:
                result = self.handle_text_to_asl_flow(
                    intent_result.parameters, context, operation_id
                )
            elif intent_result.intent == ConversationIntent.AUDIO_TO_ASL:
                result = self.handle_audio_to_asl_flow(
                    intent_result.parameters, context, operation_id
                )
            elif intent_result.intent == ConversationIntent.ASL_TO_TEXT:
                result = self.handle_asl_to_text_flow(
                    intent_result.parameters, context, operation_id
                )
            else:
                # Handle non-translation intents
                result = self._handle_non_translation_intent(
                    intent_result, context, operation_id
                )
            
            # Calculate processing time
            processing_time = time.time() - start_time
            result.processing_time = processing_time
            
            # Complete operation tracking
            self.progress_tracker.complete_operation(
                operation_id=operation_id,
                result=result,
                session_id=context.session_id
            )
            
            logger.info(f"Translation flow completed in {processing_time:.2f}s")
            return result
            
        except Exception as e:
            error_msg = f"Translation flow failed: {str(e)}"
            logger.error(error_msg, exc_info=True)
            
            # Create error result
            result = TranslationResult(
                input_text=intent_result.parameters.get('text', 'Unknown input'),
                input_type=intent_result.input_type,
                success=False,
                error_message=error_msg,
                status=TranslationStatus.FAILED,
                processing_time=time.time() - start_time if 'start_time' in locals() else 0.0
            )
            
            # Mark operation as failed if it exists
            if 'operation_id' in locals():
                self.progress_tracker.fail_operation(
                    operation_id=operation_id,
                    error_message=error_msg,
                    session_id=context.session_id if 'context' in locals() else None
                )
            
            return result
    
    def handle_text_to_asl_flow(self, parameters: Dict[str, Any], 
                               context: ConversationContext,
                               operation_id: str) -> TranslationResult:
        """
        Handle text-to-ASL translation workflow
        
        Args:
            parameters: Intent parameters containing text to translate
            context: Conversation context
            operation_id: Operation identifier for progress tracking
        
        Returns:
            TranslationResult: Translation result
        """
        try:
            text_content = parameters.get('text')
            if not text_content:
                raise ValueError("No text content provided for translation")
            
            logger.info(f"Starting text-to-ASL workflow for: {text_content[:50]}...")
            
            # Update progress: Starting text-to-gloss conversion
            self.progress_tracker.update_progress(
                operation_id, 0.1, "Converting text to ASL gloss", context.session_id
            )
            
            # Step 1: Convert text to ASL gloss
            gloss_result = self.tools['text_to_asl_gloss'](text_content)
            
            if not gloss_result:
                raise ValueError("Failed to generate ASL gloss from text")
            
            logger.info(f"Generated gloss: {gloss_result}")
            
            # Update progress: Starting video generation
            self.progress_tracker.update_progress(
                operation_id, 0.5, "Generating ASL videos from gloss", context.session_id
            )
            
            # Step 2: Generate videos from gloss
            video_result = self.tools['gloss_to_video'](
                gloss_sentence=gloss_result,
                text=text_content,
                pose_only=False,
                pre_sign=True
            )
            
            if not video_result or not isinstance(video_result, dict):
                raise ValueError("Failed to generate videos from gloss")
            
            # Extract video URLs
            video_urls = {}
            for url_key in ['PoseURL', 'SignURL', 'AvatarURL']:
                if url_key in video_result and video_result[url_key]:
                    video_urls[url_key.replace('URL', '').lower()] = video_result[url_key]
            
            logger.info(f"Generated {len(video_urls)} video URLs")
            
            # Update progress: Completed
            self.progress_tracker.update_progress(
                operation_id, 1.0, "Translation completed successfully", context.session_id
            )
            
            # Create successful result
            return create_text_translation_result(
                input_text=text_content,
                gloss=gloss_result,
                video_urls=video_urls,
                success=True
            )
            
        except Exception as e:
            error_msg = f"Text-to-ASL workflow failed: {str(e)}"
            logger.error(error_msg, exc_info=True)
            
            return TranslationResult(
                input_text=parameters.get('text', 'Unknown text'),
                input_type=InputType.TEXT,
                success=False,
                error_message=error_msg,
                status=TranslationStatus.FAILED
            )  
  
    def handle_audio_to_asl_flow(self, parameters: Dict[str, Any], 
                                context: ConversationContext,
                                operation_id: str) -> TranslationResult:
        """
        Handle audio-to-ASL translation workflow
        
        Args:
            parameters: Intent parameters containing audio file information
            context: Conversation context
            operation_id: Operation identifier for progress tracking
        
        Returns:
            TranslationResult: Translation result
        """
        try:
            # Extract audio parameters
            bucket_name = parameters.get('bucket_name') or parameters.get('BucketName')
            key_name = parameters.get('key_name') or parameters.get('KeyName')
            
            if not bucket_name or not key_name:
                raise ValueError("Missing required parameters: bucket_name and key_name")
            
            logger.info(f"Starting audio-to-ASL workflow for: {bucket_name}/{key_name}")
            
            # Update progress: Starting audio processing
            self.progress_tracker.update_progress(
                operation_id, 0.1, "Processing audio file", context.session_id
            )
            
            # Step 1: Process audio and get transcription
            transcription_result = self.tools['process_audio_input'](bucket_name, key_name)
            
            if not transcription_result:
                raise ValueError("Failed to transcribe audio")
            
            # Handle case where transcription returns a job name (async processing)
            if isinstance(transcription_result, str) and transcription_result.startswith('transcription-job-'):
                # Update progress: Waiting for transcription
                self.progress_tracker.update_progress(
                    operation_id, 0.3, "Waiting for audio transcription to complete", context.session_id
                )
                
                # Get the actual transcription result
                transcribed_text = self.tools['get_transcription_result'](transcription_result)
            else:
                transcribed_text = transcription_result
            
            if not transcribed_text:
                raise ValueError("Failed to get transcription result")
            
            logger.info(f"Transcribed text: {transcribed_text}")
            
            # Update progress: Converting to gloss
            self.progress_tracker.update_progress(
                operation_id, 0.5, "Converting transcribed text to ASL gloss", context.session_id
            )
            
            # Step 2: Convert transcribed text to ASL gloss
            gloss_result = self.tools['text_to_asl_gloss'](transcribed_text)
            
            if not gloss_result:
                raise ValueError("Failed to generate ASL gloss from transcribed text")
            
            logger.info(f"Generated gloss: {gloss_result}")
            
            # Update progress: Generating videos
            self.progress_tracker.update_progress(
                operation_id, 0.7, "Generating ASL videos from gloss", context.session_id
            )
            
            # Step 3: Generate videos from gloss
            video_result = self.tools['gloss_to_video'](
                gloss_sentence=gloss_result,
                text=transcribed_text,
                pose_only=False,
                pre_sign=True
            )
            
            if not video_result or not isinstance(video_result, dict):
                raise ValueError("Failed to generate videos from gloss")
            
            # Extract video URLs
            video_urls = {}
            for url_key in ['PoseURL', 'SignURL', 'AvatarURL']:
                if url_key in video_result and video_result[url_key]:
                    video_urls[url_key.replace('URL', '').lower()] = video_result[url_key]
            
            logger.info(f"Generated {len(video_urls)} video URLs")
            
            # Update progress: Completed
            self.progress_tracker.update_progress(
                operation_id, 1.0, "Audio-to-ASL translation completed successfully", context.session_id
            )
            
            # Create successful result
            return create_audio_translation_result(
                input_text=f"{bucket_name}/{key_name}",
                transcribed_text=transcribed_text,
                gloss=gloss_result,
                video_urls=video_urls,
                success=True
            )
            
        except Exception as e:
            error_msg = f"Audio-to-ASL workflow failed: {str(e)}"
            logger.error(error_msg, exc_info=True)
            
            return TranslationResult(
                input_text=f"{parameters.get('bucket_name', 'unknown')}/{parameters.get('key_name', 'unknown')}",
                input_type=InputType.AUDIO,
                success=False,
                error_message=error_msg,
                status=TranslationStatus.FAILED
            )
    
    def handle_asl_to_text_flow(self, parameters: Dict[str, Any], 
                               context: ConversationContext,
                               operation_id: str) -> TranslationResult:
        """
        Handle ASL-to-text analysis workflow
        
        Args:
            parameters: Intent parameters containing video/stream information
            context: Conversation context
            operation_id: Operation identifier for progress tracking
        
        Returns:
            TranslationResult: Translation result
        """
        try:
            # Determine input type and parameters
            stream_name = parameters.get('stream_name') or parameters.get('StreamName')
            bucket_name = parameters.get('bucket_name') or parameters.get('BucketName')
            key_name = parameters.get('key_name') or parameters.get('KeyName')
            
            if stream_name:
                # Stream-based analysis
                logger.info(f"Starting ASL stream analysis for: {stream_name}")
                input_reference = stream_name
                input_type = InputType.STREAM
                
                # Update progress: Starting stream analysis
                self.progress_tracker.update_progress(
                    operation_id, 0.2, "Analyzing ASL video stream", context.session_id
                )
                
                # Analyze ASL from video stream
                analysis_result = self.tools['analyze_asl_video_stream'](stream_name)
                
            elif bucket_name and key_name:
                # S3-based analysis
                logger.info(f"Starting ASL S3 analysis for: {bucket_name}/{key_name}")
                input_reference = f"{bucket_name}/{key_name}"
                input_type = InputType.VIDEO
                
                # Update progress: Starting S3 analysis
                self.progress_tracker.update_progress(
                    operation_id, 0.2, "Analyzing ASL video from S3", context.session_id
                )
                
                # Analyze ASL from S3
                analysis_result = self.tools['analyze_asl_from_s3'](bucket_name, key_name)
                
            else:
                raise ValueError("Missing required parameters: either stream_name or bucket_name/key_name")
            
            if not analysis_result:
                raise ValueError("Failed to analyze ASL video")
            
            logger.info(f"ASL analysis result: {analysis_result}")
            
            # Update progress: Completed
            self.progress_tracker.update_progress(
                operation_id, 1.0, "ASL analysis completed successfully", context.session_id
            )
            
            # Create successful result
            return create_asl_analysis_result(
                input_reference=input_reference,
                interpreted_text=analysis_result,
                input_type=input_type,
                success=True
            )
            
        except Exception as e:
            error_msg = f"ASL-to-text workflow failed: {str(e)}"
            logger.error(error_msg, exc_info=True)
            
            # Determine input reference for error result
            if parameters.get('stream_name'):
                input_ref = parameters['stream_name']
                input_type = InputType.STREAM
            else:
                input_ref = f"{parameters.get('bucket_name', 'unknown')}/{parameters.get('key_name', 'unknown')}"
                input_type = InputType.VIDEO
            
            return TranslationResult(
                input_text=input_ref,
                input_type=input_type,
                success=False,
                error_message=error_msg,
                status=TranslationStatus.FAILED
            )
    
    def _handle_non_translation_intent(self, intent_result: IntentResult, 
                                     context: ConversationContext,
                                     operation_id: str) -> TranslationResult:
        """
        Handle non-translation intents (help, status, etc.)
        
        Args:
            intent_result: Intent classification result
            context: Conversation context
            operation_id: Operation identifier
        
        Returns:
            TranslationResult: Result indicating the intent was handled
        """
        intent = intent_result.intent
        
        # Create a result indicating this was a non-translation intent
        result = TranslationResult(
            input_text=intent_result.parameters.get('original_input', 'Non-translation request'),
            input_type=intent_result.input_type,
            success=True,
            status=TranslationStatus.COMPLETED,
            metadata={'intent': intent.value, 'handled_by': 'orchestrator'}
        )
        
        if intent == ConversationIntent.HELP_REQUEST:
            result.interpreted_text = "Help request handled by conversation system"
        elif intent == ConversationIntent.STATUS_CHECK:
            result.interpreted_text = "Status check handled by conversation system"
        elif intent == ConversationIntent.RETRY_REQUEST:
            result.interpreted_text = "Retry request handled by conversation system"
        elif intent == ConversationIntent.CONTEXT_REFERENCE:
            result.interpreted_text = "Context reference handled by conversation system"
        elif intent == ConversationIntent.GREETING:
            result.interpreted_text = "Greeting handled by conversation system"
        else:
            result.interpreted_text = f"Intent {intent.value} handled by conversation system"
        
        return result
    
    def _estimate_operation_duration(self, intent: ConversationIntent) -> float:
        """
        Estimate operation duration based on intent type
        
        Args:
            intent: Conversation intent
        
        Returns:
            float: Estimated duration in seconds
        """
        duration_estimates = {
            ConversationIntent.TEXT_TO_ASL: 5.0,
            ConversationIntent.AUDIO_TO_ASL: 15.0,  # Longer due to transcription
            ConversationIntent.ASL_TO_TEXT: 10.0,
            ConversationIntent.HELP_REQUEST: 1.0,
            ConversationIntent.STATUS_CHECK: 0.5,
            ConversationIntent.RETRY_REQUEST: 5.0,
            ConversationIntent.CONTEXT_REFERENCE: 1.0,
            ConversationIntent.GREETING: 0.5
        }
        
        return duration_estimates.get(intent, 5.0)  # Default to 5 seconds
    
    def get_operation_status(self, operation_id: str, session_id: Optional[str] = None) -> Optional[OperationStatus]:
        """
        Get status of an operation
        
        Args:
            operation_id: Operation identifier
            session_id: Optional session ID for persistent lookup
        
        Returns:
            OperationStatus or None if operation not found
        """
        return self.progress_tracker.get_operation_status(operation_id, session_id)
    
    def get_active_operations(self, session_id: str) -> List[OperationStatus]:
        """
        Get list of all active operations for a session
        
        Args:
            session_id: Session identifier
        
        Returns:
            List of active operation statuses
        """
        return self.progress_tracker.get_active_operations(session_id)
    
    def get_recent_status_updates(self, session_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get recent status updates for a session
        
        Args:
            session_id: Session identifier
            limit: Maximum number of updates to return
        
        Returns:
            List of recent status updates
        """
        return self.progress_tracker.get_recent_status_updates(session_id, limit)
    
    def get_queue_status(self, session_id: str) -> Dict[str, Any]:
        """
        Get operation queue status for a session
        
        Args:
            session_id: Session identifier
        
        Returns:
            Dict containing queue status information
        """
        return self.operation_queue.get_queue_status(session_id)
    
    def get_tool_availability(self) -> Dict[str, bool]:
        """
        Check availability of translation tools
        
        Returns:
            Dict mapping tool names to availability status
        """
        availability = {}
        
        for tool_name, tool_func in self.tools.items():
            try:
                # Check if tool is a placeholder (simple heuristic)
                is_placeholder = (
                    hasattr(tool_func, '__name__') and 
                    'placeholder' in tool_func.__name__.lower()
                )
                availability[tool_name] = not is_placeholder
            except Exception:
                availability[tool_name] = False
        
        return availability
    
    def get_orchestrator_status(self) -> Dict[str, Any]:
        """
        Get overall orchestrator status and metrics
        
        Returns:
            Dict containing orchestrator status information
        """
        return {
            'active_operations_count': len(self.active_operations),
            'active_operations': [op.operation_id for op in self.active_operations.values()],
            'tool_availability': self.get_tool_availability(),
            'tools_loaded': list(self.tools.keys()),
            'timestamp': datetime.now().isoformat()
        }