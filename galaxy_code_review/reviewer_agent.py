"""
Reviewer Agent component that performs the actual code review using LLM.
Supports multiple model providers: OpenAI (GPT), Anthropic (Claude), and DeepSeek.
"""

import logging
import os
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

# Import model provider libraries
try:
    import openai
except ImportError:
    logger.warning("OpenAI package not installed. GPT models will not be available.")

try:
    import anthropic
except ImportError:
    logger.warning("Anthropic package not installed. Claude models will not be available.")

try:
    import deepseek
except ImportError:
    logger.warning("DeepSeek package not installed. DeepSeek models will not be available.")


class ReviewerAgent:
    """
    LLM-powered component that performs code review.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the reviewer agent.
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        reviewer_config = config.get('reviewer', {})
        
        # Get model configuration
        self.provider = reviewer_config.get('provider', 'openai')
        self.model = reviewer_config.get('model', 'gpt-4')
        self.temperature = reviewer_config.get('temperature', 0.2)
        
        # Initialize clients based on provider
        if self.provider == 'openai':
            self._init_openai_client(reviewer_config)
        elif self.provider == 'anthropic':
            self._init_anthropic_client(reviewer_config)
        elif self.provider == 'deepseek':
            self._init_deepseek_client(reviewer_config)
        else:
            logger.warning(f"Unknown model provider: {self.provider}. Defaulting to OpenAI.")
            self.provider = 'openai'
            self._init_openai_client(reviewer_config)
    
    def _init_openai_client(self, reviewer_config: Dict[str, Any]):
        """Initialize OpenAI client."""
        api_key = os.environ.get('OPENAI_API_KEY') or reviewer_config.get('api_key')
        if api_key:
            try:
                openai.api_key = api_key
                self.openai_client = openai
                logger.info("OpenAI client initialized successfully.")
            except NameError:
                logger.error("OpenAI package not installed. Please install it with 'pip install openai'")
        else:
            logger.warning("No OpenAI API key provided. GPT models will not be available.")
    
    def _init_anthropic_client(self, reviewer_config: Dict[str, Any]):
        """Initialize Anthropic client."""
        api_key = os.environ.get('ANTHROPIC_API_KEY') or reviewer_config.get('anthropic_api_key')
        if api_key:
            try:
                self.anthropic_client = anthropic.Anthropic(api_key=api_key)
                logger.info("Anthropic client initialized successfully.")
            except NameError:
                logger.error("Anthropic package not installed. Please install it with 'pip install anthropic'")
        else:
            logger.warning("No Anthropic API key provided. Claude models will not be available.")
    
    def _init_deepseek_client(self, reviewer_config: Dict[str, Any]):
        """Initialize DeepSeek client."""
        api_key = os.environ.get('DEEPSEEK_API_KEY') or reviewer_config.get('deepseek_api_key')
        if api_key:
            try:
                self.deepseek_client = deepseek.DeepSeek(api_key=api_key)
                logger.info("DeepSeek client initialized successfully.")
            except NameError:
                logger.error("DeepSeek package not installed. Please install it with 'pip install deepseek'")
        else:
            logger.warning("No DeepSeek API key provided. DeepSeek models will not be available.")
    
    def review(
        self, 
        file_path: str, 
        changes: List[Dict[str, Any]], 
        context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Review code changes and provide feedback.
        
        Args:
            file_path: Path to the file being reviewed
            changes: List of change objects from the diff parser
            context: Context information from the context retriever
            
        Returns:
            List of review comment objects, each containing:
            - line: Line number to attach the comment to
            - content: Content of the comment
            - severity: 'info', 'warning', or 'error'
            - category: Category of the issue (e.g., 'security', 'performance')
            - original_response: The original LLM response (for fine-tuning)
        """
        if not changes:
            return []
        
        # Prepare the prompt for the LLM
        prompt = self._prepare_review_prompt(file_path, changes, context)
        
        # Store the original prompt in the context for fine-tuning
        context['original_prompt'] = prompt
        
        # Get review comments from LLM
        try:
            review_response = self._get_llm_review(prompt)
            comments = self._parse_llm_response(review_response)
            
            # Store the original response in each comment for fine-tuning
            for comment in comments:
                comment['original_response'] = review_response
                
            return comments
        except Exception as e:
            logger.error(f"Error during LLM review: {str(e)}")
            return []
    
    def _prepare_review_prompt(
        self, 
        file_path: str, 
        changes: List[Dict[str, Any]], 
        context: Dict[str, Any]
    ) -> str:
        """
        Prepare the prompt for the LLM.
        
        Args:
            file_path: Path to the file being reviewed
            changes: List of change objects
            context: Context information
            
        Returns:
            Formatted prompt string
        """
        file_extension = file_path.split('.')[-1] if '.' in file_path else ''
        language = self._get_language_from_extension(file_extension)
        
        # Format the changes for the prompt
        changes_text = ""
        for change in changes:
            if change['type'] == 'addition':
                line_range = f"Lines {change['start_line']}-{change['end_line']}"
                changes_text += f"\n{line_range} (Added):\n```{language}\n{change['content']}\n```\n"
            elif change['type'] == 'deletion':
                line_range = f"Lines {change.get('old_start_line', '?')}-{change.get('old_end_line', '?')}"
                changes_text += f"\n{line_range} (Removed):\n```{language}\n{change['content']}\n```\n"
        
        # Include relevant context
        context_text = ""
        if context.get('file_content'):
            context_text += f"\nFull file content:\n```{language}\n{context['file_content']}\n```\n"
        
        if context.get('imports'):
            context_text += "\nImports:\n"
            for imp in context['imports']:
                context_text += f"- {imp}\n"
        
        if context.get('pr_description'):
            context_text += f"\nPull Request Description:\n{context['pr_description']}\n"
        
        # Build the complete prompt
        prompt = f"""
You are an expert code reviewer analyzing changes in a pull request.

File: {file_path}
Language: {language}

Your task is to review the following code changes and provide constructive feedback:
{changes_text}

Additional context:
{context_text}

Please analyze the code for:
1. Bugs and logical errors
2. Security vulnerabilities
3. Performance issues
4. Code style and best practices
5. Potential edge cases
6. Maintainability concerns

For each issue you find, provide:
- The line number(s) where the issue occurs
- A clear explanation of the problem
- A suggested fix or improvement
- The severity (info, warning, or error)
- The category of the issue (e.g., security, performance, style)

Format your response as a JSON array of objects, where each object represents a review comment:
[
  {{
    "line": <line_number>,
    "content": "<explanation and suggestion>",
    "severity": "<info|warning|error>",
    "category": "<category>"
  }},
  ...
]

If you don't find any issues, return an empty array: []
"""
        return prompt
    
    def _get_language_from_extension(self, extension: str) -> str:
        """
        Map file extension to language name.
        
        Args:
            extension: File extension
            
        Returns:
            Language name
        """
        extension_map = {
            'py': 'python',
            'js': 'javascript',
            'ts': 'typescript',
            'java': 'java',
            'go': 'go',
            'rb': 'ruby',
            'php': 'php',
            'cs': 'csharp',
            'cpp': 'cpp',
            'c': 'c',
            'h': 'c',
            'hpp': 'cpp',
            'html': 'html',
            'css': 'css',
            'md': 'markdown',
            'json': 'json',
            'yaml': 'yaml',
            'yml': 'yaml',
            'sh': 'bash',
            'sql': 'sql'
        }
        
        return extension_map.get(extension.lower(), 'text')
    
    def _get_llm_review(self, prompt: str) -> str:
        """
        Get review comments from the LLM based on the configured provider.
        
        Args:
            prompt: Formatted prompt string
            
        Returns:
            LLM response as a string
            
        Raises:
            Exception: If the LLM request fails
        """
        system_message = "You are an expert code reviewer providing detailed, actionable feedback."
        
        try:
            if self.provider == 'openai':
                return self._get_openai_review(system_message, prompt)
            elif self.provider == 'anthropic':
                return self._get_anthropic_review(system_message, prompt)
            elif self.provider == 'deepseek':
                return self._get_deepseek_review(system_message, prompt)
            else:
                # Fallback to OpenAI if provider is unknown
                logger.warning(f"Unknown provider {self.provider}, falling back to OpenAI")
                return self._get_openai_review(system_message, prompt)
        except Exception as e:
            logger.error(f"Error calling {self.provider} API: {str(e)}")
            raise
    
    def _get_openai_review(self, system_message: str, prompt: str) -> str:
        """Get review from OpenAI models."""
        try:
            response = openai.ChatCompletion.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": prompt}
                ],
                temperature=self.temperature,
                max_tokens=2000
            )
            
            return response.choices[0].message.content
        except NameError:
            # OpenAI package not installed, return mock response for testing
            logger.warning("Using mock OpenAI response because package is not installed")
            return "[]"
        except Exception as e:
            logger.error(f"Error calling OpenAI API: {str(e)}")
            raise
    
    def _get_anthropic_review(self, system_message: str, prompt: str) -> str:
        """Get review from Anthropic Claude models."""
        try:
            response = self.anthropic_client.messages.create(
                model=self.model,
                system=system_message,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                temperature=self.temperature,
                max_tokens=2000
            )
            
            return response.content[0].text
        except AttributeError:
            # Anthropic client not initialized
            logger.warning("Using mock Claude response because client is not initialized")
            return "[]"
        except Exception as e:
            logger.error(f"Error calling Anthropic API: {str(e)}")
            raise
    
    def _get_deepseek_review(self, system_message: str, prompt: str) -> str:
        """Get review from DeepSeek models."""
        try:
            response = self.deepseek_client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": prompt}
                ],
                temperature=self.temperature,
                max_tokens=2000
            )
            
            return response.choices[0].message.content
        except AttributeError:
            # DeepSeek client not initialized
            logger.warning("Using mock DeepSeek response because client is not initialized")
            return "[]"
        except Exception as e:
            logger.error(f"Error calling DeepSeek API: {str(e)}")
            raise
    
    def _parse_llm_response(self, response: str) -> List[Dict[str, Any]]:
        """
        Parse the LLM response into structured review comments.
        
        Args:
            response: LLM response string
            
        Returns:
            List of review comment objects
        """
        import json
        
        try:
            # Extract JSON array from response (in case there's additional text)
            import re
            json_match = re.search(r'\[[\s\S]*\]', response)
            if json_match:
                json_str = json_match.group(0)
                comments = json.loads(json_str)
                
                # Validate and clean up comments
                valid_comments = []
                for comment in comments:
                    if 'line' in comment and 'content' in comment:
                        # Ensure required fields are present
                        if 'severity' not in comment:
                            comment['severity'] = 'info'
                        if 'category' not in comment:
                            comment['category'] = 'general'
                        
                        valid_comments.append(comment)
                
                return valid_comments
            else:
                logger.warning("No valid JSON array found in LLM response")
                return []
        except json.JSONDecodeError:
            logger.error("Failed to parse LLM response as JSON")
            return []
        except Exception as e:
            logger.error(f"Error parsing LLM response: {str(e)}")
            return []