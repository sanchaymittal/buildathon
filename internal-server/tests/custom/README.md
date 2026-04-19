# DevOps Custom Tests

This directory contains custom test modules for the DevOps agent. These tests verify the functionality of the CLI interface, error handling, and OpenAI Agents integration.

## Test Suite Features

| Test File | Description | Test Count | Features Tested |
|-----------|-------------|------------|-----------------|
| `test_cli_format.py` | Tests for CLI output formatting | 3 | JSON formatting, Table formatting for lists, Table formatting for dictionaries |
| `test_cli.py` | Tests for CLI module functionality | 10 | Format output, EC2 commands, GitHub commands, Deployment commands |
| `test_error_handling.py` | Tests for error handling mechanisms | 12 | AWS service errors, GitHub errors, Credential errors, Error suggestions |
| `run_cli_test.py` | Simple CLI format tests | 3 | JSON output, Table output for lists, Table output for dictionaries |
| `run_cli_tests.py` | Comprehensive CLI tests | 7 | Format output, EC2 commands, GitHub commands |
| `run_cli_error_tests.py` | CLI error handling tests | 8 | Resource errors, Permission errors, Validation errors, Credential errors |
| `test_openai_agents_simple.py` | Simple OpenAI Agents tests | 1 | Tracing functionality |
| `test_openai_agents_ec2.py` | OpenAI Agents EC2 tests | 4 | List instances, Start instances, Stop instances, Create instances |
| `test_openai_agents_tracing.py` | OpenAI Agents tracing tests | 1 | Tracing context management |

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

### OpenAI Agents Tests
These tests verify the integration with OpenAI's Agents SDK, including tracing, EC2 operations, and GitHub operations.

## Adding New Tests

When adding new tests:

1. Create a new test file following the naming convention `test_*.py`
2. Add the test file to the `test_files` list in `run_tests.py`
3. Ensure your tests can run independently without external dependencies
4. Use mocks for external services like AWS and GitHub