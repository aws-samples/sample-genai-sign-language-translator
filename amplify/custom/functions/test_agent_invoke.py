#!/usr/bin/env python3
"""
Test script to invoke the agent locally with a sample prompt
"""

import sys
import os
import json
from pathlib import Path

# Add the functions directory to path
functions_dir = Path(__file__).parent
sys.path.insert(0, str(functions_dir))

# Set required environment variables
os.environ.setdefault('AWS_REGION', 'us-west-2')
os.environ.setdefault('ENG_TO_ASL_MODEL', 'us.amazon.nova-lite-v1:0')
os.environ.setdefault('POSE_BUCKET', 'genasl-avatar')
os.environ.setdefault('ASL_DATA_BUCKET', 'genasl-data')
os.environ.setdefault('KEY_PREFIX', 'aslavatarv2/gloss2pose/lookup/')
os.environ.setdefault('TABLE_NAME', 'Pose_Data6')
os.environ.setdefault('MAX_TOKENS', '3000')
os.environ.setdefault('TEMPERATURE', '0.0')

def test_agent_invoke():
    """Test invoking the agent with a sample prompt"""
    print("=" * 80)
    print("Testing Agent Invocation")
    print("=" * 80)
    
    try:
        # Import the agent invoke function
        from signlanguageagent.slagent import invoke
        
        # Create test payload - use a clear translation request
        payload = {
            "message": "I want to translate 'Hello, how are you?' to American Sign Language",
            "type": "text"
        }
        
        print(f"\nTest Payload:")
        print(json.dumps(payload, indent=2))
        print("\n" + "=" * 80)
        print("Invoking Agent...")
        print("=" * 80 + "\n")
        
        # Invoke the agent
        result = invoke(payload)
        
        print("\n" + "=" * 80)
        print("Agent Response:")
        print("=" * 80)
        print(result)
        print("\n" + "=" * 80)
        
        # Try to parse if it's JSON
        try:
            if isinstance(result, str) and (result.startswith('{') or result.startswith('[')):
                parsed = json.loads(result)
                print("\nParsed JSON Response:")
                print(json.dumps(parsed, indent=2))
        except:
            pass
        
        return True
        
    except Exception as e:
        print(f"\n✗ Error invoking agent: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_agent_invoke()
    sys.exit(0 if success else 1)
