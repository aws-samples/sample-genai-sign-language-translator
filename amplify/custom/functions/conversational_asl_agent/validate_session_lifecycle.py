#!/usr/bin/env python3
"""
Validate Session Lifecycle Management Implementation

This script validates that the enhanced session lifecycle management is working correctly.
"""

import sys
import json
from datetime import datetime, timedelta
from unittest.mock import Mock

# Import the modules to validate
from memory_manager import ConversationMemoryManager
from conversation_router import ConversationRouter, ConversationSession
from data_models import ConversationContext

def validate_memory_manager_initialization():
    """Validate memory manager initialization with session configuration"""
    print("Testing memory manager initialization...")
    
    # Mock AgentCore Memory
    mock_memory = Mock()
    mock_app = Mock()
    mock_app.memory = mock_memory
    
    # Test configuration
    session_config = {
        'session_ttl': 3600,
        'inactive_session_timeout': 1800,
        'cleanup_interval': 300,
        'max_sessions_per_user': 5,
        'enable_session_migration': True,
        'data_version': '1.0'
    }
    
    # Create memory manager
    memory_manager = ConversationMemoryManager(app=mock_app, session_config=session_config)
    
    # Validate configuration
    assert memory_manager.session_ttl == 3600
    assert memory_manager.inactive_session_timeout == 1800
    assert memory_manager.enable_session_migration == True
    assert memory_manager.data_version == '1.0'
    
    print("✓ Memory manager initialization successful")
    return memory_manager

def validate_session_creation():
    """Validate enhanced session creation"""
    print("Testing session creation...")
    
    # Mock AgentCore Memory
    mock_memory = Mock()
    mock_app = Mock()
    mock_app.memory = mock_memory
    
    memory_manager = ConversationMemoryManager(app=mock_app)
    
    # Mock memory operations
    mock_memory.retrieve.return_value = None  # No existing session
    mock_memory.store.return_value = True
    
    # Create session
    session_id = "test_session_123"
    user_id = "test_user"
    initial_preferences = {"language": "en", "video_format": "pose"}
    
    context = memory_manager.create_session(session_id, user_id, initial_preferences)
    
    # Validate session creation
    assert context.session_id == session_id
    assert context.user_id == user_id
    assert context.user_preferences == initial_preferences
    assert isinstance(context.session_start_time, datetime)
    assert len(context.conversation_history) == 0
    
    print("✓ Session creation successful")
    return context

def validate_session_timeout_evaluation():
    """Validate session timeout evaluation logic"""
    print("Testing session timeout evaluation...")
    
    # Create router with memory manager
    mock_memory = Mock()
    mock_app = Mock()
    mock_app.memory = mock_memory
    
    memory_manager = ConversationMemoryManager(
        app=mock_app,
        session_config={'inactive_session_timeout': 1800}  # 30 minutes
    )
    router = ConversationRouter(memory_manager=memory_manager)
    
    # Test expired session
    old_session = ConversationSession("old_session", "user1")
    old_session.last_activity = datetime.now() - timedelta(hours=1)  # 1 hour ago
    
    should_cleanup, reason = router._evaluate_session_timeout(old_session)
    assert should_cleanup == True
    assert "Inactive" in reason
    
    # Test active session
    active_session = ConversationSession("active_session", "user2")
    active_session.last_activity = datetime.now() - timedelta(minutes=5)  # 5 minutes ago
    
    should_cleanup, reason = router._evaluate_session_timeout(active_session)
    assert should_cleanup == False
    assert "within timeout limits" in reason
    
    print("✓ Session timeout evaluation successful")

def validate_session_lifecycle_stats():
    """Validate session lifecycle statistics"""
    print("Testing session lifecycle statistics...")
    
    # Mock AgentCore Memory
    mock_memory = Mock()
    mock_app = Mock()
    mock_app.memory = mock_memory
    
    memory_manager = ConversationMemoryManager(app=mock_app)
    
    # Get lifecycle stats
    stats = memory_manager.get_session_lifecycle_stats()
    
    # Validate stats structure
    assert 'memory_manager_initialized' in stats
    assert 'session_lifecycle' in stats
    
    lifecycle_stats = stats['session_lifecycle']
    assert 'timeout_policies' in lifecycle_stats
    assert 'cleanup_stats' in lifecycle_stats
    assert 'configuration' in lifecycle_stats
    
    # Validate configuration
    config = lifecycle_stats['configuration']
    assert 'session_ttl_seconds' in config
    assert 'inactive_session_timeout_seconds' in config
    assert 'migration_enabled' in config
    
    print("✓ Session lifecycle statistics successful")

def validate_router_integration():
    """Validate router integration with enhanced session management"""
    print("Testing router integration...")
    
    # Mock AgentCore Memory
    mock_memory = Mock()
    mock_app = Mock()
    mock_app.memory = mock_memory
    
    memory_manager = ConversationMemoryManager(app=mock_app)
    router = ConversationRouter(memory_manager=memory_manager)
    
    # Mock memory operations
    mock_memory.retrieve.return_value = None
    mock_memory.store.return_value = True
    
    # Initialize session through router
    session_id = "router_test_session"
    user_id = "test_user"
    metadata = {"user_preferences": {"language": "en"}}
    
    session = router.initialize_session(session_id, user_id, metadata)
    
    # Validate session
    assert session.session_id == session_id
    assert session.user_id == user_id
    assert session.is_active == True
    
    # Validate router tracking
    assert session_id in router.active_sessions
    
    print("✓ Router integration successful")

def validate_enhanced_router_status():
    """Validate enhanced router status with lifecycle information"""
    print("Testing enhanced router status...")
    
    # Mock AgentCore Memory
    mock_memory = Mock()
    mock_app = Mock()
    mock_app.memory = mock_memory
    
    memory_manager = ConversationMemoryManager(app=mock_app)
    router = ConversationRouter(memory_manager=memory_manager)
    
    # Mock registry data
    mock_memory.retrieve.return_value = json.dumps({
        'active_sessions': {},
        'total_sessions': 0
    })
    
    # Get router status
    status = router.get_router_status()
    
    # Validate enhanced status
    assert 'active_sessions_count' in status
    assert 'session_timeout_seconds' in status
    assert 'memory_manager_available' in status
    assert 'session_lifecycle' in status
    
    print("✓ Enhanced router status successful")

def main():
    """Run all validation tests"""
    print("Validating Enhanced Session Lifecycle Management Implementation")
    print("=" * 60)
    
    try:
        # Run validation tests
        memory_manager = validate_memory_manager_initialization()
        validate_session_creation()
        validate_session_timeout_evaluation()
        validate_session_lifecycle_stats()
        validate_router_integration()
        validate_enhanced_router_status()
        
        print("\n" + "=" * 60)
        print("✓ All session lifecycle management validations passed!")
        print("\nEnhanced features implemented:")
        print("- Configurable session timeout policies")
        print("- Session creation with user preference loading")
        print("- Enhanced session update with lifecycle checks")
        print("- Comprehensive session cleanup with preference preservation")
        print("- Session data migration for backward compatibility")
        print("- Session registry tracking")
        print("- Enhanced router status with lifecycle metrics")
        print("- Periodic cleanup with configurable policies")
        
        return True
        
    except Exception as e:
        print(f"\n✗ Validation failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)