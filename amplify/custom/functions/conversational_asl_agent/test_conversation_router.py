"""
Test Conversation Router

Basic tests for the ConversationRouter functionality to validate implementation.
"""

import unittest
from unittest.mock import Mock, patch
from datetime import datetime

from conversation_router import ConversationRouter, ConversationSession, ConversationResponse
from data_models import ConversationIntent, InputType, ConversationContext
from memory_manager import ConversationMemoryManager

class TestConversationRouter(unittest.TestCase):
    """Test cases for ConversationRouter"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Create mock memory manager to avoid AgentCore dependency in tests
        self.mock_memory_manager = Mock(spec=ConversationMemoryManager)
        self.mock_memory_manager.get_conversation_context.return_value = ConversationContext()
        self.mock_memory_manager.update_conversation_context.return_value = True
        
        # Create router with mock memory manager
        self.router = ConversationRouter(memory_manager=self.mock_memory_manager)
    
    def test_initialize_session_new(self):
        """Test initializing a new session"""
        session = self.router.initialize_session(user_id="test_user")
        
        self.assertIsInstance(session, ConversationSession)
        self.assertIsNotNone(session.session_id)
        self.assertEqual(session.user_id, "test_user")
        self.assertTrue(session.is_active)
        self.assertIn(session.session_id, self.router.active_sessions)
    
    def test_initialize_session_existing(self):
        """Test retrieving an existing session"""
        # Create initial session
        session1 = self.router.initialize_session(session_id="test_session")
        original_activity = session1.last_activity
        
        # Retrieve same session
        session2 = self.router.initialize_session(session_id="test_session")
        
        self.assertEqual(session1.session_id, session2.session_id)
        self.assertGreater(session2.last_activity, original_activity)
    
    def test_cleanup_session(self):
        """Test session cleanup"""
        # Create session
        session = self.router.initialize_session(session_id="test_cleanup")
        self.assertIn("test_cleanup", self.router.active_sessions)
        
        # Mock memory manager cleanup
        self.mock_memory_manager.cleanup_session.return_value = True
        
        # Cleanup session
        result = self.router.cleanup_session("test_cleanup")
        
        self.assertTrue(result)
        self.assertNotIn("test_cleanup", self.router.active_sessions)
        self.mock_memory_manager.cleanup_session.assert_called_once_with("test_cleanup")
    
    @patch('conversation_router.ConversationRouter._route_intent')
    def test_handle_conversation_basic(self, mock_route_intent):
        """Test basic conversation handling"""
        # Mock the intent routing
        mock_route_intent.return_value = ("Hello! How can I help you?", None)
        
        # Handle conversation
        response = self.router.handle_conversation(
            user_input="Hello",
            session_id="test_session",
            user_id="test_user"
        )
        
        # Verify response
        self.assertIsInstance(response, ConversationResponse)
        self.assertEqual(response.message, "Hello! How can I help you?")
        self.assertEqual(response.session_id, "test_session")
        self.assertIsNotNone(response.response_id)
        
        # Verify memory manager was called
        self.mock_memory_manager.get_conversation_context.assert_called()
        self.mock_memory_manager.update_session.assert_called()
    
    def test_handle_conversation_error(self):
        """Test conversation handling with error"""
        # Mock memory manager to raise exception
        self.mock_memory_manager.get_conversation_context.side_effect = Exception("Memory error")
        
        # Handle conversation
        response = self.router.handle_conversation(
            user_input="Hello",
            session_id="test_session"
        )
        
        # Verify error response
        self.assertIsInstance(response, ConversationResponse)
        self.assertIn("unexpected issue", response.message)
        self.assertTrue(response.metadata.get('error', False))
    
    def test_get_session_info(self):
        """Test getting session information"""
        # Create session
        session = self.router.initialize_session(
            session_id="info_test",
            user_id="test_user",
            metadata={"test": "data"}
        )
        
        # Mock context
        mock_context = ConversationContext()
        mock_context.conversation_history = []
        mock_context.user_preferences = {"pref": "value"}
        self.mock_memory_manager.get_conversation_context.return_value = mock_context
        
        # Get session info
        info = self.router.get_session_info("info_test")
        
        # Verify info
        self.assertIsNotNone(info)
        self.assertEqual(info['session_id'], "info_test")
        self.assertEqual(info['user_id'], "test_user")
        self.assertEqual(info['interaction_count'], 0)
        self.assertEqual(info['user_preferences'], {"pref": "value"})
    
    def test_get_active_sessions(self):
        """Test getting active sessions list"""
        # Create multiple sessions
        self.router.initialize_session(session_id="session1", user_id="user1")
        self.router.initialize_session(session_id="session2", user_id="user2")
        
        # Get active sessions
        sessions = self.router.get_active_sessions()
        
        # Verify sessions
        self.assertEqual(len(sessions), 2)
        session_ids = [s['session_id'] for s in sessions]
        self.assertIn("session1", session_ids)
        self.assertIn("session2", session_ids)
    
    def test_get_router_status(self):
        """Test getting router status"""
        # Create some sessions
        self.router.initialize_session(session_id="status_test1")
        self.router.initialize_session(session_id="status_test2")
        
        # Get status
        status = self.router.get_router_status()
        
        # Verify status
        self.assertIsInstance(status, dict)
        self.assertEqual(status['active_sessions_count'], 2)
        self.assertIn("status_test1", status['active_session_ids'])
        self.assertIn("status_test2", status['active_session_ids'])
        self.assertTrue(status['memory_manager_available'])

class TestConversationSession(unittest.TestCase):
    """Test cases for ConversationSession"""
    
    def test_session_creation(self):
        """Test session creation"""
        session = ConversationSession(
            session_id="test_session",
            user_id="test_user",
            metadata={"key": "value"}
        )
        
        self.assertEqual(session.session_id, "test_session")
        self.assertEqual(session.user_id, "test_user")
        self.assertEqual(session.metadata, {"key": "value"})
        self.assertTrue(session.is_active)
        self.assertIsInstance(session.created_at, datetime)
    
    def test_update_activity(self):
        """Test activity update"""
        session = ConversationSession("test_session")
        original_activity = session.last_activity
        
        # Update activity
        session.update_activity()
        
        self.assertGreater(session.last_activity, original_activity)
    
    def test_session_duration(self):
        """Test session duration calculation"""
        session = ConversationSession("test_session")
        
        # Duration should be very small for new session
        duration = session.get_session_duration()
        self.assertGreaterEqual(duration, 0)
        self.assertLess(duration, 1)  # Should be less than 1 second
    
    def test_to_dict(self):
        """Test session serialization"""
        session = ConversationSession(
            session_id="dict_test",
            user_id="test_user",
            metadata={"test": "data"}
        )
        
        session_dict = session.to_dict()
        
        self.assertEqual(session_dict['session_id'], "dict_test")
        self.assertEqual(session_dict['user_id'], "test_user")
        self.assertEqual(session_dict['metadata'], {"test": "data"})
        self.assertTrue(session_dict['is_active'])
        self.assertIn('created_at', session_dict)
        self.assertIn('duration_seconds', session_dict)

class TestConversationResponse(unittest.TestCase):
    """Test cases for ConversationResponse"""
    
    def test_response_creation(self):
        """Test response creation"""
        response = ConversationResponse(
            message="Test message",
            session_id="test_session",
            metadata={"key": "value"}
        )
        
        self.assertEqual(response.message, "Test message")
        self.assertEqual(response.session_id, "test_session")
        self.assertEqual(response.metadata, {"key": "value"})
        self.assertIsNotNone(response.response_id)
        self.assertIsInstance(response.timestamp, datetime)
    
    def test_to_dict(self):
        """Test response serialization"""
        response = ConversationResponse(
            message="Test message",
            session_id="test_session"
        )
        
        response_dict = response.to_dict()
        
        self.assertEqual(response_dict['message'], "Test message")
        self.assertEqual(response_dict['session_id'], "test_session")
        self.assertIn('response_id', response_dict)
        self.assertIn('timestamp', response_dict)
        self.assertIsNone(response_dict['translation_result'])

if __name__ == '__main__':
    unittest.main()