"""
Deployment Configuration for Conversational ASL Agent

This module provides configuration utilities for deploying the conversational ASL agent
with proper environment variables and AgentCore Memory settings.
"""

import os
import json
from typing import Dict, Any, Optional

class ConversationalAgentDeployConfig:
    """Configuration manager for conversational agent deployment"""
    
    def __init__(self, environment: str = "dev"):
        """
        Initialize deployment configuration
        
        Args:
            environment: Deployment environment (dev, staging, prod)
        """
        self.environment = environment
        self.config = self._load_base_config()
    
    def _load_base_config(self) -> Dict[str, Any]:
        """Load base configuration settings"""
        return {
            # Core ASL translation settings
            "ENG_TO_ASL_MODEL": os.getenv("ENG_TO_ASL_MODEL", "us.amazon.nova-lite-v1:0"),
            "ASL_TO_ENG_MODEL": os.getenv("ASL_TO_ENG_MODEL", "us.amazon.nova-lite-v1:0"),
            "POSE_BUCKET": os.getenv("POSE_BUCKET", "genasl-avatar"),
            "ASL_DATA_BUCKET": os.getenv("ASL_DATA_BUCKET", "genasl-data"),
            "KEY_PREFIX": os.getenv("KEY_PREFIX", "aslavatarv2/gloss2pose/lookup/"),
            "TABLE_NAME": os.getenv("TABLE_NAME", "Pose_Data6"),
            "AWS_REGION": os.getenv("AWS_REGION", "us-west-2"),
            
            # AgentCore settings
            "BEDROCK_AGENT_RUNTIME_REGION": os.getenv("AWS_REGION", "us-west-2"),
            "LOG_LEVEL": os.getenv("LOG_LEVEL", "INFO"),
            
            # Conversational agent specific settings
            "CONVERSATION_MEMORY_TTL": self._get_memory_ttl(),
            "CONVERSATION_HISTORY_LIMIT": self._get_history_limit(),
            "CONVERSATION_CONTEXT_CLEANUP_INTERVAL": self._get_cleanup_interval(),
            "CONVERSATION_ENABLE_PROACTIVE_TIPS": self._get_boolean_setting("CONVERSATION_ENABLE_PROACTIVE_TIPS", True),
            "CONVERSATION_ENABLE_CONTEXT_ANALYSIS": self._get_boolean_setting("CONVERSATION_ENABLE_CONTEXT_ANALYSIS", True),
            "CONVERSATION_RESPONSE_ENHANCEMENT": self._get_boolean_setting("CONVERSATION_RESPONSE_ENHANCEMENT", True),
            
            # Memory optimization settings
            "AGENTCORE_MEMORY_OPTIMIZATION": self._get_boolean_setting("AGENTCORE_MEMORY_OPTIMIZATION", True),
            "AGENTCORE_MEMORY_COMPRESSION": self._get_boolean_setting("AGENTCORE_MEMORY_COMPRESSION", True),
            "AGENTCORE_MEMORY_BATCH_SIZE": os.getenv("AGENTCORE_MEMORY_BATCH_SIZE", "10"),
            
            # Performance settings
            "MAX_TOKENS": os.getenv("MAX_TOKENS", "3000"),
            "TEMPERATURE": os.getenv("TEMPERATURE", "0.0"),
        }
    
    def _get_memory_ttl(self) -> str:
        """Get memory TTL based on environment"""
        ttl_map = {
            "dev": "1800",      # 30 minutes for development
            "staging": "3600",  # 1 hour for staging
            "prod": "7200"      # 2 hours for production
        }
        return os.getenv("CONVERSATION_MEMORY_TTL", ttl_map.get(self.environment, "3600"))
    
    def _get_history_limit(self) -> str:
        """Get conversation history limit based on environment"""
        limit_map = {
            "dev": "25",        # Smaller limit for development
            "staging": "50",    # Medium limit for staging
            "prod": "100"       # Larger limit for production
        }
        return os.getenv("CONVERSATION_HISTORY_LIMIT", limit_map.get(self.environment, "50"))
    
    def _get_cleanup_interval(self) -> str:
        """Get cleanup interval based on environment"""
        interval_map = {
            "dev": "600",       # 10 minutes for development
            "staging": "300",   # 5 minutes for staging
            "prod": "180"       # 3 minutes for production
        }
        return os.getenv("CONVERSATION_CONTEXT_CLEANUP_INTERVAL", interval_map.get(self.environment, "300"))
    
    def _get_boolean_setting(self, key: str, default: bool) -> str:
        """Get boolean setting as string"""
        value = os.getenv(key, str(default).lower())
        return value.lower() if isinstance(value, str) else str(default).lower()
    
    def get_environment_variables(self) -> Dict[str, str]:
        """
        Get all environment variables for deployment
        
        Returns:
            Dict of environment variables
        """
        return {k: str(v) for k, v in self.config.items()}
    
    def get_lambda_configuration(self) -> Dict[str, Any]:
        """
        Get Lambda function configuration
        
        Returns:
            Dict containing Lambda configuration settings
        """
        memory_map = {
            "dev": 1024,        # 1GB for development
            "staging": 1536,    # 1.5GB for staging
            "prod": 2048        # 2GB for production
        }
        
        timeout_map = {
            "dev": 600,         # 10 minutes for development
            "staging": 900,     # 15 minutes for staging
            "prod": 900         # 15 minutes for production
        }
        
        return {
            "memory_size": memory_map.get(self.environment, 1536),
            "timeout": timeout_map.get(self.environment, 900),
            "environment_variables": self.get_environment_variables(),
            "tracing": "Active",
            "runtime": "python3.11"
        }
    
    def get_agentcore_memory_config(self) -> Dict[str, Any]:
        """
        Get AgentCore Memory configuration
        
        Returns:
            Dict containing AgentCore Memory settings
        """
        return {
            "memory_ttl": int(self.config["CONVERSATION_MEMORY_TTL"]),
            "history_limit": int(self.config["CONVERSATION_HISTORY_LIMIT"]),
            "cleanup_interval": int(self.config["CONVERSATION_CONTEXT_CLEANUP_INTERVAL"]),
            "optimization_enabled": self.config["AGENTCORE_MEMORY_OPTIMIZATION"] == "true",
            "compression_enabled": self.config["AGENTCORE_MEMORY_COMPRESSION"] == "true",
            "batch_size": int(self.config["AGENTCORE_MEMORY_BATCH_SIZE"])
        }
    
    def validate_configuration(self) -> Dict[str, Any]:
        """
        Validate deployment configuration
        
        Returns:
            Dict containing validation results
        """
        validation_results = {
            "valid": True,
            "errors": [],
            "warnings": []
        }
        
        # Check required environment variables
        required_vars = [
            "ENG_TO_ASL_MODEL",
            "ASL_TO_ENG_MODEL", 
            "POSE_BUCKET",
            "ASL_DATA_BUCKET",
            "TABLE_NAME",
            "AWS_REGION"
        ]
        
        for var in required_vars:
            if not self.config.get(var):
                validation_results["errors"].append(f"Missing required environment variable: {var}")
                validation_results["valid"] = False
        
        # Check memory settings
        try:
            memory_ttl = int(self.config["CONVERSATION_MEMORY_TTL"])
            if memory_ttl < 300:  # Less than 5 minutes
                validation_results["warnings"].append("Memory TTL is very short, may impact conversation continuity")
        except ValueError:
            validation_results["errors"].append("Invalid CONVERSATION_MEMORY_TTL value")
            validation_results["valid"] = False
        
        try:
            history_limit = int(self.config["CONVERSATION_HISTORY_LIMIT"])
            if history_limit < 10:
                validation_results["warnings"].append("History limit is very low, may impact context awareness")
            elif history_limit > 200:
                validation_results["warnings"].append("History limit is very high, may impact performance")
        except ValueError:
            validation_results["errors"].append("Invalid CONVERSATION_HISTORY_LIMIT value")
            validation_results["valid"] = False
        
        return validation_results
    
    def export_config_json(self, filepath: str) -> None:
        """
        Export configuration to JSON file
        
        Args:
            filepath: Path to export configuration
        """
        config_export = {
            "environment": self.environment,
            "lambda_configuration": self.get_lambda_configuration(),
            "agentcore_memory_config": self.get_agentcore_memory_config(),
            "validation": self.validate_configuration()
        }
        
        with open(filepath, 'w') as f:
            json.dump(config_export, f, indent=2)
    
    def print_deployment_summary(self) -> None:
        """Print deployment configuration summary"""
        print(f"\n=== Conversational ASL Agent Deployment Configuration ===")
        print(f"Environment: {self.environment}")
        print(f"Memory Size: {self.get_lambda_configuration()['memory_size']} MB")
        print(f"Timeout: {self.get_lambda_configuration()['timeout']} seconds")
        print(f"Memory TTL: {self.config['CONVERSATION_MEMORY_TTL']} seconds")
        print(f"History Limit: {self.config['CONVERSATION_HISTORY_LIMIT']} items")
        print(f"Cleanup Interval: {self.config['CONVERSATION_CONTEXT_CLEANUP_INTERVAL']} seconds")
        
        validation = self.validate_configuration()
        print(f"\nValidation Status: {'✅ VALID' if validation['valid'] else '❌ INVALID'}")
        
        if validation['errors']:
            print("Errors:")
            for error in validation['errors']:
                print(f"  - {error}")
        
        if validation['warnings']:
            print("Warnings:")
            for warning in validation['warnings']:
                print(f"  - {warning}")
        
        print("=" * 60)

def main():
    """Main function for testing deployment configuration"""
    import sys
    
    environment = sys.argv[1] if len(sys.argv) > 1 else "dev"
    config = ConversationalAgentDeployConfig(environment)
    
    config.print_deployment_summary()
    
    # Export configuration
    config.export_config_json(f"deployment_config_{environment}.json")
    print(f"\nConfiguration exported to deployment_config_{environment}.json")

if __name__ == "__main__":
    main()