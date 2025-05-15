"""
Context Retriever component for collecting relevant context from the codebase.
"""

import logging
from typing import Dict, List, Any, Optional

from galaxy_code_review.bitbucket_api import BitbucketAPI

logger = logging.getLogger(__name__)


class ContextRetriever:
    """
    Retrieves relevant context for code changes to provide to the reviewer agent.
    """
    
    def __init__(self, bitbucket_api: BitbucketAPI):
        """
        Initialize the context retriever.
        
        Args:
            bitbucket_api: BitbucketAPI instance for retrieving files
        """
        self.bitbucket_api = bitbucket_api
    
    def get_context(
        self, 
        repo_slug: str, 
        pr_info: Dict[str, Any], 
        file_path: str
    ) -> Dict[str, Any]:
        """
        Get context for a specific file in a pull request.
        
        Args:
            repo_slug: Repository slug in format workspace/repo-slug
            pr_info: Pull request information
            file_path: Path to the file
            
        Returns:
            Dictionary containing context information:
            - file_content: Current content of the file
            - imports: List of imported modules/packages
            - related_files: List of related files and their content
            - file_history: Recent commit history for this file
            - pr_description: Description of the pull request
        """
        context = {
            'file_content': self._get_file_content(repo_slug, pr_info, file_path),
            'imports': self._extract_imports(repo_slug, pr_info, file_path),
            'related_files': self._find_related_files(repo_slug, pr_info, file_path),
            'file_history': self._get_file_history(repo_slug, file_path),
            'pr_description': pr_info.get('description', '')
        }
        
        return context
    
    def _get_file_content(
        self, 
        repo_slug: str, 
        pr_info: Dict[str, Any], 
        file_path: str
    ) -> str:
        """
        Get the current content of a file in the pull request.
        
        Args:
            repo_slug: Repository slug
            pr_info: Pull request information
            file_path: Path to the file
            
        Returns:
            Content of the file as a string
        """
        try:
            # Get the file from the source branch of the PR
            source_branch = pr_info.get('source', {}).get('branch', {}).get('name')
            if not source_branch:
                logger.warning(f"Could not determine source branch for PR, using default branch")
                return self.bitbucket_api.get_file_content(repo_slug, file_path)
            
            return self.bitbucket_api.get_file_content(repo_slug, file_path, source_branch)
        except Exception as e:
            logger.warning(f"Failed to get content for {file_path}: {str(e)}")
            return ""
    
    def _extract_imports(
        self, 
        repo_slug: str, 
        pr_info: Dict[str, Any], 
        file_path: str
    ) -> List[str]:
        """
        Extract import statements from a file to understand dependencies.
        
        Args:
            repo_slug: Repository slug
            pr_info: Pull request information
            file_path: Path to the file
            
        Returns:
            List of import statements
        """
        content = self._get_file_content(repo_slug, pr_info, file_path)
        if not content:
            return []
        
        imports = []
        
        # Simple regex-based extraction for different languages
        if file_path.endswith('.py'):
            # Python imports
            import re
            import_patterns = [
                r'^\s*import\s+(.+?)(?:\s+as\s+.+?)?\s*$',  # import module
                r'^\s*from\s+(.+?)\s+import\s+.+?\s*$'      # from module import ...
            ]
            
            for pattern in import_patterns:
                for line in content.split('\n'):
                    match = re.match(pattern, line)
                    if match:
                        imports.append(match.group(0).strip())
        
        elif file_path.endswith('.js') or file_path.endswith('.ts'):
            # JavaScript/TypeScript imports
            import re
            import_patterns = [
                r'^\s*import\s+.*?from\s+[\'"](.+?)[\'"].*?\s*$',  # import ... from 'module'
                r'^\s*const\s+.*?require\([\'"](.+?)[\'"]\).*?\s*$'  # const ... = require('module')
            ]
            
            for pattern in import_patterns:
                for line in content.split('\n'):
                    match = re.match(pattern, line)
                    if match:
                        imports.append(match.group(0).strip())
        
        # Add more language-specific import extraction as needed
        
        return imports
    
    def _find_related_files(
        self, 
        repo_slug: str, 
        pr_info: Dict[str, Any], 
        file_path: str
    ) -> Dict[str, str]:
        """
        Find files related to the current file based on imports and naming patterns.
        
        Args:
            repo_slug: Repository slug
            pr_info: Pull request information
            file_path: Path to the file
            
        Returns:
            Dictionary mapping file paths to their content
        """
        related_files = {}
        
        # Get files in the same directory
        directory = '/'.join(file_path.split('/')[:-1])
        if directory:
            try:
                directory_files = self.bitbucket_api.list_directory(
                    repo_slug, 
                    directory, 
                    pr_info.get('source', {}).get('branch', {}).get('name')
                )
                
                # Get content of files in the same directory (limit to 5 to avoid too much data)
                for related_path in directory_files[:5]:
                    if related_path != file_path:
                        content = self._get_file_content(repo_slug, pr_info, related_path)
                        if content:
                            related_files[related_path] = content
            except Exception as e:
                logger.warning(f"Failed to list directory {directory}: {str(e)}")
        
        # Find test files for the current file
        filename = file_path.split('/')[-1]
        base_name = filename.split('.')[0]
        
        # Common test file naming patterns
        test_patterns = [
            f"test_{base_name}",
            f"{base_name}_test",
            f"tests/{base_name}_test",
            f"tests/test_{base_name}"
        ]
        
        for pattern in test_patterns:
            try:
                # Try to find test files with common extensions
                for ext in ['.py', '.js', '.ts', '.java', '.go']:
                    test_path = f"{pattern}{ext}"
                    content = self._get_file_content(repo_slug, pr_info, test_path)
                    if content:
                        related_files[test_path] = content
                        break  # Found one test file, no need to check other extensions
            except Exception:
                # Ignore errors when test files don't exist
                pass
        
        return related_files
    
    def _get_file_history(self, repo_slug: str, file_path: str) -> List[Dict[str, Any]]:
        """
        Get recent commit history for a file.
        
        Args:
            repo_slug: Repository slug
            file_path: Path to the file
            
        Returns:
            List of recent commits affecting this file
        """
        try:
            # Get the last 5 commits for this file
            commits = self.bitbucket_api.get_file_commits(repo_slug, file_path, limit=5)
            return commits
        except Exception as e:
            logger.warning(f"Failed to get commit history for {file_path}: {str(e)}")
            return []