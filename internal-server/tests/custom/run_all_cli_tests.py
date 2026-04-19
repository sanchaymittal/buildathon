"""
Script to run all CLI tests.
"""

import sys
import os
import subprocess

def run_all_tests():
    """Run all CLI tests."""
    # List of test files to run
    test_files = [
        "test_cli_format.py",
        "test_cli.py",
        "test_error_handling.py",
        "run_cli_test.py",
        "run_cli_tests.py",
        "run_cli_error_tests.py"
    ]
    
    # Run each test file
    all_passed = True
    for test_file in test_files:
        print(f"\n=== Running {test_file} ===")
        result = subprocess.run(["python", test_file], capture_output=False)
        if result.returncode != 0:
            all_passed = False
    
    # Return appropriate exit code
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(run_all_tests())