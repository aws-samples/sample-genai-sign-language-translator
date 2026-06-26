#!/usr/bin/env python3
"""
Local test script for the AgentCore agent
Tests basic imports and initialization without running the full server
"""

import sys
import os
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

def test_imports():
    """Test that all modules can be imported"""
    print("=" * 60)
    print("Testing Module Imports")
    print("=" * 60)
    
    try:
        print("\n1. Testing signlanguageagent imports...")
        from signlanguageagent import config, utils, monitoring
        print("   ✓ Core modules imported successfully")
        
        print("\n2. Testing configuration...")
        print(f"   Model: {config.model.eng_to_asl_model}")
        print(f"   Region: {config.aws.region}")
        print(f"   Max Tokens: {config.model.max_tokens}")
        print("   ✓ Configuration loaded successfully")
        
        print("\n3. Testing tool handler imports...")
        sys.path.insert(0, str(functions_dir / 'text2gloss'))
        sys.path.insert(0, str(functions_dir / 'gloss2pose'))
        sys.path.insert(0, str(functions_dir / 'audio_processing'))
        sys.path.insert(0, str(functions_dir / 'asl_analysis'))
        
        from text2gloss_handler import text_to_asl_gloss
        print("   ✓ text2gloss_handler imported")
        
        from gloss2pose_handler import gloss_to_video
        print("   ✓ gloss2pose_handler imported")
        
        from audio_processing_handler import process_audio_input
        print("   ✓ audio_processing_handler imported")
        
        from asl_analysis_handler import analyze_asl_video_stream
        print("   ✓ asl_analysis_handler imported")
        
        print("\n4. Testing agent initialization (without running)...")
        # Import but don't run the agent
        import signlanguageagent.slagent as slagent_module
        
        # Check that key components exist
        assert hasattr(slagent_module, 'agent'), "Agent not initialized"
        assert hasattr(slagent_module, 'app'), "App not initialized"
        assert hasattr(slagent_module, 'health_check'), "health_check function not found"
        
        print("   ✓ Agent module structure validated")
        
        print("\n5. Testing health check function...")
        health = slagent_module.health_check()
        print(f"   Status: {health['status']}")
        print(f"   Tools: {health['tools_count']}")
        print(f"   Available tools: {', '.join(health['available_tools'])}")
        print("   ✓ Health check passed")
        
        print("\n" + "=" * 60)
        print("✓ All tests passed successfully!")
        print("=" * 60)
        return True
        
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_agent_structure():
    """Test the agent structure and available tools"""
    print("\n" + "=" * 60)
    print("Testing Agent Structure")
    print("=" * 60)
    
    try:
        from signlanguageagent.slagent import agent, available_tools
        
        print(f"\n1. Agent model: {agent.model}")
        print(f"2. Available tools count: {len(available_tools)}")
        print(f"3. Tool names:")
        for tool in available_tools:
            print(f"   - {tool.__name__}")
        
        print("\n✓ Agent structure validated")
        return True
        
    except Exception as e:
        print(f"\n✗ Agent structure test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("AgentCore Local Test Suite")
    print("=" * 60)
    
    results = []
    
    # Test 1: Imports
    results.append(("Module Imports", test_imports()))
    
    # Test 2: Agent Structure
    results.append(("Agent Structure", test_agent_structure()))
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    for test_name, passed in results:
        status = "✓ PASSED" if passed else "✗ FAILED"
        print(f"{test_name}: {status}")
    
    all_passed = all(result[1] for result in results)
    
    if all_passed:
        print("\n✓ All tests passed! Agent is ready for deployment.")
        return 0
    else:
        print("\n✗ Some tests failed. Please fix the issues before deploying.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
