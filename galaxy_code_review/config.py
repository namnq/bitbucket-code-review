"""
Configuration management for Bitbucket Galaxy Code Review.
"""

import os
import yaml
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


def load_config(config_path: str) -> Dict[str, Any]:
    """
    Load configuration from a YAML file.
    
    Args:
        config_path: Path to the configuration file
        
    Returns:
        Dictionary containing configuration values
        
    Raises:
        FileNotFoundError: If the configuration file doesn't exist
        ValueError: If the configuration is invalid
    """
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Configuration file not found: {config_path}")
    
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
    except Exception as e:
        raise ValueError(f"Failed to parse configuration file: {str(e)}")
    
    # Validate required configuration
    validate_config(config)
    
    # Set environment variables if specified
    if 'env_vars' in config:
        for key, value in config['env_vars'].items():
            os.environ[key] = str(value)
    
    return config


def validate_config(config: Dict[str, Any]) -> None:
    """
    Validate that the configuration contains all required fields.
    
    Args:
        config: Configuration dictionary to validate
        
    Raises:
        ValueError: If required configuration is missing
    """
    # Check for required top-level sections
    required_sections = ['bitbucket', 'reviewer']
    for section in required_sections:
        if section not in config:
            raise ValueError(f"Missing required configuration section: {section}")
    
    # Validate Bitbucket configuration
    required_bitbucket_fields = ['username', 'app_password', 'api_url']
    for field in required_bitbucket_fields:
        if field not in config['bitbucket']:
            raise ValueError(f"Missing required Bitbucket configuration: {field}")
    
    # Validate reviewer configuration
    required_reviewer_fields = ['model', 'temperature']
    for field in required_reviewer_fields:
        if field not in config['reviewer']:
            raise ValueError(f"Missing required reviewer configuration: {field}")
    
    logger.debug("Configuration validation successful")