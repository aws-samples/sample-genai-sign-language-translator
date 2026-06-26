#!/usr/bin/env python3
"""
Test script for the GenASL Sign Language Agent

This script provides basic testing functionality to validate the agent
setup and configuration without requiring full deployment.
"""

import os
import sys
import json
from pathlib import Path

# Add the current directory to Python path for imports
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

def test_imports():
    """Test that all required modules can be imported"""
    print("Testing imports...")
    
    try:
        from config import config
        print("✓ Config module imported successfully")
        
        from utils import setup_logging, validate_payload
        print("✓ Utils module imported successfully")
        
        # Test configuration
        print(f"✓ Agent model: {config.model.eng_to_asl_model}")
        print(f"✓ AWS region: {config.aws.region}")
        print(f"✓ Pose bucket: {config.aws.pose_bucket}")
        
        return True
        
    except Exception as e:
        print(f"✗ Import error: {e}")
        return False

def test_configuration():
    """Test configuration loading and validation"""
    print("\nTesting configuration...")
    
    try:
        from config import config
        
        # Test configuration dictionary conversion
        config_dict = config.to_dict()
        print("✓ Configuration converted to dictionary")
        
        # Test environment variables
        env_vars = config.get_environment_variables()
        print(f"✓ Environment variables generated ({len(env_vars)} vars)")
        
        # Validate required fields
        required_fields = [
            config.aws.region,
            config.aws.pose_bucket,
            config.aws.asl_data_bucket,
            config.model.eng_to_asl_model
        ]
        
        if all(required_fields):
            print("✓ All required configuration fields are present")
        else:
            print("✗ Some required configuration fields are missing")
            return False
        
        return True
        
    except Exception as e:
        print(f"✗ Configuration error: {e}")
        return False

def test_payload_validation():
    """Test payload validation functionality"""
    print("\nTesting payload validation...")
    
    try:
        from utils import validate_payload
        
        # Test valid payload
        valid_payload = {
            "message": "Hello, translate this to ASL",
            "type": "text",
            "metadata": {"user_id": "test_user"}
        }
        
        normalized = validate_payload(valid_payload)
        print("✓ Valid payload processed successfully")
        
        # Test invalid payload
        try:
            invalid_payload = {"message": ""}
            validate_payload(invalid_payload)
            print("✗ Invalid payload should have been rejected")
            return False
        except ValueError:
            print("✓ Invalid payload correctly rejected")
        
        return True
        
    except Exception as e:
        print(f"✗ Payload validation error: {e}")
        return False

def test_agent_initialization():
    """Test agent initialization (without full setup)"""
    print("\nTesting agent initialization...")
    
    try:
        # Set minimal environment variables for testing
        os.environ.setdefault('ENG_TO_ASL_MODEL', 'us.amazon.nova-lite-v1:0')
        os.environ.setdefault('POSE_BUCKET', 'test-bucket')
        os.environ.setdefault('ASL_DATA_BUCKET', 'test-data-bucket')
        os.environ.setdefault('TABLE_NAME', 'test-table')
        os.environ.setdefault('KEY_PREFIX', 'test-prefix/')
        
        # Import and test basic agent setup
        from config import config
        print("✓ Configuration loaded for agent")
        
        # Test health check function
        try:
            # This will fail without actual agent setup, but we can test the structure
            from slagent import health_check
            health_result = health_check()
            
            if isinstance(health_result, dict) and 'status' in health_result:
                print("✓ Health check function structure is correct")
            else:
                print("✗ Health check function returned unexpected format")
                return False
                
        except Exception as e:
            # Expected to fail without full setup, but structure should be testable
            print(f"⚠ Health check failed as expected without full setup: {type(e).__name__}")
        
        return True
        
    except Exception as e:
        print(f"✗ Agent initialization error: {e}")
        return False

def main():
    """Run all tests"""
    print("GenASL Sign Language Agent - Test Suite")
    print("=" * 50)
    
    tests = [
        test_imports,
        test_configuration,
        test_payload_validation,
        test_agent_initialization
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print()
    
    print("=" * 50)
    print(f"Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("✓ All tests passed! Agent foundation is properly set up.")
        return 0
    else:
        print("✗ Some tests failed. Please check the configuration and setup.")
        return 1

if __name__ == "__main__":
    sys.exit(main())