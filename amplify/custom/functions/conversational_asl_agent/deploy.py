#!/usr/bin/env python3
"""
Deployment Script for Conversational ASL Agent

This script helps deploy the conversational ASL agent with proper configuration
and validation checks.
"""

import os
import sys
import json
import subprocess
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional

from deploy_config import ConversationalAgentDeployConfig

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ConversationalAgentDeployer:
    """Deployment manager for conversational ASL agent"""
    
    def __init__(self, environment: str = "dev", dry_run: bool = False):
        """
        Initialize deployer
        
        Args:
            environment: Target deployment environment
            dry_run: If True, only validate without deploying
        """
        self.environment = environment
        self.dry_run = dry_run
        self.config = ConversationalAgentDeployConfig(environment)
        self.deployment_root = Path(__file__).parent
        
        logger.info(f"Initializing deployment for environment: {environment}")
        if dry_run:
            logger.info("Running in DRY RUN mode - no actual deployment will occur")
    
    def validate_prerequisites(self) -> bool:
        """
        Validate deployment prerequisites
        
        Returns:
            bool: True if all prerequisites are met
        """
        logger.info("Validating deployment prerequisites...")
        
        validation_results = []
        
        # Check if all required files exist
        required_files = [
            "conversational_asl_agent_main.py",
            "conversation_router.py",
            "memory_manager.py",
            "data_models.py",
            "requirements.txt",
            ".bedrock_agentcore.yaml",
            "Dockerfile"
        ]
        
        for file in required_files:
            file_path = self.deployment_root / file
            if file_path.exists():
                logger.info(f"✅ Found required file: {file}")
                validation_results.append(True)
            else:
                logger.error(f"❌ Missing required file: {file}")
                validation_results.append(False)
        
        # Validate configuration
        config_validation = self.config.validate_configuration()
        if config_validation["valid"]:
            logger.info("✅ Configuration validation passed")
            validation_results.append(True)
        else:
            logger.error("❌ Configuration validation failed")
            for error in config_validation["errors"]:
                logger.error(f"   - {error}")
            validation_results.append(False)
        
        # Check AWS credentials
        try:
            result = subprocess.run(
                ["aws", "sts", "get-caller-identity"],
                capture_output=True,
                text=True,
                check=True
            )
            logger.info("✅ AWS credentials are valid")
            validation_results.append(True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            logger.error("❌ AWS credentials not configured or AWS CLI not available")
            validation_results.append(False)
        
        # Check if AgentCore is available
        try:
            import bedrock_agentcore
            logger.info("✅ AgentCore SDK is available")
            validation_results.append(True)
        except ImportError:
            logger.error("❌ AgentCore SDK not available")
            validation_results.append(False)
        
        all_valid = all(validation_results)
        logger.info(f"Prerequisites validation: {'✅ PASSED' if all_valid else '❌ FAILED'}")
        
        return all_valid
    
    def prepare_deployment_package(self) -> bool:
        """
        Prepare deployment package
        
        Returns:
            bool: True if package preparation succeeded
        """
        logger.info("Preparing deployment package...")
        
        try:
            # Create deployment configuration file
            config_file = self.deployment_root / f"deployment_config_{self.environment}.json"
            self.config.export_config_json(str(config_file))
            logger.info(f"✅ Created deployment configuration: {config_file}")
            
            # Validate Python syntax for all Python files
            python_files = list(self.deployment_root.glob("*.py"))
            for py_file in python_files:
                try:
                    with open(py_file, 'r') as f:
                        compile(f.read(), py_file, 'exec')
                    logger.info(f"✅ Python syntax valid: {py_file.name}")
                except SyntaxError as e:
                    logger.error(f"❌ Python syntax error in {py_file.name}: {e}")
                    return False
            
            # Check requirements.txt
            requirements_file = self.deployment_root / "requirements.txt"
            if requirements_file.exists():
                logger.info("✅ Requirements file found")
            else:
                logger.error("❌ Requirements file missing")
                return False
            
            logger.info("✅ Deployment package preparation completed")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error preparing deployment package: {e}")
            return False
    
    def deploy_lambda_function(self) -> bool:
        """
        Deploy Lambda function (simulation for dry run)
        
        Returns:
            bool: True if deployment succeeded
        """
        logger.info("Deploying Lambda function...")
        
        if self.dry_run:
            logger.info("🔍 DRY RUN: Would deploy Lambda function with configuration:")
            lambda_config = self.config.get_lambda_configuration()
            for key, value in lambda_config.items():
                if key != "environment_variables":
                    logger.info(f"   {key}: {value}")
            logger.info(f"   environment_variables: {len(lambda_config['environment_variables'])} variables")
            return True
        
        # In a real deployment, this would use AWS CDK or AWS CLI
        # For now, we'll simulate the deployment
        logger.info("🚀 Lambda function deployment would be executed here")
        logger.info("   - Function name: SignLanguageAgentFunction-" + self.environment)
        logger.info("   - Handler: conversational_asl_agent_main.invoke")
        logger.info("   - Runtime: python3.11")
        logger.info(f"   - Memory: {self.config.get_lambda_configuration()['memory_size']} MB")
        logger.info(f"   - Timeout: {self.config.get_lambda_configuration()['timeout']} seconds")
        
        return True
    
    def configure_agentcore_memory(self) -> bool:
        """
        Configure AgentCore Memory settings
        
        Returns:
            bool: True if configuration succeeded
        """
        logger.info("Configuring AgentCore Memory...")
        
        memory_config = self.config.get_agentcore_memory_config()
        
        if self.dry_run:
            logger.info("🔍 DRY RUN: Would configure AgentCore Memory with:")
            for key, value in memory_config.items():
                logger.info(f"   {key}: {value}")
            return True
        
        # In a real deployment, this would configure AgentCore Memory
        logger.info("🔧 AgentCore Memory configuration would be applied here")
        logger.info(f"   - Memory TTL: {memory_config['memory_ttl']} seconds")
        logger.info(f"   - History Limit: {memory_config['history_limit']} items")
        logger.info(f"   - Cleanup Interval: {memory_config['cleanup_interval']} seconds")
        logger.info(f"   - Optimization: {memory_config['optimization_enabled']}")
        logger.info(f"   - Compression: {memory_config['compression_enabled']}")
        
        return True
    
    def run_deployment_tests(self) -> bool:
        """
        Run deployment tests
        
        Returns:
            bool: True if all tests passed
        """
        logger.info("Running deployment tests...")
        
        try:
            # Test import of main module
            sys.path.insert(0, str(self.deployment_root))
            
            try:
                import conversational_asl_agent_main
                logger.info("✅ Main module import successful")
            except ImportError as e:
                logger.error(f"❌ Failed to import main module: {e}")
                return False
            
            # Test health check
            try:
                health_result = conversational_asl_agent_main.health_check()
                if health_result.get("status") in ["healthy", "degraded"]:
                    logger.info("✅ Health check passed")
                else:
                    logger.error(f"❌ Health check failed: {health_result}")
                    return False
            except Exception as e:
                logger.error(f"❌ Health check error: {e}")
                return False
            
            # Test basic invocation
            try:
                test_payload = {
                    "message": "Hello, test deployment",
                    "type": "text",
                    "session_id": "deployment_test"
                }
                
                response = conversational_asl_agent_main.invoke(test_payload)
                if response and isinstance(response, str):
                    logger.info("✅ Basic invocation test passed")
                else:
                    logger.error(f"❌ Basic invocation test failed: {response}")
                    return False
            except Exception as e:
                logger.error(f"❌ Basic invocation test error: {e}")
                return False
            
            logger.info("✅ All deployment tests passed")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error running deployment tests: {e}")
            return False
        finally:
            # Clean up sys.path
            if str(self.deployment_root) in sys.path:
                sys.path.remove(str(self.deployment_root))
    
    def deploy(self) -> bool:
        """
        Execute full deployment process
        
        Returns:
            bool: True if deployment succeeded
        """
        logger.info(f"Starting deployment process for environment: {self.environment}")
        
        # Print deployment summary
        self.config.print_deployment_summary()
        
        # Step 1: Validate prerequisites
        if not self.validate_prerequisites():
            logger.error("❌ Prerequisites validation failed")
            return False
        
        # Step 2: Prepare deployment package
        if not self.prepare_deployment_package():
            logger.error("❌ Deployment package preparation failed")
            return False
        
        # Step 3: Run deployment tests
        if not self.run_deployment_tests():
            logger.error("❌ Deployment tests failed")
            return False
        
        # Step 4: Deploy Lambda function
        if not self.deploy_lambda_function():
            logger.error("❌ Lambda function deployment failed")
            return False
        
        # Step 5: Configure AgentCore Memory
        if not self.configure_agentcore_memory():
            logger.error("❌ AgentCore Memory configuration failed")
            return False
        
        logger.info("🎉 Deployment completed successfully!")
        
        if not self.dry_run:
            logger.info("Next steps:")
            logger.info("1. Update your CDK/CloudFormation template with the new configuration")
            logger.info("2. Deploy using 'amplify push' or your deployment pipeline")
            logger.info("3. Test the deployed function using the AWS console or API calls")
            logger.info("4. Monitor CloudWatch logs for any issues")
        
        return True

def main():
    """Main function for deployment script"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Deploy Conversational ASL Agent")
    parser.add_argument(
        "--environment", "-e",
        choices=["dev", "staging", "prod"],
        default="dev",
        help="Target deployment environment"
    )
    parser.add_argument(
        "--dry-run", "-d",
        action="store_true",
        help="Perform dry run without actual deployment"
    )
    parser.add_argument(
        "--validate-only", "-v",
        action="store_true",
        help="Only validate prerequisites and configuration"
    )
    
    args = parser.parse_args()
    
    deployer = ConversationalAgentDeployer(
        environment=args.environment,
        dry_run=args.dry_run or args.validate_only
    )
    
    if args.validate_only:
        logger.info("Running validation only...")
        success = deployer.validate_prerequisites() and deployer.prepare_deployment_package()
        if success:
            logger.info("✅ Validation completed successfully")
            sys.exit(0)
        else:
            logger.error("❌ Validation failed")
            sys.exit(1)
    
    success = deployer.deploy()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()