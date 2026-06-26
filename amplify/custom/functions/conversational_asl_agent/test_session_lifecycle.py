#!/usr/bin/env python3
"""
Test Session Lifecycle Management

This module tests the enhanced session lifecycle management functionality
including session creation, update, cleanup, timeout handling, and data migration.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import time
from datetime import datetime, timedelta
import json

# Import the modules to test
from memory_manager import ConversationMemoryManager
from conversation_router import ConversationRouter, ConversationSession
from data_models import ConversationContext, ConversationInteraction, ConversationIntent, TranslationResult

class TestSessionLifecycleManagement(unittest.TestCase):
    """Test cases for enhanced session lifecycle management"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Mock AgentCore Memory
        self.mock_memory = Mock()
        self.mock_app = Mock()
        self.mock_app.memory = self.mock_memory
        
        # Create memory manager with test configuration
        session_config = {
            'session_ttl': 3600,  # 1 hour
            'inactive_session_timeout': 1800,  # 30 minutes
            'cleanup_interval': 300,  # 5 minutes
            'max_sessions_per_user': 5,
            'enable_session_migration': True,
            'data_version': '1.0'
        }
        
        self.memory_manager = ConversationMemoryManager(
            app=self.mock_app,
            session_config=session_config
        )
        
        # Create conversation router
        self.router = ConversationRouter(memory_manager=self.memory_manager)
    
    def test_session_creation_with_lifecycle_management(self):
        """Test enhanced session creation"""
        session_id = "test_session_lifecycle"
        user_id = "test_user"
        initial_preferences = {"language": "en", "video_format": "pose"}
        
        # Mock memory operations
        self.mock_memory.retrieve.return_value = None  # No existing session
        self.mock_memory.store.return_value = True
        
        # Create session
        context = self.memory_manager.create_session(
            session_id, user_id, initial_preferences
        )
        
        # Verify session was created correctly
        self.assertEqual(context.session_id, session_id)
        self.assertEqual(context.user_id, user_id)
        self.assertEqual(context.user_preferences, initial_preferences)
        self.assertIsInstance(context.session_start_time, datetime)
        self.assertEqual(len(context.conversation_history), 0)
        
        # Verify memory operations were called
        self.mock_memory.store.assert_called()
    
    def test_session_update_with_lifecycle_checks(self):
        """Test enhanced session update with lifecycle checks"""
        session_id = "test_session_update"
        
        # Create a context
        context = ConversationContext(
            session_id=session_id,
            user_id="test_user",
            session_start_time=datetime.now() - timedelta(minutes=10),
            last_activity_time=datetime.now() - timedelta(minutes=5)
        )
        
        # Mock memory operations
        self.mock_memory.retrieve.return_value = json.dumps({
            'session_id': session_id,
            'user_id': 'test_user',
            'session_start_time': context.session_start_time.isoformat(),
            'last_activity_time': context.last_activity_time.isoformat(),
            'conversation_history': [],
            'user_preferences': {},
            'current_operations': [],
            'error_count': 0,
            'total_interactions': 0
        })
        self.mock_memory.store.return_value = True
        
        # Update session
        success = self.memory_manager.update_session(session_id, context)
        
        # Verify update was successful
        self.assertTrue(success)
        self.mock_memory.store.assert_called()
    
    def test_session_timeout_evaluation(self):
        """Test session timeout evaluation logic"""
        # Create a session that should timeout due to inactivity
        old_session = ConversationSession(
            session_id="old_session",
            user_id="test_user"
        )
        old_session.last_activity = datetime.now() - timedelta(hours=3)  # 3 hours ago
        
        # Evaluate timeout
        should_cleanup, reason = self.router._evaluate_session_timeout(old_session)
        
        # Verify session should be cleaned up
        self.assertTrue(should_cleanup)
        self.assertIn("Inactive", reason)
        
        # Create a recent session that should not timeout
        recent_session = ConversationSession(
            session_id="recent_session",
            user_id="test_user"
        )
        recent_session.last_activity = datetime.now() - timedelta(minutes=5)  # 5 minutes ago
        
        # Evaluate timeout
        should_cleanup, reason = self.router._evaluate_session_timeout(recent_session)
        
        # Verify session should not be cleaned up
        self.assertFalse(should_cleanup)
        self.assertIn("within timeout limits", reason)
    
    def test_session_cleanup_with_preference_preservation(self):
        """Test session cleanup with user preference preservation"""
        session_id = "test_cleanup_session"
        user_id = "test_user"
        
        # Mock context with user preferences
        context_data = {
            'session_id': session_id,
            'user_id': user_id,
            'session_start_time': datetime.now().isoformat(),
            'last_activity_time': datetime.now().isoformat(),
            'conversation_history': [],
            'user_preferences': {'language': 'en', 'video_format': 'pose'},
            'current_operations': [],
            'error_count': 0,
            'total_interactions': 5
        }
        
        # Mock memory operations
        self.mock_memory.retrieve.side_effect = [
            json.dumps(context_data),  # For context retrieval
            None  # For global preferences (doesn't exist yet)
        ]
        self.mock_memory.store.return_value = True
        self.mock_memory.delete.return_value = True
        
        # Cleanup session
        success = self.memory_manager.cleanup_session(session_id)
        
        # Verify cleanup was successful
        self.assertTrue(success)
        
        # Verify memory operations were called
        self.mock_memory.delete.assert_called()
        # Should have stored global preferences
        store_calls = self.mock_memory.store.call_args_list
        self.assertTrue(any('global_preferences' in str(call) for call in store_calls))
    
    def test_session_migration(self):
        """Test session data migration for backward compatibility"""
        session_id = "test_migration_session"
        
        # Mock old version context data (missing some fields)
        old_context_data = {
            'session_id': session_id,
            'user_id': 'test_user',
            'session_start_time': datetime.now().isoformat(),
            'last_activity_time': datetime.now().isoformat(),
            'conversation_history': [],
            'user_preferences': {}
            # Missing: error_count, total_interactions
        }
        
        # Mock memory operations
        self.mock_memory.retrieve.return_value = json.dumps(old_context_data)
        self.mock_memory.store.return_value = True
        
        # Perform migration
        success = self.memory_manager.migrate_session_data(session_id, "0.9", "1.0")
        
        # Verify migration was successful
        self.assertTrue(success)
        self.mock_memory.store.assert_called()
    
    def test_comprehensive_cleanup_with_policies(self):
        """Test comprehensive cleanup with configurable policies"""
        # Mock session registry
        registry_data = {
            'active_sessions': {
                'session1': {'created_at': datetime.now().isoformat()},
                'session2': {'created_at': datetime.now().isoformat()}
            },
            'total_sessions': 2
        }
        
        # Mock memory operations
        self.mock_memory.retrieve.side_effect = [
            json.dumps(registry_data),  # Session registry
            # Mock contexts for each session (both should be cleaned up)
            json.dumps({
                'session_id': 'session1',
                'session_start_time': (datetime.now() - timedelta(hours=2)).isoformat(),
                'last_activity_time': (datetime.now() - timedelta(hours=2)).isoformat(),
                'user_preferences': {}
            }),
            json.dumps({
                'session_id': 'session2', 
                'session_start_time': (datetime.now() - timedelta(hours=3)).isoformat(),
                'last_activity_time': (datetime.now() - timedelta(hours=3)).isoformat(),
                'user_preferences': {}
            })
        ]
        self.mock_memory.store.return_value = True
        self.mock_memory.delete.return_value = True
        
        # Force cleanup by setting last cleanup time to past
        self.memory_manager.last_cleanup = time.time() - 7200  # 2 hours ago
        
        # Run cleanup
        cleaned_count = self.memory_manager.cleanup_expired_sessions()
        
        # Verify cleanup was performed
        # Note: The actual count depends on the mocked data and timeout policies
        self.assertIsInstance(cleaned_count, int)
        
        # Verify cleanup stats were updated
        self.assertGreater(self.memory_manager.cleanup_stats['total_cleanups'], 0)
    
    def test_session_lifecycle_stats(self):
        """Test session lifecycle statistics reporting"""
        # Get lifecycle stats
        stats = self.memory_manager.get_session_lifecycle_stats()
        
        # Verify stats structure
        self.assertIn('memory_manager_initialized', stats)
        self.assertIn('session_lifecycle', stats)
        
        lifecycle_stats = stats['session_lifecycle']
        self.assertIn('timeout_policies', lifecycle_stats)
        self.assertIn('cleanup_stats', lifecycle_stats)
        self.assertIn('configuration', lifecycle_stats)
        
        # Verify configuration values
        config = lifecycle_stats['configuration']
        self.assertEqual(config['session_ttl_seconds'], 3600)
        self.assertEqual(config['inactive_session_timeout_seconds'], 1800)
        self.assertTrue(config['migration_enabled'])
    
    def test_router_session_initialization_with_lifecycle(self):
        """Test router session initialization with enhanced lifecycle management"""
        session_id = "test_router_session"
        user_id = "test_user"
        metadata = {"user_preferences": {"language": "en"}}
        
        # Mock memory operations
        self.mock_memory.retrieve.return_value = None  # No existing session
        self.mock_memory.store.return_value = True
        
        # Initialize session through router
        session = self.router.initialize_session(session_id, user_id, metadata)
        
        # Verify session was created
        self.assertEqual(session.session_id, session_id)
        self.assertEqual(session.user_id, user_id)
        self.assertTrue(session.is_active)
        
        # Verify session is tracked in router
        self.assertIn(session_id, self.router.active_sessions)
    
    def test_router_periodic_cleanup_with_enhanced_policies(self):
        """Test router periodic cleanup with enhanced timeout policies"""
        # Add some test sessions to router
        old_session = ConversationSession("old_session", "user1")
        old_session.last_activity = datetime.now() - timedelta(hours=2)
        
        recent_session = ConversationSession("recent_session", "user2") 
        recent_session.last_activity = datetime.now() - timedelta(minutes=5)
        
        self.router.active_sessions["old_session"] = old_session
        self.router.active_sessions["recent_session"] = recent_session
        
        # Mock memory operations for cleanup
        self.mock_memory.retrieve.return_value = "{}"  # Empty registry
        self.mock_memory.delete.return_value = True
        
        # Force cleanup by setting last cleanup time to past
        self.router.last_cleanup = time.time() - 7200  # 2 hours ago
        
        # Run periodic cleanup
        self.router._perform_periodic_cleanup()
        
        # Verify old session was cleaned up but recent session remains
        self.assertNotIn("old_session", self.router.active_sessions)
        self.assertIn("recent_session", self.router.active_sessions)

if __name__ == '__main__':
    unittest.main()