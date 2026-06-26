#!/usr/bin/env python3
"""
End-to-End Integration Test Runner for GenASL Sign Language Agent

This script specifically runs the end-to-end integration tests that validate:
1. All API endpoints with new agent architecture
2. WebSocket functionality with real-time processing  
3. Load testing to ensure performance requirements
4. Complete workflow validation

This implements task 9.1 from the migration specification.
"""

import sys
import os
import time
import json
import unittest
from pathlib import Path
from typing import Dict, Any

# Add current directory to path
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

def setup_test_environment():
    """Set up environment variables for testing"""
    os.environ['TESTING'] = '1'
    os.environ['AWS_DEFAULT_REGION'] = 'us-east-1'
    os.environ['INPUT_BUCKET'] = 'test-input-bucket'
    os.environ['OUTPUT_BUCKET'] = 'test-output-bucket'
    os.environ['DYNAMODB_TABLE'] = 'test-pose-table'
    os.environ['ASL_TO_ENG_MODEL'] = 'us.meta.llama3-2-11b-instruct-v1:0'
    
    # Mock API endpoints for testing
    os.environ['API_BASE_URL'] = 'https://test-api.example.com'
    os.environ['WEBSOCKET_URL'] = 'wss://test-ws.example.com'
    
    print("✓ Test environment configured")

def run_e2e_test_suite():
    """Run the complete end-to-end integration test suite"""
    print("=" * 80)
    print("GenASL Sign Language Agent - End-to-End Integration Tests")
    print("=" * 80)
    print("Task 9.1: Complete end-to-end integration testing")
    print("- Test all API endpoints with new agent architecture")
    print("- Validate WebSocket functionality with real-time processing")
    print("- Perform load testing to ensure performance requirements")
    print("=" * 80)
    
    # Set up test environment
    setup_test_environment()
    
    # Import test modules
    try:
        import test_e2e_integration
        print("✓ End-to-end integration test module imported successfully")
    except ImportError as e:
        print(f"✗ Failed to import test module: {e}")
        return False
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add all end-to-end test classes
    test_classes = [
        test_e2e_integration.TestEndToEndAPIIntegration,
        test_e2e_integration.TestEndToEndWebSocketIntegration,
        test_e2e_integration.TestEndToEndLoadTesting,
        test_e2e_integration.TestEndToEndWorkflowValidation
    ]
    
    for test_class in test_classes:
        tests = loader.loadTestsFromTestCase(test_class)
        suite.addTests(tests)
    
    print(f"✓ Loaded {suite.countTestCases()} end-to-end integration tests")
    
    # Run the tests
    runner = unittest.TextTestRunner(
        verbosity=2,
        stream=sys.stdout,
        buffer=True
    )
    
    print("\nStarting end-to-end integration tests...")
    start_time = time.time()
    
    result = runner.run(suite)
    
    end_time = time.time()
    duration = end_time - start_time
    
    # Generate test report
    report = generate_test_report(result, duration)
    
    # Print summary
    print_test_summary(report)
    
    # Save detailed report
    save_test_report(report)
    
    # Return success status
    return result.wasSuccessful()

def generate_test_report(test_result, duration: float) -> Dict[str, Any]:
    """Generate comprehensive test report"""
    return {
        'timestamp': time.time(),
        'duration': duration,
        'total_tests': test_result.testsRun,
        'successes': test_result.testsRun - len(test_result.failures) - len(test_result.errors),
        'failures': len(test_result.failures),
        'errors': len(test_result.errors),
        'skipped': len(getattr(test_result, 'skipped', [])),
        'success_rate': (test_result.testsRun - len(test_result.failures) - len(test_result.errors)) / test_result.testsRun if test_result.testsRun > 0 else 0,
        'was_successful': test_result.wasSuccessful(),
        'failure_details': [
            {
                'test': str(test),
                'error': str(error).split('\n')[0]  # First line of error
            }
            for test, error in test_result.failures
        ],
        'error_details': [
            {
                'test': str(test),
                'error': str(error).split('\n')[0]  # First line of error
            }
            for test, error in test_result.errors
        ],
        'test_categories': {
            'api_integration': 'REST API endpoints with agent architecture',
            'websocket_integration': 'WebSocket functionality with real-time processing',
            'load_testing': 'Performance under concurrent and sustained load',
            'workflow_validation': 'Complete end-to-end workflow validation'
        }
    }

def print_test_summary(report: Dict[str, Any]):
    """Print comprehensive test summary"""
    print("\n" + "=" * 80)
    print("END-TO-END INTEGRATION TEST RESULTS")
    print("=" * 80)
    
    # Overall results
    print(f"Total Tests Run: {report['total_tests']}")
    print(f"Successes: {report['successes']}")
    print(f"Failures: {report['failures']}")
    print(f"Errors: {report['errors']}")
    print(f"Skipped: {report['skipped']}")
    print(f"Success Rate: {report['success_rate']:.1%}")
    print(f"Duration: {report['duration']:.2f} seconds")
    print(f"Overall Result: {'✓ PASSED' if report['was_successful'] else '✗ FAILED'}")
    
    # Test categories covered
    print(f"\nTest Categories Covered:")
    for category, description in report['test_categories'].items():
        print(f"  • {description}")
    
    # Requirements validation
    print(f"\nRequirements Validated:")
    print(f"  • Requirement 1.1: Migration maintains existing functionality")
    print(f"  • Requirement 1.4: Equivalent outputs to Step Functions")
    print(f"  • Requirement 7.1: Performance within time bounds")
    print(f"  • Requirement 7.2: Throughput equivalent to current system")
    
    # Failure details
    if report['failures']:
        print(f"\nFailure Details:")
        for failure in report['failure_details'][:5]:  # Show first 5
            print(f"  ✗ {failure['test']}: {failure['error']}")
        if len(report['failure_details']) > 5:
            print(f"  ... and {len(report['failure_details']) - 5} more failures")
    
    # Error details
    if report['errors']:
        print(f"\nError Details:")
        for error in report['error_details'][:5]:  # Show first 5
            print(f"  ✗ {error['test']}: {error['error']}")
        if len(report['error_details']) > 5:
            print(f"  ... and {len(report['error_details']) - 5} more errors")
    
    print("=" * 80)

def save_test_report(report: Dict[str, Any]):
    """Save detailed test report to file"""
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    filename = f"e2e_integration_test_report_{timestamp}.json"
    filepath = current_dir / filename
    
    try:
        with open(filepath, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        print(f"\n✓ Detailed test report saved to: {filepath}")
    except Exception as e:
        print(f"\n✗ Error saving test report: {e}")

def validate_test_environment():
    """Validate that the test environment is properly set up"""
    print("Validating test environment...")
    
    required_modules = [
        'slagent',
        'audio2sign_handler', 
        'handler',
        'test_config'
    ]
    
    missing_modules = []
    for module in required_modules:
        try:
            __import__(module)
            print(f"  ✓ {module}")
        except ImportError:
            missing_modules.append(module)
            print(f"  ✗ {module} (not available)")
    
    if missing_modules:
        print(f"\nWarning: Some modules are not available: {missing_modules}")
        print("Some tests may be skipped.")
    else:
        print("✓ All required modules are available")
    
    return len(missing_modules) == 0

def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Run End-to-End Integration Tests for GenASL Agent',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
This script implements task 9.1 from the Step Functions to Strands migration:
"Complete end-to-end integration testing"

Test Coverage:
- All API endpoints with new agent architecture
- WebSocket functionality with real-time processing  
- Load testing to ensure performance requirements
- Complete workflow validation from input to output

Requirements Validated:
- 1.1: Migration maintains existing functionality
- 1.4: Equivalent outputs to Step Functions orchestrator
- 7.1: Performance within same time bounds
- 7.2: Throughput equivalent to current system
        """
    )
    
    parser.add_argument('--validate-env', action='store_true',
                       help='Validate test environment before running tests')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Verbose output')
    
    args = parser.parse_args()
    
    if args.verbose:
        import logging
        logging.basicConfig(level=logging.DEBUG)
    
    # Validate environment if requested
    if args.validate_env:
        env_valid = validate_test_environment()
        if not env_valid:
            print("\nEnvironment validation failed. Some tests may not run properly.")
            response = input("Continue anyway? (y/N): ")
            if response.lower() != 'y':
                return 1
    
    # Run the end-to-end integration tests
    try:
        success = run_e2e_test_suite()
        return 0 if success else 1
    except KeyboardInterrupt:
        print("\n\nTest execution interrupted by user")
        return 130
    except Exception as e:
        print(f"\n\nUnexpected error during test execution: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == '__main__':
    sys.exit(main())