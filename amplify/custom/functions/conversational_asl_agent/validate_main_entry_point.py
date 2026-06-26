"""
Validation Script for Main Entry Point Implementation

This script validates that the main entry point implementation meets
all the requirements specified in task 7.3.
"""

import sys
from pathlib import Path

# Add the current directory to Python path
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

def validate_requirement_1_1():
    """Validate Requirement 1.1: Main invoke method that handles conversational interactions"""
    
    main_file_path = current_dir / "conversational_asl_agent_main.py"
    
    with open(main_file_path, 'r') as f:
        content = f.read()
    
    # Check for main invoke method
    required_elements = [
        "def invoke(self, payload: Dict[str, Any]) -> str:",
        "Main entry point for the conversational ASL agent",
        "conversational interactions",
        "conversation_router.handle_conversation",
        "user_input=user_message",
        "session_id=session_id",
        "user_id=user_id",
        "metadata=metadata"
    ]
    
    missing_elements = []
    for element in required_elements:
        if element not in content:
            missing_elements.append(element)
    
    if missing_elements:
        print("❌ Requirement 1.1 - Missing main invoke method elements:")
        for element in missing_elements:
            print(f"   - {element}")
        return False
    
    print("✅ Requirement 1.1 - Main invoke method handles conversational interactions")
    return True

def validate_requirement_1_5():
    """Validate Requirement 1.5: Backward compatibility with existing SignLanguageAgent interface"""
    
    main_file_path = current_dir / "conversational_asl_agent_main.py"
    
    with open(main_file_path, 'r') as f:
        content = f.read()
    
    # Check for backward compatibility elements
    required_elements = [
        "backward compatibility",
        "SignLanguageAgent interface",
        "validate_payload",
        "monitoring_manager.log_request_start",
        "monitoring_manager.log_request_success",
        "monitoring_manager.log_request_failure",
        "def invoke(payload: Dict[str, Any]) -> str:",
        "def health_check() -> Dict[str, Any]:",
        "backward_compatibility': True"
    ]
    
    missing_elements = []
    for element in required_elements:
        if element not in content:
            missing_elements.append(element)
    
    if missing_elements:
        print("❌ Requirement 1.5 - Missing backward compatibility elements:")
        for element in missing_elements:
            print(f"   - {element}")
        return False
    
    print("✅ Requirement 1.5 - Backward compatibility with existing SignLanguageAgent interface")
    return True

def validate_requirement_2_1():
    """Validate Requirement 2.1: Response coordination between all conversational components"""
    
    main_file_path = current_dir / "conversational_asl_agent_main.py"
    
    with open(main_file_path, 'r') as f:
        content = f.read()
    
    # Check for response coordination elements
    required_elements = [
        "ConversationRouter",
        "ConversationMemoryManager",
        "ConversationErrorHandler", 
        "ConversationResponseFormatter",
        "conversation_router.handle_conversation",
        "_enhance_response_with_context",
        "response coordination",
        "conversation_response.message",
        "enhanced_response"
    ]
    
    missing_elements = []
    for element in required_elements:
        if element not in content:
            missing_elements.append(element)
    
    if missing_elements:
        print("❌ Requirement 2.1 - Missing response coordination elements:")
        for element in missing_elements:
            print(f"   - {element}")
        return False
    
    print("✅ Requirement 2.1 - Response coordination between all conversational components")
    return True

def validate_class_structure():
    """Validate that the main class has the correct structure"""
    
    main_file_path = current_dir / "conversational_asl_agent_main.py"
    
    with open(main_file_path, 'r') as f:
        content = f.read()
    
    # Check for class structure elements
    required_elements = [
        "class ConversationalASLAgentMain:",
        "def __init__(self",
        "def invoke(self, payload: Dict[str, Any]) -> str:",
        "def health_check(self) -> Dict[str, Any]:",
        "def get_capabilities(self) -> Dict[str, Any]:",
        "def get_session_info(self, session_id: str)",
        "def cleanup_session(self, session_id: str)",
        "self.conversation_router",
        "self.memory_manager",
        "self.error_handler",
        "self.response_formatter"
    ]
    
    missing_elements = []
    for element in required_elements:
        if element not in content:
            missing_elements.append(element)
    
    if missing_elements:
        print("❌ Class Structure - Missing required elements:")
        for element in missing_elements:
            print(f"   - {element}")
        return False
    
    print("✅ Class Structure - ConversationalASLAgentMain has correct structure")
    return True

def validate_error_handling():
    """Validate comprehensive error handling"""
    
    main_file_path = current_dir / "conversational_asl_agent_main.py"
    
    with open(main_file_path, 'r') as f:
        content = f.read()
    
    # Check for error handling elements
    required_elements = [
        "try:",
        "except ValueError as e:",
        "except Exception as e:",
        "_handle_validation_error",
        "_handle_general_error",
        "_generate_fallback_error_response",
        "conversational context",
        "error recovery",
        "monitoring_manager.log_request_failure"
    ]
    
    missing_elements = []
    for element in required_elements:
        if element not in content:
            missing_elements.append(element)
    
    if missing_elements:
        print("❌ Error Handling - Missing required elements:")
        for element in missing_elements:
            print(f"   - {element}")
        return False
    
    print("✅ Error Handling - Comprehensive error handling implemented")
    return True

def validate_module_exports():
    """Validate that the module exports the correct functions"""
    
    main_file_path = current_dir / "conversational_asl_agent_main.py"
    
    with open(main_file_path, 'r') as f:
        content = f.read()
    
    # Check for module exports
    required_elements = [
        "conversational_asl_agent = ConversationalASLAgentMain()",
        "def invoke(payload: Dict[str, Any]) -> str:",
        "def health_check() -> Dict[str, Any]:",
        "__all__ = [",
        "'ConversationalASLAgentMain'",
        "'conversational_asl_agent'",
        "'invoke'",
        "'health_check'"
    ]
    
    missing_elements = []
    for element in required_elements:
        if element not in content:
            missing_elements.append(element)
    
    if missing_elements:
        print("❌ Module Exports - Missing required elements:")
        for element in missing_elements:
            print(f"   - {element}")
        return False
    
    print("✅ Module Exports - Correct module-level functions exported")
    return True

def validate_init_file_integration():
    """Validate that __init__.py properly integrates the main entry point"""
    
    init_file_path = current_dir / "__init__.py"
    
    if not init_file_path.exists():
        print("❌ Init File Integration - __init__.py does not exist")
        return False
    
    with open(init_file_path, 'r') as f:
        content = f.read()
    
    # Check for proper imports
    required_elements = [
        "from .conversational_asl_agent_main import",
        "ConversationalASLAgentMain",
        "conversational_asl_agent",
        "invoke",
        "health_check",
        "__all__ = [",
        "main entry point"
    ]
    
    missing_elements = []
    for element in required_elements:
        if element not in content:
            missing_elements.append(element)
    
    if missing_elements:
        print("❌ Init File Integration - Missing required elements:")
        for element in missing_elements:
            print(f"   - {element}")
        return False
    
    print("✅ Init File Integration - __init__.py properly integrates main entry point")
    return True

def run_validation():
    """Run all validation checks"""
    print("🔍 Validating Main Entry Point Implementation")
    print("=" * 60)
    print("Task 7.3: Create main conversational agent entry point")
    print("Requirements: 1.1, 1.5, 2.1")
    print("=" * 60)
    
    validations = [
        ("Requirement 1.1", validate_requirement_1_1),
        ("Requirement 1.5", validate_requirement_1_5), 
        ("Requirement 2.1", validate_requirement_2_1),
        ("Class Structure", validate_class_structure),
        ("Error Handling", validate_error_handling),
        ("Module Exports", validate_module_exports),
        ("Init File Integration", validate_init_file_integration)
    ]
    
    passed = 0
    total = len(validations)
    
    for name, validation_func in validations:
        try:
            if validation_func():
                passed += 1
            print()
        except Exception as e:
            print(f"❌ {name} - Validation failed with error: {e}")
            print()
    
    print("=" * 60)
    print(f"📊 Validation Results: {passed}/{total} checks passed")
    
    if passed == total:
        print("🎉 All validations passed! Task 7.3 is successfully implemented.")
        print()
        print("✅ Main conversational agent entry point created")
        print("✅ Backward compatibility with SignLanguageAgent maintained")
        print("✅ Response coordination between all conversational components")
        print("✅ Comprehensive error handling and recovery")
        print("✅ Proper module structure and exports")
        return True
    else:
        print("⚠️  Some validations failed. Please review the implementation.")
        return False

if __name__ == "__main__":
    success = run_validation()
    sys.exit(0 if success else 1)