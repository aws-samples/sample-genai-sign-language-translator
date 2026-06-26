#!/usr/bin/env python3
"""
Integration Tests for Conversation Flows

End-to-end integration tests for complete conversation workflows,
multi-modal input switching, and session persistence functionality.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import sys
from pathlib import Path
from datetime import datetime, timedelta
import json

# Add current directory to path for imports
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

try:
    from conversation_router import ConversationRouter, ConversationSession, ConversationResponse
    from conversational_agent import ConversationalASLAgent
    from memory_manager import ConversationMemoryManager
    from intent_classifier import ConversationIntentClassifier
    from conversation_orchestrator import ConversationOrchestrator
    from response_formatter import ConversationResponseFormatter
    from data_models import (
        ConversationContext, ConversationInteraction, TranslationResult,
        ConversationIntent, InputType, IntentResult, TranslationStatus,
        create_text_translation_result, create_audio_translation_result
    )
except ImportError as e:
    print(f"Import error: {e}")
    # Handle import issues for testing
    pass

class TestCompleteConversationFlows(unittest.TestCase):
    """Integration tests for complete conversation workflows"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Create mock AgentCore app
        self.mock_app = Mock()
        self.mock_memory = Mock()
        self.mock_app.memory = self.mock_memory
        
        # Create mock tools
        self.mock_tools = {
            'text_to_asl_gloss': Mock(),
            'gloss_to_video': Mock(),
            'process_audio_input': Mock(),
            'analyze_asl_video_stream': Mock(),
            'analyze_asl_from_s3': Mock()
        }
        
        # Create memory storage simulation
        self.memory_storage = {}
        
        def mock_store(key, value, ttl=None):
            self.memory_storage[key] = value
        
        def mock_retrieve(key):
            return self.memory_storage.get(key)
        
        def mock_delete(key):
            if key in self.memory_storage:
                del self.memory_storage[key]
        
        self.mock_memory.store = Mock(side_effect=mock_store)
        self.mock_memory.retrieve = Mock(side_effect=mock_retrieve)
        self.mock_memory.delete = Mock(side_effect=mock_delete)
        
        # Create components
        self.memory_manager = ConversationMemoryManager(app=self.mock_app)
        self.intent_classifier = ConversationIntentClassifier()
        self.orchestrator = ConversationOrchestrator(tools=self.mock_tools)
        self.response_formatter = ConversationResponseFormatter()
        self.router = ConversationRouter(memory_manager=self.memory_manager)
        
        # Test session info
        self.test_session_id = "integration_test_session"
        self.test_user_id = "integration_test_user"
    
    def test_complete_text_to_asl_workflow(self):
        """Test complete text-to-ASL conversation workflow"""
        # Setup mock tool responses
        self.mock_tools['text_to_asl_gloss'].return_value = {
            'gloss': 'HELLO NICE MEET YOU',
            'success': True,
            'processing_time': 1.5
        }
        
        self.mock_tools['gloss_to_video'].return_value = {
            'video_urls': {
                'pose': 'https://example.com/pose_12345.mp4',
                'sign': 'https://example.com/sign_12345.mp4',
                'avatar': 'https://example.com/avatar_12345.mp4'
            },
            'success': True,
            'processing_time': 2.8
        }
        
        # Simulate complete conversation flow
        user_input = "Translate 'Hello, nice to meet you' to ASL"
        
        # 1. Initialize session
        session = self.router.initialize_session(
            session_id=self.test_session_id,
            user_id=self.test_user_id
        )
        self.assertIsNotNone(session)
        
        # 2. Classify intent
        context = self.memory_manager.get_conversation_context(
            session_id=self.test_session_id,
            user_id=self.test_user_id
        )
        
        intent_result = self.intent_classifier.classify_intent(user_input, context)
        self.assertEqual(intent_result.intent, ConversationIntent.TEXT_TO_ASL)
        
        # 3. Execute translation workflow
        translation_result = self.orchestrator.execute_translation_flow(intent_result, context)
        self.assertTrue(translation_result.success)
        self.assertEqual(translation_result.gloss, 'HELLO NICE MEET YOU')
        self.assertIn('pose', translation_result.video_urls)
        
        # 4. Format response
        response_text = self.response_formatter.format_translation_response(
            translation_result, context
        )
        self.assertIsInstance(response_text, str)
        self.assertIn('HELLO NICE MEET YOU', response_text)
        
        # 5. Update context with interaction
        interaction = ConversationInteraction(
            timestamp=datetime.now(),
            user_input=user_input,
            intent=intent_result.intent,
            agent_response=response_text,
            translation_result=translation_result
        )
        
        context.add_interaction(interaction)
        self.memory_manager.update_conversation_context(self.test_session_id, context)
        
        # 6. Verify context persistence
        retrieved_context = self.memory_manager.retrieve_conversation_context(self.test_session_id)
        self.assertIsNotNone(retrieved_context)
        self.assertEqual(len(retrieved_context.conversation_history), 1)
        self.assertEqual(retrieved_context.last_translation.gloss, 'HELLO NICE MEET YOU')
    
    def test_complete_audio_to_asl_workflow(self):
        """Test complete audio-to-ASL conversation workflow"""
        # Setup mock tool responses
        self.mock_tools['process_audio_input'].return_value = {
            'transcribed_text': 'Good morning everyone',
            'success': True,
            'processing_time': 3.2
        }
        
        self.mock_tools['text_to_asl_gloss'].return_value = {
            'gloss': 'GOOD MORNING EVERYONE',
            'success': True,
            'processing_time': 1.8
        }
        
        self.mock_tools['gloss_to_video'].return_value = {
            'video_urls': {
                'pose': 'https://example.com/audio_pose.mp4',
                'avatar': 'https://example.com/audio_avatar.mp4'
            },
            'success': True,
            'processing_time': 3.5
        }
        
        # Simulate audio translation workflow
        user_input = "I have an audio file called greeting.mp3 to translate to ASL"
        
        # Get context
        context = self.memory_manager.get_conversation_context(
            session_id=self.test_session_id,
            user_id=self.test_user_id
        )
        
        # Classify intent
        intent_result = self.intent_classifier.classify_intent(user_input, context)
        self.assertEqual(intent_result.intent, ConversationIntent.AUDIO_TO_ASL)
        
        # Execute workflow
        translation_result = self.orchestrator.execute_translation_flow(intent_result, context)
        
        # Verify result
        self.assertTrue(translation_result.success)
        self.assertEqual(translation_result.input_type, InputType.AUDIO)
        self.assertEqual(translation_result.gloss, 'GOOD MORNING EVERYONE')
        self.assertEqual(translation_result.interpreted_text, 'Good morning everyone')
        
        # Verify processing time accumulation
        expected_min_time = 3.2 + 1.8 + 3.5  # Sum of tool processing times
        self.assertGreater(translation_result.processing_time, expected_min_time - 1.0)
    
    def test_complete_asl_to_text_workflow(self):
        """Test complete ASL-to-text conversation workflow"""
        # Setup mock tool response
        self.mock_tools['analyze_asl_from_s3'].return_value = {
            'interpreted_text': 'Thank you very much for your help',
            'confidence': 0.94,
            'success': True,
            'processing_time': 4.1
        }
        
        # Simulate ASL analysis workflow
        user_input = "Can you analyze this ASL video and tell me what it says?"
        
        # Get context
        context = self.memory_manager.get_conversation_context(
            session_id=self.test_session_id,
            user_id=self.test_user_id
        )
        
        # Classify intent
        intent_result = self.intent_classifier.classify_intent(user_input, context)
        self.assertEqual(intent_result.intent, ConversationIntent.ASL_TO_TEXT)
        
        # Execute workflow
        translation_result = self.orchestrator.execute_translation_flow(intent_result, context)
        
        # Verify result
        self.assertTrue(translation_result.success)
        self.assertEqual(translation_result.input_type, InputType.VIDEO)
        self.assertEqual(translation_result.interpreted_text, 'Thank you very much for your help')
        self.assertGreater(translation_result.processing_time, 4.0)
    
    def test_multi_modal_input_switching(self):
        """Test switching between different input types within same session"""
        # Get context
        context = self.memory_manager.get_conversation_context(
            session_id=self.test_session_id,
            user_id=self.test_user_id
        )
        
        # Setup mock responses for different modalities
        self.mock_tools['text_to_asl_gloss'].return_value = {
            'gloss': 'HELLO',
            'success': True,
            'processing_time': 1.0
        }
        
        self.mock_tools['gloss_to_video'].return_value = {
            'video_urls': {'pose': 'https://example.com/hello_pose.mp4'},
            'success': True,
            'processing_time': 2.0
        }
        
        self.mock_tools['process_audio_input'].return_value = {
            'transcribed_text': 'How are you',
            'success': True,
            'processing_time': 2.5
        }
        
        self.mock_tools['analyze_asl_from_s3'].return_value = {
            'interpreted_text': 'I am fine thank you',
            'success': True,
            'processing_time': 3.0
        }
        
        # Test sequence: Text -> Audio -> Video
        test_sequence = [
            ("Translate 'Hello' to ASL", ConversationIntent.TEXT_TO_ASL, InputType.TEXT),
            ("Process this audio file", ConversationIntent.AUDIO_TO_ASL, InputType.AUDIO),
            ("Analyze this ASL video", ConversationIntent.ASL_TO_TEXT, InputType.VIDEO)
        ]
        
        for i, (user_input, expected_intent, expected_input_type) in enumerate(test_sequence):
            with self.subTest(step=i, input=user_input):
                # Classify intent
                intent_result = self.intent_classifier.classify_intent(user_input, context)
                self.assertEqual(intent_result.intent, expected_intent)
                self.assertEqual(intent_result.input_type, expected_input_type)
                
                # Execute workflow
                translation_result = self.orchestrator.execute_translation_flow(intent_result, context)
                self.assertTrue(translation_result.success)
                
                # Add to context
                interaction = ConversationInteraction(
                    timestamp=datetime.now(),
                    user_input=user_input,
                    intent=intent_result.intent,
                    agent_response="Response",
                    translation_result=translation_result
                )
                context.add_interaction(interaction)
        
        # Verify all interactions are stored
        self.assertEqual(len(context.conversation_history), 3)
        
        # Verify different input types were processed
        input_types = [interaction.translation_result.input_type 
                      for interaction in context.conversation_history]
        self.assertIn(InputType.TEXT, input_types)
        self.assertIn(InputType.AUDIO, input_types)
        self.assertIn(InputType.VIDEO, input_types)
    
    def test_session_persistence_and_context_continuity(self):
        """Test session persistence and context continuity across interactions"""
        # Create initial context with some history
        context = self.memory_manager.get_conversation_context(
            session_id=self.test_session_id,
            user_id=self.test_user_id
        )
        
        # Add initial interaction
        initial_result = create_text_translation_result(
            input_text="Hello",
            gloss="HELLO",
            video_urls={"pose": "https://example.com/hello.mp4"},
            success=True
        )
        
        initial_interaction = ConversationInteraction(
            timestamp=datetime.now(),
            user_input="Translate 'Hello'",
            intent=ConversationIntent.TEXT_TO_ASL,
            agent_response="Translation completed",
            translation_result=initial_result
        )
        
        context.add_interaction(initial_interaction)
        context.update_user_preference("preferred_format", "mp4")
        
        # Store context
        self.memory_manager.update_conversation_context(self.test_session_id, context)
        
        # Simulate session interruption and restoration
        # Clear local context and retrieve from memory
        retrieved_context = self.memory_manager.retrieve_conversation_context(self.test_session_id)
        
        # Verify context continuity
        self.assertIsNotNone(retrieved_context)
        self.assertEqual(retrieved_context.session_id, self.test_session_id)
        self.assertEqual(retrieved_context.user_id, self.test_user_id)
        self.assertEqual(len(retrieved_context.conversation_history), 1)
        self.assertEqual(retrieved_context.user_preferences["preferred_format"], "mp4")
        self.assertEqual(retrieved_context.last_translation.gloss, "HELLO")
        
        # Add another interaction to test continuity
        second_interaction = ConversationInteraction(
            timestamp=datetime.now(),
            user_input="Show me that last translation again",
            intent=ConversationIntent.CONTEXT_REFERENCE,
            agent_response="Here's your previous translation"
        )
        
        retrieved_context.add_interaction(second_interaction)
        self.memory_manager.update_conversation_context(self.test_session_id, retrieved_context)
        
        # Verify updated context
        final_context = self.memory_manager.retrieve_conversation_context(self.test_session_id)
        self.assertEqual(len(final_context.conversation_history), 2)
        self.assertEqual(final_context.total_interactions, 2)
    
    def test_error_handling_in_complete_workflow(self):
        """Test error handling throughout complete conversation workflow"""
        # Setup tool failure scenario
        self.mock_tools['text_to_asl_gloss'].return_value = {
            'success': False,
            'error': 'Gloss generation service unavailable',
            'processing_time': 0.5
        }
        
        # Get context
        context = self.memory_manager.get_conversation_context(
            session_id=self.test_session_id,
            user_id=self.test_user_id
        )
        
        # Simulate workflow with error
        user_input = "Translate 'Hello world' to ASL"
        
        # Classify intent (should succeed)
        intent_result = self.intent_classifier.classify_intent(user_input, context)
        self.assertEqual(intent_result.intent, ConversationIntent.TEXT_TO_ASL)
        
        # Execute workflow (should handle error gracefully)
        translation_result = self.orchestrator.execute_translation_flow(intent_result, context)
        
        # Verify error handling
        self.assertFalse(translation_result.success)
        self.assertIsNotNone(translation_result.error_message)
        self.assertIn('Gloss generation service unavailable', translation_result.error_message)
        
        # Format error response
        error_response = self.response_formatter.format_error_response(
            Exception(translation_result.error_message), context
        )
        
        # Verify error response is user-friendly
        self.assertIsInstance(error_response, str)
        self.assertGreater(len(error_response), 0)
        
        # Add error interaction to context
        error_interaction = ConversationInteraction(
            timestamp=datetime.now(),
            user_input=user_input,
            intent=intent_result.intent,
            agent_response=error_response,
            translation_result=translation_result,
            error_occurred=True,
            error_message=translation_result.error_message
        )
        
        context.add_interaction(error_interaction)
        
        # Verify error tracking
        self.assertEqual(context.error_count, 1)
        self.assertEqual(context.get_error_rate(), 100.0)  # 1 error out of 1 interaction
    
    def test_conversation_router_integration(self):
        """Test complete integration through conversation router"""
        # Setup successful tool responses
        self.mock_tools['text_to_asl_gloss'].return_value = {
            'gloss': 'GOOD MORNING',
            'success': True,
            'processing_time': 1.2
        }
        
        self.mock_tools['gloss_to_video'].return_value = {
            'video_urls': {'pose': 'https://example.com/morning.mp4'},
            'success': True,
            'processing_time': 2.1
        }
        
        # Mock the router's internal components
        with patch.object(self.router, 'intent_classifier', self.intent_classifier), \
             patch.object(self.router, 'orchestrator', self.orchestrator), \
             patch.object(self.router, 'response_formatter', self.response_formatter):
            
            # Handle conversation through router
            response = self.router.handle_conversation(
                user_input="Translate 'Good morning' to ASL",
                session_id=self.test_session_id,
                user_id=self.test_user_id
            )
            
            # Verify response
            self.assertIsInstance(response, ConversationResponse)
            self.assertEqual(response.session_id, self.test_session_id)
            self.assertIsNotNone(response.message)
            self.assertIsNotNone(response.response_id)
            
            # Verify session was created/updated
            session_info = self.router.get_session_info(self.test_session_id)
            self.assertIsNotNone(session_info)
            self.assertEqual(session_info['user_id'], self.test_user_id)
            self.assertGreater(session_info['interaction_count'], 0)

class TestConversationFlowEdgeCases(unittest.TestCase):
    """Test edge cases and boundary conditions in conversation flows"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Create minimal setup for edge case testing
        self.mock_app = Mock()
        self.mock_memory = Mock()
        self.mock_app.memory = self.mock_memory
        
        # Simple memory storage
        self.memory_storage = {}
        self.mock_memory.store = Mock(side_effect=lambda k, v, ttl=None: self.memory_storage.update({k: v}))
        self.mock_memory.retrieve = Mock(side_effect=lambda k: self.memory_storage.get(k))
        self.mock_memory.delete = Mock(side_effect=lambda k: self.memory_storage.pop(k, None))
        
        self.memory_manager = ConversationMemoryManager(app=self.mock_app)
        self.intent_classifier = ConversationIntentClassifier()
    
    def test_empty_conversation_history(self):
        """Test handling of empty conversation history"""
        context = self.memory_manager.get_conversation_context(
            session_id="empty_test",
            user_id="test_user"
        )
        
        # Verify empty context
        self.assertEqual(len(context.conversation_history), 0)
        self.assertEqual(context.total_interactions, 0)
        self.assertIsNone(context.last_translation)
        self.assertEqual(context.get_error_rate(), 0.0)
        
        # Test intent classification with empty context
        intent_result = self.intent_classifier.classify_intent("Hello", context)
        self.assertIsNotNone(intent_result)
        self.assertIsInstance(intent_result.intent, ConversationIntent)
    
    def test_very_long_conversation_history(self):
        """Test handling of very long conversation histories"""
        context = self.memory_manager.get_conversation_context(
            session_id="long_test",
            user_id="test_user"
        )
        
        # Add many interactions
        for i in range(100):
            interaction = ConversationInteraction(
                timestamp=datetime.now(),
                user_input=f"Test input {i}",
                intent=ConversationIntent.TEXT_TO_ASL,
                agent_response=f"Response {i}"
            )
            context.add_interaction(interaction)
        
        # Update context (should trigger history limiting)
        self.memory_manager.update_conversation_context("long_test", context)
        
        # Verify history was limited
        self.assertLessEqual(len(context.conversation_history), 50)  # history_limit
        self.assertEqual(context.total_interactions, 100)  # Total count preserved
    
    def test_concurrent_session_access(self):
        """Test concurrent access to different sessions"""
        sessions = []
        
        # Create multiple sessions concurrently
        for i in range(10):
            session_id = f"concurrent_session_{i}"
            context = self.memory_manager.get_conversation_context(
                session_id=session_id,
                user_id=f"user_{i}"
            )
            
            # Add unique interaction to each
            interaction = ConversationInteraction(
                timestamp=datetime.now(),
                user_input=f"Unique input for session {i}",
                intent=ConversationIntent.TEXT_TO_ASL,
                agent_response=f"Unique response for session {i}"
            )
            context.add_interaction(interaction)
            
            self.memory_manager.update_conversation_context(session_id, context)
            sessions.append((session_id, context))
        
        # Verify all sessions are independent
        for session_id, original_context in sessions:
            retrieved_context = self.memory_manager.retrieve_conversation_context(session_id)
            self.assertIsNotNone(retrieved_context)
            self.assertEqual(retrieved_context.session_id, session_id)
            self.assertEqual(len(retrieved_context.conversation_history), 1)
            
            # Verify unique content
            unique_input = retrieved_context.conversation_history[0].user_input
            self.assertIn(session_id.split('_')[-1], unique_input)
    
    def test_session_timeout_simulation(self):
        """Test session timeout and cleanup behavior"""
        # Create session with old timestamp
        old_context = ConversationContext(
            session_id="timeout_test",
            user_id="test_user",
            session_start_time=datetime.now() - timedelta(hours=25),  # Older than 24h TTL
            last_activity_time=datetime.now() - timedelta(hours=25)
        )
        
        # Store context
        self.memory_manager.store_conversation_context("timeout_test", old_context)
        
        # Simulate TTL expiration by clearing storage
        self.memory_storage.clear()
        
        # Try to retrieve expired session
        retrieved_context = self.memory_manager.retrieve_conversation_context("timeout_test")
        self.assertIsNone(retrieved_context)
        
        # Verify new context is created when accessing expired session
        new_context = self.memory_manager.get_conversation_context(
            session_id="timeout_test",
            user_id="test_user"
        )
        
        self.assertIsNotNone(new_context)
        self.assertEqual(len(new_context.conversation_history), 0)
        self.assertEqual(new_context.total_interactions, 0)
    
    def test_malformed_input_handling(self):
        """Test handling of malformed or unusual inputs"""
        context = self.memory_manager.get_conversation_context(
            session_id="malformed_test",
            user_id="test_user"
        )
        
        malformed_inputs = [
            "",  # Empty string
            "   ",  # Whitespace only
            "a" * 1000,  # Very long input
            "🤖🔤📹",  # Emoji only
            "translate translate translate translate",  # Repetitive
            "Translate 'unclosed quote",  # Malformed quotes
            None,  # None input
        ]
        
        for malformed_input in malformed_inputs:
            with self.subTest(input=repr(malformed_input)):
                try:
                    intent_result = self.intent_classifier.classify_intent(malformed_input, context)
                    
                    # Should not crash and should return valid result
                    self.assertIsNotNone(intent_result)
                    self.assertIsInstance(intent_result.intent, ConversationIntent)
                    self.assertIsInstance(intent_result.confidence, float)
                    self.assertGreaterEqual(intent_result.confidence, 0.0)
                    self.assertLessEqual(intent_result.confidence, 1.0)
                    
                except Exception as e:
                    # If exception occurs, it should be handled gracefully
                    self.assertIsInstance(e, (ValueError, TypeError, AttributeError))

if __name__ == '__main__':
    unittest.main()