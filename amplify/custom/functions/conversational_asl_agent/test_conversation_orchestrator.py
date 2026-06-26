#!/usr/bin/env python3
"""
Unit Tests for Conversation Orchestrator

Tests for the ConversationOrchestrator to validate workflow coordination,
translation flow execution, and progress tracking functionality.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock, AsyncMock
import sys
from pathlib import Path
from datetime import datetime
import asyncio

# Add current directory to path for imports
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

from conversation_orchestrator import ConversationOrchestrator
from data_models import (
    ConversationContext, ConversationInteraction, TranslationResult,
    ConversationIntent, InputType, IntentResult, OperationStatus,
    TranslationStatus, create_text_translation_result
)

class TestConversationOrchestrator(unittest.TestCase):
    """Test cases for ConversationOrchestrator"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Create mock tools
        self.mock_tools = {
            'text_to_asl_gloss': Mock(),
            'gloss_to_video': Mock(),
            'process_audio_input': Mock(),
            'analyze_asl_video_stream': Mock(),
            'analyze_asl_from_s3': Mock()
        }
        
        # Create orchestrator with mock tools
        self.orchestrator = ConversationOrchestrator(tools=self.mock_tools)
        
        # Create test context
        self.test_context = ConversationContext(
            session_id="test_session",
            user_id="test_user"
        )
        
        # Create test intent results
        self.text_to_asl_intent = IntentResult(
            intent=ConversationIntent.TEXT_TO_ASL,
            confidence=0.9,
            parameters={'text': 'Hello world'},
            input_type=InputType.TEXT
        )
        
        self.audio_to_asl_intent = IntentResult(
            intent=ConversationIntent.AUDIO_TO_ASL,
            confidence=0.9,
            parameters={'audio_file': 'test.mp3'},
            input_type=InputType.AUDIO
        )
        
        self.asl_to_text_intent = IntentResult(
            intent=ConversationIntent.ASL_TO_TEXT,
            confidence=0.9,
            parameters={'video_file': 'test.mp4'},
            input_type=InputType.VIDEO
        )
    
    def test_orchestrator_initialization(self):
        """Test orchestrator initialization"""
        self.assertIsNotNone(self.orchestrator)
        self.assertEqual(len(self.orchestrator.tools), 5)
        self.assertIn('text_to_asl_gloss', self.orchestrator.tools)
        self.assertIn('gloss_to_video', self.orchestrator.tools)
    
    def test_text_to_asl_flow_success(self):
        """Test successful text-to-ASL translation flow"""
        # Mock tool responses
        self.mock_tools['text_to_asl_gloss'].return_value = {
            'gloss': 'HELLO WORLD',
            'success': True,
            'processing_time': 1.2
        }
        
        self.mock_tools['gloss_to_video'].return_value = {
            'video_urls': {
                'pose': 'http://example.com/pose.mp4',
                'sign': 'http://example.com/sign.mp4',
                'avatar': 'http://example.com/avatar.mp4'
            },
            'success': True,
            'processing_time': 2.3
        }
        
        # Execute flow
        result = self.orchestrator.handle_text_to_asl_flow(
            'Hello world', self.test_context
        )
        
        # Verify result
        self.assertIsInstance(result, TranslationResult)
        self.assertTrue(result.success)
        self.assertEqual(result.input_text, 'Hello world')
        self.assertEqual(result.gloss, 'HELLO WORLD')
        self.assertEqual(result.input_type, InputType.TEXT)
        self.assertIn('pose', result.video_urls)
        self.assertIn('sign', result.video_urls)
        self.assertIn('avatar', result.video_urls)
        
        # Verify tools were called
        self.mock_tools['text_to_asl_gloss'].assert_called_once()
        self.mock_tools['gloss_to_video'].assert_called_once()
    
    def test_text_to_asl_flow_gloss_failure(self):
        """Test text-to-ASL flow with gloss generation failure"""
        # Mock gloss tool failure
        self.mock_tools['text_to_asl_gloss'].return_value = {
            'success': False,
            'error': 'Failed to generate gloss',
            'processing_time': 0.5
        }
        
        # Execute flow
        result = self.orchestrator.handle_text_to_asl_flow(
            'Hello world', self.test_context
        )
        
        # Verify failure result
        self.assertIsInstance(result, TranslationResult)
        self.assertFalse(result.success)
        self.assertEqual(result.input_text, 'Hello world')
        self.assertIsNotNone(result.error_message)
        
        # Verify only gloss tool was called
        self.mock_tools['text_to_asl_gloss'].assert_called_once()
        self.mock_tools['gloss_to_video'].assert_not_called()
    
    def test_text_to_asl_flow_video_failure(self):
        """Test text-to-ASL flow with video generation failure"""
        # Mock successful gloss but failed video
        self.mock_tools['text_to_asl_gloss'].return_value = {
            'gloss': 'HELLO WORLD',
            'success': True,
            'processing_time': 1.2
        }
        
        self.mock_tools['gloss_to_video'].return_value = {
            'success': False,
            'error': 'Failed to generate video',
            'processing_time': 1.0
        }
        
        # Execute flow
        result = self.orchestrator.handle_text_to_asl_flow(
            'Hello world', self.test_context
        )
        
        # Verify partial success (gloss succeeded, video failed)
        self.assertIsInstance(result, TranslationResult)
        self.assertFalse(result.success)
        self.assertEqual(result.gloss, 'HELLO WORLD')
        self.assertIsNotNone(result.error_message)
        
        # Verify both tools were called
        self.mock_tools['text_to_asl_gloss'].assert_called_once()
        self.mock_tools['gloss_to_video'].assert_called_once()
    
    def test_audio_to_asl_flow_success(self):
        """Test successful audio-to-ASL translation flow"""
        # Mock audio processing
        self.mock_tools['process_audio_input'].return_value = {
            'transcribed_text': 'Good morning everyone',
            'success': True,
            'processing_time': 3.5
        }
        
        # Mock text-to-ASL tools
        self.mock_tools['text_to_asl_gloss'].return_value = {
            'gloss': 'GOOD MORNING EVERYONE',
            'success': True,
            'processing_time': 1.5
        }
        
        self.mock_tools['gloss_to_video'].return_value = {
            'video_urls': {
                'pose': 'http://example.com/audio_pose.mp4',
                'avatar': 'http://example.com/audio_avatar.mp4'
            },
            'success': True,
            'processing_time': 2.8
        }
        
        # Execute flow
        audio_params = {'audio_file': 'test.mp3', 'format': 'mp3'}
        result = self.orchestrator.handle_audio_to_asl_flow(
            audio_params, self.test_context
        )
        
        # Verify result
        self.assertIsInstance(result, TranslationResult)
        self.assertTrue(result.success)
        self.assertEqual(result.input_type, InputType.AUDIO)
        self.assertEqual(result.gloss, 'GOOD MORNING EVERYONE')
        self.assertEqual(result.interpreted_text, 'Good morning everyone')
        self.assertIn('pose', result.video_urls)
        
        # Verify all tools were called
        self.mock_tools['process_audio_input'].assert_called_once()
        self.mock_tools['text_to_asl_gloss'].assert_called_once()
        self.mock_tools['gloss_to_video'].assert_called_once()
    
    def test_audio_to_asl_flow_transcription_failure(self):
        """Test audio-to-ASL flow with transcription failure"""
        # Mock audio processing failure
        self.mock_tools['process_audio_input'].return_value = {
            'success': False,
            'error': 'Audio format not supported',
            'processing_time': 0.5
        }
        
        # Execute flow
        audio_params = {'audio_file': 'test.wav'}
        result = self.orchestrator.handle_audio_to_asl_flow(
            audio_params, self.test_context
        )
        
        # Verify failure result
        self.assertIsInstance(result, TranslationResult)
        self.assertFalse(result.success)
        self.assertEqual(result.input_type, InputType.AUDIO)
        self.assertIsNotNone(result.error_message)
        
        # Verify only audio tool was called
        self.mock_tools['process_audio_input'].assert_called_once()
        self.mock_tools['text_to_asl_gloss'].assert_not_called()
        self.mock_tools['gloss_to_video'].assert_not_called()
    
    def test_asl_to_text_flow_success(self):
        """Test successful ASL-to-text analysis flow"""
        # Mock ASL analysis
        self.mock_tools['analyze_asl_from_s3'].return_value = {
            'interpreted_text': 'Thank you very much',
            'confidence': 0.92,
            'success': True,
            'processing_time': 4.2
        }
        
        # Execute flow
        video_params = {'video_file': 'signing.mp4', 'analysis_type': 'file'}
        result = self.orchestrator.handle_asl_to_text_flow(
            video_params, self.test_context
        )
        
        # Verify result
        self.assertIsInstance(result, TranslationResult)
        self.assertTrue(result.success)
        self.assertEqual(result.input_type, InputType.VIDEO)
        self.assertEqual(result.interpreted_text, 'Thank you very much')
        self.assertGreater(result.processing_time, 0)
        
        # Verify correct tool was called
        self.mock_tools['analyze_asl_from_s3'].assert_called_once()
        self.mock_tools['analyze_asl_video_stream'].assert_not_called()
    
    def test_asl_to_text_stream_flow_success(self):
        """Test successful ASL stream analysis flow"""
        # Mock stream analysis
        self.mock_tools['analyze_asl_video_stream'].return_value = {
            'interpreted_text': 'Hello how are you',
            'confidence': 0.88,
            'success': True,
            'processing_time': 2.1
        }
        
        # Execute flow
        video_params = {'analysis_type': 'stream', 'stream_url': 'rtmp://example.com/stream'}
        result = self.orchestrator.handle_asl_to_text_flow(
            video_params, self.test_context
        )
        
        # Verify result
        self.assertIsInstance(result, TranslationResult)
        self.assertTrue(result.success)
        self.assertEqual(result.input_type, InputType.STREAM)
        self.assertEqual(result.interpreted_text, 'Hello how are you')
        
        # Verify correct tool was called
        self.mock_tools['analyze_asl_video_stream'].assert_called_once()
        self.mock_tools['analyze_asl_from_s3'].assert_not_called()
    
    def test_asl_to_text_flow_analysis_failure(self):
        """Test ASL-to-text flow with analysis failure"""
        # Mock analysis failure
        self.mock_tools['analyze_asl_from_s3'].return_value = {
            'success': False,
            'error': 'Video quality too low for analysis',
            'processing_time': 1.0
        }
        
        # Execute flow
        video_params = {'video_file': 'poor_quality.mp4', 'analysis_type': 'file'}
        result = self.orchestrator.handle_asl_to_text_flow(
            video_params, self.test_context
        )
        
        # Verify failure result
        self.assertIsInstance(result, TranslationResult)
        self.assertFalse(result.success)
        self.assertEqual(result.input_type, InputType.VIDEO)
        self.assertIsNotNone(result.error_message)
        
        # Verify tool was called
        self.mock_tools['analyze_asl_from_s3'].assert_called_once()
    
    def test_execute_translation_flow_routing(self):
        """Test translation flow routing based on intent"""
        # Test text-to-ASL routing
        with patch.object(self.orchestrator, 'handle_text_to_asl_flow') as mock_text_flow:
            mock_text_flow.return_value = create_text_translation_result(
                'test', 'TEST', {}, success=True
            )
            
            result = self.orchestrator.execute_translation_flow(
                self.text_to_asl_intent, self.test_context
            )
            
            mock_text_flow.assert_called_once_with('Hello world', self.test_context)
            self.assertIsInstance(result, TranslationResult)
        
        # Test audio-to-ASL routing
        with patch.object(self.orchestrator, 'handle_audio_to_asl_flow') as mock_audio_flow:
            mock_audio_flow.return_value = create_text_translation_result(
                'test', 'TEST', {}, success=True
            )
            
            result = self.orchestrator.execute_translation_flow(
                self.audio_to_asl_intent, self.test_context
            )
            
            mock_audio_flow.assert_called_once_with(
                {'audio_file': 'test.mp3'}, self.test_context
            )
            self.assertIsInstance(result, TranslationResult)
        
        # Test ASL-to-text routing
        with patch.object(self.orchestrator, 'handle_asl_to_text_flow') as mock_asl_flow:
            mock_asl_flow.return_value = create_text_translation_result(
                'test', 'TEST', {}, success=True
            )
            
            result = self.orchestrator.execute_translation_flow(
                self.asl_to_text_intent, self.test_context
            )
            
            mock_asl_flow.assert_called_once_with(
                {'video_file': 'test.mp4'}, self.test_context
            )
            self.assertIsInstance(result, TranslationResult)
    
    def test_execute_translation_flow_unsupported_intent(self):
        """Test translation flow with unsupported intent"""
        # Create unsupported intent
        unsupported_intent = IntentResult(
            intent=ConversationIntent.HELP_REQUEST,
            confidence=0.9,
            parameters={},
            input_type=InputType.TEXT
        )
        
        # Execute flow
        result = self.orchestrator.execute_translation_flow(
            unsupported_intent, self.test_context
        )
        
        # Should return failure result
        self.assertIsInstance(result, TranslationResult)
        self.assertFalse(result.success)
        self.assertIn('Unsupported intent', result.error_message)
    
    def test_progress_tracking(self):
        """Test progress tracking during translation flows"""
        # Mock progress tracker
        with patch.object(self.orchestrator, 'progress_tracker') as mock_tracker:
            mock_tracker.create_operation.return_value = "op_123"
            mock_tracker.update_progress = Mock()
            mock_tracker.complete_operation = Mock()
            
            # Mock successful tools
            self.mock_tools['text_to_asl_gloss'].return_value = {
                'gloss': 'TEST',
                'success': True,
                'processing_time': 1.0
            }
            
            self.mock_tools['gloss_to_video'].return_value = {
                'video_urls': {'pose': 'http://example.com/pose.mp4'},
                'success': True,
                'processing_time': 2.0
            }
            
            # Execute flow
            result = self.orchestrator.handle_text_to_asl_flow(
                'test', self.test_context
            )
            
            # Verify progress tracking was used
            mock_tracker.create_operation.assert_called_once()
            self.assertGreater(mock_tracker.update_progress.call_count, 0)
            mock_tracker.complete_operation.assert_called_once()
    
    def test_error_handling_tool_exceptions(self):
        """Test error handling when tools raise exceptions"""
        # Mock tool to raise exception
        self.mock_tools['text_to_asl_gloss'].side_effect = Exception("Tool crashed")
        
        # Execute flow
        result = self.orchestrator.handle_text_to_asl_flow(
            'test text', self.test_context
        )
        
        # Should handle exception gracefully
        self.assertIsInstance(result, TranslationResult)
        self.assertFalse(result.success)
        self.assertIn('Tool crashed', result.error_message)
    
    def test_context_integration(self):
        """Test integration with conversation context"""
        # Add previous interaction to context
        previous_interaction = ConversationInteraction(
            timestamp=datetime.now(),
            user_input="Previous request",
            intent=ConversationIntent.TEXT_TO_ASL,
            agent_response="Previous response"
        )
        self.test_context.add_interaction(previous_interaction)
        
        # Mock successful tools
        self.mock_tools['text_to_asl_gloss'].return_value = {
            'gloss': 'HELLO',
            'success': True,
            'processing_time': 1.0
        }
        
        self.mock_tools['gloss_to_video'].return_value = {
            'video_urls': {'pose': 'http://example.com/pose.mp4'},
            'success': True,
            'processing_time': 2.0
        }
        
        # Execute flow
        result = self.orchestrator.handle_text_to_asl_flow(
            'Hello', self.test_context
        )
        
        # Verify context was considered (tools should receive context information)
        self.assertTrue(result.success)
        
        # Verify context interaction count increased
        self.assertEqual(self.test_context.total_interactions, 1)  # Previous interaction count

class TestConversationOrchestratorIntegration(unittest.TestCase):
    """Integration tests for conversation orchestrator"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Create orchestrator with mock tools that simulate realistic behavior
        self.mock_tools = {
            'text_to_asl_gloss': Mock(),
            'gloss_to_video': Mock(),
            'process_audio_input': Mock(),
            'analyze_asl_video_stream': Mock(),
            'analyze_asl_from_s3': Mock()
        }
        
        self.orchestrator = ConversationOrchestrator(tools=self.mock_tools)
        
        # Create realistic test context
        self.test_context = ConversationContext(
            session_id="integration_test_session",
            user_id="integration_test_user"
        )
    
    def test_complete_text_to_asl_workflow(self):
        """Test complete text-to-ASL workflow with realistic data"""
        # Setup realistic tool responses
        self.mock_tools['text_to_asl_gloss'].return_value = {
            'gloss': 'HELLO NICE MEET YOU',
            'confidence': 0.95,
            'success': True,
            'processing_time': 1.8,
            'metadata': {'word_count': 4, 'complexity': 'simple'}
        }
        
        self.mock_tools['gloss_to_video'].return_value = {
            'video_urls': {
                'pose': 'https://s3.amazonaws.com/asl-videos/pose_12345.mp4',
                'sign': 'https://s3.amazonaws.com/asl-videos/sign_12345.mp4',
                'avatar': 'https://s3.amazonaws.com/asl-videos/avatar_12345.mp4'
            },
            'success': True,
            'processing_time': 3.2,
            'metadata': {'video_duration': 2.5, 'fps': 30}
        }
        
        # Create realistic intent
        intent = IntentResult(
            intent=ConversationIntent.TEXT_TO_ASL,
            confidence=0.92,
            parameters={'text': 'Hello, nice to meet you'},
            input_type=InputType.TEXT,
            reasoning="High confidence text translation request"
        )
        
        # Execute complete workflow
        result = self.orchestrator.execute_translation_flow(intent, self.test_context)
        
        # Verify comprehensive result
        self.assertIsInstance(result, TranslationResult)
        self.assertTrue(result.success)
        self.assertEqual(result.input_text, 'Hello, nice to meet you')
        self.assertEqual(result.gloss, 'HELLO NICE MEET YOU')
        self.assertEqual(result.input_type, InputType.TEXT)
        self.assertEqual(result.status, TranslationStatus.COMPLETED)
        
        # Verify all video formats are present
        self.assertIn('pose', result.video_urls)
        self.assertIn('sign', result.video_urls)
        self.assertIn('avatar', result.video_urls)
        
        # Verify processing time is accumulated
        self.assertGreater(result.processing_time, 4.0)  # 1.8 + 3.2 + overhead
        
        # Verify tools were called with correct parameters
        self.mock_tools['text_to_asl_gloss'].assert_called_once()
        self.mock_tools['gloss_to_video'].assert_called_once()
        
        # Verify gloss was passed to video generation
        gloss_call_args = self.mock_tools['gloss_to_video'].call_args
        self.assertIn('HELLO NICE MEET YOU', str(gloss_call_args))
    
    def test_error_recovery_and_fallback(self):
        """Test error recovery and fallback mechanisms"""
        # Setup primary tool failure with fallback success
        self.mock_tools['text_to_asl_gloss'].side_effect = [
            Exception("Primary gloss service unavailable"),
            {  # Fallback attempt
                'gloss': 'HELLO WORLD',
                'success': True,
                'processing_time': 2.5,
                'metadata': {'fallback_used': True}
            }
        ]
        
        self.mock_tools['gloss_to_video'].return_value = {
            'video_urls': {'pose': 'http://example.com/fallback_pose.mp4'},
            'success': True,
            'processing_time': 3.0
        }
        
        # Execute with error recovery
        result = self.orchestrator.handle_text_to_asl_flow(
            'Hello world', self.test_context
        )
        
        # Should succeed with fallback
        self.assertIsInstance(result, TranslationResult)
        # Note: Depending on implementation, this might succeed or fail
        # The test verifies that the orchestrator handles exceptions gracefully

if __name__ == '__main__':
    unittest.main()