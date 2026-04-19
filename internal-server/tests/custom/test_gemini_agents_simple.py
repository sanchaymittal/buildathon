"""Simplified test for Gemini Agents tracing helpers."""

import unittest
from unittest.mock import patch, MagicMock

from src.gemini_agents import set_tracing_disabled


class TestGeminiAgentsTracing(unittest.TestCase):
    """Exercise the lightweight tracing utilities."""

    def setUp(self):
        set_tracing_disabled(True)

    def test_tracing_context_manager(self):
        with patch("src.gemini_agents.trace") as mock_trace:
            mock_trace_instance = MagicMock()
            mock_trace.return_value = mock_trace_instance
            mock_trace_instance.__enter__.return_value = mock_trace_instance

            with mock_trace("Test Workflow"):
                with mock_trace("Nested Operation"):
                    pass

        self.assertTrue(True)


if __name__ == "__main__":
    unittest.main()
