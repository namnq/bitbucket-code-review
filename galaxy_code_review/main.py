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
    parser.add_argument("--fine-tune", action="store_true",
                        help="Start fine-tuning process using collected feedback")
    parser.add_argument("--check-fine-tuning", type=str,
                        help="Check status of a fine-tuning job by ID")
    parser.add_argument("--feedback-stats", action="store_true",
                        help="Show statistics from collected feedback")
    
    args = parser.parse_args()
    
    # Validate arguments
    if not any([args.repo and args.pr_id, args.collect_feedback, 
                args.fine_tune, args.check_fine_tuning, args.feedback_stats]):
        parser.error("Either --repo and --pr-id, or one of --collect-feedback, --fine-tune, "
                    "--check-fine-tuning, or --feedback-stats is required")
    
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
            stats = feedback_collector.get_feedback_stats()
            return render_template('feedback.html', 
                                  stats=stats,
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
            stats = feedback_collector.get_feedback_stats()
            
            return render_template('feedback.html',
                                  pr_id=pr_id,
                                  comment_id=comment_id,
                                  file_path="example/file.py",
                                  line_number="42",
                                  comment_content="This is a sample comment for demonstration purposes.",
                                  stats=stats)
        
        @app.route('/feedback/helpful', methods=['GET'])
        def helpful_feedback():
            """Quick feedback that a comment was helpful."""
            comment_id = request.args.get('id', '')
            pr_id = request.args.get('pr', '')
            
            if comment_id and pr_id:
                feedback_collector.store_feedback(
                    pr_id=pr_id,
                    file_path="",  # This would be retrieved in a real implementation
                    comment_id=comment_id,
                    feedback={
                        "rating": 5,
                        "is_helpful": True,
                        "accepted": None,
                        "user_comment": "Marked as helpful via quick feedback link"
                    }
                )
            
            return redirect(url_for('index'))
        
        @app.route('/feedback/not-helpful', methods=['GET'])
        def not_helpful_feedback():
            """Quick feedback that a comment was not helpful."""
            comment_id = request.args.get('id', '')
            pr_id = request.args.get('pr', '')
            
            if comment_id and pr_id:
                feedback_collector.store_feedback(
                    pr_id=pr_id,
                    file_path="",  # This would be retrieved in a real implementation
                    comment_id=comment_id,
                    feedback={
                        "rating": 2,
                        "is_helpful": False,
                        "accepted": None,
                        "user_comment": "Marked as not helpful via quick feedback link"
                    }
                )
            
            return redirect(url_for('index'))
        
        @app.route('/stats', methods=['GET'])
        def get_stats():
            """API endpoint to get feedback statistics."""
            stats = feedback_collector.get_feedback_stats()
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
        
        # Get all feedback records
        feedback_records = feedback_collector.get_all_feedback()
        
        if not feedback_records:
            logger.error("No feedback records found for fine-tuning")
            return 1
        
        # Prepare training data
        training_file_path = fine_tuner.prepare_training_data(feedback_records)
        
        if not training_file_path:
            logger.error("Failed to prepare training data")
            return 1
        
        # Start fine-tuning job
        job_id = fine_tuner.start_fine_tuning(training_file_path)
        
        if not job_id:
            logger.error("Failed to start fine-tuning job")
            return 1
        
        logger.info(f"Fine-tuning job started with ID: {job_id}")
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
        fine_tuner = ModelFineTuner(config)
        status = fine_tuner.check_fine_tuning_status(job_id)
        
        logger.info(f"Fine-tuning job status: {status['status']}")
        
        if status['status'] == 'succeeded':
            logger.info(f"Fine-tuned model: {status['fine_tuned_model']}")
            
            # Ask if the user wants to update the configuration
            response = input("Do you want to update the configuration to use this model? (y/n): ")
            if response.lower() == 'y':
                fine_tuner.update_model_in_config(status['fine_tuned_model'])
                logger.info("Configuration updated to use the fine-tuned model")
        
        return 0
        
    except Exception as e:
        logger.error(f"Error checking fine-tuning status: {str(e)}")
        return 1


def show_feedback_stats(config):
    """
    Show statistics from collected feedback.
    
    Args:
        config: Configuration dictionary
        
    Returns:
        0 on success, 1 on error
    """
    try:
        feedback_collector = FeedbackCollector(config)
        stats = feedback_collector.get_feedback_stats()
        
        logger.info("Feedback Statistics:")
        logger.info(f"Total comments with feedback: {stats['total_comments']}")
        logger.info(f"Average rating: {stats['average_rating']}")
        logger.info(f"Percentage marked as helpful: {stats['helpful_percentage']}%")
        logger.info(f"Acceptance rate: {stats['acceptance_rate']}%")
        
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
                    feedback_data = {
                        "pr_id": str(args.pr_id),
                        "file_path": file_path,
                        "comment_id": comment.get('id', 'unknown'),
                        "original_prompt": file_context['original_prompt'],
                        "original_response": comment['original_response'],
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
        
        # Handle different modes of operation
        if args.collect_feedback:
            return run_feedback_server(config, args.feedback_port)
        elif args.fine_tune:
            return run_fine_tuning(config)
        elif args.check_fine_tuning:
            return check_fine_tuning_status(config, args.check_fine_tuning)
        elif args.feedback_stats:
            return show_feedback_stats(config)
        else:
            return run_code_review(args, config)
        
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        if args.debug:
            logger.exception("Detailed error information:")
        return 1


if __name__ == "__main__":
    sys.exit(main())