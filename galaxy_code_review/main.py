"""
Main entry point for the Bitbucket Galaxy Code Review application.
"""

import argparse
import logging
import sys

from galaxy_code_review.config import load_config
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


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Bitbucket Galaxy Code Review")
    parser.add_argument("--config", type=str, default="config.yaml", 
                        help="Path to configuration file")
    parser.add_argument("--repo", type=str, required=True,
                        help="Repository slug in format workspace/repo-slug")
    parser.add_argument("--pr-id", type=int, required=True,
                        help="Pull request ID to review")
    parser.add_argument("--debug", action="store_true",
                        help="Enable debug logging")
    
    return parser.parse_args()


def main():
    """Main function to run the code review process."""
    args = parse_arguments()
    
    # Set debug logging if requested
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
    try:
        # Load configuration
        config = load_config(args.config)
        
        # Initialize components
        bitbucket_api = BitbucketAPI(config)
        diff_parser = DiffParser()
        context_retriever = ContextRetriever(bitbucket_api)
        reviewer_agent = ReviewerAgent(config)
        comment_formatter = CommentFormatter()
        
        # Get pull request information
        logger.info(f"Retrieving PR #{args.pr_id} from {args.repo}")
        pr_info = bitbucket_api.get_pull_request(args.repo, args.pr_id)
        
        # Get diff from pull request
        diff = bitbucket_api.get_pull_request_diff(args.repo, args.pr_id)
        
        # Parse diff to extract changed files and lines
        changed_files = diff_parser.parse(diff)
        
        # For each changed file, retrieve context and perform review
        for file_path, changes in changed_files.items():
            logger.info(f"Reviewing changes in {file_path}")
            
            # Get file context
            file_context = context_retriever.get_context(args.repo, pr_info, file_path)
            
            # Perform code review
            review_comments = reviewer_agent.review(file_path, changes, file_context)
            
            # Format comments for Bitbucket
            formatted_comments = comment_formatter.format(review_comments)
            
            # Post comments to Bitbucket
            for comment in formatted_comments:
                bitbucket_api.post_comment(args.repo, args.pr_id, comment)
        
        logger.info("Code review completed successfully")
        
    except Exception as e:
        logger.error(f"Error during code review: {str(e)}")
        if args.debug:
            logger.exception("Detailed error information:")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())