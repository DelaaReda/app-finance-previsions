#!/usr/bin/env python3
"""
Test to verify that launch_fullstack.py has valid Python syntax and can be imported without errors.
"""
import sys
import os
import unittest
from pathlib import Path

class TestLaunchFullstackSyntax(unittest.TestCase):
    """Test class to verify syntax and import of launch_fullstack.py"""
    
    def test_syntax_validity(self):
        """Test that launch_fullstack.py has valid Python syntax."""
        script_path = Path(__file__).parent / "scripts" / "launch_fullstack.py"
        
        # Read and parse the file to check for syntax errors
        with open(script_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # This will raise a SyntaxError if there are syntax issues
        try:
            compile(content, str(script_path), 'exec')
        except SyntaxError as e:
            self.fail(f"Syntax error in launch_fullstack.py: {e}")
    
    def test_can_import_without_errors(self):
        """Test that launch_fullstack.py can be imported without errors."""
        # Add the scripts directory to the path so we can import the module
        scripts_dir = Path(__file__).parent / "scripts"
        sys.path.insert(0, str(scripts_dir))
        
        try:
            # Import the module - this will execute the top-level code
            import launch_fullstack
            # Verify that expected functions exist
            self.assertTrue(hasattr(launch_fullstack, 'launch_api'))
            self.assertTrue(hasattr(launch_fullstack, 'launch_frontend'))
            self.assertTrue(hasattr(launch_fullstack, 'main'))
        except ImportError as e:
            self.fail(f"Failed to import launch_fullstack.py: {e}")
        except Exception as e:
            self.fail(f"Error during import of launch_fullstack.py: {e}")
        finally:
            # Clean up: remove the path addition
            if str(scripts_dir) in sys.path:
                sys.path.remove(str(scripts_dir))

if __name__ == "__main__":
    unittest.main()