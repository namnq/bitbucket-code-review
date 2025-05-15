#!/usr/bin/env python3
"""
Example script to demonstrate the Bitbucket Galaxy Code Review system.
This script simulates a code review on a mock pull request.
"""

import logging
import sys
import yaml

from galaxy_code_review.bitbucket_api import BitbucketAPI
from galaxy_code_review.diff_parser import DiffParser
from galaxy_code_review.context_retriever import ContextRetriever
from galaxy_code_review.reviewer_agent import ReviewerAgent
from galaxy_code_review.comment_formatter import CommentFormatter

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)


# Mock data for demonstration
MOCK_DIFF = """diff --git a/example.py b/example.py
index 1234567..abcdefg 100644
--- a/example.py
+++ b/example.py
@@ -1,5 +1,6 @@
 import os
 import sys
+import json
 
 def process_data(data):
     # Process the input data
@@ -10,7 +11,7 @@ def process_data(data):
     return result
 
 def validate_input(input_data):
-    if input_data is None:
+    if not input_data:
         return False
     
     # Additional validation logic
@@ -20,6 +21,13 @@ def validate_input(input_data):
 def main():
     data = get_data_from_user()
     if validate_input(data):
-        result = process_data(data)
-        print(f"Result: {result}")
+        try:
+            result = process_data(data)
+            print(f"Result: {result}")
+        except Exception as e:
+            print(f"Error processing data: {str(e)}")
+
+def get_data_from_user():
+    user_input = input("Enter data: ")
+    return json.loads(user_input)
"""

MOCK_FILE_CONTENT = """import os
import sys
import json

def process_data(data):
    # Process the input data
    result = {}
    for key, value in data.items():
        result[key] = value * 2
    
    return result

def validate_input(input_data):
    if not input_data:
        return False
    
    # Additional validation logic
    return True

def main():
    data = get_data_from_user()
    if validate_input(data):
        try:
            result = process_data(data)
            print(f"Result: {result}")
        except Exception as e:
            print(f"Error processing data: {str(e)}")

def get_data_from_user():
    user_input = input("Enter data: ")
    return json.loads(user_input)
"""

MOCK_PR_INFO = {
    "id": 123,
    "title": "Add JSON support",
    "description": "This PR adds JSON support for user input data.",
    "source": {
        "branch": {
            "name": "feature/json-support"
        }
    },
    "destination": {
        "branch": {
            "name": "main"
        }
    }
}


class MockBitbucketAPI(BitbucketAPI):
    """Mock BitbucketAPI for demonstration purposes."""
    
    def __init__(self):
        """Initialize with mock config."""
        self.username = "mock_user"
        self.app_password = "mock_password"
        self.api_url = "https://api.bitbucket.org/2.0/"
    
    def get_pull_request(self, repo_slug, pr_id):
        """Return mock PR info."""
        return MOCK_PR_INFO
    
    def get_pull_request_diff(self, repo_slug, pr_id):
        """Return mock diff."""
        return MOCK_DIFF
    
    def get_file_content(self, repo_slug, file_path, ref=None):
        """Return mock file content."""
        return MOCK_FILE_CONTENT
    
    def list_directory(self, repo_slug, directory_path, ref=None):
        """Return mock directory listing."""
        return ["example.py"]
    
    def get_file_commits(self, repo_slug, file_path, limit=5):
        """Return mock commits."""
        return [
            {
                "hash": "abc123",
                "message": "Initial commit",
                "date": "2025-05-10T12:00:00Z"
            }
        ]
    
    def post_comment(self, repo_slug, pr_id, comment):
        """Mock posting a comment."""
        logger.info(f"Would post comment to PR #{pr_id}:")
        logger.info(f"  Line: {comment.get('inline', {}).get('to', 'N/A')}")
        logger.info(f"  Content: {comment.get('content', {}).get('raw', '')}")
        return {"id": 456}


class MockReviewerAgent(ReviewerAgent):
    """Mock ReviewerAgent that returns predefined comments."""
    
    def __init__(self):
        """Initialize with mock config."""
        self.config = {
            "reviewer": {
                "model": "mock-model",
                "temperature": 0.2
            }
        }
        self.model = self.config["reviewer"]["model"]
        self.temperature = self.config["reviewer"]["temperature"]
    
    def review(self, file_path, changes, context):
        """Return mock review comments."""
        return [
            {
                "line": 21,
                "content": "Consider adding type hints to the function parameters and return values for better code readability and IDE support.",
                "severity": "info",
                "category": "style"
            },
            {
                "line": 31,
                "content": "The `json.loads()` function can raise a `json.JSONDecodeError` if the input is not valid JSON. You should handle this exception explicitly.",
                "severity": "warning",
                "category": "error-handling"
            },
            {
                "line": 11,
                "content": "The condition `if not input_data:` will return False for empty dictionaries, lists, and strings, not just None. Make sure this is the intended behavior.",
                "severity": "warning",
                "category": "logic"
            }
        ]


def main():
    """Run a simulated code review."""
    logger.info("Starting simulated code review")
    
    # Create mock components
    bitbucket_api = MockBitbucketAPI()
    diff_parser = DiffParser()
    context_retriever = ContextRetriever(bitbucket_api)
    reviewer_agent = MockReviewerAgent()
    comment_formatter = CommentFormatter()
    
    # Simulate repository and PR information
    repo_slug = "workspace/repo"
    pr_id = 123
    
    # Get PR information and diff
    pr_info = bitbucket_api.get_pull_request(repo_slug, pr_id)
    diff = bitbucket_api.get_pull_request_diff(repo_slug, pr_id)
    
    # Parse diff
    changed_files = diff_parser.parse(diff)
    
    # Process each changed file
    for file_path, changes in changed_files.items():
        logger.info(f"Reviewing changes in {file_path}")
        
        # Get file context
        file_context = context_retriever.get_context(repo_slug, pr_info, file_path)
        
        # Perform code review
        review_comments = reviewer_agent.review(file_path, changes, file_context)
        
        # Format comments
        formatted_comments = comment_formatter.format(review_comments)
        
        # Post comments
        for comment in formatted_comments:
            bitbucket_api.post_comment(repo_slug, pr_id, comment)
    
    logger.info("Simulated code review completed")


if __name__ == "__main__":
    main()