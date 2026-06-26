#!/usr/bin/env python3
"""
Validate Error Handling Implementation

Simple validation script to test the error handling components.
"""

import sys
import os

# Add current directory to path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

def test_error_handling():
    """Test the error handling implementation"""
    print("Testing Error Handling Implementation...")
    
    try:
        # Test ConversationErrorHandler
        from error_handler import ConversationErrorHandler, ErrorType, ErrorSeverity
        print("✓ ConversationErrorHandler imports successfully")
        
        handler = ConversationErrorHandler()
        print("✓ ConversationErrorHandler initializes successfully")
        
        # Test error classification
        test_error = ValueError("test validation error")
        classification = handler.classify_error(test_error)
        print(f"✓ Error classification works: {classification.error_type.value}")
        print(f"  - Severity: {classification.severity.value}")
        print(f"  - Recoverable: {classification.is_recoverable}")
        print(f"  - User actionable: {classification.user_actionable}")
        
    except Exception as e:
        print(f"✗ ConversationErrorHandler test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    try:
        # Test AlternativeApproachSuggester
        from alternative_suggestions import AlternativeApproachSuggester
        print("✓ AlternativeApproachSuggester imports successfully")
        
        suggester = AlternativeApproachSuggester()
        print("✓ AlternativeApproachSuggester initializes successfully")
        
        # Test suggestion generation
        from data_models import ConversationContext
        context = ConversationContext()
        suggestions = suggester.generate_suggestions(
            "text_to_asl", classification, context
        )
        print(f"✓ Generated {len(suggestions)} alternative suggestions")
        
        if suggestions:
            first_suggestion = suggestions[0]
            print(f"  - First suggestion: {first_suggestion.title}")
            print(f"  - Priority: {first_suggestion.priority.value}")
        
    except Exception as e:
        print(f"✗ AlternativeApproachSuggester test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    try:
        # Test GracefulErrorRecovery
        from error_recovery import GracefulErrorRecovery
        print("✓ GracefulErrorRecovery imports successfully")
        
        recovery = GracefulErrorRecovery(handler, suggester)
        print("✓ GracefulErrorRecovery initializes successfully")
        
        # Test recovery decision logic
        should_recover = recovery.should_attempt_recovery(test_error, context)
        print(f"✓ Recovery decision logic works: should_recover = {should_recover}")
        
    except Exception as e:
        print(f"✗ GracefulErrorRecovery test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    try:
        # Test conversational response generation
        response = handler.handle_error(test_error, context)
        print("✓ Conversational error response generated successfully")
        print(f"  - Response length: {len(response)} characters")
        print(f"  - Contains 'sorry': {'sorry' in response.lower()}")
        
    except Exception as e:
        print(f"✗ Error response generation failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    try:
        # Test input format guidance
        from data_models import InputType
        guidance = suggester.get_input_format_guidance(InputType.TEXT)
        print("✓ Input format guidance generated successfully")
        print(f"  - Title: {guidance['title']}")
        print(f"  - Guidelines count: {len(guidance['guidelines'])}")
        
    except Exception as e:
        print(f"✗ Input format guidance test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print("\n" + "="*50)
    print("All error handling tests passed successfully!")
    print("="*50)
    return True

def test_integration():
    """Test integration with conversational agent"""
    print("\nTesting Integration with Conversational Agent...")
    
    try:
        # Test that the conversational agent can use error handling
        from conversational_agent import ConversationalASLAgent
        from data_models import ConversationContext
        
        # Mock the memory manager to avoid AgentCore dependencies
        import unittest.mock
        with unittest.mock.patch('conversational_agent.ConversationMemoryManager'):
            agent = ConversationalASLAgent()
            print("✓ ConversationalASLAgent with error handling initializes successfully")
        
        context = ConversationContext(session_id="test", user_id="test")
        
        # Test translation error handling
        test_error = Exception("translation failed")
        response = agent.handle_translation_error(
            test_error, "text_to_asl", {"text": "test"}, context
        )
        print("✓ Translation error handling works")
        print(f"  - Response length: {len(response)} characters")
        
        # Test input format correction
        format_response = agent.suggest_input_format_corrections(
            "audio", "unsupported format", context
        )
        print("✓ Input format correction suggestions work")
        print(f"  - Response length: {len(format_response)} characters")
        
        # Test retry workflow
        retry_response = agent.generate_retry_workflow(
            "text to asl translation", context
        )
        print("✓ Retry workflow generation works")
        print(f"  - Response length: {len(retry_response)} characters")
        
    except Exception as e:
        print(f"✗ Integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print("✓ Integration tests passed!")
    return True

def main():
    """Main test function"""
    print("Validating Error Handling Implementation")
    print("=" * 50)
    
    # Test basic error handling components
    basic_success = test_error_handling()
    
    if not basic_success:
        print("\nBasic tests failed. Stopping here.")
        return False
    
    # Test integration
    integration_success = test_integration()
    
    if basic_success and integration_success:
        print("\n🎉 All validation tests passed!")
        print("Error handling implementation is working correctly.")
        return True
    else:
        print("\n❌ Some tests failed.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)