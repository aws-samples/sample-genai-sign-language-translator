"""
Test Response Formatter

Simple test to verify the response formatter functionality works correctly.
"""

import sys
from pathlib import Path

# Add current directory to path for imports
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

from response_formatter import ConversationResponseFormatter
from data_models import (
    ConversationContext, 
    ConversationInteraction, 
    TranslationResult, 
    ConversationIntent,
    InputType,
    create_text_translation_result,
    create_audio_translation_result,
    create_asl_analysis_result
)
from datetime import datetime

def test_response_formatter():
    """Test the response formatter with various scenarios"""
    formatter = ConversationResponseFormatter()
    
    # Create test context
    context = ConversationContext(
        session_id="test_session",
        user_id="test_user"
    )
    
    print("=== Testing Response Formatter ===\n")
    
    # Test 1: Text to ASL translation response
    print("1. Testing Text-to-ASL Translation Response:")
    text_result = create_text_translation_result(
        input_text="Hello, how are you?",
        gloss="HELLO HOW YOU",
        video_urls={
            'pose': 'https://example.com/pose.mp4',
            'sign': 'https://example.com/sign.mp4',
            'avatar': 'https://example.com/avatar.mp4'
        },
        processing_time=2.3,
        success=True
    )
    
    response = formatter.format_translation_response(text_result, context)
    print(response)
    print("\n" + "="*50 + "\n")
    
    # Test 2: Help response
    print("2. Testing Help Response:")
    help_response = formatter.format_help_response('general', context)
    print(help_response)
    print("\n" + "="*50 + "\n")
    
    # Test 3: Error response
    print("3. Testing Error Response:")
    error_response = formatter.format_error_response(
        Exception("Network timeout occurred"), 
        context
    )
    print(error_response)
    print("\n" + "="*50 + "\n")
    
    # Test 4: Proactive tips (after adding some history)
    print("4. Testing Proactive Tips:")
    # Add some interactions to context
    for i in range(3):
        interaction = ConversationInteraction(
            timestamp=datetime.now(),
            user_input=f"Test input {i}",
            intent=ConversationIntent.TEXT_TO_ASL,
            agent_response="Test response",
            translation_result=text_result
        )
        context.add_interaction(interaction)
    
    proactive_tip = formatter.generate_proactive_tips(context)
    if proactive_tip:
        print(proactive_tip)
    else:
        print("No proactive tips generated for this context")
    print("\n" + "="*50 + "\n")
    
    # Test 5: Different detail levels
    print("5. Testing Different Detail Levels:")
    
    print("Brief format:")
    brief_response = formatter.format_translation_response(text_result, context, "brief")
    print(brief_response)
    print("\n" + "-"*30 + "\n")
    
    print("Detailed format:")
    detailed_response = formatter.format_translation_response(text_result, context, "detailed")
    print(detailed_response)
    print("\n" + "="*50 + "\n")
    
    # Test 6: Audio translation response
    print("6. Testing Audio-to-ASL Translation Response:")
    audio_result = create_audio_translation_result(
        input_text="audio_file.mp3",
        transcribed_text="Good morning everyone",
        gloss="GOOD MORNING EVERYONE",
        video_urls={
            'pose': 'https://example.com/audio_pose.mp4',
            'avatar': 'https://example.com/audio_avatar.mp4'
        },
        processing_time=5.1,
        success=True
    )
    
    audio_response = formatter.format_translation_response(audio_result, context)
    print(audio_response)
    print("\n" + "="*50 + "\n")
    
    print("=== Response Formatter Tests Complete ===")

if __name__ == "__main__":
    test_response_formatter()