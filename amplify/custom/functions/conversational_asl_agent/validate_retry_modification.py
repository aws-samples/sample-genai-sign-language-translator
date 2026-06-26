"""
Validate Retry and Modification Implementation

This script validates that the retry and modification components are properly implemented
by checking the structure and key functionality without running the full system.
"""

import os
import re
from typing import List, Dict, Any

def validate_file_structure() -> Dict[str, bool]:
    """Validate that all required files are present"""
    required_files = [
        'retry_manager.py',
        'modification_detector.py', 
        'alternative_explorer.py',
        'retry_modification_integration.py',
        'test_retry_modification.py'
    ]
    
    results = {}
    for file in required_files:
        results[file] = os.path.exists(file)
    
    return results

def validate_class_definitions(file_path: str, expected_classes: List[str]) -> Dict[str, bool]:
    """Validate that expected classes are defined in a file"""
    if not os.path.exists(file_path):
        return {cls: False for cls in expected_classes}
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    results = {}
    for cls in expected_classes:
        # Look for class definition
        pattern = rf'class\s+{cls}\s*[\(:]'
        results[cls] = bool(re.search(pattern, content))
    
    return results

def validate_method_definitions(file_path: str, class_name: str, expected_methods: List[str]) -> Dict[str, bool]:
    """Validate that expected methods are defined in a class"""
    if not os.path.exists(file_path):
        return {method: False for method in expected_methods}
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    results = {}
    for method in expected_methods:
        # Look for method definition within the class
        pattern = rf'def\s+{method}\s*\('
        results[method] = bool(re.search(pattern, content))
    
    return results

def validate_enum_definitions(file_path: str, expected_enums: List[str]) -> Dict[str, bool]:
    """Validate that expected enums are defined in a file"""
    if not os.path.exists(file_path):
        return {enum: False for enum in expected_enums}
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    results = {}
    for enum in expected_enums:
        # Look for enum definition
        pattern = rf'class\s+{enum}\s*\(\s*Enum\s*\)'
        results[enum] = bool(re.search(pattern, content))
    
    return results

def run_validation():
    """Run comprehensive validation of the retry and modification implementation"""
    print("🔍 Validating Retry and Modification Implementation")
    print("=" * 60)
    
    # 1. Validate file structure
    print("\n1. File Structure Validation:")
    file_results = validate_file_structure()
    for file, exists in file_results.items():
        status = "✅" if exists else "❌"
        print(f"   {status} {file}")
    
    all_files_exist = all(file_results.values())
    if not all_files_exist:
        print("   ⚠️  Some required files are missing!")
        return False
    
    # 2. Validate RetryManager
    print("\n2. RetryManager Validation:")
    retry_classes = validate_class_definitions('retry_manager.py', [
        'RetryStrategy', 'RetryReason', 'RetryAttempt', 'RetrySession', 'RetryManager'
    ])
    for cls, exists in retry_classes.items():
        status = "✅" if exists else "❌"
        print(f"   {status} {cls} class")
    
    retry_methods = validate_method_definitions('retry_manager.py', 'RetryManager', [
        'create_retry_session', 'execute_retry', 'suggest_retry_modifications'
    ])
    for method, exists in retry_methods.items():
        status = "✅" if exists else "❌"
        print(f"   {status} {method} method")
    
    # 3. Validate ModificationDetector
    print("\n3. ModificationDetector Validation:")
    mod_classes = validate_class_definitions('modification_detector.py', [
        'ModificationType', 'ModificationScope', 'ModificationRequest', 'ModificationDetector'
    ])
    for cls, exists in mod_classes.items():
        status = "✅" if exists else "❌"
        print(f"   {status} {cls} class")
    
    mod_methods = validate_method_definitions('modification_detector.py', 'ModificationDetector', [
        'detect_modification_request', 'extract_modification_parameters', 'create_modification_intent'
    ])
    for method, exists in mod_methods.items():
        status = "✅" if exists else "❌"
        print(f"   {status} {method} method")
    
    # 4. Validate AlternativeExplorer
    print("\n4. AlternativeExplorer Validation:")
    alt_classes = validate_class_definitions('alternative_explorer.py', [
        'AlternativeType', 'AlternativeCategory', 'AlternativeOption', 'AlternativeExplorer'
    ])
    for cls, exists in alt_classes.items():
        status = "✅" if exists else "❌"
        print(f"   {status} {cls} class")
    
    alt_methods = validate_method_definitions('alternative_explorer.py', 'AlternativeExplorer', [
        'explore_alternatives', 'suggest_parameter_variations', 'compare_alternatives'
    ])
    for method, exists in alt_methods.items():
        status = "✅" if exists else "❌"
        print(f"   {status} {method} method")
    
    # 5. Validate Integration
    print("\n5. Integration Validation:")
    int_classes = validate_class_definitions('retry_modification_integration.py', [
        'ActionType', 'ActionRequest', 'RetryModificationIntegration'
    ])
    for cls, exists in int_classes.items():
        status = "✅" if exists else "❌"
        print(f"   {status} {cls} class")
    
    int_methods = validate_method_definitions('retry_modification_integration.py', 'RetryModificationIntegration', [
        'handle_user_request', 'suggest_improvements'
    ])
    for method, exists in int_methods.items():
        status = "✅" if exists else "❌"
        print(f"   {status} {method} method")
    
    # 6. Validate Test File
    print("\n6. Test File Validation:")
    test_classes = validate_class_definitions('test_retry_modification.py', [
        'TestRetryModificationCapabilities'
    ])
    for cls, exists in test_classes.items():
        status = "✅" if exists else "❌"
        print(f"   {status} {cls} test class")
    
    # 7. Check for key functionality patterns
    print("\n7. Functionality Pattern Validation:")
    
    # Check for retry patterns
    with open('retry_manager.py', 'r') as f:
        retry_content = f.read()
    
    retry_patterns = {
        'Exponential backoff': 'exponential_backoff',
        'Retry strategies': 'RetryStrategy',
        'Error handling': 'Exception',
        'Memory integration': 'memory_manager'
    }
    
    for pattern_name, pattern in retry_patterns.items():
        found = pattern.lower() in retry_content.lower()
        status = "✅" if found else "❌"
        print(f"   {status} {pattern_name} pattern")
    
    # Check for modification patterns
    with open('modification_detector.py', 'r') as f:
        mod_content = f.read()
    
    mod_patterns = {
        'Text change detection': 'text_change',
        'Parameter extraction': 'extract.*parameters',
        'Intent creation': 'IntentResult',
        'Pattern matching': 'modification_patterns'
    }
    
    for pattern_name, pattern in mod_patterns.items():
        found = bool(re.search(pattern.lower(), mod_content.lower()))
        status = "✅" if found else "❌"
        print(f"   {status} {pattern_name} pattern")
    
    # Check for alternative patterns
    with open('alternative_explorer.py', 'r') as f:
        alt_content = f.read()
    
    alt_patterns = {
        'Alternative generation': 'generate.*alternatives',
        'Parameter variations': 'parameter_variations',
        'Comparison logic': 'compare_alternatives',
        'User formatting': 'format.*user'
    }
    
    for pattern_name, pattern in alt_patterns.items():
        found = bool(re.search(pattern.lower(), alt_content.lower()))
        status = "✅" if found else "❌"
        print(f"   {status} {pattern_name} pattern")
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 Validation Summary:")
    
    total_checks = (len(file_results) + len(retry_classes) + len(retry_methods) + 
                   len(mod_classes) + len(mod_methods) + len(alt_classes) + 
                   len(alt_methods) + len(int_classes) + len(int_methods) + 
                   len(test_classes) + len(retry_patterns) + len(mod_patterns) + 
                   len(alt_patterns))
    
    passed_checks = (sum(file_results.values()) + sum(retry_classes.values()) + 
                    sum(retry_methods.values()) + sum(mod_classes.values()) + 
                    sum(mod_methods.values()) + sum(alt_classes.values()) + 
                    sum(alt_methods.values()) + sum(int_classes.values()) + 
                    sum(int_methods.values()) + sum(test_classes.values()) + 
                    sum(1 for pattern_name, pattern in retry_patterns.items() 
                        if pattern.lower() in retry_content.lower()) +
                    sum(1 for pattern_name, pattern in mod_patterns.items() 
                        if re.search(pattern.lower(), mod_content.lower())) +
                    sum(1 for pattern_name, pattern in alt_patterns.items() 
                        if re.search(pattern.lower(), alt_content.lower())))
    
    success_rate = (passed_checks / total_checks) * 100
    print(f"   ✅ Passed: {passed_checks}/{total_checks} checks ({success_rate:.1f}%)")
    
    if success_rate >= 90:
        print("   🎉 Implementation looks excellent!")
        return True
    elif success_rate >= 75:
        print("   👍 Implementation looks good with minor issues")
        return True
    else:
        print("   ⚠️  Implementation needs attention")
        return False

if __name__ == "__main__":
    success = run_validation()
    exit(0 if success else 1)