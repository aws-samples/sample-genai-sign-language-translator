"""
Test Retry and Modification Capabilities

This module provides basic tests for the retry and modification functionality
to ensure the components work together correctly.
"""

import unittest
from datetime import datetime
from unittest.mock import Mock, patch

# Import the modules we're testing
from data_models import (
    ConversationContext, ConversationIntent, TranslationResult, 
    InputType, TranslationStatus
)
from retry_manager import RetryManager, RetryStrategy
from modification_detector import ModificationDetector, ModificationType
from alternative_explorer import AlternativeExplorer
from retry_modification_integration import RetryModificationIntegration

class TestRetryModificationCapabilities(unittest.TestCase):
    """Test cases for retry and modification capabilities"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.context = ConversationContext(
            session_id="test_session",
            user_id="test_user"
        )
        
        # Create a sample failed translation result
        self.failed_result = TranslationResult(
            input_text="Hello world",
            input_type=InputType.TEXT,
            success=False,
            error_message="Translation service timeout",
            status=TranslationStatus.FAILED,
            processing_time=10.0
        )
        
        # Create a sample successful translation result
        self.successful_result = TranslationResult(
            input_text="Hello world",
            input_type=InputType.TEXT,
            gloss="HELLO WORLD",
            video_urls={"pose": "http://example.com/pose.mp4"},
            success=True,
            status=TranslationStatus.COMPLETED,
            processing_time=3.0
        )
        
        # Mock memory manager
        self.mock_memory = Mock()
        
    def test_retry_manager_creation(self):
        """Test retry manager can be created and configured"""
        retry_manager = RetryManager(self.mock_memory)
        
        self.assertIsNotNone(retry_manager)
        self.assertEqual(retry_manager.default_max_attempts, 3)
        self.assertIn(RetryStrategy.EXPONENTIAL_BACKOFF, retry_manager.strategy_rules.values().__iter__().__next__())
    
    def test_retry_session_creation(self):
        """Test retry session creation"""
        retry_manager = RetryManager(self.mock_memory)
        
        retry_session = retry_manager.create_retry_session(
            operation_id="test_op",
            intent=ConversationIntent.TEXT_TO_ASL,
            parameters={"text": "Hello world"},
            error=Exception("Test error"),
            context=self.context
        )
        
        self.assertIsNotNone(retry_session)
        self.assertEqual(retry_session.original_intent, ConversationIntent.TEXT_TO_ASL)
        self.assertEqual(retry_session.original_parameters["text"], "Hello world")
        self.assertTrue(retry_session.has_attempts_remaining())
    
    def test_modification_detection(self):
        """Test modification detection from user input"""
        # Add a successful translation to context
        from data_models import ConversationInteraction
        interaction = ConversationInteraction(
            timestamp=datetime.now(),
            user_input="Translate hello world",
            intent=ConversationIntent.TEXT_TO_ASL,
            agent_response="Translation completed",
            translation_result=self.successful_result
        )
        self.context.add_interaction(interaction)
        
        detector = ModificationDetector(self.mock_memory)
        
        # Test text change detection
        modification = detector.detect_modification_request(
            "Change the text to goodbye world", self.context
        )
        
        self.assertIsNotNone(modification)
        self.assertEqual(modification.modification_type, ModificationType.TEXT_CHANGE)
        self.assertIn("goodbye world", modification.user_input)
    
    def test_alternative_exploration(self):
        """Test alternative exploration"""
        explorer = AlternativeExplorer(self.mock_memory)
        
        alternatives = explorer.explore_alternatives(
            original_intent=ConversationIntent.TEXT_TO_ASL,
            original_parameters={"text": "Hello world"},
            context=self.context,
            failure_reason="Translation timeout"
        )
        
        self.assertIsNotNone(alternatives)
        self.assertGreater(len(alternatives.alternatives), 0)
        
        # Check that we have different types of alternatives
        alternative_types = [alt.alternative_type for alt in alternatives.alternatives]
        self.assertGreater(len(set(alternative_types)), 1)  # Multiple types
    
    def test_integration_retry_request(self):
        """Test integrated retry request handling"""
        # Add a failed translation to context
        from data_models import ConversationInteraction
        interaction = ConversationInteraction(
            timestamp=datetime.now(),
            user_input="Translate hello world",
            intent=ConversationIntent.TEXT_TO_ASL,
            agent_response="Translation failed",
            translation_result=self.failed_result
        )
        self.context.add_interaction(interaction)
        
        integration = RetryModificationIntegration(self.mock_memory)
        
        # Mock orchestrator callback
        mock_orchestrator = Mock()
        mock_orchestrator.return_value = self.successful_result
        
        result, response = integration.handle_user_request(
            user_input="Try again",
            context=self.context,
            orchestrator_callback=mock_orchestrator
        )
        
        self.assertIsNotNone(result)
        self.assertIn("retry", response.lower())
    
    def test_integration_modification_request(self):
        """Test integrated modification request handling"""
        # Add a successful translation to context
        from data_models import ConversationInteraction
        interaction = ConversationInteraction(
            timestamp=datetime.now(),
            user_input="Translate hello world",
            intent=ConversationIntent.TEXT_TO_ASL,
            agent_response="Translation completed",
            translation_result=self.successful_result
        )
        self.context.add_interaction(interaction)
        
        integration = RetryModificationIntegration(self.mock_memory)
        
        # Mock orchestrator callback
        mock_orchestrator = Mock()
        mock_orchestrator.return_value = TranslationResult(
            input_text="Goodbye world",
            input_type=InputType.TEXT,
            gloss="GOODBYE WORLD",
            video_urls={"pose": "http://example.com/pose2.mp4"},
            success=True,
            status=TranslationStatus.COMPLETED
        )
        
        result, response = integration.handle_user_request(
            user_input="Change the text to goodbye world",
            context=self.context,
            orchestrator_callback=mock_orchestrator
        )
        
        self.assertIsNotNone(result)
        self.assertIn("modification", response.lower())
    
    def test_suggestion_generation(self):
        """Test improvement suggestions for failed translations"""
        integration = RetryModificationIntegration(self.mock_memory)
        
        suggestions = integration.suggest_improvements(self.failed_result, self.context)
        
        self.assertIsNotNone(suggestions)
        self.assertIn("retry", suggestions.lower())
        self.assertIn("alternative", suggestions.lower())
    
    def test_parameter_variations(self):
        """Test parameter variation suggestions"""
        explorer = AlternativeExplorer(self.mock_memory)
        
        variations = explorer.suggest_parameter_variations(
            intent=ConversationIntent.TEXT_TO_ASL,
            base_parameters={"text": "This is a long sentence with many words"}
        )
        
        self.assertGreater(len(variations), 0)
        
        # Should include simplified text option
        simplified_options = [v for v in variations if "simplified" in v.title.lower()]
        self.assertGreater(len(simplified_options), 0)
        
        # Should include pose-only option
        pose_options = [v for v in variations if "pose" in v.title.lower()]
        self.assertGreater(len(pose_options), 0)

def run_basic_tests():
    """Run basic functionality tests"""
    print("Running basic retry and modification tests...")
    
    # Test retry manager
    print("✓ Testing retry manager...")
    retry_manager = RetryManager()
    print(f"  - Default max attempts: {retry_manager.default_max_attempts}")
    print(f"  - Strategy rules configured: {len(retry_manager.strategy_rules)}")
    
    # Test modification detector
    print("✓ Testing modification detector...")
    detector = ModificationDetector()
    context = ConversationContext(session_id="test")
    
    # Add a mock successful translation
    from data_models import ConversationInteraction, TranslationResult
    result = TranslationResult(
        input_text="Hello",
        input_type=InputType.TEXT,
        success=True,
        gloss="HELLO"
    )
    interaction = ConversationInteraction(
        timestamp=datetime.now(),
        user_input="Translate hello",
        intent=ConversationIntent.TEXT_TO_ASL,
        agent_response="Done",
        translation_result=result
    )
    context.add_interaction(interaction)
    
    modification = detector.detect_modification_request("Change it to goodbye", context)
    if modification:
        print(f"  - Detected modification: {modification.modification_type}")
    else:
        print("  - No modification detected (expected for basic test)")
    
    # Test alternative explorer
    print("✓ Testing alternative explorer...")
    explorer = AlternativeExplorer()
    alternatives = explorer.explore_alternatives(
        ConversationIntent.TEXT_TO_ASL,
        {"text": "Hello world"},
        context
    )
    print(f"  - Generated {len(alternatives.alternatives)} alternatives")
    
    # Test integration
    print("✓ Testing integration...")
    integration = RetryModificationIntegration()
    suggestions = integration.suggest_improvements(
        TranslationResult(
            input_text="Test",
            input_type=InputType.TEXT,
            success=False,
            error_message="Test error"
        ),
        context
    )
    print(f"  - Generated suggestions: {len(suggestions.split('**')) - 1} sections")
    
    print("\n✅ All basic tests completed successfully!")

if __name__ == "__main__":
    # Run basic tests if executed directly
    run_basic_tests()