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
from galaxy_code_review.feedback_collector import FeedbackCollector
from galaxy_code_review.model_fine_tuner import ModelFineTuner

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
    parser.add_argument("--repo", type=str, required=False,
                        help="Repository slug in format workspace/repo-slug")
    parser.add_argument("--pr-id", type=int, required=False,
                        help="Pull request ID to review")
    parser.add_argument("--debug", action="store_true",
                        help="Enable debug logging")
    
    # Add feedback and fine-tuning related arguments
    parser.add_argument("--collect-feedback", action="store_true",
                        help="Start feedback collection server")
    parser.add_argument("--feedback-port", type=int, default=8000,
                        help="Port for feedback collection server")
    parser.add_argument("--collect-reactions", action="store_true",
                        help="Collect feedback from PR comment reactions")
    parser.add_argument("--reactions-pr", type=int,
                        help="PR ID to collect reactions from (use with --collect-reactions)")
    parser.add_argument("--fine-tune", action="store_true",
                        help="Start fine-tuning process using collected feedback")
    parser.add_argument("--provider", type=str, choices=["openai", "anthropic", "deepseek"],
                        help="Specify model provider for fine-tuning or feedback stats")
    parser.add_argument("--check-fine-tuning", type=str,
                        help="Check status of a fine-tuning job by ID")
    parser.add_argument("--feedback-stats", action="store_true",
                        help="Show statistics from collected feedback")
    
    args = parser.parse_args()
    
    # Validate arguments
    if not any([args.repo and args.pr_id, args.collect_feedback, args.collect_reactions,
                args.fine_tune, args.check_fine_tuning, args.feedback_stats]):
        parser.error("Either --repo and --pr-id, or one of --collect-feedback, --collect-reactions, "
                    "--fine-tune, --check-fine-tuning, or --feedback-stats is required")
                    
    # Additional validation for reactions collection
    if args.collect_reactions and not args.reactions_pr:
        parser.error("--reactions-pr is required when using --collect-reactions")
    
    return args


def run_feedback_server(config, port):
    """
    Run a web server to collect feedback on review comments.
    
    Args:
        config: Configuration dictionary
        port: Port to run the server on
        
    Returns:
        0 on success, 1 on error
    """
    try:
        import flask
        from flask import Flask, request, jsonify, render_template, redirect, url_for
        import os
        
        app = Flask("BitbucketGalaxyFeedback", 
                   template_folder=os.path.join(os.path.dirname(__file__), 'templates'))
        feedback_collector = FeedbackCollector(config)
        
        @app.route('/', methods=['GET'])
        def index():
            """Home page with feedback statistics."""
            provider = request.args.get('provider', None)
            stats = feedback_collector.get_feedback_stats(provider)
            return render_template('feedback.html', 
                                  stats=stats,
                                  provider=provider,
                                  pr_id="",
                                  comment_id="",
                                  file_path="",
                                  line_number="",
                                  comment_content="")
        
        @app.route('/health', methods=['GET'])
        def health_check():
            """Health check endpoint."""
            return jsonify({"status": "ok"})
        
        @app.route('/feedback', methods=['POST'])
        def submit_feedback():
            """API endpoint to submit feedback."""
            data = request.json
            if not data:
                return jsonify({"error": "No data provided"}), 400
                
            required_fields = ['pr_id', 'file_path', 'comment_id']
            for field in required_fields:
                if field not in data:
                    return jsonify({"error": f"Missing required field: {field}"}), 400
            
            result = feedback_collector.store_feedback(
                pr_id=data['pr_id'],
                file_path=data['file_path'],
                comment_id=data['comment_id'],
                feedback=data.get('feedback', {})
            )
            
            if result:
                return jsonify({"status": "success"})
            else:
                return jsonify({"error": "Failed to store feedback"}), 500
        
        @app.route('/feedback/<pr_id>/<comment_id>', methods=['GET'])
        def feedback_form(pr_id, comment_id):
            """Render feedback form for a specific comment."""
            # In a real implementation, you would retrieve the comment details from a database
            # For this example, we'll use placeholder values
            provider = request.args.get('provider', None)
            stats = feedback_collector.get_feedback_stats(provider)
            
            # Try to get the actual feedback record to display provider info
            feedback_record = None
            all_feedback = feedback_collector.get_all_feedback()
            for record in all_feedback:
                if record.get('pr_id') == pr_id and record.get('comment_id') == comment_id:
                    feedback_record = record
                    break
            
            # Get provider from the record if available
            comment_provider = None
            comment_model = None
            if feedback_record:
                comment_provider = feedback_record.get('provider', 'unknown')
                comment_model = feedback_record.get('model', 'unknown')
            
            return render_template('feedback.html',
                                  pr_id=pr_id,
                                  comment_id=comment_id,
                                  file_path="example/file.py",
                                  line_number="42",
                                  comment_content="This is a sample comment for demonstration purposes.",
                                  provider=provider,
                                  comment_provider=comment_provider,
                                  comment_model=comment_model,
                                  stats=stats)
        
        @app.route('/feedback/helpful', methods=['GET'])
        def helpful_feedback():
            """Quick feedback that a comment was helpful."""
            comment_id = request.args.get('id', '')
            pr_id = request.args.get('pr', '')
            provider = request.args.get('provider', None)
            model = request.args.get('model', None)
            
            if comment_id and pr_id:
                feedback_data = {
                    "rating": 5,
                    "is_helpful": True,
                    "accepted": None,
                    "user_comment": "Marked as helpful via quick feedback link"
                }
                
                # Add provider and model information if available
                if provider:
                    feedback_data["provider"] = provider
                if model:
                    feedback_data["model"] = model
                
                feedback_collector.store_feedback(
                    pr_id=pr_id,
                    file_path="",  # This would be retrieved in a real implementation
                    comment_id=comment_id,
                    feedback=feedback_data
                )
            
            return redirect(url_for('index'))
        
        @app.route('/feedback/not-helpful', methods=['GET'])
        def not_helpful_feedback():
            """Quick feedback that a comment was not helpful."""
            comment_id = request.args.get('id', '')
            pr_id = request.args.get('pr', '')
            provider = request.args.get('provider', None)
            model = request.args.get('model', None)
            
            if comment_id and pr_id:
                feedback_data = {
                    "rating": 2,
                    "is_helpful": False,
                    "accepted": None,
                    "user_comment": "Marked as not helpful via quick feedback link"
                }
                
                # Add provider and model information if available
                if provider:
                    feedback_data["provider"] = provider
                if model:
                    feedback_data["model"] = model
                
                feedback_collector.store_feedback(
                    pr_id=pr_id,
                    file_path="",  # This would be retrieved in a real implementation
                    comment_id=comment_id,
                    feedback=feedback_data
                )
            
            return redirect(url_for('index'))
        
        @app.route('/stats', methods=['GET'])
        def get_stats():
            """API endpoint to get feedback statistics."""
            provider = request.args.get('provider', None)
            stats = feedback_collector.get_feedback_stats(provider)
            return jsonify(stats)
        
        logger.info(f"Starting feedback collection server on port {port}")
        logger.info(f"Access the feedback server at http://localhost:{port}/")
        app.run(host='0.0.0.0', port=port, debug=False)
        return 0
        
    except ImportError:
        logger.error("Flask is required for the feedback server. Install with 'pip install flask'")
        return 1
    except Exception as e:
        logger.error(f"Error running feedback server: {str(e)}")
        return 1


def run_fine_tuning(config):
    """
    Run the fine-tuning process using collected feedback.
    
    Args:
        config: Configuration dictionary
        
    Returns:
        0 on success, 1 on error
    """
    try:
        feedback_collector = FeedbackCollector(config)
        fine_tuner = ModelFineTuner(config)
        
        # Get provider from config
        provider = config.get('reviewer', {}).get('provider', 'openai')
        logger.info(f"Running fine-tuning for provider: {provider}")
        
        # Prepare training data using the feedback collector
        training_file_path = fine_tuner.prepare_training_data(feedback_collector)
        
        if not training_file_path:
            logger.error(f"Failed to prepare training data for {provider}")
            return 1
        
        # Start fine-tuning job
        job_id = fine_tuner.start_fine_tuning(training_file_path)
        
        if not job_id:
            logger.error(f"Failed to start {provider} fine-tuning job")
            return 1
        
        logger.info(f"{provider.capitalize()} fine-tuning job started with ID: {job_id}")
        logger.info("You can check the status with --check-fine-tuning")
        
        return 0
        
    except Exception as e:
        logger.error(f"Error during fine-tuning: {str(e)}")
        return 1


def check_fine_tuning_status(config, job_id):
    """
    Check the status of a fine-tuning job.
    
    Args:
        config: Configuration dictionary
        job_id: Fine-tuning job ID
        
    Returns:
        0 on success, 1 on error
    """
    try:
        # Get provider from config
        provider = config.get('reviewer', {}).get('provider', 'openai')
        logger.info(f"Checking fine-tuning status for provider: {provider}")
        
        fine_tuner = ModelFineTuner(config)
        status = fine_tuner.check_fine_tuning_status(job_id)
        
        if not status:
            logger.error(f"Failed to get status for {provider} job ID: {job_id}")
            return 1
        
        # Get provider information from status
        job_provider = status.get('provider', provider)
        logger.info(f"Fine-tuning job status for {job_provider} job: {status['status']}")
        
        # Display additional provider-specific information if available
        if 'provider_info' in status:
            logger.info(f"Provider-specific information:")
            for key, value in status['provider_info'].items():
                logger.info(f"  {key}: {value}")
        
        if status['status'] == 'succeeded':
            logger.info(f"Fine-tuned model: {status['fine_tuned_model']}")
            
            # Ask if the user wants to update the configuration
            response = input(f"Do you want to update the configuration to use this {job_provider} model? (y/n): ")
            if response.lower() == 'y':
                fine_tuner.update_model_in_config(status['fine_tuned_model'], job_provider)
                logger.info(f"Configuration updated to use the fine-tuned {job_provider} model")
        
        return 0
        
    except Exception as e:
        logger.error(f"Error checking fine-tuning status: {str(e)}")
        return 1


def collect_reactions_feedback(config, repo_slug, pr_id):
    """
    Collect feedback from reactions on PR comments.
    
    Args:
        config: Configuration dictionary
        repo_slug: Repository slug in format workspace/repo-slug
        pr_id: Pull request ID
        
    Returns:
        0 on success, 1 on error
    """
    try:
        # Initialize components
        bitbucket_api = BitbucketAPI(config)
        feedback_collector = FeedbackCollector(config, bitbucket_api)
        
        # Collect feedback from reactions
        logger.info(f"Collecting feedback from reactions in PR #{pr_id} from {repo_slug}")
        count = feedback_collector.collect_reactions_feedback(repo_slug, pr_id)
        
        logger.info(f"Collected {count} feedback records from reactions")
        
        # Show updated statistics
        stats = feedback_collector.get_feedback_stats()
        logger.info("Updated Feedback Statistics:")
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
        logger.error(f"Error collecting reactions feedback: {str(e)}")
        return 1


def show_feedback_stats(config, provider=None):
    """
    Show statistics from collected feedback.
    
    Args:
        config: Configuration dictionary
        provider: Optional provider to filter statistics
        
    Returns:
        0 on success, 1 on error
    """
    try:
        feedback_collector = FeedbackCollector(config)
        
        # Get stats filtered by provider if specified
        stats = feedback_collector.get_feedback_stats(provider)
        
        if provider:
            logger.info(f"{provider.upper()} Feedback Statistics:")
        else:
            logger.info("Overall Feedback Statistics:")
            
        logger.info(f"Total comments with feedback: {stats['total_comments']}")
        logger.info(f"Average rating: {stats['average_rating']}")
        logger.info(f"Percentage marked as helpful: {stats['helpful_percentage']}%")
        logger.info(f"Acceptance rate: {stats['acceptance_rate']}%")
        
        # Show reaction counts
        if 'reaction_counts' in stats and stats['reaction_counts']:
            logger.info("Reaction counts:")
            for emoji, count in stats['reaction_counts'].items():
                logger.info(f"  {emoji}: {count}")
        
        # Show provider-specific statistics if no provider filter was applied
        if not provider and 'provider_stats' in stats and stats['provider_stats']:
            logger.info("\nProvider-Specific Statistics:")
            for p, provider_stats in stats['provider_stats'].items():
                logger.info(f"\n{p.upper()} Statistics:")
                logger.info(f"  Total comments: {provider_stats['total_comments']}")
                logger.info(f"  Average rating: {provider_stats['average_rating']}")
                logger.info(f"  Helpful percentage: {provider_stats['helpful_percentage']}%")
                logger.info(f"  Acceptance rate: {provider_stats['acceptance_rate']}%")
        
        return 0
        
    except Exception as e:
        logger.error(f"Error showing feedback stats: {str(e)}")
        return 1


def run_code_review(args, config):
    """
    Run the code review process.
    
    Args:
        args: Command-line arguments
        config: Configuration dictionary
        
    Returns:
        0 on success, 1 on error
    """
    try:
        # Initialize components
        bitbucket_api = BitbucketAPI(config)
        diff_parser = DiffParser()
        context_retriever = ContextRetriever(bitbucket_api)
        reviewer_agent = ReviewerAgent(config)
        comment_formatter = CommentFormatter(config)
        feedback_collector = FeedbackCollector(config)
        
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
                # Store the original prompt and response for future fine-tuning
                if 'original_prompt' in file_context and 'original_response' in comment:
                    # Get provider and model information from the reviewer agent
                    provider = reviewer_agent.provider
                    model = reviewer_agent.model
                    
                    feedback_data = {
                        "pr_id": str(args.pr_id),
                        "file_path": file_path,
                        "comment_id": comment.get('id', 'unknown'),
                        "original_prompt": file_context['original_prompt'],
                        "original_response": comment['original_response'],
                        # Store provider and model information
                        "provider": provider,
                        "model": model,
                        # Initialize with neutral feedback
                        "rating": 3,
                        "is_helpful": None,
                        "user_comment": "",
                        "accepted": None
                    }
                    feedback_collector.store_feedback(
                        pr_id=str(args.pr_id),
                        file_path=file_path,
                        comment_id=comment.get('id', 'unknown'),
                        feedback=feedback_data
                    )
                
                # Post the comment to Bitbucket
                bitbucket_api.post_comment(args.repo, args.pr_id, comment)
        
        logger.info("Code review completed successfully")
        return 0
        
    except Exception as e:
        logger.error(f"Error during code review: {str(e)}")
        if args.debug:
            logger.exception("Detailed error information:")
        return 1


def main():
    """Main function to run the code review process."""
    args = parse_arguments()
    
    # Set debug logging if requested
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
    try:
        # Load configuration
        config = load_config(args.config)
        
        # If provider is specified, update the config
        if args.provider:
            logger.info(f"Using provider: {args.provider}")
            if 'reviewer' not in config:
                config['reviewer'] = {}
            config['reviewer']['provider'] = args.provider
        
        # Handle different modes of operation
        if args.collect_feedback:
            return run_feedback_server(config, args.feedback_port)
        elif args.collect_reactions:
            # For reactions collection, we need the repo slug
            repo_slug = args.repo or config.get('bitbucket', {}).get('default_repo')
            if not repo_slug:
                logger.error("Repository slug is required for collecting reactions feedback")
                logger.error("Provide it with --repo or set default_repo in config")
                return 1
            return collect_reactions_feedback(config, repo_slug, args.reactions_pr)
        elif args.fine_tune:
            return run_fine_tuning(config)
        elif args.check_fine_tuning:
            return check_fine_tuning_status(config, args.check_fine_tuning)
        elif args.feedback_stats:
            return show_feedback_stats(config, args.provider)
        else:
            return run_code_review(args, config)
        
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        if args.debug:
            logger.exception("Detailed error information:")
        return 1


if __name__ == "__main__":
    sys.exit(main())