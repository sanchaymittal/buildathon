"""
Master script to run all DevOps CLI and OpenAI Agents tests.
"""

import unittest
import sys
import os

# Add the parent directory to the path so we can import our modules
sys.path.append(os.path.join(os.path.dirname(__file__), '../../..'))

# Import CLI test modules
from devops.tests.custom.test_cli_format import TestCLIFormatOutput

# Import OpenAI Agents test modules
from devops.tests.custom.test_openai_agents_simple import TestOpenAIAgentsTracing
from devops.tests.custom.test_openai_agents_ec2 import TestOpenAIAgentsEC2

def run_all_tests():
    """Run all tests."""
    # Create a test suite
    test_suite = unittest.TestSuite()
    test_loader = unittest.TestLoader()
    
    print("=== Running CLI Tests ===")
    
    # Add tests from test_cli_format.py
    test_suite.addTest(test_loader.loadTestsFromTestCase(TestCLIFormatOutput))
    
    print("\n=== Running OpenAI Agents Tests ===")
    
    # Add tests from test_openai_agents_simple.py
    test_suite.addTest(test_loader.loadTestsFromTestCase(TestOpenAIAgentsTracing))
    
    # Add tests from test_openai_agents_ec2.py
    test_suite.addTest(test_loader.loadTestsFromTestCase(TestOpenAIAgentsEC2))
    
    # Run the tests
    test_runner = unittest.TextTestRunner(verbosity=2)
    result = test_runner.run(test_suite)
    
    # Print summary
    print("\n=== Test Summary ===")
    print(f"Total tests: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Skipped: {len(result.skipped)}")
    
    # Return appropriate exit code
    return 0 if result.wasSuccessful() else 1

if __name__ == "__main__":
    sys.exit(run_all_tests())