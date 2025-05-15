#!/usr/bin/env python3
"""
Example script to demonstrate the feedback collection and fine-tuning functionality.
"""

import os
import sys
import logging
import argparse
import yaml
import threading
import time
import webbrowser
from galaxy_code_review.feedback_collector import FeedbackCollector
from galaxy_code_review.model_fine_tuner import ModelFineTuner
from galaxy_code_review.main import run_feedback_server

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def load_config(config_path):
    """Load configuration from YAML file."""
    try:
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    except Exception as e:
        logger.error(f"Error loading config: {str(e)}")
        return None

def generate_sample_feedback(feedback_collector):
    """Generate some sample feedback data for demonstration."""
    # Sample PR and comment IDs
    pr_ids = ["123", "124", "125"]
    comment_ids = [f"comment-{i}" for i in range(1, 11)]
    file_paths = ["src/main.py", "src/utils.py", "tests/test_main.py"]
    
    # Generate some positive feedback
    for i in range(5):
        feedback_collector.store_feedback(
            pr_id=pr_ids[i % len(pr_ids)],
            comment_id=comment_ids[i % len(comment_ids)],
            file_path=file_paths[i % len(file_paths)],
            feedback={
                "rating": 4 + (i % 2),  # 4 or 5 stars
                "is_helpful": True,
                "accepted": True,
                "user_comment": "This was a great suggestion, thanks!"
            }
        )
    
    # Generate some neutral feedback
    for i in range(3):
        feedback_collector.store_feedback(
            pr_id=pr_ids[(i + 1) % len(pr_ids)],
            comment_id=comment_ids[(i + 5) % len(comment_ids)],
            file_path=file_paths[(i + 1) % len(file_paths)],
            feedback={
                "rating": 3,
                "is_helpful": True,
                "accepted": False,
                "user_comment": "Good point, but I decided to implement it differently."
            }
        )
    
    # Generate some negative feedback
    for i in range(2):
        feedback_collector.store_feedback(
            pr_id=pr_ids[(i + 2) % len(pr_ids)],
            comment_id=comment_ids[(i + 8) % len(comment_ids)],
            file_path=file_paths[(i + 2) % len(file_paths)],
            feedback={
                "rating": 1 + i,  # 1 or 2 stars
                "is_helpful": False,
                "accepted": False,
                "user_comment": "This suggestion doesn't apply to our codebase."
            }
        )
    
    logger.info("Generated 10 sample feedback entries")

def main():
    """Main entry point for the example script."""
    parser = argparse.ArgumentParser(description="Feedback and Fine-tuning Example")
    parser.add_argument("--config", default="config.yaml", help="Path to config file")
    parser.add_argument("--port", type=int, default=12000, help="Port for feedback server")
    parser.add_argument("--generate-samples", action="store_true", help="Generate sample feedback data")
    parser.add_argument("--fine-tune", action="store_true", help="Run fine-tuning process")
    parser.add_argument("--stats", action="store_true", help="Show feedback statistics")
    
    args = parser.parse_args()
    
    # Load configuration
    config = load_config(args.config)
    if not config:
        logger.error("Failed to load configuration")
        return 1
    
    # Create feedback collector
    feedback_collector = FeedbackCollector(config)
    
    # Generate sample data if requested
    if args.generate_samples:
        generate_sample_feedback(feedback_collector)
    
    # Show statistics if requested
    if args.stats:
        stats = feedback_collector.get_feedback_stats()
        print("\n=== Feedback Statistics ===")
        print(f"Total comments with feedback: {stats['total_comments']}")
        print(f"Average rating: {stats['average_rating']:.2f}")
        print(f"Helpful percentage: {stats['helpful_percentage']:.2f}%")
        print(f"Acceptance rate: {stats['acceptance_rate']:.2f}%")
        print("===========================\n")
    
    # Run fine-tuning if requested
    if args.fine_tune:
        fine_tuner = ModelFineTuner(config)
        logger.info("Starting fine-tuning process...")
        
        # Create a sample training file
        import os
        training_file_dir = config.get('fine_tuning', {}).get('training_file_dir', 'training_data')
        training_file_path = os.path.join(training_file_dir, 'sample_training_data.jsonl')
        
        # Create sample training data
        with open(training_file_path, 'w') as f:
            f.write('{"messages": [{"role": "system", "content": "You are a code review assistant."}, {"role": "user", "content": "Review this code: def add(a, b): return a + b"}, {"role": "assistant", "content": "The code looks good. It correctly implements an addition function."}]}\n')
            f.write('{"messages": [{"role": "system", "content": "You are a code review assistant."}, {"role": "user", "content": "Review this code: def divide(a, b): return a / b"}, {"role": "assistant", "content": "The code needs error handling for division by zero."}]}\n')
        
        logger.info(f"Created sample training file at {training_file_path}")
        
        # Start fine-tuning
        job_id = fine_tuner.start_fine_tuning(training_file_path)
        if job_id:
            logger.info(f"Fine-tuning job started with ID: {job_id}")
            logger.info("This is a simulated fine-tuning job for demonstration purposes.")
            logger.info("In a real implementation, this would start an actual fine-tuning job with OpenAI or another provider.")
        else:
            logger.error("Failed to start fine-tuning job")
    
    # Start feedback server in a separate thread
    def run_server():
        run_feedback_server(config, args.port)
    
    server_thread = threading.Thread(target=run_server)
    server_thread.daemon = True
    server_thread.start()
    
    # Open browser to the feedback server
    time.sleep(1)  # Give the server a moment to start
    webbrowser.open(f"http://localhost:{args.port}/")
    
    logger.info(f"Feedback server running at http://localhost:{args.port}/")
    logger.info("Press Ctrl+C to exit")
    
    try:
        # Keep the main thread alive
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())