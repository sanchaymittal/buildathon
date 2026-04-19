"""
Unit tests for the CLI format_output function.

These tests verify the functionality of the format_output function.
"""

import json
import unittest

def format_output(data, format_type='json'):
    """Format data for output in the specified format."""
    if format_type == 'json':
        return json.dumps(data, indent=2)
    elif format_type == 'table':
        if isinstance(data, list) and len(data) > 0 and isinstance(data[0], dict):
            # Create a table for a list of dictionaries
            headers = list(data[0].keys())
            header_row = " | ".join(headers)
            separator = "-" * len(header_row)
            rows = []
            for item in data:
                row = " | ".join(str(item.get(h, "")) for h in headers)
                rows.append(row)
            return f"{header_row}\n{separator}\n" + "\n".join(rows)
        elif isinstance(data, dict):
            # Create a simple key-value table for a single dictionary
            return "\n".join(f"{k}: {v}" for k, v in data.items())
        else:
            # Fall back to JSON for other data types
            return json.dumps(data, indent=2)
    else:
        # Default to JSON for unknown format types
        return json.dumps(data, indent=2)


class TestCLIFormatOutput(unittest.TestCase):
    """Tests for the format_output function."""
    
    def test_format_json(self):
        """Test JSON output formatting."""
        data = {"id": "i-1234", "name": "test-instance", "state": "running"}
        output = format_output(data, format_type='json')
        # Verify it's valid JSON
        parsed = json.loads(output)
        self.assertEqual(parsed["id"], "i-1234")
        self.assertEqual(parsed["name"], "test-instance")
    
    def test_format_table_list(self):
        """Test table output formatting for a list of dictionaries."""
        data = [
            {"id": "i-1234", "name": "instance-1", "state": "running"},
            {"id": "i-5678", "name": "instance-2", "state": "stopped"}
        ]
        output = format_output(data, format_type='table')
        
        # Verify it contains headers and data
        self.assertIn("id | name | state", output.lower())
        self.assertIn("i-1234 | instance-1 | running", output)
        self.assertIn("i-5678 | instance-2 | stopped", output)
    
    def test_format_table_dict(self):
        """Test table output formatting for a single dictionary."""
        data = {"id": "i-1234", "name": "test-instance", "state": "running"}
        output = format_output(data, format_type='table')
        
        # Verify it contains key-value pairs
        self.assertIn("id: i-1234", output)
        self.assertIn("name: test-instance", output)
        self.assertIn("state: running", output)


if __name__ == "__main__":
    unittest.main()