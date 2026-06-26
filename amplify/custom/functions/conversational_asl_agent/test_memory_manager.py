#!/usr/bin/env python3
"""
Unit Tests for Memory Manager

Tests for the ConversationMemoryManager to validate AgentCore Memory integration,
data serialization, and conversation context management functionality.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import json
import sys
from pathlib import Path
from datetime import datetime, timedelta

# Add current directory to path for imports
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

from memory_manager import ConversationMemoryManager
from data_models import (
    ConversationContext, ConversationInteraction, TranslationResult,
    ConversationIntent, InputType, TranslationStatus,
    create_text_translation_result
)

class TestConversationMemoryManager(unittest.TestCase):
    """Test cases for ConversationMemoryManager"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Create mock AgentCore app and memory
        self.mock_app = Mock()
        self.mock_memory = Mock()
        self.mock_app.memory = self.mock_memory
        
        # Create memory manager with mock app
        self.memory_manager = ConversationMemoryManager(app=self.mock_app)
        
        # Create test data
        self.test_session_id = "test_session_123"
        self.test_user_id = "test_user_456"
        
        self.test_context = ConversationContext(
            session_id=self.test_session_id,
            user_id=self.test_user_id,
            session_start_time=datetime.now(),
            last_activity_time=datetime.now(),
            user_preferences={"language": "en", "video_format": "mp4"},
            error_count=0,
            total_interactions=2
        )
        
        # Add test interactions
        self.test_interaction = ConversationInteraction(
            timestamp=datetime.now(),
            user_input="Translate 'hello'",
            intent=ConversationIntent.TEXT_TO_ASL,
            agent_response="Translation completed",
            translation_result=create_text_translation_result(
                input_text="hello",
                gloss="HELLO",
                video_urls={"pose": "http://example.com/pose.mp4"},
                processing_time=1.5,
                success=True
            )
        )
        
        self.test_context.add_interaction(self.test_interaction)
    
    def test_memory_key_generation(self):
        """Test memory key generation methods"""
        session_id = "test_session"
        user_id = "test_user"
        
        # Test session key generation
        session_key = self.memory_manager.generate_session_key(session_id)
        self.assertEqual(session_key, "session:test_session:context")
        
        # Test history key generation
        history_key = self.memory_manager.generate_history_key(session_id)
        self.assertEqual(history_key, "session:test_session:history")
        
        # Test preferences key generation
        preferences_key = self.memory_manager.generate_preferences_key(session_id)
        self.assertEqual(preferences_key, "session:test_session:preferences")
        
        # Test last result key generation
        result_key = self.memory_manager.generate_last_result_key(session_id)
        self.assertEqual(result_key, "session:test_session:last_result")
        
        # Test user global key generation
        global_key = self.memory_manager.generate_user_global_key(user_id)
        self.assertEqual(global_key, "user:test_user:global_preferences")
    
    def test_conversation_context_serialization(self):
        """Test conversation context serialization and deserialization"""
        # Test serialization
        serialized = self.memory_manager.serialize_conversation_context(self.test_context)
        
        # Should be valid JSON
        self.assertIsInstance(serialized, str)
        context_dict = json.loads(serialized)
        
        # Check key fields are present
        self.assertEqual(context_dict['session_id'], self.test_session_id)
        self.assertEqual(context_dict['user_id'], self.test_user_id)
        self.assertEqual(context_dict['error_count'], 0)
        self.assertEqual(context_dict['total_interactions'], 2)
        
        # Check datetime fields are serialized as ISO strings
        self.assertIsInstance(context_dict['session_start_time'], str)
        self.assertIsInstance(context_dict['last_activity_time'], str)
        
        # Test deserialization
        deserialized = self.memory_manager.deserialize_conversation_context(serialized)
        
        # Check deserialized object
        self.assertIsInstance(deserialized, ConversationContext)
        self.assertEqual(deserialized.session_id, self.test_session_id)
        self.assertEqual(deserialized.user_id, self.test_user_id)
        self.assertEqual(deserialized.error_count, 0)
        self.assertEqual(deserialized.total_interactions, 2)
        
        # Check datetime fields are restored
        self.assertIsInstance(deserialized.session_start_time, datetime)
        self.assertIsInstance(deserialized.last_activity_time, datetime)
    
    def test_conversation_history_serialization(self):
        """Test conversation history serialization and deserialization"""
        history = [self.test_interaction]
        
        # Test serialization
        serialized = self.memory_manager.serialize_conversation_history(history)
        
        # Should be valid JSON
        self.assertIsInstance(serialized, str)
        history_list = json.loads(serialized)
        
        # Check structure
        self.assertEqual(len(history_list), 1)
        interaction_dict = history_list[0]
        
        self.assertEqual(interaction_dict['user_input'], "Translate 'hello'")
        self.assertEqual(interaction_dict['intent'], ConversationIntent.TEXT_TO_ASL.value)
        self.assertEqual(interaction_dict['agent_response'], "Translation completed")
        
        # Test deserialization
        deserialized = self.memory_manager.deserialize_conversation_history(serialized)
        
        # Check deserialized objects
        self.assertEqual(len(deserialized), 1)
        interaction = deserialized[0]
        
        self.assertIsInstance(interaction, ConversationInteraction)
        self.assertEqual(interaction.user_input, "Translate 'hello'")
        self.assertEqual(interaction.intent, ConversationIntent.TEXT_TO_ASL)
        self.assertEqual(interaction.agent_response, "Translation completed")
        self.assertIsInstance(interaction.timestamp, datetime)
    
    def test_translation_result_serialization(self):
        """Test translation result serialization and deserialization"""
        result = create_text_translation_result(
            input_text="test text",
            gloss="TEST TEXT",
            video_urls={"pose": "http://example.com/pose.mp4", "sign": "http://example.com/sign.mp4"},
            processing_time=2.5,
            success=True
        )
        
        # Test serialization
        serialized = self.memory_manager.serialize_translation_result(result)
        
        # Should be valid JSON
        self.assertIsInstance(serialized, str)
        result_dict = json.loads(serialized)
        
        # Check key fields
        self.assertEqual(result_dict['input_text'], "test text")
        self.assertEqual(result_dict['gloss'], "TEST TEXT")
        self.assertEqual(result_dict['input_type'], InputType.TEXT.value)
        self.assertEqual(result_dict['processing_time'], 2.5)
        self.assertTrue(result_dict['success'])
        
        # Test deserialization
        deserialized = self.memory_manager.deserialize_translation_result(serialized)
        
        # Check deserialized object
        self.assertIsInstance(deserialized, TranslationResult)
        self.assertEqual(deserialized.input_text, "test text")
        self.assertEqual(deserialized.gloss, "TEST TEXT")
        self.assertEqual(deserialized.input_type, InputType.TEXT)
        self.assertEqual(deserialized.processing_time, 2.5)
        self.assertTrue(deserialized.success)
    
    def test_store_conversation_context(self):
        """Test storing conversation context in memory"""
        # Mock memory store method
        self.mock_memory.store = Mock()
        
        # Store context
        result = self.memory_manager.store_conversation_context(
            self.test_session_id, self.test_context
        )
        
        # Should return True for success
        self.assertTrue(result)
        
        # Verify memory.store was called multiple times for different data
        self.assertGreater(self.mock_memory.store.call_count, 1)
        
        # Check that session context key was used
        call_args_list = self.mock_memory.store.call_args_list
        session_key_used = any(
            call[0][0] == f"session:{self.test_session_id}:context"
            for call in call_args_list
        )
        self.assertTrue(session_key_used)
    
    def test_retrieve_conversation_context(self):
        """Test retrieving conversation context from memory"""
        # Mock memory retrieve method
        context_data = self.memory_manager.serialize_conversation_context(self.test_context)
        history_data = self.memory_manager.serialize_conversation_history([self.test_interaction])
        preferences_data = json.dumps({"language": "en", "video_format": "mp4"})
        
        def mock_retrieve(key):
            if "context" in key:
                return context_data
            elif "history" in key:
                return history_data
            elif "preferences" in key:
                return preferences_data
            return None
        
        self.mock_memory.retrieve = Mock(side_effect=mock_retrieve)
        
        # Retrieve context
        retrieved_context = self.memory_manager.retrieve_conversation_context(self.test_session_id)
        
        # Should return ConversationContext object
        self.assertIsInstance(retrieved_context, ConversationContext)
        self.assertEqual(retrieved_context.session_id, self.test_session_id)
        self.assertEqual(retrieved_context.user_id, self.test_user_id)
        
        # Should have conversation history
        self.assertEqual(len(retrieved_context.conversation_history), 1)
        self.assertEqual(retrieved_context.conversation_history[0].user_input, "Translate 'hello'")
        
        # Should have user preferences
        self.assertEqual(retrieved_context.user_preferences["language"], "en")
    
    def test_retrieve_nonexistent_context(self):
        """Test retrieving non-existent conversation context"""
        # Mock memory retrieve to return None
        self.mock_memory.retrieve = Mock(return_value=None)
        
        # Try to retrieve non-existent context
        result = self.memory_manager.retrieve_conversation_context("nonexistent_session")
        
        # Should return None
        self.assertIsNone(result)
    
    def test_get_conversation_context_existing(self):
        """Test getting existing conversation context"""
        # Mock retrieve to return existing context
        context_data = self.memory_manager.serialize_conversation_context(self.test_context)
        self.mock_memory.retrieve = Mock(return_value=context_data)
        self.mock_memory.store = Mock()
        
        # Get context
        result = self.memory_manager.get_conversation_context(
            session_id=self.test_session_id,
            user_id=self.test_user_id
        )
        
        # Should return existing context
        self.assertIsInstance(result, ConversationContext)
        self.assertEqual(result.session_id, self.test_session_id)
        
        # Should update last activity time and store
        self.mock_memory.store.assert_called()
    
    def test_get_conversation_context_new(self):
        """Test getting new conversation context when none exists"""
        # Mock retrieve to return None (no existing context)
        self.mock_memory.retrieve = Mock(return_value=None)
        self.mock_memory.store = Mock()
        
        # Get context without providing session_id
        result = self.memory_manager.get_conversation_context(user_id=self.test_user_id)
        
        # Should create new context
        self.assertIsInstance(result, ConversationContext)
        self.assertEqual(result.user_id, self.test_user_id)
        self.assertIsNotNone(result.session_id)
        
        # Should store new context
        self.mock_memory.store.assert_called()
    
    def test_update_conversation_context(self):
        """Test updating conversation context"""
        # Mock memory store
        self.mock_memory.store = Mock(return_value=True)
        
        # Update context
        original_activity_time = self.test_context.last_activity_time
        result = self.memory_manager.update_conversation_context(
            self.test_session_id, self.test_context
        )
        
        # Should return True for success
        self.assertTrue(result)
        
        # Should update last activity time
        self.assertGreater(self.test_context.last_activity_time, original_activity_time)
        
        # Should call store
        self.mock_memory.store.assert_called()
    
    def test_update_context_with_history_limit(self):
        """Test updating context with conversation history limit"""
        # Create context with many interactions
        large_context = ConversationContext(
            session_id="test_session",
            user_id="test_user"
        )
        
        # Add more interactions than the limit
        for i in range(60):  # More than history_limit (50)
            interaction = ConversationInteraction(
                timestamp=datetime.now(),
                user_input=f"Test input {i}",
                intent=ConversationIntent.TEXT_TO_ASL,
                agent_response=f"Response {i}"
            )
            large_context.add_interaction(interaction)
        
        # Mock memory store
        self.mock_memory.store = Mock(return_value=True)
        
        # Update context
        result = self.memory_manager.update_conversation_context("test_session", large_context)
        
        # Should succeed
        self.assertTrue(result)
        
        # Should limit history to history_limit
        self.assertLessEqual(len(large_context.conversation_history), 50)
    
    def test_cleanup_session(self):
        """Test session cleanup"""
        # Mock memory delete
        self.mock_memory.delete = Mock()
        
        # Cleanup session
        result = self.memory_manager.cleanup_session(self.test_session_id)
        
        # Should return True for success
        self.assertTrue(result)
        
        # Should call delete for all session keys
        expected_calls = 4  # context, history, preferences, last_result
        self.assertEqual(self.mock_memory.delete.call_count, expected_calls)
    
    def test_cleanup_session_with_errors(self):
        """Test session cleanup with some delete errors"""
        # Mock memory delete to fail for some keys
        def mock_delete(key):
            if "preferences" in key:
                raise Exception("Delete failed")
        
        self.mock_memory.delete = Mock(side_effect=mock_delete)
        
        # Cleanup session
        result = self.memory_manager.cleanup_session(self.test_session_id)
        
        # Should return False due to partial failure
        self.assertFalse(result)
        
        # Should still attempt all deletes
        expected_calls = 4
        self.assertEqual(self.mock_memory.delete.call_count, expected_calls)
    
    def test_get_memory_stats(self):
        """Test getting memory statistics"""
        stats = self.memory_manager.get_memory_stats()
        
        # Should return dictionary with expected keys
        self.assertIsInstance(stats, dict)
        self.assertIn('memory_manager_initialized', stats)
        self.assertIn('session_ttl_seconds', stats)
        self.assertIn('history_limit', stats)
        self.assertIn('agentcore_memory_available', stats)
        
        # Should indicate memory is available
        self.assertTrue(stats['memory_manager_initialized'])
        self.assertTrue(stats['agentcore_memory_available'])
    
    def test_error_handling_serialization(self):
        """Test error handling in serialization methods"""
        # Test with invalid data that can't be serialized
        invalid_context = Mock()
        invalid_context.session_id = object()  # Non-serializable object
        
        with self.assertRaises(Exception):
            self.memory_manager.serialize_conversation_context(invalid_context)
    
    def test_error_handling_deserialization(self):
        """Test error handling in deserialization methods"""
        # Test with invalid JSON
        with self.assertRaises(Exception):
            self.memory_manager.deserialize_conversation_context("invalid json")
        
        # Test with valid JSON but wrong structure
        with self.assertRaises(Exception):
            self.memory_manager.deserialize_conversation_context('{"wrong": "structure"}')

class TestMemoryManagerIntegration(unittest.TestCase):
    """Integration tests for memory manager functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Create mock app with more realistic behavior
        self.mock_app = Mock()
        self.mock_memory = Mock()
        self.mock_app.memory = self.mock_memory
        
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
        
        self.memory_manager = ConversationMemoryManager(app=self.mock_app)
    
    def test_full_context_lifecycle(self):
        """Test complete context lifecycle: create, store, retrieve, update, cleanup"""
        session_id = "lifecycle_test_session"
        user_id = "lifecycle_test_user"
        
        # 1. Create new context
        context = self.memory_manager.get_conversation_context(
            session_id=session_id,
            user_id=user_id
        )
        
        self.assertEqual(context.session_id, session_id)
        self.assertEqual(context.user_id, user_id)
        self.assertEqual(len(context.conversation_history), 0)
        
        # 2. Add interaction and update
        interaction = ConversationInteraction(
            timestamp=datetime.now(),
            user_input="Hello",
            intent=ConversationIntent.GREETING,
            agent_response="Hello! How can I help you?"
        )
        
        context.add_interaction(interaction)
        context.update_user_preference("language", "en")
        
        # 3. Update in memory
        update_result = self.memory_manager.update_conversation_context(session_id, context)
        self.assertTrue(update_result)
        
        # 4. Retrieve and verify
        retrieved_context = self.memory_manager.retrieve_conversation_context(session_id)
        self.assertIsNotNone(retrieved_context)
        self.assertEqual(len(retrieved_context.conversation_history), 1)
        self.assertEqual(retrieved_context.user_preferences["language"], "en")
        
        # 5. Cleanup
        cleanup_result = self.memory_manager.cleanup_session(session_id)
        self.assertTrue(cleanup_result)
        
        # 6. Verify cleanup
        final_context = self.memory_manager.retrieve_conversation_context(session_id)
        self.assertIsNone(final_context)
    
    def test_concurrent_session_handling(self):
        """Test handling multiple concurrent sessions"""
        sessions = []
        
        # Create multiple sessions
        for i in range(5):
            session_id = f"concurrent_session_{i}"
            context = self.memory_manager.get_conversation_context(
                session_id=session_id,
                user_id=f"user_{i}"
            )
            sessions.append((session_id, context))
        
        # Add interactions to each session
        for session_id, context in sessions:
            interaction = ConversationInteraction(
                timestamp=datetime.now(),
                user_input=f"Test input for {session_id}",
                intent=ConversationIntent.TEXT_TO_ASL,
                agent_response="Test response"
            )
            context.add_interaction(interaction)
            self.memory_manager.update_conversation_context(session_id, context)
        
        # Verify all sessions can be retrieved independently
        for session_id, original_context in sessions:
            retrieved_context = self.memory_manager.retrieve_conversation_context(session_id)
            self.assertIsNotNone(retrieved_context)
            self.assertEqual(retrieved_context.session_id, session_id)
            self.assertEqual(len(retrieved_context.conversation_history), 1)
        
        # Cleanup all sessions
        for session_id, _ in sessions:
            cleanup_result = self.memory_manager.cleanup_session(session_id)
            self.assertTrue(cleanup_result)

if __name__ == '__main__':
    unittest.main()