# DevOps Custom Tests

This directory contains custom test modules for the DevOps agent. These tests verify CLI behaviour, error handling, and Gemini agent integration without touching live infrastructure.

## Test Suite Features

| Test File | Description | Test Count | Features Tested |
|-----------|-------------|------------|-----------------|
| `test_cli_format.py` | Tests for CLI output formatting | 3 | JSON formatting, table formatting for lists, table formatting for dictionaries |
| `test_cli.py` | Tests for CLI module functionality | 8 | Format output, Docker command routing, GitHub commands, deployment command plumbing |
| `test_error_handling.py` | Tests for error handling mechanisms | 12 | Cloud service errors, GitHub errors, credential errors, user suggestions |
| `test_gemini_agents_simple.py` | Simple Gemini tracing tests | 1 | Tracing functionality |
| `test_gemini_agents.py` | Gemini agent smoke tests | 6 | Runner invocation, security guardrail, sensitive info guardrail, tracing |

## Running the Tests

To run all tests, use the `run_tests.py` script:

```bash
cd /workspaces/devops/devops/tests/custom
python run_tests.py
```

This will execute all test files and report the results.

## Test Categories

### CLI Tests
These tests verify the command-line interface functionality, including command parsing, output formatting, and error handling.

### Error Handling Tests
These tests ensure that errors are properly caught, formatted, and presented to the user with helpful suggestions.

### Gemini Agents Tests
These tests verify the integration with the lightweight Gemini Agents compatibility layer, including tracing and guardrail hooks.

## Adding New Tests

When adding new tests:

1. Create a new test file following the naming convention `test_*.py`
2. Add the test file to the `test_files` list in `run_tests.py`
3. Ensure your tests can run independently without external dependencies
4. Use mocks for external services like container runtimes and GitHub
