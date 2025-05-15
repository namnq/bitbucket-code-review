"""
Feedback Collector component that collects and stores user feedback on review comments.
"""

import logging
import json
import os
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple

from galaxy_code_review.bitbucket_api import BitbucketAPI

logger = logging.getLogger(__name__)


class FeedbackCollector:
    """
    Collects and stores user feedback on review comments for future model improvements.
    """
    
    def __init__(self, config: Dict[str, Any], bitbucket_api: Optional[BitbucketAPI] = None):
        """
        Initialize the feedback collector.
        
        Args:
            config: Configuration dictionary
            bitbucket_api: Optional BitbucketAPI instance for collecting reactions
        """
        self.config = config
        self.feedback_dir = config.get('feedback', {}).get('storage_dir', 'feedback_data')
        self.bitbucket_api = bitbucket_api
        
        # Create feedback directory if it doesn't exist
        if not os.path.exists(self.feedback_dir):
            os.makedirs(self.feedback_dir)
            logger.info(f"Created feedback storage directory: {self.feedback_dir}")
            
        # Emoji to rating mapping
        self.emoji_rating_map = {
            "👍": {"rating": 5, "is_helpful": True},     # Thumbs up: 5 stars, helpful
            "❤️": {"rating": 5, "is_helpful": True},     # Heart: 5 stars, helpful
            "🎉": {"rating": 5, "is_helpful": True},     # Party: 5 stars, helpful
            "👎": {"rating": 2, "is_helpful": False},    # Thumbs down: 2 stars, not helpful
            "😕": {"rating": 3, "is_helpful": None},     # Confused: 3 stars, neutral
            "🚀": {"rating": 4, "is_helpful": True},     # Rocket: 4 stars, helpful
            "👀": {"rating": 3, "is_helpful": None},     # Eyes: 3 stars, neutral
        }
    
    def store_feedback(
        self,
        pr_id: str,
        file_path: str,
        comment_id: str,
        feedback: Dict[str, Any]
    ) -> bool:
        """
        Store user feedback for a specific review comment.
        
        Args:
            pr_id: Pull request ID
            file_path: Path to the file that was reviewed
            comment_id: ID of the comment that received feedback
            feedback: Feedback data containing:
                - rating: User rating (1-5)
                - is_helpful: Whether the comment was helpful (boolean)
                - user_comment: Optional user comment about the review
                - accepted: Whether the suggestion was accepted (boolean)
                
        Returns:
            True if feedback was stored successfully, False otherwise
        """
        try:
            # Create a feedback record
            feedback_record = {
                "pr_id": pr_id,
                "file_path": file_path,
                "comment_id": comment_id,
                "timestamp": datetime.now().isoformat(),
                "rating": feedback.get("rating"),
                "is_helpful": feedback.get("is_helpful"),
                "user_comment": feedback.get("user_comment"),
                "accepted": feedback.get("accepted")
            }
            
            # Generate a unique filename for the feedback
            filename = f"{pr_id}_{comment_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}.json"
            filepath = os.path.join(self.feedback_dir, filename)
            
            # Write feedback to file
            with open(filepath, 'w') as f:
                json.dump(feedback_record, f, indent=2)
            
            logger.info(f"Stored feedback for comment {comment_id} in PR {pr_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error storing feedback: {str(e)}")
            return False
    
    def get_all_feedback(self) -> List[Dict[str, Any]]:
        """
        Retrieve all stored feedback records.
        
        Returns:
            List of feedback records
        """
        feedback_records = []
        
        try:
            for filename in os.listdir(self.feedback_dir):
                if filename.endswith('.json'):
                    filepath = os.path.join(self.feedback_dir, filename)
                    with open(filepath, 'r') as f:
                        feedback_record = json.load(f)
                        feedback_records.append(feedback_record)
        except Exception as e:
            logger.error(f"Error retrieving feedback records: {str(e)}")
        
        return feedback_records
    
    def collect_reactions_feedback(
        self,
        repo_slug: str,
        pr_id: int
    ) -> int:
        """
        Collect feedback from comment reactions in a pull request.
        
        Args:
            repo_slug: Repository slug in format workspace/repo-slug
            pr_id: Pull request ID
            
        Returns:
            Number of feedback records collected
        """
        if not self.bitbucket_api:
            logger.warning("BitbucketAPI not provided, cannot collect reactions feedback")
            return 0
            
        try:
            # Get all comments on the PR
            comments = self.bitbucket_api.get_pr_comments(repo_slug, pr_id)
            
            # Filter for comments made by our bot
            # In a real implementation, you would have a way to identify your bot's comments
            # For now, we'll assume all comments with an ID are from our bot
            bot_comments = [c for c in comments if c.get('id')]
            
            feedback_count = 0
            
            for comment in bot_comments:
                comment_id = comment.get('id')
                if not comment_id:
                    continue
                    
                # Get reactions for this comment
                reactions = self.bitbucket_api.get_comment_reactions(repo_slug, pr_id, comment_id)
                
                if not reactions:
                    continue
                    
                # Process each reaction as feedback
                for reaction in reactions:
                    emoji = reaction.get('emoji')
                    user = reaction.get('user', {}).get('display_name', 'Unknown User')
                    
                    if emoji in self.emoji_rating_map:
                        # Convert emoji to feedback data
                        feedback_data = self.emoji_rating_map[emoji].copy()
                        feedback_data['user_comment'] = f"Reaction: {emoji} from {user}"
                        
                        # Store the feedback
                        file_path = comment.get('inline', {}).get('path', '')
                        success = self.store_feedback(
                            pr_id=str(pr_id),
                            file_path=file_path,
                            comment_id=comment_id,
                            feedback=feedback_data
                        )
                        
                        if success:
                            feedback_count += 1
                            
            logger.info(f"Collected {feedback_count} feedback records from reactions in PR #{pr_id}")
            return feedback_count
            
        except Exception as e:
            logger.error(f"Error collecting reactions feedback: {str(e)}")
            return 0
    
    def get_feedback_stats(self) -> Dict[str, Any]:
        """
        Calculate statistics from collected feedback.
        
        Returns:
            Dictionary containing feedback statistics:
            - total_comments: Total number of comments with feedback
            - average_rating: Average rating across all comments
            - helpful_percentage: Percentage of comments marked as helpful
            - acceptance_rate: Percentage of suggestions that were accepted
            - reaction_counts: Count of each reaction type
        """
        feedback_records = self.get_all_feedback()
        
        if not feedback_records:
            return {
                "total_comments": 0,
                "average_rating": 0,
                "helpful_percentage": 0,
                "acceptance_rate": 0,
                "reaction_counts": {}
            }
        
        total = len(feedback_records)
        ratings_sum = sum(record.get("rating", 0) for record in feedback_records if record.get("rating") is not None)
        helpful_count = sum(1 for record in feedback_records if record.get("is_helpful") is True)
        accepted_count = sum(1 for record in feedback_records if record.get("accepted") is True)
        
        # Count reactions
        reaction_counts = {}
        for record in feedback_records:
            user_comment = record.get("user_comment", "")
            if user_comment and user_comment.startswith("Reaction:"):
                # Extract emoji from the user_comment
                parts = user_comment.split()
                if len(parts) > 1:
                    emoji = parts[1]
                    reaction_counts[emoji] = reaction_counts.get(emoji, 0) + 1
        
        # Calculate statistics
        average_rating = ratings_sum / total if total > 0 else 0
        helpful_percentage = (helpful_count / total) * 100 if total > 0 else 0
        acceptance_rate = (accepted_count / total) * 100 if total > 0 else 0
        
        return {
            "total_comments": total,
            "average_rating": round(average_rating, 2),
            "helpful_percentage": round(helpful_percentage, 2),
            "acceptance_rate": round(acceptance_rate, 2),
            "reaction_counts": reaction_counts
        }