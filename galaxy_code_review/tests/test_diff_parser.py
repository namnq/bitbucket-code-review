"""
Tests for the DiffParser component.
"""

import unittest
from galaxy_code_review.diff_parser import DiffParser


class TestDiffParser(unittest.TestCase):
    """Test cases for the DiffParser class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.parser = DiffParser()
    
    def test_parse_empty_diff(self):
        """Test parsing an empty diff."""
        result = self.parser.parse("")
        self.assertEqual(result, {})
    
    def test_parse_addition(self):
        """Test parsing a diff with an addition."""
        diff = """diff --git a/file.py b/file.py
index 1234567..abcdefg 100644
--- a/file.py
+++ b/file.py
@@ -10,6 +10,7 @@ def existing_function():
     return True
 
 # New function added
+def new_function():
     return False
 """
        result = self.parser.parse(diff)
        
        self.assertIn('file.py', result)
        changes = result['file.py']
        
        self.assertEqual(len(changes), 1)
        self.assertEqual(changes[0]['type'], 'addition')
        self.assertEqual(changes[0]['start_line'], 13)
        self.assertEqual(changes[0]['end_line'], 13)
        self.assertEqual(changes[0]['content'], 'def new_function():')
    
    def test_parse_deletion(self):
        """Test parsing a diff with a deletion."""
        diff = """diff --git a/file.py b/file.py
index 1234567..abcdefg 100644
--- a/file.py
+++ b/file.py
@@ -10,7 +10,6 @@ def existing_function():
     return True
 
 # Function to be removed
-def old_function():
     return False
 """
        result = self.parser.parse(diff)
        
        self.assertIn('file.py', result)
        changes = result['file.py']
        
        self.assertEqual(len(changes), 1)
        self.assertEqual(changes[0]['type'], 'deletion')
        self.assertEqual(changes[0]['old_start_line'], 13)
        self.assertEqual(changes[0]['old_end_line'], 13)
        self.assertEqual(changes[0]['content'], 'def old_function():')
    
    def test_parse_multiple_changes(self):
        """Test parsing a diff with multiple changes."""
        diff = """diff --git a/file.py b/file.py
index 1234567..abcdefg 100644
--- a/file.py
+++ b/file.py
@@ -10,7 +10,7 @@ def existing_function():
     return True
 
 # Modified function
-def old_function():
+def new_function():
     return False
 
@@ -20,6 +20,8 @@ def another_function():
     # Some code
     pass
 
+# Added comment
+
 def final_function():
     return None
 """
        result = self.parser.parse(diff)
        
        self.assertIn('file.py', result)
        changes = result['file.py']
        
        # We expect at least 2 changes (one deletion, one addition)
        self.assertGreaterEqual(len(changes), 2)
        
        # Check that we have both types of changes
        change_types = [change['type'] for change in changes]
        self.assertIn('deletion', change_types)
        self.assertIn('addition', change_types)


if __name__ == '__main__':
    unittest.main()