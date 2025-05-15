#!/usr/bin/env python3
"""
Example script demonstrating how to collect feedback from Bitbucket PR comment reactions.
"""

import argparse
import logging
import sys
import os

from galaxy_code_review.config import load_config
from galaxy_code_review.bitbucket_api import BitbucketAPI
from galaxy_code_review.feedback_collector import FeedbackCollector

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)


def main():
    """Main function to demonstrate reaction feedback collection."""
    parser = argparse.ArgumentParser(description="Bitbucket Reaction Feedback Example")
    parser.add_argument("--config", type=str, default="config.yaml", 
                        help="Path to configuration file")
    parser.add_argument("--repo", type=str, required=True,
                        help="Repository slug in format workspace/repo-slug")
    parser.add_argument("--pr-id", type=int, required=True,
                        help="Pull request ID to collect reactions from")
    parser.add_argument("--debug", action="store_true",
                        help="Enable debug logging")
    
    args = parser.parse_args()
    
    # Set debug logging if requested
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
    try:
        # Load configuration
        config = load_config(args.config)
        
        # Initialize components
        bitbucket_api = BitbucketAPI(config)
        feedback_collector = FeedbackCollector(config, bitbucket_api)
        
        # Collect feedback from reactions
        logger.info(f"Collecting feedback from reactions in PR #{args.pr_id} from {args.repo}")
        count = feedback_collector.collect_reactions_feedback(args.repo, args.pr_id)
        
        logger.info(f"Collected {count} feedback records from reactions")
        
        # Show updated statistics
        stats = feedback_collector.get_feedback_stats()
        logger.info("Feedback Statistics:")
        logger.info(f"Total comments with feedback: {stats['total_comments']}")
        logger.info(f"Average rating: {stats['average_rating']}")
        logger.info(f"Percentage marked as helpful: {stats['helpful_percentage']}%")
        logger.info(f"Acceptance rate: {stats['acceptance_rate']}%")
        
        # Show reaction counts
        if 'reaction_counts' in stats and stats['reaction_counts']:
            logger.info("Reaction counts:")
            for emoji, count in stats['reaction_counts'].items():
                logger.info(f"  {emoji}: {count}")
        
        return 0
        
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        if args.debug:
            logger.exception("Detailed error information:")
        return 1


if __name__ == "__main__":
    sys.exit(main())