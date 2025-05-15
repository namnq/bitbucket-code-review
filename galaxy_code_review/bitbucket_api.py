"""
Bitbucket API integration for Galaxy Code Review.
"""

import logging
import requests
from typing import Dict, List, Any, Optional
from urllib.parse import urljoin

logger = logging.getLogger(__name__)


class BitbucketAPI:
    """
    Client for interacting with Bitbucket Cloud API.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the Bitbucket API client.
        
        Args:
            config: Configuration dictionary containing Bitbucket credentials
        """
        self.username = config['bitbucket']['username']
        self.app_password = config['bitbucket']['app_password']
        self.api_url = config['bitbucket']['api_url']
        
        # Ensure API URL ends with a slash
        if not self.api_url.endswith('/'):
            self.api_url += '/'
    
    def get_pull_request(self, repo_slug: str, pr_id: int) -> Dict[str, Any]:
        """
        Get pull request information.
        
        Args:
            repo_slug: Repository slug in format workspace/repo-slug
            pr_id: Pull request ID
            
        Returns:
            Pull request information as a dictionary
            
        Raises:
            Exception: If the API request fails
        """
        url = urljoin(self.api_url, f'repositories/{repo_slug}/pullrequests/{pr_id}')
        
        response = self._make_request('GET', url)
        return response
    
    def get_pull_request_diff(self, repo_slug: str, pr_id: int) -> str:
        """
        Get the diff for a pull request.
        
        Args:
            repo_slug: Repository slug in format workspace/repo-slug
            pr_id: Pull request ID
            
        Returns:
            Diff content as a string
            
        Raises:
            Exception: If the API request fails
        """
        url = urljoin(self.api_url, f'repositories/{repo_slug}/pullrequests/{pr_id}/diff')
        
        response = self._make_request('GET', url, raw=True)
        return response
    
    def get_file_content(
        self, 
        repo_slug: str, 
        file_path: str, 
        ref: Optional[str] = None
    ) -> str:
        """
        Get the content of a file from the repository.
        
        Args:
            repo_slug: Repository slug in format workspace/repo-slug
            file_path: Path to the file
            ref: Git reference (branch, tag, or commit), defaults to the main branch
            
        Returns:
            File content as a string
            
        Raises:
            Exception: If the API request fails
        """
        url = urljoin(self.api_url, f'repositories/{repo_slug}/src')
        if ref:
            url = urljoin(url + '/', f'{ref}/{file_path}')
        else:
            url = urljoin(url + '/', file_path)
        
        response = self._make_request('GET', url, raw=True)
        return response
    
    def list_directory(
        self, 
        repo_slug: str, 
        directory_path: str, 
        ref: Optional[str] = None
    ) -> List[str]:
        """
        List files in a directory.
        
        Args:
            repo_slug: Repository slug in format workspace/repo-slug
            directory_path: Path to the directory
            ref: Git reference (branch, tag, or commit), defaults to the main branch
            
        Returns:
            List of file paths
            
        Raises:
            Exception: If the API request fails
        """
        url = urljoin(self.api_url, f'repositories/{repo_slug}/src')
        if ref:
            url = urljoin(url + '/', f'{ref}/{directory_path}')
        else:
            url = urljoin(url + '/', directory_path)
        
        response = self._make_request('GET', url)
        
        # Extract file paths from the response
        files = []
        for item in response.get('values', []):
            if item.get('type') == 'commit_file':
                files.append(item.get('path'))
        
        return files
    
    def get_file_commits(
        self, 
        repo_slug: str, 
        file_path: str, 
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Get commit history for a file.
        
        Args:
            repo_slug: Repository slug in format workspace/repo-slug
            file_path: Path to the file
            limit: Maximum number of commits to return
            
        Returns:
            List of commit objects
            
        Raises:
            Exception: If the API request fails
        """
        url = urljoin(self.api_url, f'repositories/{repo_slug}/commits')
        params = {
            'path': file_path,
            'limit': limit
        }
        
        response = self._make_request('GET', url, params=params)
        return response.get('values', [])
    
    def post_comment(
        self, 
        repo_slug: str, 
        pr_id: int, 
        comment: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Post a comment on a pull request.
        
        Args:
            repo_slug: Repository slug in format workspace/repo-slug
            pr_id: Pull request ID
            comment: Comment object
            
        Returns:
            API response
            
        Raises:
            Exception: If the API request fails
        """
        url = urljoin(self.api_url, f'repositories/{repo_slug}/pullrequests/{pr_id}/comments')
        
        response = self._make_request('POST', url, json=comment)
        return response
    
    def _make_request(
        self, 
        method: str, 
        url: str, 
        params: Optional[Dict[str, Any]] = None, 
        json: Optional[Dict[str, Any]] = None, 
        raw: bool = False
    ) -> Any:
        """
        Make an HTTP request to the Bitbucket API.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            url: API endpoint URL
            params: Query parameters
            json: JSON body for POST requests
            raw: If True, return the raw response text instead of JSON
            
        Returns:
            Response as a dictionary or string
            
        Raises:
            Exception: If the API request fails
        """
        headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }
        
        try:
            response = requests.request(
                method=method,
                url=url,
                auth=(self.username, self.app_password),
                headers=headers,
                params=params,
                json=json
            )
            
            response.raise_for_status()
            
            if raw:
                return response.text
            else:
                return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed: {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response status: {e.response.status_code}")
                logger.error(f"Response body: {e.response.text}")
            raise Exception(f"Bitbucket API request failed: {str(e)}")