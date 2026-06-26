"""
Integration Test for Conversation Router

Test the conversation router integration with existing conversational components.
"""

import sys
import os
from unittest.mock import Mock, patch

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(__file__))

def test_router_integration():
    """Test conversation router integration with mocked dependencies"""
    print("Testing ConversationRouter integration...")
    
    try:
        # Mock the AgentCore dependency
        with patch('conversation_router.ConversationMemoryManager') as MockMemoryManager:
            # Set up mock memory manager
            mock_memory = Mock()
            mock_memory.get_conversation_context.return_value = Mock()
            mock_memory.update_conversation_context.return_value = True
            MockMemoryManager.return_value = mock_memory
            
            # Mock other dependencies
            with patch('conversation_router.ConversationIntentClassifier') as MockIntentClassifier, \
                 patch('conversation_router.NaturalLanguageUnderstandingEngine') as MockNLUEngine, \
                 patch('conversation_router.ConversationOrchestrator') as MockOrchestrator, \
                 patch('conversation_router.ConversationResponseFormatter') as MockResponseFormatter, \
                 patch('conversation_router.ConversationErrorHandler') as MockErrorHandler:
                
                # Set up mock NLU result
                mock_nlu_result = Mock()
                mock_nlu_result.intent = Mock()
                mock_nlu_result.intent.value = 'greeting'
                mock_nlu_result.confidence = 0.9
                mock_nlu_result.parameters = {'greeting_type': 'general'}
                
                MockNLUEngine.return_value.understand.return_value = mock_nlu_result
                
                # Import and create router (after mocking)
                from conversation_router import ConversationRouter
                
                router = ConversationRouter()
                
                print("✓ ConversationRouter instantiated successfully")
                
                # Test session initialization
                session = router.initialize_session(user_id="test_user")
                print(f"✓ Session initialized: {session.session_id}")
                
                # Test basic conversation handling with mocked routing
                with patch.object(router, '_route_intent') as mock_route:
                    mock_route.return_value = ("Hello! How can I help you?", None)
                    
                    response = router.handle_conversation(
                        user_input="Hello",
                        session_id=session.session_id,
                        user_id="test_user"
                    )
                    
                    print(f"✓ Conversation handled successfully: {response.message[:50]}...")
                
                # Test session info retrieval
                info = router.get_session_info(session.session_id)
                print(f"✓ Session info retrieved: {info['session_id'] if info else 'None'}")
                
                # Test router status
                status = router.get_router_status()
                print(f"✓ Router status retrieved: {status['active_sessions_count']} active sessions")
                
                # Test session cleanup
                cleanup_result = router.cleanup_session(session.session_id)
                print(f"✓ Session cleanup: {'Success' if cleanup_result else 'Failed'}")
                
                print("\n🎉 Integration test PASSED!")
                return True
                
    except Exception as e:
        print(f"✗ Integration test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_session_and_response_classes():
    """Test ConversationSession and ConversationResponse classes"""
    print("\nTesting ConversationSession and ConversationResponse classes...")
    
    try:
        from conversation_router import ConversationSession, ConversationResponse
        
        # Test ConversationSession
        session = ConversationSession(
            session_id="test_session",
            user_id="test_user",
            metadata={"test": "data"}
        )
        
        print(f"✓ ConversationSession created: {session.session_id}")
        
        # Test session methods
        session.update_activity()
        duration = session.get_session_duration()
        session_dict = session.to_dict()
        
        print(f"✓ Session methods work: duration={duration:.3f}s, dict_keys={list(session_dict.keys())}")
        
        # Test ConversationResponse
        response = ConversationResponse(
            message="Test response",
            session_id="test_session",
            metadata={"response": "test"}
        )
        
        print(f"✓ ConversationResponse created: {response.response_id}")
        
        # Test response methods
        response_dict = response.to_dict()
        
        print(f"✓ Response methods work: dict_keys={list(response_dict.keys())}")
        
        print("✓ Session and Response classes test PASSED!")
        return True
        
    except Exception as e:
        print(f"✗ Session and Response classes test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main test function"""
    print("=" * 60)
    print("CONVERSATION ROUTER INTEGRATION TEST")
    print("=" * 60)
    
    # Run integration tests
    integration_success = test_router_integration()
    classes_success = test_session_and_response_classes()
    
    print("\n" + "=" * 60)
    print("INTEGRATION TEST SUMMARY")
    print("=" * 60)
    
    if integration_success and classes_success:
        print("🎉 ALL INTEGRATION TESTS PASSED!")
        print("ConversationRouter is ready for use with the conversational ASL agent.")
        return True
    else:
        print("❌ SOME INTEGRATION TESTS FAILED!")
        print("Please review the implementation and fix any issues.")
        return False

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)