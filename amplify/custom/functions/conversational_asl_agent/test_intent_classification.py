#!/usr/bin/env python3
"""
Unit Tests for Intent Classification

Tests for the ConversationIntentClassifier to validate intent detection,
parameter extraction, and context-aware classification functionality.
"""

import unittest
from unittest.mock import Mock, patch
import sys
from pathlib import Path

# Add current directory to path for imports
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

try:
    from intent_classifier import ConversationIntentClassifier
    from data_models import (
        ConversationIntent, InputType, ConversationContext, 
        ConversationInteraction, TranslationResult
    )
except ImportError:
    # Handle relative import issues for testing
    import sys
    import os
    sys.path.append(os.path.dirname(__file__))
    from intent_classifier import ConversationIntentClassifier
    from data_models import (
        ConversationIntent, InputType, ConversationContext, 
        ConversationInteraction, TranslationResult
    )
from datetime import datetime

class TestConversationIntentClassifier(unittest.TestCase):
    """Test cases for ConversationIntentClassifier"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.classifier = ConversationIntentClassifier()
        self.test_context = ConversationContext(
            session_id="test_session",
            user_id="test_user"
        )
    
    def test_text_to_asl_intent_detection(self):
        """Test detection of text-to-ASL translation intents"""
        test_cases = [
            "Translate 'Hello world' to ASL",
            "Convert this text: 'How are you today?'",
            "Turn 'Good morning' into sign language",
            "Can you translate 'Thank you' to ASL?",
            "Please help me translate 'I love you'",
            "How do you sign 'Happy birthday'?",
            "What is 'Good luck' in ASL?"
        ]
        
        for test_input in test_cases:
            with self.subTest(input=test_input):
                result = self.classifier.classify_intent(test_input, self.test_context)
                
                self.assertEqual(result.intent, ConversationIntent.TEXT_TO_ASL)
                self.assertGreater(result.confidence, 0.6)
                self.assertEqual(result.input_type, InputType.TEXT)
                self.assertIn('text', result.parameters)
    
    def test_audio_to_asl_intent_detection(self):
        """Test detection of audio-to-ASL translation intents"""
        test_cases = [
            "Translate this audio file to ASL",
            "Convert my voice recording to sign language",
            "Process this audio and make it into ASL",
            "I have an audio file to translate",
            "Can you analyze this recording and convert to ASL?",
            "From audio to sign language please",
            "Transcribe and translate this audio"
        ]
        
        for test_input in test_cases:
            with self.subTest(input=test_input):
                result = self.classifier.classify_intent(test_input, self.test_context)
                
                self.assertEqual(result.intent, ConversationIntent.AUDIO_TO_ASL)
                self.assertGreater(result.confidence, 0.6)
                self.assertEqual(result.input_type, InputType.AUDIO)
    
    def test_asl_to_text_intent_detection(self):
        """Test detection of ASL-to-text analysis intents"""
        test_cases = [
            "Analyze this ASL video",
            "What does this sign language video say?",
            "Interpret this ASL signing",
            "Can you read this sign language?",
            "Translate this ASL video to English",
            "I have an ASL video to analyze",
            "What is this signing saying?"
        ]
        
        for test_input in test_cases:
            with self.subTest(input=test_input):
                result = self.classifier.classify_intent(test_input, self.test_context)
                
                self.assertEqual(result.intent, ConversationIntent.ASL_TO_TEXT)
                self.assertGreater(result.confidence, 0.6)
                self.assertEqual(result.input_type, InputType.VIDEO)
    
    def test_help_request_intent_detection(self):
        """Test detection of help request intents"""
        test_cases = [
            "Help me understand how this works",
            "What can you do?",
            "I need assistance",
            "How do I use this system?",
            "What are your capabilities?",
            "Show me examples",
            "I'm new to this, can you guide me?",
            "Getting started help"
        ]
        
        for test_input in test_cases:
            with self.subTest(input=test_input):
                result = self.classifier.classify_intent(test_input, self.test_context)
                
                self.assertEqual(result.intent, ConversationIntent.HELP_REQUEST)
                self.assertGreater(result.confidence, 0.6)
    
    def test_status_check_intent_detection(self):
        """Test detection of status check intents"""
        test_cases = [
            "What's the status of my translation?",
            "Is my request done yet?",
            "How long will this take?",
            "Check progress please",
            "What's happening with my job?",
            "Still processing?",
            "How much time is left?"
        ]
        
        for test_input in test_cases:
            with self.subTest(input=test_input):
                result = self.classifier.classify_intent(test_input, self.test_context)
                
                self.assertEqual(result.intent, ConversationIntent.STATUS_CHECK)
                self.assertGreater(result.confidence, 0.6)
    
    def test_retry_request_intent_detection(self):
        """Test detection of retry request intents"""
        test_cases = [
            "Try that again please",
            "That didn't work, retry",
            "Can you redo that translation?",
            "Let's try a different approach",
            "That failed, try again",
            "Repeat that last action",
            "Do that over"
        ]
        
        for test_input in test_cases:
            with self.subTest(input=test_input):
                result = self.classifier.classify_intent(test_input, self.test_context)
                
                self.assertEqual(result.intent, ConversationIntent.RETRY_REQUEST)
                self.assertGreater(result.confidence, 0.6)
                self.assertTrue(result.requires_context)
    
    def test_context_reference_intent_detection(self):
        """Test detection of context reference intents"""
        test_cases = [
            "Show me that last translation again",
            "What about the previous result?",
            "Can you display that first video?",
            "The translation you just did",
            "That one from before",
            "The second result please"
        ]
        
        for test_input in test_cases:
            with self.subTest(input=test_input):
                result = self.classifier.classify_intent(test_input, self.test_context)
                
                self.assertEqual(result.intent, ConversationIntent.CONTEXT_REFERENCE)
                self.assertGreater(result.confidence, 0.6)
                self.assertTrue(result.requires_context)
    
    def test_greeting_intent_detection(self):
        """Test detection of greeting intents"""
        test_cases = [
            "Hello",
            "Hi there",
            "Good morning",
            "Good afternoon",
            "Hey",
            "How are you?",
            "Nice to meet you"
        ]
        
        for test_input in test_cases:
            with self.subTest(input=test_input):
                result = self.classifier.classify_intent(test_input, self.test_context)
                
                self.assertEqual(result.intent, ConversationIntent.GREETING)
                self.assertGreater(result.confidence, 0.6)
    
    def test_parameter_extraction_text_translation(self):
        """Test parameter extraction for text translation requests"""
        test_cases = [
            ("Translate 'Hello world'", "Hello world"),
            ("Convert this text: 'How are you?'", "How are you?"),
            ("Turn 'Good morning' into ASL", "Good morning"),
            ("Please translate I love you", "I love you"),
            ("How do you sign Happy birthday?", "Happy birthday")
        ]
        
        for test_input, expected_text in test_cases:
            with self.subTest(input=test_input):
                result = self.classifier.classify_intent(test_input, self.test_context)
                
                self.assertEqual(result.intent, ConversationIntent.TEXT_TO_ASL)
                self.assertIn('text', result.parameters)
                self.assertEqual(result.parameters['text'], expected_text)
    
    def test_context_aware_classification(self):
        """Test context-aware intent classification"""
        # Create context with previous translation interactions
        context_with_history = ConversationContext(
            session_id="test_session",
            user_id="test_user"
        )
        
        # Add previous text-to-ASL interactions
        for i in range(3):
            interaction = ConversationInteraction(
                timestamp=datetime.now(),
                user_input=f"Translate 'test {i}'",
                intent=ConversationIntent.TEXT_TO_ASL,
                agent_response="Translation completed",
                translation_result=None
            )
            context_with_history.add_interaction(interaction)
        
        # Test that context boosts confidence for similar intents
        result_with_context = self.classifier.classify_intent(
            "Convert this text", context_with_history
        )
        result_without_context = self.classifier.classify_intent(
            "Convert this text", None
        )
        
        # Context should boost confidence for text translation
        self.assertGreaterEqual(
            result_with_context.confidence, 
            result_without_context.confidence
        )
    
    def test_confidence_scoring(self):
        """Test confidence scoring accuracy"""
        # High confidence cases
        high_confidence_cases = [
            "Translate 'Hello world' to ASL",
            "Analyze this ASL video",
            "I have an audio file to translate"
        ]
        
        for test_input in high_confidence_cases:
            with self.subTest(input=test_input):
                result = self.classifier.classify_intent(test_input, self.test_context)
                self.assertGreater(result.confidence, 0.8)
        
        # Lower confidence cases (ambiguous)
        lower_confidence_cases = [
            "Can you help with this?",
            "What about that?",
            "Process this"
        ]
        
        for test_input in lower_confidence_cases:
            with self.subTest(input=test_input):
                result = self.classifier.classify_intent(test_input, self.test_context)
                # Should still classify but with lower confidence
                self.assertLess(result.confidence, 0.8)
    
    def test_alternative_intents(self):
        """Test alternative intent suggestions"""
        # Ambiguous input that could match multiple intents
        ambiguous_input = "translate this"
        
        result = self.classifier.classify_intent(ambiguous_input, self.test_context)
        
        # Should have alternative intents
        self.assertGreater(len(result.alternative_intents), 0)
        
        # Alternative intents should be tuples of (intent, confidence)
        for alt_intent, alt_confidence in result.alternative_intents:
            self.assertIsInstance(alt_intent, ConversationIntent)
            self.assertIsInstance(alt_confidence, float)
            self.assertGreaterEqual(alt_confidence, 0.0)
            self.assertLessEqual(alt_confidence, 1.0)
    
    def test_unknown_intent_handling(self):
        """Test handling of unknown or unclear intents"""
        unclear_inputs = [
            "asdfghjkl",
            "...",
            "xyz 123",
            "",
            "   "
        ]
        
        for test_input in unclear_inputs:
            with self.subTest(input=test_input):
                result = self.classifier.classify_intent(test_input, self.test_context)
                
                # Should classify as unknown with low confidence
                self.assertEqual(result.intent, ConversationIntent.UNKNOWN)
                self.assertLess(result.confidence, 0.6)
    
    def test_input_type_detection(self):
        """Test input type detection from text analysis"""
        test_cases = [
            ("Translate this text", InputType.TEXT),
            ("Process this audio file", InputType.AUDIO),
            ("Analyze this video", InputType.VIDEO),
            ("Stream analysis please", InputType.STREAM),
            ("Convert voice recording", InputType.AUDIO)
        ]
        
        for test_input, expected_type in test_cases:
            with self.subTest(input=test_input):
                result = self.classifier.classify_intent(test_input, self.test_context)
                self.assertEqual(result.input_type, expected_type)
    
    def test_requires_context_detection(self):
        """Test detection of intents that require context"""
        context_required_inputs = [
            "Show me that again",
            "Try that once more",
            "What's the status?",
            "That last translation"
        ]
        
        for test_input in context_required_inputs:
            with self.subTest(input=test_input):
                result = self.classifier.classify_intent(test_input, self.test_context)
                self.assertTrue(result.requires_context)
        
        context_not_required_inputs = [
            "Translate 'hello'",
            "Help me please",
            "Good morning"
        ]
        
        for test_input in context_not_required_inputs:
            with self.subTest(input=test_input):
                result = self.classifier.classify_intent(test_input, self.test_context)
                self.assertFalse(result.requires_context)
    
    def test_error_handling(self):
        """Test error handling in intent classification"""
        # Test with None input
        result = self.classifier.classify_intent(None, self.test_context)
        self.assertEqual(result.intent, ConversationIntent.UNKNOWN)
        
        # Test with invalid context
        result = self.classifier.classify_intent("Hello", None)
        self.assertIsNotNone(result)
        self.assertIsInstance(result.intent, ConversationIntent)

class TestIntentClassifierPatterns(unittest.TestCase):
    """Test specific pattern matching functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.classifier = ConversationIntentClassifier()
    
    def test_text_extraction_patterns(self):
        """Test text extraction from various input patterns"""
        test_cases = [
            ("Translate 'Hello world'", "Hello world"),
            ('Convert "How are you?"', "How are you?"),
            ("Turn this into ASL: Good morning", "Good morning"),
            ("Please translate I am happy", "I am happy"),
            ("Make ASL video for Thank you very much", "Thank you very much")
        ]
        
        for test_input, expected_text in test_cases:
            with self.subTest(input=test_input):
                extracted = self.classifier._extract_text_content(
                    test_input, 
                    self.classifier.intent_patterns[ConversationIntent.TEXT_TO_ASL][0]['patterns']
                )
                self.assertEqual(extracted, expected_text)
    
    def test_audio_parameter_extraction(self):
        """Test audio parameter extraction"""
        test_cases = [
            ("Process audio file named recording.mp3", {"audio_file": "recording.mp3"}),
            ("Translate this wav file", {"preferred_format": "wav"}),
            ("I have an audio recording called interview.m4a", {"audio_file": "interview.m4a"})
        ]
        
        for test_input, expected_params in test_cases:
            with self.subTest(input=test_input):
                extracted = self.classifier._extract_audio_parameters(test_input)
                for key, value in expected_params.items():
                    self.assertIn(key, extracted)
                    self.assertEqual(extracted[key], value)
    
    def test_video_parameter_extraction(self):
        """Test video parameter extraction"""
        test_cases = [
            ("Analyze video file called signing.mp4", {"video_file": "signing.mp4"}),
            ("Process this stream in real-time", {"analysis_type": "stream"}),
            ("I have a video to analyze", {"analysis_type": "file"})
        ]
        
        for test_input, expected_params in test_cases:
            with self.subTest(input=test_input):
                extracted = self.classifier._extract_video_parameters(test_input)
                for key, value in expected_params.items():
                    self.assertIn(key, extracted)
                    self.assertEqual(extracted[key], value)
    
    def test_help_topic_extraction(self):
        """Test help topic extraction"""
        test_cases = [
            ("help with translation", "translation"),
            ("show me audio features", "audio"),
            ("what are your capabilities?", "features"),
            ("I'm new, getting started", "getting_started"),
            ("give me examples", "examples"),
            ("help with video analysis", "video")
        ]
        
        for test_input, expected_topic in test_cases:
            with self.subTest(input=test_input):
                extracted = self.classifier._extract_help_topic(test_input.lower())
                self.assertEqual(extracted, expected_topic)

if __name__ == '__main__':
    unittest.main()