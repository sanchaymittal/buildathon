"""
Script to run OpenAI Agents tests.
"""

import sys
import os
import unittest
import pytest
import asyncio
from unittest.mock import patch, MagicMock

# Add the parent directory to the path so we can import our modules
sys.path.append(os.path.join(os.path.dirname(__file__), '../../..'))

# Create mock classes for pydantic
class BaseModel:
    """Mock BaseModel class."""
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

def Field(*args, **kwargs):
    """Mock Field function."""
    return None

# Patch modules
sys.modules['pydantic'] = MagicMock()
sys.modules['pydantic'].BaseModel = BaseModel
sys.modules['pydantic'].Field = Field

# Run the test
if __name__ == "__main__":
    print("Running test_openai_agents.py...")
    
    # Use pytest to run the test
    result = pytest.main(['-xvs', 'tests/custom/test_openai_agents.py::test_tracing'])
    
    # Exit with the appropriate code
    sys.exit(result)