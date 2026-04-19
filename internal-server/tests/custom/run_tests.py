#!/usr/bin/env python3
"""
Script to run all the individual test files directly.
"""

import os
import sys
import subprocess

# Get the current directory
current_dir = os.path.dirname(os.path.abspath(__file__))

def run_tests():
    """Run all the individual test files."""
    # List of test files to run
    test_files = [
        "test_cli_format.py",
        "test_cli.py",
        "test_error_handling.py",
        "run_cli_test.py",
        "test_gemini_agents_simple.py",
        "test_gemini_agents.py",
    ]
    
    # Run each test file
    for test_file in test_files:
        print(f"\n=== Running {test_file} ===")
        test_path = os.path.join(current_dir, test_file)
        
        # Use pytest for test_cli.py since it uses pytest fixtures
        if test_file in {"test_cli.py", "test_gemini_agents.py"}:
            result = subprocess.run(["pytest", "-xvs", test_path], capture_output=False)
        else:
            # Use python for other test files
            result = subprocess.run(["python", test_path], capture_output=False)
        
        if result.returncode != 0:
            print(f"Error running {test_file}")
    
    print("\n=== All tests completed ===")

if __name__ == "__main__":
    run_tests()
