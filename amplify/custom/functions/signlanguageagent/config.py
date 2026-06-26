"""
Configuration module for the GenASL Sign Language Agent

This module provides centralized configuration management for the agent,
including environment variables, AWS service settings, and agent parameters.
"""

import os
from typing import Dict, Any, Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

@dataclass
class AWSConfig:
    """AWS service configuration"""
    region: str
    pose_bucket: str
    asl_data_bucket: str
    table_name: str
    key_prefix: str

@dataclass
class ModelConfig:
    """AI model configuration"""
    eng_to_asl_model: str
    asl_to_eng_model: Optional[str]
    max_tokens: int
    temperature: float
    top_p: float

@dataclass
class AgentConfig:
    """Agent runtime configuration"""
    log_level: str
    timeout_seconds: int
    max_retries: int
    retry_delay: float

class ConfigManager:
    """Centralized configuration manager for the GenASL agent"""
    
    def __init__(self):
        self.aws = self._load_aws_config()
        self.model = self._load_model_config()
        self.agent = self._load_agent_config()
        
        # Validate configuration
        self._validate_config()
        
        logger.info("Configuration loaded successfully")
    
    def _load_aws_config(self) -> AWSConfig:
        """Load AWS service configuration from environment variables"""
        return AWSConfig(
            region=os.environ.get('AWS_REGION', 'us-west-2'),
            pose_bucket=os.environ.get('POSE_BUCKET', 'genasl-avatar'),
            asl_data_bucket=os.environ.get('ASL_DATA_BUCKET', 'genasl-data'),
            table_name=os.environ.get('TABLE_NAME', 'Pose_Data6'),
            key_prefix=os.environ.get('KEY_PREFIX', 'aslavatarv2/gloss2pose/lookup/')
        )
    
    def _load_model_config(self) -> ModelConfig:
        """Load AI model configuration from environment variables"""
        return ModelConfig(
            eng_to_asl_model=os.environ.get('ENG_TO_ASL_MODEL', 'us.amazon.nova-lite-v1:0'),
            asl_to_eng_model=os.environ.get('ASL_TO_ENG_MODEL'),
            max_tokens=int(os.environ.get('MAX_TOKENS', '3000')),
            temperature=float(os.environ.get('TEMPERATURE', '0.0')),
            top_p=float(os.environ.get('TOP_P', '0.5'))
        )
    
    def _load_agent_config(self) -> AgentConfig:
        """Load agent runtime configuration from environment variables"""
        return AgentConfig(
            log_level=os.environ.get('LOG_LEVEL', 'INFO'),
            timeout_seconds=int(os.environ.get('TIMEOUT_SECONDS', '300')),
            max_retries=int(os.environ.get('MAX_RETRIES', '3')),
            retry_delay=float(os.environ.get('RETRY_DELAY', '1.0'))
        )
    
    def _validate_config(self):
        """Validate the loaded configuration"""
        required_fields = [
            (self.aws.region, 'AWS_REGION'),
            (self.aws.pose_bucket, 'POSE_BUCKET'),
            (self.aws.asl_data_bucket, 'ASL_DATA_BUCKET'),
            (self.aws.table_name, 'TABLE_NAME'),
            (self.model.eng_to_asl_model, 'ENG_TO_ASL_MODEL')
        ]
        
        missing_fields = []
        for value, field_name in required_fields:
            if not value:
                missing_fields.append(field_name)
        
        if missing_fields:
            raise ValueError(f"Missing required configuration fields: {', '.join(missing_fields)}")
        
        # Validate numeric ranges
        if self.model.max_tokens <= 0:
            raise ValueError("MAX_TOKENS must be greater than 0")
        
        if not 0.0 <= self.model.temperature <= 2.0:
            raise ValueError("TEMPERATURE must be between 0.0 and 2.0")
        
        if not 0.0 <= self.model.top_p <= 1.0:
            raise ValueError("TOP_P must be between 0.0 and 1.0")
    
    def get_environment_variables(self) -> Dict[str, str]:
        """Get all configuration as environment variables dictionary"""
        return {
            'AWS_REGION': self.aws.region,
            'POSE_BUCKET': self.aws.pose_bucket,
            'ASL_DATA_BUCKET': self.aws.asl_data_bucket,
            'TABLE_NAME': self.aws.table_name,
            'KEY_PREFIX': self.aws.key_prefix,
            'ENG_TO_ASL_MODEL': self.model.eng_to_asl_model,
            'ASL_TO_ENG_MODEL': self.model.asl_to_eng_model or '',
            'MAX_TOKENS': str(self.model.max_tokens),
            'TEMPERATURE': str(self.model.temperature),
            'TOP_P': str(self.model.top_p),
            'LOG_LEVEL': self.agent.log_level,
            'TIMEOUT_SECONDS': str(self.agent.timeout_seconds),
            'MAX_RETRIES': str(self.agent.max_retries),
            'RETRY_DELAY': str(self.agent.retry_delay)
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary for serialization"""
        return {
            'aws': {
                'region': self.aws.region,
                'pose_bucket': self.aws.pose_bucket,
                'asl_data_bucket': self.aws.asl_data_bucket,
                'table_name': self.aws.table_name,
                'key_prefix': self.aws.key_prefix
            },
            'model': {
                'eng_to_asl_model': self.model.eng_to_asl_model,
                'asl_to_eng_model': self.model.asl_to_eng_model,
                'max_tokens': self.model.max_tokens,
                'temperature': self.model.temperature,
                'top_p': self.model.top_p
            },
            'agent': {
                'log_level': self.agent.log_level,
                'timeout_seconds': self.agent.timeout_seconds,
                'max_retries': self.agent.max_retries,
                'retry_delay': self.agent.retry_delay
            }
        }

# Global configuration instance
config = ConfigManager()