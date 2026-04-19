"""
Script to inspect the FunctionTool object.
"""

from agents import function_tool

@function_tool()
def test_func():
    """Test function."""
    return "Hello, world!"

print("Type:", type(test_func))
print("Dir:", dir(test_func))

# Try to find a way to access the original function
for attr in dir(test_func):
    if not attr.startswith('__'):
        try:
            value = getattr(test_func, attr)
            if callable(value):
                print(f"Callable attribute: {attr}")
        except Exception as e:
            print(f"Error accessing {attr}: {e}")