"""Master script to run DevOps CLI and Gemini agent tests."""

import os
import sys
import unittest

import pytest


sys.path.append(os.path.join(os.path.dirname(__file__), "../../.."))

from devops.tests.custom.test_cli_format import TestCLIFormatOutput


def run_all_tests() -> int:
    """Run CLI unit tests via unittest and Gemini tests via pytest."""

    test_suite = unittest.TestSuite()
    test_loader = unittest.TestLoader()

    print("=== Running CLI Tests ===")
    test_suite.addTest(test_loader.loadTestsFromTestCase(TestCLIFormatOutput))

    runner = unittest.TextTestRunner(verbosity=2)
    unit_result = runner.run(test_suite)

    print("\n=== Running Gemini Agent Tests (pytest) ===")
    gemini_tests = pytest.main([
        "-xvs",
        os.path.join(os.path.dirname(__file__), "test_gemini_agents.py"),
        os.path.join(os.path.dirname(__file__), "test_gemini_agents_simple.py"),
    ])

    print("\n=== Test Summary ===")
    print(f"Unit tests run: {unit_result.testsRun}")
    print(f"Unit failures: {len(unit_result.failures)}")
    print(f"Unit errors: {len(unit_result.errors)}")
    print(f"Unit skipped: {len(unit_result.skipped)}")
    print(f"Gemini pytest exit code: {gemini_tests}")

    return 0 if unit_result.wasSuccessful() and gemini_tests == 0 else 1


if __name__ == "__main__":
    sys.exit(run_all_tests())
