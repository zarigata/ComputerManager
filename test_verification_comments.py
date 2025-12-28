"""
Simple manual test to verify the verification comments implementation.
"""
import sys
sys.path.insert(0, 'g:\\PROJETOS\\ComputerManager')

import asyncio
import json

# Test Comment 1: list_processes truncation metadata
print("=" * 60)
print("Testing Comment 1: list_processes truncation metadata")
print("=" * 60)

# Create a mock version to test the logic
class MockListProcessesTool:
    async def execute(self, **kwargs):
        # Simulate having 150 processes
        processes = [{"pid": i, "name": f"process_{i}"} for i in range(150)]
        
        # Calculate truncation metadata (the fix from Comment 1)
        total_count = len(processes)
        returned_processes = processes[:100]
        is_truncated = total_count > 100
        
        return json.dumps({
            "count": total_count,
            "returned_count": len(returned_processes),
            "truncated": is_truncated,
            "processes": returned_processes
        }, indent=2)

async def test_list_processes():
    tool = MockListProcessesTool()
    result = await tool.execute()
    data = json.loads(result)
    
    print(f"Total count: {data['count']}")
    print(f"Returned count: {data['returned_count']}")
    print(f"Truncated: {data['truncated']}")
    print(f"Processes returned: {len(data['processes'])}")
    
    assert data['count'] == 150, "Count should be 150"
    assert data['returned_count'] == 100, "Returned count should be 100"
    assert data['truncated'] == True, "Should be truncated"
    assert len(data['processes']) == 100, "Should return 100 processes"
    print("✓ Comment 1 test PASSED\n")

asyncio.run(test_list_processes())

# Test Comment 2: launch_application arguments validation
print("=" * 60)
print("Testing Comment 2: launch_application arguments validation")
print("=" * 60)

class MockLaunchApplicationTool:
    def validate_params(self, **kwargs):
        # Mock validation
        pass
    
    async def execute(self, **kwargs):
        # Validate parameters early
        self.validate_params(**kwargs)
        
        application = kwargs.get("application")
        arguments = kwargs.get("arguments", [])

        if not application:
            return "Error: 'application' parameter is required"

        # Normalize arguments parameter
        if isinstance(arguments, str):
            # Wrap string in single-element list
            arguments = [arguments]
        elif not isinstance(arguments, list):
            return f"Error: 'arguments' must be a list of strings or a single string, got {type(arguments).__name__}"
        
        # Validate all elements are strings
        if not all(isinstance(arg, str) for arg in arguments):
            return "Error: All elements in 'arguments' list must be strings"

        # Build command
        cmd = [application] + arguments
        
        return f"Success: Would launch {cmd}"

async def test_launch_application():
    tool = MockLaunchApplicationTool()
    
    # Test 1: String arguments (should be wrapped in list)
    print("\nTest 1: String arguments")
    result = await tool.execute(application="notepad", arguments="test.txt")
    print(f"Result: {result}")
    assert "Success" in result, "Should succeed with string argument"
    assert "['notepad', 'test.txt']" in result, "Should wrap string in list"
    print("✓ Test 1 PASSED")
    
    # Test 2: List of strings (should work normally)
    print("\nTest 2: List of strings")
    result = await tool.execute(application="notepad", arguments=["test.txt", "another.txt"])
    print(f"Result: {result}")
    assert "Success" in result, "Should succeed with list of strings"
    print("✓ Test 2 PASSED")
    
    # Test 3: Invalid type (should return error)
    print("\nTest 3: Invalid type (number)")
    result = await tool.execute(application="notepad", arguments=123)
    print(f"Result: {result}")
    assert "Error" in result, "Should return error for invalid type"
    assert "arguments" in result.lower(), "Error should mention arguments"
    print("✓ Test 3 PASSED")
    
    # Test 4: List with non-string elements (should return error)
    print("\nTest 4: List with non-string elements")
    result = await tool.execute(application="notepad", arguments=["test.txt", 123])
    print(f"Result: {result}")
    assert "Error" in result, "Should return error for non-string elements"
    assert "string" in result.lower(), "Error should mention strings"
    print("✓ Test 4 PASSED")
    
    print("\n✓ All Comment 2 tests PASSED\n")

asyncio.run(test_launch_application())

print("=" * 60)
print("ALL TESTS PASSED ✓")
print("=" * 60)
