"""
Test Error Handling Implementation

Basic tests to validate the error handling and recovery components
of the conversational ASL agent.
"""

import unittest
import asyncio
from datetime import datetime
from unittest.mock import Mock, patch

from .error_handler import ConversationErrorHandler, ErrorType, ErrorSeverity
from .alternative_suggestions import AlternativeApproachSuggester, AlternativeType
from .error_recovery import GracefulErrorRecovery, RecoveryResult
from .data_models import ConversationContext, ConversationInteraction, ConversationIntent
from .conversational_agent import ConversationalASLAgent

class TestErrorHandling(unittest.TestCase):
    """Test cases for error handling functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.error_handler = ConversationErrorHandler()
        self.alternative_suggester = AlternativeApproachSuggester()
        self.error_recovery = GracefulErrorRecovery(self.error_handler, self.alternative_suggester)
        self.context = ConversationContext(
            session_id="test_session",
            user_id="test_user"
        )
    
    def test_error_classification(self):
        """Test error classification functionality"""
        # Test user input error
        user_error = ValueError("invalid input format")
        classification = self.error_handler.classify_error(user_error)
        
        self.assertEqual(classification.error_type, ErrorType.VALIDATION_ERROR)
        self.assertEqual(classification.severity, ErrorSeverity.LOW)
        self.assertTrue(classification.is_recoverable)
        self.assertTrue(classification.user_actionable)
    
    def test_translation_error_classification(self):
        """Test classification of translation-specific errors"""
        translation_error = Exception("translation failed")
        classification = self.error_handler.classify_error(translation_error)
        
        self.assertEqual(classification.error_type, ErrorType.TRANSLATION_ERROR)
        self.assertEqual(classification.severity, ErrorSeverity.MEDIUM)
        self.assertTrue(classification.is_recoverable)
    
    def test_error_response_generation(self):
        """Test conversational error response generation"""
        error = Exception("test error")
        classification = self.error_handler.classify_error(error)
        
        response = self.error_handler.generate_error_response(
            error, classification, self.context
        )
        
        self.assertIsInstance(response, str)
        self.assertGreater(len(response), 0)
        self.assertIn("sorry", response.lower())  # Should be conversational
    
    def test_alternative_suggestions_generation(self):
        """Test generation of alternative approach suggestions"""
        error = Exception("translation failed")
        classification = self.error_handler.classify_error(error)
        
        suggestions = self.alternative_suggester.generate_suggestions(
            "text_to_asl", classification, self.context
        )
        
        self.assertIsInstance(suggestions, list)
        self.assertGreater(len(suggestions), 0)
        
        # Check first suggestion structure
        first_suggestion = suggestions[0]
        self.assertIsInstance(first_suggestion.title, str)
        self.assertIsInstance(first_suggestion.description, str)
        self.assertIsInstance(first_suggestion.instructions, list)
    
    def test_input_format_guidance(self):
        """Test input format guidance generation"""
        from .data_models import InputType
        
        guidance = self.alternative_suggester.get_input_format_guidance(InputType.TEXT)
        
        self.assertIn('title', guidance)
        self.assertIn('description', guidance)
        self.assertIn('guidelines', guidance)
        self.assertIsInstance(guidance['guidelines'], list)
    
    def test_retry_workflow_suggestions(self):
        """Test retry workflow suggestion generation"""
        workflow = self.alternative_suggester.generate_retry_workflow_suggestions(
            "text to asl translation", self.context
        )
        
        self.assertIsInstance(workflow, list)
        self.assertGreater(len(workflow), 0)
        
        # Each step should be a string
        for step in workflow:
            self.assertIsInstance(step, str)
            self.assertGreater(len(step), 0)
    
    def test_recovery_strategy_determination(self):
        """Test recovery strategy determination"""
        error = Exception("network timeout")
        classification = self.error_handler.classify_error(error)
        
        strategies = self.error_recovery._determine_recovery_strategies(
            classification, self.context
        )
        
        self.assertIsInstance(strategies, list)
        self.assertGreater(len(strategies), 0)
    
    def test_should_attempt_recovery(self):
        """Test recovery attempt decision logic"""
        # Should attempt recovery for recoverable errors
        recoverable_error = Exception("translation failed")
        should_recover = self.error_recovery.should_attempt_recovery(
            recoverable_error, self.context
        )
        self.assertTrue(should_recover)
        
        # Should not attempt recovery if too many errors
        high_error_context = ConversationContext(error_count=10)
        should_not_recover = self.error_recovery.should_attempt_recovery(
            recoverable_error, high_error_context
        )
        self.assertFalse(should_not_recover)
    
    async def test_error_recovery_flow(self):
        """Test the complete error recovery flow"""
        error = Exception("test translation error")
        
        # Mock operation function that fails then succeeds
        mock_operation = Mock(side_effect=[error, "success_result"])
        
        result, data, message = await self.error_recovery.recover_from_error(
            error, "test_operation", {"param": "value"}, self.context, mock_operation
        )
        
        # Should return some result (even if not successful)
        self.assertIsInstance(result, RecoveryResult)
        self.assertIsInstance(message, str)
        self.assertGreater(len(message), 0)

class TestConversationalAgentErrorHandling(unittest.TestCase):
    """Test error handling integration in the conversational agent"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Mock the memory manager to avoid AgentCore dependencies
        with patch('sample-genai-sign-language-translator.amplify.custom.functions.conversational_asl_agent.conversational_agent.ConversationMemoryManager'):
            self.agent = ConversationalASLAgent()
        
        self.context = ConversationContext(
            session_id="test_session",
            user_id="test_user"
        )
    
    def test_translation_error_handling(self):
        """Test translation-specific error handling"""
        error = Exception("gloss generation failed")
        
        response = self.agent.handle_translation_error(
            error, "text_to_asl", {"text": "test"}, self.context
        )
        
        self.assertIsInstance(response, str)
        self.assertGreater(len(response), 0)
        self.assertIn("sorry", response.lower())
    
    def test_input_format_correction_suggestions(self):
        """Test input format correction guidance"""
        response = self.agent.suggest_input_format_corrections(
            "audio", "unsupported format", self.context
        )
        
        self.assertIsInstance(response, str)
        self.assertIn("audio", response.lower())
        self.assertIn("format", response.lower())
    
    def test_retry_workflow_generation(self):
        """Test retry workflow generation"""
        response = self.agent.generate_retry_workflow(
            "text to asl translation", self.context
        )
        
        self.assertIsInstance(response, str)
        self.assertIn("step", response.lower())
    
    def test_conversation_error_handling(self):
        """Test conversation-level error handling"""
        error = Exception("conversation processing failed")
        
        response = self.agent._handle_conversation_error(
            error, self.context, "test_session"
        )
        
        self.assertIsInstance(response, str)
        self.assertGreater(len(response), 0)
        
        # Should have incremented error count
        self.assertEqual(self.context.error_count, 1)

def run_basic_functionality_tests():
    """Run basic functionality tests for error handling"""
    print("Testing Error Handling Implementation...")
    
    # Test error handler initialization
    try:
        error_handler = ConversationErrorHandler()
        print("✓ ConversationErrorHandler initialized successfully")
    except Exception as e:
        print(f"✗ ConversationErrorHandler initialization failed: {e}")
        return False
    
    # Test alternative suggester initialization
    try:
        suggester = AlternativeApproachSuggester()
        print("✓ AlternativeApproachSuggester initialized successfully")
    except Exception as e:
        print(f"✗ AlternativeApproachSuggester initialization failed: {e}")
        return False
    
    # Test error recovery initialization
    try:
        recovery = GracefulErrorRecovery(error_handler, suggester)
        print("✓ GracefulErrorRecovery initialized successfully")
    except Exception as e:
        print(f"✗ GracefulErrorRecovery initialization failed: {e}")
        return False
    
    # Test basic error classification
    try:
        test_error = ValueError("test validation error")
        classification = error_handler.classify_error(test_error)
        
        if classification.error_type == ErrorType.VALIDATION_ERROR:
            print("✓ Error classification working correctly")
        else:
            print(f"✗ Error classification incorrect: got {classification.error_type}")
            return False
    except Exception as e:
        print(f"✗ Error classification failed: {e}")
        return False
    
    # Test suggestion generation
    try:
        context = ConversationContext()
        suggestions = suggester.generate_suggestions(
            "test_operation", classification, context
        )
        
        if isinstance(suggestions, list) and len(suggestions) > 0:
            print("✓ Alternative suggestions generated successfully")
        else:
            print("✗ Alternative suggestions generation failed")
            return False
    except Exception as e:
        print(f"✗ Alternative suggestions generation failed: {e}")
        return False
    
    print("All basic error handling tests passed!")
    return True

if __name__ == "__main__":
    # Run basic functionality tests
    success = run_basic_functionality_tests()
    
    if success:
        print("\nRunning detailed unit tests...")
        # Run unit tests
        unittest.main(verbosity=2)
    else:
        print("\nBasic functionality tests failed. Skipping unit tests.")
        exit(1)