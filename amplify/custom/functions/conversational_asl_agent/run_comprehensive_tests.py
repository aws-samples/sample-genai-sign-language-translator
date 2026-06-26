#!/usr/bin/env python3
"""
Comprehensive Test Runner for Conversational ASL Agent

Runs all unit tests and integration tests for the conversational agent components.
Provides detailed test results and coverage information.
"""

import unittest
import sys
import os
from pathlib import Path
import time
from datetime import datetime

# Add current directory to path for imports
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

def run_test_suite():
    """Run comprehensive test suite for conversational ASL agent"""
    
    print("=" * 80)
    print("CONVERSATIONAL ASL AGENT - COMPREHENSIVE TEST SUITE")
    print("=" * 80)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Test modules to run
    test_modules = [
        'test_basic_functionality',
        'test_intent_classification', 
        'test_memory_manager',
        'test_conversation_orchestrator',
        'test_conversation_router',
        'test_response_formatter',
        'test_error_handling',
        'test_retry_modification',
        'test_integration_flows'
    ]
    
    # Track results
    total_tests = 0
    total_failures = 0
    total_errors = 0
    total_skipped = 0
    module_results = {}
    
    start_time = time.time()
    
    for module_name in test_modules:
        print(f"Running tests from {module_name}...")
        print("-" * 60)
        
        try:
            # Import and run test module
            test_module = __import__(module_name)
            
            # Create test suite
            loader = unittest.TestLoader()
            suite = loader.loadTestsFromModule(test_module)
            
            # Run tests
            runner = unittest.TextTestRunner(
                verbosity=2,
                stream=sys.stdout,
                buffer=True
            )
            
            result = runner.run(suite)
            
            # Track results
            module_results[module_name] = {
                'tests_run': result.testsRun,
                'failures': len(result.failures),
                'errors': len(result.errors),
                'skipped': len(result.skipped) if hasattr(result, 'skipped') else 0,
                'success': result.wasSuccessful()
            }
            
            total_tests += result.testsRun
            total_failures += len(result.failures)
            total_errors += len(result.errors)
            total_skipped += len(result.skipped) if hasattr(result, 'skipped') else 0
            
            print(f"✓ {module_name}: {result.testsRun} tests, "
                  f"{len(result.failures)} failures, {len(result.errors)} errors")
            
        except ImportError as e:
            print(f"⚠ Skipping {module_name}: Import error - {e}")
            module_results[module_name] = {
                'tests_run': 0,
                'failures': 0,
                'errors': 1,
                'skipped': 0,
                'success': False,
                'import_error': str(e)
            }
            total_errors += 1
            
        except Exception as e:
            print(f"❌ Error running {module_name}: {e}")
            module_results[module_name] = {
                'tests_run': 0,
                'failures': 0,
                'errors': 1,
                'skipped': 0,
                'success': False,
                'error': str(e)
            }
            total_errors += 1
        
        print()
    
    end_time = time.time()
    duration = end_time - start_time
    
    # Print summary
    print("=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    
    print(f"Total execution time: {duration:.2f} seconds")
    print(f"Total tests run: {total_tests}")
    print(f"Total failures: {total_failures}")
    print(f"Total errors: {total_errors}")
    print(f"Total skipped: {total_skipped}")
    print()
    
    # Module breakdown
    print("MODULE BREAKDOWN:")
    print("-" * 40)
    
    for module_name, results in module_results.items():
        status = "✓ PASS" if results['success'] else "❌ FAIL"
        
        if 'import_error' in results:
            print(f"{module_name:30} {status} (Import Error)")
        elif 'error' in results:
            print(f"{module_name:30} {status} (Runtime Error)")
        else:
            print(f"{module_name:30} {status} "
                  f"({results['tests_run']} tests, "
                  f"{results['failures']} failures, "
                  f"{results['errors']} errors)")
    
    print()
    
    # Overall result
    overall_success = total_failures == 0 and total_errors == 0
    
    if overall_success:
        print("🎉 ALL TESTS PASSED!")
        print("The conversational ASL agent is ready for deployment.")
    else:
        print("⚠ SOME TESTS FAILED")
        print("Please review the failures and errors above.")
        
        if total_failures > 0:
            print(f"- {total_failures} test failures need to be fixed")
        if total_errors > 0:
            print(f"- {total_errors} test errors need to be resolved")
    
    print()
    print("=" * 80)
    
    return overall_success

def run_specific_test_category(category):
    """Run tests for a specific category"""
    
    category_modules = {
        'unit': [
            'test_basic_functionality',
            'test_intent_classification',
            'test_memory_manager',
            'test_conversation_orchestrator',
            'test_response_formatter'
        ],
        'integration': [
            'test_integration_flows',
            'test_conversation_router',
            'test_error_handling',
            'test_retry_modification'
        ],
        'core': [
            'test_basic_functionality',
            'test_intent_classification',
            'test_memory_manager'
        ]
    }
    
    if category not in category_modules:
        print(f"Unknown test category: {category}")
        print(f"Available categories: {', '.join(category_modules.keys())}")
        return False
    
    print(f"Running {category.upper()} tests...")
    print("=" * 60)
    
    modules = category_modules[category]
    success = True
    
    for module_name in modules:
        try:
            print(f"\nRunning {module_name}...")
            test_module = __import__(module_name)
            
            loader = unittest.TestLoader()
            suite = loader.loadTestsFromModule(test_module)
            
            runner = unittest.TextTestRunner(verbosity=2)
            result = runner.run(suite)
            
            if not result.wasSuccessful():
                success = False
                
        except Exception as e:
            print(f"Error running {module_name}: {e}")
            success = False
    
    return success

def validate_test_environment():
    """Validate that the test environment is properly set up"""
    
    print("Validating test environment...")
    print("-" * 40)
    
    # Check required modules
    required_modules = [
        'data_models',
        'intent_classifier',
        'memory_manager',
        'conversation_orchestrator',
        'response_formatter',
        'conversation_router'
    ]
    
    missing_modules = []
    
    for module_name in required_modules:
        try:
            __import__(module_name)
            print(f"✓ {module_name}")
        except ImportError as e:
            print(f"❌ {module_name}: {e}")
            missing_modules.append(module_name)
    
    if missing_modules:
        print(f"\n⚠ Missing modules: {', '.join(missing_modules)}")
        print("Please ensure all conversational agent components are implemented.")
        return False
    
    print("\n✓ Test environment validation passed!")
    return True

def main():
    """Main test runner entry point"""
    
    if len(sys.argv) > 1:
        category = sys.argv[1].lower()
        
        if category == 'validate':
            return 0 if validate_test_environment() else 1
        elif category in ['unit', 'integration', 'core']:
            return 0 if run_specific_test_category(category) else 1
        elif category == 'help':
            print("Usage: python run_comprehensive_tests.py [category]")
            print("\nCategories:")
            print("  unit        - Run unit tests only")
            print("  integration - Run integration tests only") 
            print("  core        - Run core component tests only")
            print("  validate    - Validate test environment")
            print("  help        - Show this help message")
            print("\nRun without arguments to execute all tests.")
            return 0
        else:
            print(f"Unknown category: {category}")
            print("Use 'help' for usage information.")
            return 1
    
    # Validate environment first
    if not validate_test_environment():
        return 1
    
    # Run comprehensive test suite
    success = run_test_suite()
    return 0 if success else 1

if __name__ == '__main__':
    exit(main())