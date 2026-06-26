#!/usr/bin/env python3
"""
Test runner for GenASL Sign Language Agent

This script runs all test suites and generates comprehensive test reports
including unit tests, integration tests, and performance benchmarks.
"""

import sys
import os
import unittest
import time
import json
from pathlib import Path
from io import StringIO
from typing import Dict, Any, List

# Add current directory to path
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

# Import test modules
try:
    import test_tools
    import test_integration
    import test_performance
    import test_e2e_integration
    from test_config import performance_benchmark, get_cache_stats
except ImportError as e:
    print(f"Error importing test modules: {e}")
    sys.exit(1)

class TestResult:
    """Custom test result class to capture detailed results"""
    
    def __init__(self):
        self.tests_run = 0
        self.failures = []
        self.errors = []
        self.skipped = []
        self.success_count = 0
        self.start_time = None
        self.end_time = None
    
    def start_test(self, test):
        """Called when a test starts"""
        if self.start_time is None:
            self.start_time = time.time()
    
    def add_success(self, test):
        """Called when a test passes"""
        self.success_count += 1
        self.tests_run += 1
    
    def add_error(self, test, err):
        """Called when a test has an error"""
        self.errors.append((test, err))
        self.tests_run += 1
    
    def add_failure(self, test, err):
        """Called when a test fails"""
        self.failures.append((test, err))
        self.tests_run += 1
    
    def add_skip(self, test, reason):
        """Called when a test is skipped"""
        self.skipped.append((test, reason))
        self.tests_run += 1
    
    def stop_test(self, test):
        """Called when a test ends"""
        self.end_time = time.time()
    
    @property
    def duration(self):
        """Get test duration"""
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        return 0
    
    @property
    def success_rate(self):
        """Get success rate"""
        if self.tests_run == 0:
            return 0.0
        return self.success_count / self.tests_run
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        return {
            'tests_run': self.tests_run,
            'success_count': self.success_count,
            'failures': len(self.failures),
            'errors': len(self.errors),
            'skipped': len(self.skipped),
            'success_rate': self.success_rate,
            'duration': self.duration,
            'failure_details': [
                {'test': str(test), 'error': str(err)} 
                for test, err in self.failures
            ],
            'error_details': [
                {'test': str(test), 'error': str(err)} 
                for test, err in self.errors
            ],
            'skipped_details': [
                {'test': str(test), 'reason': str(reason)} 
                for test, reason in self.skipped
            ]
        }

class TestRunner:
    """Main test runner class"""
    
    def __init__(self):
        self.results = {}
        self.overall_start_time = None
        self.overall_end_time = None
    
    def run_test_suite(self, test_module, suite_name: str) -> TestResult:
        """Run a specific test suite"""
        print(f"\n{'='*60}")
        print(f"Running {suite_name} Tests")
        print(f"{'='*60}")
        
        # Create test loader and suite
        loader = unittest.TestLoader()
        suite = loader.loadTestsFromModule(test_module)
        
        # Create custom test result
        result = TestResult()
        
        # Capture stdout for cleaner output
        old_stdout = sys.stdout
        sys.stdout = StringIO()
        
        try:
            # Run the tests
            runner = unittest.TextTestRunner(
                stream=sys.stdout,
                verbosity=2,
                resultclass=lambda: result
            )
            
            start_time = time.time()
            test_result = runner.run(suite)
            end_time = time.time()
            
            # Update result with actual values from test_result
            result.tests_run = test_result.testsRun
            result.failures = test_result.failures
            result.errors = test_result.errors
            result.skipped = getattr(test_result, 'skipped', [])
            result.success_count = (result.tests_run - 
                                  len(result.failures) - 
                                  len(result.errors) - 
                                  len(result.skipped))
            result.start_time = start_time
            result.end_time = end_time
            
        finally:
            # Restore stdout
            captured_output = sys.stdout.getvalue()
            sys.stdout = old_stdout
        
        # Print summary
        self._print_suite_summary(suite_name, result)
        
        return result
    
    def _print_suite_summary(self, suite_name: str, result: TestResult):
        """Print summary for a test suite"""
        print(f"\n{suite_name} Results:")
        print(f"  Tests Run: {result.tests_run}")
        print(f"  Successes: {result.success_count}")
        print(f"  Failures: {len(result.failures)}")
        print(f"  Errors: {len(result.errors)}")
        print(f"  Skipped: {len(result.skipped)}")
        print(f"  Success Rate: {result.success_rate:.1%}")
        print(f"  Duration: {result.duration:.2f}s")
        
        # Print failure details
        if result.failures:
            print(f"\n  Failures:")
            for test, error in result.failures[:3]:  # Show first 3
                print(f"    - {test}: {str(error).split(chr(10))[0]}")
            if len(result.failures) > 3:
                print(f"    ... and {len(result.failures) - 3} more")
        
        # Print error details
        if result.errors:
            print(f"\n  Errors:")
            for test, error in result.errors[:3]:  # Show first 3
                print(f"    - {test}: {str(error).split(chr(10))[0]}")
            if len(result.errors) > 3:
                print(f"    ... and {len(result.errors) - 3} more")
    
    def run_all_tests(self) -> Dict[str, Any]:
        """Run all test suites"""
        self.overall_start_time = time.time()
        
        print("GenASL Sign Language Agent - Test Suite")
        print("=" * 60)
        
        # Define test suites
        test_suites = [
            (test_tools, "Unit Tests"),
            (test_integration, "Integration Tests"),
            (test_performance, "Performance Tests"),
            (test_e2e_integration, "End-to-End Integration Tests")
        ]
        
        # Run each test suite
        for test_module, suite_name in test_suites:
            try:
                result = self.run_test_suite(test_module, suite_name)
                self.results[suite_name.lower().replace(' ', '_')] = result
            except Exception as e:
                print(f"Error running {suite_name}: {e}")
                # Create a failed result
                failed_result = TestResult()
                failed_result.tests_run = 1
                failed_result.errors = [("Suite Error", str(e))]
                self.results[suite_name.lower().replace(' ', '_')] = failed_result
        
        self.overall_end_time = time.time()
        
        # Generate overall report
        return self._generate_overall_report()
    
    def _generate_overall_report(self) -> Dict[str, Any]:
        """Generate overall test report"""
        total_tests = sum(result.tests_run for result in self.results.values())
        total_successes = sum(result.success_count for result in self.results.values())
        total_failures = sum(len(result.failures) for result in self.results.values())
        total_errors = sum(len(result.errors) for result in self.results.values())
        total_skipped = sum(len(result.skipped) for result in self.results.values())
        
        overall_success_rate = total_successes / total_tests if total_tests > 0 else 0.0
        overall_duration = self.overall_end_time - self.overall_start_time
        
        # Print overall summary
        print(f"\n{'='*60}")
        print("OVERALL TEST RESULTS")
        print(f"{'='*60}")
        print(f"Total Tests: {total_tests}")
        print(f"Successes: {total_successes}")
        print(f"Failures: {total_failures}")
        print(f"Errors: {total_errors}")
        print(f"Skipped: {total_skipped}")
        print(f"Success Rate: {overall_success_rate:.1%}")
        print(f"Total Duration: {overall_duration:.2f}s")
        
        # Performance benchmarks summary
        if hasattr(performance_benchmark, 'results') and performance_benchmark.results:
            print(f"\nPerformance Benchmarks:")
            for benchmark in performance_benchmark.results[-5:]:  # Show last 5
                print(f"  {benchmark['function']}: {benchmark['avg_time']:.3f}s avg, "
                      f"{benchmark['success_rate']:.1%} success")
        
        # Create comprehensive report
        report = {
            'timestamp': time.time(),
            'overall': {
                'total_tests': total_tests,
                'successes': total_successes,
                'failures': total_failures,
                'errors': total_errors,
                'skipped': total_skipped,
                'success_rate': overall_success_rate,
                'duration': overall_duration
            },
            'suites': {
                name: result.to_dict() 
                for name, result in self.results.items()
            },
            'performance_benchmarks': getattr(performance_benchmark, 'results', []),
            'system_info': self._get_system_info()
        }
        
        return report
    
    def _get_system_info(self) -> Dict[str, Any]:
        """Get system information for the report"""
        import platform
        import psutil
        
        try:
            return {
                'python_version': platform.python_version(),
                'platform': platform.platform(),
                'cpu_count': psutil.cpu_count(),
                'memory_total': psutil.virtual_memory().total,
                'memory_available': psutil.virtual_memory().available
            }
        except Exception:
            return {'error': 'Could not collect system info'}
    
    def save_report(self, report: Dict[str, Any], filename: str = None):
        """Save test report to file"""
        if filename is None:
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            filename = f"test_report_{timestamp}.json"
        
        filepath = current_dir / filename
        
        try:
            with open(filepath, 'w') as f:
                json.dump(report, f, indent=2, default=str)
            print(f"\nTest report saved to: {filepath}")
        except Exception as e:
            print(f"Error saving test report: {e}")

def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Run GenASL Agent Test Suite')
    parser.add_argument('--suite', choices=['unit', 'integration', 'performance', 'e2e', 'all'],
                       default='all', help='Test suite to run')
    parser.add_argument('--output', help='Output file for test report')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Verbose output')
    
    args = parser.parse_args()
    
    # Set up environment
    os.environ['TESTING'] = '1'
    
    runner = TestRunner()
    
    if args.suite == 'all':
        report = runner.run_all_tests()
    else:
        # Run specific suite
        suite_map = {
            'unit': (test_tools, "Unit Tests"),
            'integration': (test_integration, "Integration Tests"),
            'performance': (test_performance, "Performance Tests"),
            'e2e': (test_e2e_integration, "End-to-End Integration Tests")
        }
        
        if args.suite in suite_map:
            test_module, suite_name = suite_map[args.suite]
            result = runner.run_test_suite(test_module, suite_name)
            report = {
                'timestamp': time.time(),
                'suite': args.suite,
                'result': result.to_dict()
            }
        else:
            print(f"Unknown test suite: {args.suite}")
            return 1
    
    # Save report if requested
    if args.output:
        runner.save_report(report, args.output)
    
    # Return appropriate exit code
    if args.suite == 'all':
        overall_success_rate = report['overall']['success_rate']
        return 0 if overall_success_rate >= 0.8 else 1
    else:
        suite_success_rate = report['result']['success_rate']
        return 0 if suite_success_rate >= 0.8 else 1

if __name__ == '__main__':
    sys.exit(main())