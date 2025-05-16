"""
Model Fine-Tuner component that uses feedback data to improve the review model.
Supports multiple model providers: OpenAI (GPT), Anthropic (Claude), and DeepSeek.
"""

import logging
import json
import os
from typing import Dict, List, Any, Optional
import time

logger = logging.getLogger(__name__)

# Import model provider libraries
try:
    import openai
except ImportError:
    logger.warning("OpenAI package not installed. GPT fine-tuning will not be available.")

try:
    import anthropic
except ImportError:
    logger.warning("Anthropic package not installed. Claude fine-tuning will not be available.")

try:
    import deepseek
except ImportError:
    logger.warning("DeepSeek package not installed. DeepSeek fine-tuning will not be available.")


class ModelFineTuner:
    """
    Uses collected feedback to fine-tune the LLM for improved code reviews.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the model fine-tuner.
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.fine_tuning_config = config.get('fine_tuning', {})
        self.reviewer_config = config.get('reviewer', {})
        
        # Get provider from reviewer config
        self.provider = self.reviewer_config.get('provider', 'openai')
        
        # Get model configuration based on provider
        if self.provider == 'openai':
            self.base_model = self.fine_tuning_config.get('base_model', 'gpt-3.5-turbo')
        elif self.provider == 'anthropic':
            self.base_model = self.fine_tuning_config.get('base_model', 'claude-3-sonnet-20240229')
        elif self.provider == 'deepseek':
            self.base_model = self.fine_tuning_config.get('base_model', 'deepseek-chat')
        else:
            logger.warning(f"Unknown provider {self.provider}, defaulting to OpenAI")
            self.provider = 'openai'
            self.base_model = self.fine_tuning_config.get('base_model', 'gpt-3.5-turbo')
        
        self.training_file_dir = self.fine_tuning_config.get('training_file_dir', 'training_data')
        
        # Create training data directory if it doesn't exist
        if not os.path.exists(self.training_file_dir):
            os.makedirs(self.training_file_dir)
            logger.info(f"Created training data directory: {self.training_file_dir}")
        
        # Initialize clients based on provider
        if self.provider == 'openai':
            self._init_openai_client()
        elif self.provider == 'anthropic':
            self._init_anthropic_client()
        elif self.provider == 'deepseek':
            self._init_deepseek_client()
    
    def _init_openai_client(self):
        """Initialize OpenAI client."""
        api_key = os.environ.get('OPENAI_API_KEY') or self.reviewer_config.get('api_key')
        if api_key:
            try:
                openai.api_key = api_key
                self.openai_client = openai
                logger.info("OpenAI client initialized successfully for fine-tuning.")
            except NameError:
                logger.error("OpenAI package not installed. Please install it with 'pip install openai'")
        else:
            logger.warning("No OpenAI API key provided. GPT fine-tuning will not be available.")
    
    def _init_anthropic_client(self):
        """Initialize Anthropic client."""
        api_key = os.environ.get('ANTHROPIC_API_KEY') or self.reviewer_config.get('anthropic_api_key')
        if api_key:
            try:
                self.anthropic_client = anthropic.Anthropic(api_key=api_key)
                logger.info("Anthropic client initialized successfully for fine-tuning.")
            except NameError:
                logger.error("Anthropic package not installed. Please install it with 'pip install anthropic'")
        else:
            logger.warning("No Anthropic API key provided. Claude fine-tuning will not be available.")
    
    def _init_deepseek_client(self):
        """Initialize DeepSeek client."""
        api_key = os.environ.get('DEEPSEEK_API_KEY') or self.reviewer_config.get('deepseek_api_key')
        if api_key:
            try:
                self.deepseek_client = deepseek.DeepSeek(api_key=api_key)
                logger.info("DeepSeek client initialized successfully for fine-tuning.")
            except NameError:
                logger.error("DeepSeek package not installed. Please install it with 'pip install deepseek'")
        else:
            logger.warning("No DeepSeek API key provided. DeepSeek fine-tuning will not be available.")
    
    def prepare_training_data(self, feedback_collector, min_rating: int = 4) -> str:
        """
        Prepare training data from feedback records using the FeedbackCollector.
        
        Args:
            feedback_collector: FeedbackCollector instance
            min_rating: Minimum rating threshold for including feedback (default: 4)
            
        Returns:
            Path to the prepared training file
        """
        # Export feedback data in the format required by the current provider
        training_examples = feedback_collector.export_feedback_for_fine_tuning(
            provider=self.provider,
            min_rating=min_rating
        )
        
        if not training_examples:
            logger.warning(f"No high-quality feedback records found for {self.provider} training")
            return ""
        
        if not training_examples:
            logger.warning("No valid training examples could be created")
            return ""
        
        # Write training examples to a JSONL file
        timestamp = time.strftime("%Y%m%d%H%M%S")
        training_file_path = os.path.join(self.training_file_dir, f"training_data_{timestamp}.jsonl")
        
        with open(training_file_path, 'w') as f:
            for example in training_examples:
                f.write(json.dumps(example) + '\n')
        
        logger.info(f"Created training file with {len(training_examples)} examples: {training_file_path}")
        return training_file_path
    
    def start_fine_tuning(self, training_file_path: str) -> Optional[str]:
        """
        Start the fine-tuning process based on the configured provider.
        
        Args:
            training_file_path: Path to the training data file
            
        Returns:
            Fine-tuning job ID if successful, None otherwise
        """
        if not training_file_path or not os.path.exists(training_file_path):
            logger.error(f"Training file not found: {training_file_path}")
            return None
        
        try:
            # Route to the appropriate fine-tuning method based on provider
            if self.provider == 'openai':
                return self._start_openai_fine_tuning(training_file_path)
            elif self.provider == 'anthropic':
                return self._start_anthropic_fine_tuning(training_file_path)
            elif self.provider == 'deepseek':
                return self._start_deepseek_fine_tuning(training_file_path)
            else:
                logger.warning(f"Unknown provider {self.provider}, defaulting to OpenAI")
                return self._start_openai_fine_tuning(training_file_path)
        except Exception as e:
            logger.error(f"Error starting fine-tuning job with {self.provider}: {str(e)}")
            return None
    
    def _start_openai_fine_tuning(self, training_file_path: str) -> Optional[str]:
        """Start fine-tuning with OpenAI."""
        try:
            logger.info(f"Starting OpenAI fine-tuning with file: {training_file_path}")
            logger.info(f"Base model: {self.base_model}")
            
            # For demonstration purposes, we'll simulate a successful fine-tuning job
            # In a real implementation, you would use the OpenAI API client
            import uuid
            job_id = f"ft-openai-{uuid.uuid4()}"
            
            logger.info(f"Started OpenAI fine-tuning job with ID: {job_id}")
            return job_id
            
            # The actual implementation would look like this:
            """
            # Import the OpenAI client
            from openai import OpenAI
            
            # Initialize the client
            client = OpenAI(api_key=openai.api_key)
            
            # Upload the training file
            with open(training_file_path, 'rb') as f:
                training_file = client.files.create(
                    file=f,
                    purpose='fine-tune'
                )
            
            file_id = training_file.id
            logger.info(f"Uploaded training file with ID: {file_id}")
            
            # Start fine-tuning job
            fine_tuning_job = client.fine_tuning.jobs.create(
                training_file=file_id,
                model=self.base_model,
                suffix=f"galaxy_code_review_{time.strftime('%Y%m%d')}"
            )
            
            job_id = fine_tuning_job.id
            logger.info(f"Started fine-tuning job with ID: {job_id}")
            
            return job_id
            """
            
        except NameError:
            logger.error("OpenAI package not installed. Fine-tuning is not available.")
            return None
        except Exception as e:
            logger.error(f"Error starting OpenAI fine-tuning job: {str(e)}")
            return None
    
    def _start_anthropic_fine_tuning(self, training_file_path: str) -> Optional[str]:
        """Start fine-tuning with Anthropic Claude."""
        try:
            logger.info(f"Starting Anthropic fine-tuning with file: {training_file_path}")
            logger.info(f"Base model: {self.base_model}")
            
            # Note: This is a placeholder as Anthropic's fine-tuning API may differ
            # Check Anthropic's documentation for the actual implementation
            import uuid
            job_id = f"ft-anthropic-{uuid.uuid4()}"
            
            logger.info(f"Started Anthropic fine-tuning job with ID: {job_id}")
            logger.warning("Note: Anthropic fine-tuning is a placeholder and may not be fully implemented")
            
            return job_id
            
        except NameError:
            logger.error("Anthropic package not installed. Fine-tuning is not available.")
            return None
        except Exception as e:
            logger.error(f"Error starting Anthropic fine-tuning job: {str(e)}")
            return None
    
    def _start_deepseek_fine_tuning(self, training_file_path: str) -> Optional[str]:
        """Start fine-tuning with DeepSeek."""
        try:
            logger.info(f"Starting DeepSeek fine-tuning with file: {training_file_path}")
            logger.info(f"Base model: {self.base_model}")
            
            # Note: This is a placeholder as DeepSeek's fine-tuning API may differ
            # Check DeepSeek's documentation for the actual implementation
            import uuid
            job_id = f"ft-deepseek-{uuid.uuid4()}"
            
            logger.info(f"Started DeepSeek fine-tuning job with ID: {job_id}")
            logger.warning("Note: DeepSeek fine-tuning is a placeholder and may not be fully implemented")
            
            return job_id
            
        except NameError:
            logger.error("DeepSeek package not installed. Fine-tuning is not available.")
            return None
        except Exception as e:
            logger.error(f"Error starting DeepSeek fine-tuning job: {str(e)}")
            return None
    
    def check_fine_tuning_status(self, job_id: str) -> Dict[str, Any]:
        """
        Check the status of a fine-tuning job based on the configured provider.
        
        Args:
            job_id: Fine-tuning job ID
            
        Returns:
            Dictionary containing job status information
        """
        try:
            # Determine provider from job ID prefix
            if job_id.startswith("ft-openai-"):
                return self._check_openai_fine_tuning_status(job_id)
            elif job_id.startswith("ft-anthropic-"):
                return self._check_anthropic_fine_tuning_status(job_id)
            elif job_id.startswith("ft-deepseek-"):
                return self._check_deepseek_fine_tuning_status(job_id)
            else:
                # If no prefix, use the configured provider
                if self.provider == 'openai':
                    return self._check_openai_fine_tuning_status(job_id)
                elif self.provider == 'anthropic':
                    return self._check_anthropic_fine_tuning_status(job_id)
                elif self.provider == 'deepseek':
                    return self._check_deepseek_fine_tuning_status(job_id)
                else:
                    logger.warning(f"Unknown provider {self.provider}, defaulting to OpenAI")
                    return self._check_openai_fine_tuning_status(job_id)
        except Exception as e:
            logger.error(f"Error checking fine-tuning job status: {str(e)}")
            return {"status": "error", "error": str(e)}
    
    def _check_openai_fine_tuning_status(self, job_id: str) -> Dict[str, Any]:
        """Check status of OpenAI fine-tuning job."""
        try:
            # For demonstration purposes, we'll simulate a fine-tuning job status
            # In a real implementation, you would use the OpenAI API client
            import time
            
            status = {
                "provider": "openai",
                "status": "succeeded",
                "created_at": time.time() - 3600,  # 1 hour ago
                "finished_at": time.time() - 600,  # 10 minutes ago
                "fine_tuned_model": f"ft:gpt-3.5-turbo:galaxy-code-review:{time.strftime('%Y%m%d')}",
                "error": None
            }
            
            logger.info(f"Retrieved simulated status for OpenAI job {job_id}: {status['status']}")
            return status
            
            # The actual implementation would look like this:
            """
            # Import the OpenAI client
            from openai import OpenAI
            
            # Initialize the client
            client = OpenAI(api_key=openai.api_key)
            
            # Retrieve the fine-tuning job
            fine_tuning_job = client.fine_tuning.jobs.retrieve(job_id)
            
            status = {
                "provider": "openai",
                "status": fine_tuning_job.status,
                "created_at": fine_tuning_job.created_at,
                "finished_at": fine_tuning_job.finished_at,
                "fine_tuned_model": fine_tuning_job.fine_tuned_model,
                "error": fine_tuning_job.error
            }
            
            return status
            """
            
        except NameError:
            logger.error("OpenAI package not installed. Fine-tuning status check is not available.")
            return {"provider": "openai", "status": "error", "error": "OpenAI package not installed"}
        except Exception as e:
            logger.error(f"Error checking OpenAI fine-tuning status: {str(e)}")
            return {"provider": "openai", "status": "error", "error": str(e)}
    
    def _check_anthropic_fine_tuning_status(self, job_id: str) -> Dict[str, Any]:
        """Check status of Anthropic fine-tuning job."""
        try:
            # Note: This is a placeholder as Anthropic's fine-tuning API may differ
            # Check Anthropic's documentation for the actual implementation
            import time
            
            status = {
                "provider": "anthropic",
                "status": "succeeded",
                "created_at": time.time() - 3600,  # 1 hour ago
                "finished_at": time.time() - 600,  # 10 minutes ago
                "fine_tuned_model": f"claude-3-sonnet-ft-{job_id}",
                "error": None
            }
            
            logger.info(f"Retrieved simulated status for Anthropic job {job_id}: {status['status']}")
            logger.warning("Note: Anthropic fine-tuning status check is a placeholder")
            return status
            
        except NameError:
            logger.error("Anthropic package not installed. Fine-tuning status check is not available.")
            return {"provider": "anthropic", "status": "error", "error": "Anthropic package not installed"}
        except Exception as e:
            logger.error(f"Error checking Anthropic fine-tuning status: {str(e)}")
            return {"provider": "anthropic", "status": "error", "error": str(e)}
    
    def _check_deepseek_fine_tuning_status(self, job_id: str) -> Dict[str, Any]:
        """Check status of DeepSeek fine-tuning job."""
        try:
            # Note: This is a placeholder as DeepSeek's fine-tuning API may differ
            # Check DeepSeek's documentation for the actual implementation
            import time
            
            status = {
                "provider": "deepseek",
                "status": "succeeded",
                "created_at": time.time() - 3600,  # 1 hour ago
                "finished_at": time.time() - 600,  # 10 minutes ago
                "fine_tuned_model": f"deepseek-chat-ft-{job_id}",
                "error": None
            }
            
            logger.info(f"Retrieved simulated status for DeepSeek job {job_id}: {status['status']}")
            logger.warning("Note: DeepSeek fine-tuning status check is a placeholder")
            return status
            
        except NameError:
            logger.error("DeepSeek package not installed. Fine-tuning status check is not available.")
            return {"provider": "deepseek", "status": "error", "error": "DeepSeek package not installed"}
        except Exception as e:
            logger.error(f"Error checking DeepSeek fine-tuning status: {str(e)}")
            return {"provider": "deepseek", "status": "error", "error": str(e)}
    
    def update_model_in_config(self, fine_tuned_model: str, provider: Optional[str] = None) -> bool:
        """
        Update the configuration to use the fine-tuned model.
        
        Args:
            fine_tuned_model: Name of the fine-tuned model
            provider: Model provider (openai, anthropic, deepseek). If None, use the current provider.
            
        Returns:
            True if the configuration was updated successfully, False otherwise
        """
        try:
            # If provider is specified, update it in the config
            if provider:
                self.config['reviewer']['provider'] = provider
            
            # Update the model in the config
            self.config['reviewer']['model'] = fine_tuned_model
            
            # You might also want to save the updated configuration to disk
            # with open('config.yaml', 'w') as f:
            #     yaml.dump(self.config, f)
            
            provider_info = f" with provider {provider}" if provider else ""
            logger.info(f"Updated configuration to use fine-tuned model: {fine_tuned_model}{provider_info}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating model in configuration: {str(e)}")
            return False