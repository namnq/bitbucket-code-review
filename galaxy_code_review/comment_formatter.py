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