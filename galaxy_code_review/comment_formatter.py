"""
Comment Formatter component for generating Bitbucket comments.
"""

import logging
from typing import Dict, List, Any

logger = logging.getLogger(__name__)


class CommentFormatter:
    """
    Formats review comments for Bitbucket API.
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize the comment formatter.
        
        Args:
            config: Configuration dictionary
        """
        self.config = config or {}
        self.feedback_enabled = self.config.get('feedback', {}).get('enable_links', False)
        self.feedback_server_url = self.config.get('feedback', {}).get('server_url', 'http://localhost:8000')
    
    def format(self, review_comments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Format review comments for Bitbucket API.
        
        Args:
            review_comments: List of review comment objects from the reviewer agent
            
        Returns:
            List of formatted comment objects ready for Bitbucket API
        """
        formatted_comments = []
        
        for comment in review_comments:
            formatted_comment = self._format_comment(comment)
            if formatted_comment:
                formatted_comments.append(formatted_comment)
        
        return formatted_comments
    
    def _format_comment(self, comment: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format a single review comment for Bitbucket API.
        
        Args:
            comment: Review comment object from the reviewer agent
            
        Returns:
            Formatted comment object ready for Bitbucket API
        """
        if 'line' not in comment or 'content' not in comment:
            logger.warning("Comment missing required fields, skipping")
            return None
        
        # Get severity emoji
        severity_emoji = self._get_severity_emoji(comment.get('severity', 'info'))
        
        # Get category badge
        category_badge = self._get_category_badge(comment.get('category', 'general'))
        
        # Format the comment content with severity and category
        content = f"{severity_emoji} {category_badge}\n\n{comment['content']}"
        
        # Create the formatted comment object
        formatted_comment = {
            'content': {
                'raw': content
            },
            'inline': {
                'path': comment.get('file_path', ''),
                'to': comment['line']
            }
        }
        
        # Add feedback instructions if enabled in configuration
        if self.feedback_enabled and comment.get('id'):
            # Check if we should use reactions or web links
            use_reactions = self.config.get('feedback', {}).get('use_reactions', True)
            
            if use_reactions:
                feedback_instructions = (
                    "\n\n---\n"
                    "📊 **Was this comment helpful?** React with an emoji:\n"
                    "👍 - Helpful and implemented\n"
                    "❤️ - Very helpful\n"
                    "🚀 - Good suggestion\n"
                    "👀 - Seen but not applicable\n"
                    "👎 - Not helpful"
                )
                formatted_comment['content']['raw'] += feedback_instructions
            else:
                # Use web links as fallback
                feedback_link = (
                    "\n\n---\n"
                    "📊 **Was this comment helpful?** "
                    "[👍 Yes]({}/feedback/helpful?id={}&pr={}) | "
                    "[👎 No]({}/feedback/not-helpful?id={}&pr={})"
                ).format(
                    self.feedback_server_url, comment['id'], comment.get('pr_id', ''),
                    self.feedback_server_url, comment['id'], comment.get('pr_id', '')
                )
                formatted_comment['content']['raw'] += feedback_link
        
        # Preserve original response for fine-tuning if available
        if 'original_response' in comment:
            formatted_comment['original_response'] = comment['original_response']
            
        # Generate a unique ID for the comment if not present
        if 'id' not in comment:
            import uuid
            formatted_comment['id'] = str(uuid.uuid4())
        else:
            formatted_comment['id'] = comment['id']
        
        return formatted_comment
    
    def _get_severity_emoji(self, severity: str) -> str:
        """
        Get emoji for comment severity.
        
        Args:
            severity: Severity level ('info', 'warning', or 'error')
            
        Returns:
            Emoji string
        """
        severity_map = {
            'info': '💡 Info',
            'warning': '⚠️ Warning',
            'error': '🛑 Error'
        }
        
        return severity_map.get(severity.lower(), '💡 Info')
    
    def _get_category_badge(self, category: str) -> str:
        """
        Get badge for comment category.
        
        Args:
            category: Category of the issue
            
        Returns:
            Badge string
        """
        category_map = {
            'security': '🔒 **Security**',
            'performance': '⚡ **Performance**',
            'style': '🎨 **Style**',
            'bug': '🐛 **Bug**',
            'logic': '🧠 **Logic**',
            'maintainability': '🔧 **Maintainability**',
            'test': '🧪 **Testing**',
            'documentation': '📝 **Documentation**'
        }
        
        return category_map.get(category.lower(), f'**{category.capitalize()}**')