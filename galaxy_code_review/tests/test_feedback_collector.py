"""
Tests for the FeedbackCollector component.
"""

import unittest
import os
import json
import shutil
import tempfile
from galaxy_code_review.feedback_collector import FeedbackCollector


class TestFeedbackCollector(unittest.TestCase):
    """Test cases for the FeedbackCollector class."""
    
    def setUp(self):
        """Set up test environment."""
        # Create a temporary directory for feedback storage
        self.temp_dir = tempfile.mkdtemp()
        self.config = {
            'feedback': {
                'storage_dir': self.temp_dir
            }
        }
        self.collector = FeedbackCollector(self.config)
        
        # Sample feedback data
        self.sample_feedback = {
            "rating": 4,
            "is_helpful": True,
            "user_comment": "Great suggestion!",
            "accepted": True
        }
    
    def tearDown(self):
        """Clean up after tests."""
        # Remove the temporary directory
        shutil.rmtree(self.temp_dir)
    
    def test_store_feedback(self):
        """Test storing feedback."""
        result = self.collector.store_feedback(
            pr_id="123",
            file_path="src/main.py",
            comment_id="456",
            feedback=self.sample_feedback
        )
        
        # Check that the function returned success
        self.assertTrue(result)
        
        # Check that a file was created
        files = os.listdir(self.temp_dir)
        self.assertEqual(len(files), 1)
        
        # Check that the file contains the correct data
        with open(os.path.join(self.temp_dir, files[0]), 'r') as f:
            data = json.load(f)
            self.assertEqual(data["pr_id"], "123")
            self.assertEqual(data["file_path"], "src/main.py")
            self.assertEqual(data["comment_id"], "456")
            self.assertEqual(data["rating"], 4)
            self.assertEqual(data["is_helpful"], True)
            self.assertEqual(data["user_comment"], "Great suggestion!")
            self.assertEqual(data["accepted"], True)
    
    def test_get_all_feedback(self):
        """Test retrieving all feedback."""
        # Store multiple feedback records
        self.collector.store_feedback("123", "src/main.py", "456", self.sample_feedback)
        self.collector.store_feedback("123", "src/utils.py", "789", {
            "rating": 2,
            "is_helpful": False,
            "user_comment": "Not relevant",
            "accepted": False
        })
        
        # Retrieve all feedback
        feedback_records = self.collector.get_all_feedback()
        
        # Check that we got the correct number of records
        self.assertEqual(len(feedback_records), 2)
        
        # Check that the records contain the expected data
        ratings = [record["rating"] for record in feedback_records]
        self.assertIn(4, ratings)
        self.assertIn(2, ratings)
    
    def test_get_feedback_stats(self):
        """Test calculating feedback statistics."""
        # Store multiple feedback records
        self.collector.store_feedback("123", "src/main.py", "456", {
            "rating": 5,
            "is_helpful": True,
            "user_comment": "Great suggestion!",
            "accepted": True
        })
        self.collector.store_feedback("123", "src/utils.py", "789", {
            "rating": 3,
            "is_helpful": True,
            "user_comment": "Somewhat helpful",
            "accepted": False
        })
        self.collector.store_feedback("123", "src/api.py", "101", {
            "rating": 1,
            "is_helpful": False,
            "user_comment": "Not helpful",
            "accepted": False
        })
        
        # Calculate statistics
        stats = self.collector.get_feedback_stats()
        
        # Check that the statistics are correct
        self.assertEqual(stats["total_comments"], 3)
        self.assertEqual(stats["average_rating"], 3.0)
        self.assertEqual(stats["helpful_percentage"], 66.67)
        self.assertEqual(stats["acceptance_rate"], 33.33)
    
    def test_empty_feedback(self):
        """Test handling of empty feedback data."""
        # Calculate statistics with no feedback
        stats = self.collector.get_feedback_stats()
        
        # Check that the statistics are all zero
        self.assertEqual(stats["total_comments"], 0)
        self.assertEqual(stats["average_rating"], 0)
        self.assertEqual(stats["helpful_percentage"], 0)
        self.assertEqual(stats["acceptance_rate"], 0)


if __name__ == '__main__':
    unittest.main()