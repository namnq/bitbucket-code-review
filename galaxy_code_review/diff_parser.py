"""
Diff Parser component for extracting and understanding code changes.
"""

import re
from typing import Dict, List, Tuple, Any


class DiffParser:
    """
    Parser for git diff output to extract changed files and lines.
    """
    
    def parse(self, diff_content: str) -> Dict[str, List[Dict[str, Any]]]:
        """
        Parse git diff content to extract changed files and their modifications.
        
        Args:
            diff_content: Raw git diff content
            
        Returns:
            Dictionary mapping file paths to lists of change objects.
            Each change object contains:
            - type: 'addition', 'deletion', or 'modification'
            - start_line: Starting line number in the new file
            - end_line: Ending line number in the new file
            - content: The changed content
            - old_start_line: Starting line number in the old file (for modifications)
            - old_end_line: Ending line number in the old file (for modifications)
        """
        if not diff_content:
            return {}
        
        # Split diff into file chunks
        file_pattern = r'diff --git a/(.*?) b/(.*?)\n'
        file_chunks = re.split(file_pattern, diff_content)
        
        # First chunk is empty, then we have triplets of [file_a, file_b, chunk_content]
        result = {}
        
        for i in range(1, len(file_chunks), 3):
            if i + 2 >= len(file_chunks):
                break
                
            file_a = file_chunks[i]
            file_b = file_chunks[i + 1]
            chunk_content = file_chunks[i + 2]
            
            # Use file_b as the current file path (post-change)
            file_path = file_b
            
            # Skip binary files
            if "Binary files" in chunk_content:
                continue
                
            # Extract hunk headers and content
            changes = self._parse_hunks(chunk_content)
            
            if changes:
                result[file_path] = changes
                
        return result
    
    def _parse_hunks(self, chunk_content: str) -> List[Dict[str, Any]]:
        """
        Parse diff hunks to extract line changes.
        
        Args:
            chunk_content: Content of a file diff chunk
            
        Returns:
            List of change objects
        """
        # Extract hunk headers
        hunk_pattern = r'@@ -(\d+),?(\d*) \+(\d+),?(\d*) @@'
        hunks = re.split(hunk_pattern, chunk_content)
        
        changes = []
        
        # First element is the file header, then we have groups of 5 elements
        for i in range(1, len(hunks), 5):
            if i + 4 >= len(hunks):
                break
                
            old_start = int(hunks[i])
            old_count = int(hunks[i + 1]) if hunks[i + 1] else 1
            new_start = int(hunks[i + 2])
            new_count = int(hunks[i + 3]) if hunks[i + 3] else 1
            hunk_content = hunks[i + 4]
            
            # Process the lines in this hunk
            hunk_changes = self._process_hunk_lines(
                hunk_content, old_start, old_count, new_start, new_count
            )
            changes.extend(hunk_changes)
            
        return changes
    
    def _process_hunk_lines(
        self, 
        hunk_content: str, 
        old_start: int, 
        old_count: int, 
        new_start: int, 
        new_count: int
    ) -> List[Dict[str, Any]]:
        """
        Process the lines in a diff hunk to identify changes.
        
        Args:
            hunk_content: Content of the hunk
            old_start: Starting line number in the old file
            old_count: Number of lines in the old file
            new_start: Starting line number in the new file
            new_count: Number of lines in the new file
            
        Returns:
            List of change objects
        """
        changes = []
        lines = hunk_content.split('\n')
        
        # Skip the first line if it's empty (happens after the hunk header)
        start_idx = 1 if lines and not lines[0] else 0
        
        old_line = old_start
        new_line = new_start
        
        # Group consecutive additions/deletions
        current_change = None
        
        for line in lines[start_idx:]:
            if not line:
                continue
                
            if line.startswith('+'):
                # Addition
                if current_change and current_change['type'] == 'addition':
                    # Extend current addition
                    current_change['content'] += '\n' + line[1:]
                    current_change['end_line'] = new_line
                else:
                    # Start new addition
                    if current_change:
                        changes.append(current_change)
                    current_change = {
                        'type': 'addition',
                        'start_line': new_line,
                        'end_line': new_line,
                        'content': line[1:]
                    }
                new_line += 1
                
            elif line.startswith('-'):
                # Deletion
                if current_change and current_change['type'] == 'deletion':
                    # Extend current deletion
                    current_change['content'] += '\n' + line[1:]
                    current_change['old_end_line'] = old_line
                else:
                    # Start new deletion
                    if current_change:
                        changes.append(current_change)
                    current_change = {
                        'type': 'deletion',
                        'old_start_line': old_line,
                        'old_end_line': old_line,
                        'content': line[1:]
                    }
                old_line += 1
                
            else:
                # Context line
                if current_change:
                    changes.append(current_change)
                    current_change = None
                
                # Skip lines that start with \ (no newline at end of file)
                if not line.startswith('\\'):
                    old_line += 1
                    new_line += 1
        
        # Add the last change if there is one
        if current_change:
            changes.append(current_change)
            
        return changes