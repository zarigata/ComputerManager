"""Tests for agent tool registry."""

import pytest
from src.agent.tool_registry import BaseTool, ToolRegistry, get_tool_registry


class MockTool(BaseTool):
    """Mock tool for testing."""
    
    @property
    def name(self) -> str:
        return "mock_tool"
    
    @property
    def description(self) -> str:
        return "A mock tool for testing"
    
    @property
    def parameters(self):
        return {
            'type': 'object',
            'properties': {
                'test_param': {
                    'type': 'string',
                    'description': 'Test parameter'
                }
            },
            'required': ['test_param']
        }
    
    async def execute(self, **kwargs):
        """Execute mock tool."""
        self.validate_params(**kwargs)
        return f"Mock executed with: {kwargs.get('test_param')}"


def test_tool_registration():
    """Test tool registration."""
    registry = ToolRegistry()
    tool = MockTool()
    
    registry.register(tool)
    assert "mock_tool" in registry
    assert len(registry) == 1


def test_duplicate_registration():
    """Test that duplicate registration raises error."""
    registry = ToolRegistry()
    tool = MockTool()
    
    registry.register(tool)
    
    with pytest.raises(ValueError, match="already registered"):
        registry.register(tool)


def test_tool_retrieval():
    """Test tool retrieval."""
    registry = ToolRegistry()
    tool = MockTool()
    
    registry.register(tool)
    retrieved = registry.get("mock_tool")
    
    assert retrieved is not None
    assert retrieved.name == "mock_tool"


def test_tool_not_found():
    """Test retrieval of non-existent tool."""
    registry = ToolRegistry()
    
    result = registry.get("nonexistent")
    assert result is None


def test_tool_unregistration():
    """Test tool unregistration."""
    registry = ToolRegistry()
    tool = MockTool()
    
    registry.register(tool)
    assert "mock_tool" in registry
    
    registry.unregister("mock_tool")
    assert "mock_tool" not in registry


def test_list_tools():
    """Test listing all tools."""
    registry = ToolRegistry()
    tool1 = MockTool()
    
    registry.register(tool1)
    
    tools = registry.list_tools()
    assert len(tools) == 1
    assert tools[0].name == "mock_tool"


def test_get_tools_schema():
    """Test schema generation."""
    registry = ToolRegistry()
    tool = MockTool()
    
    registry.register(tool)
    
    schemas = registry.get_tools_schema()
    assert len(schemas) == 1
    assert schemas[0]['type'] == 'function'
    assert schemas[0]['function']['name'] == 'mock_tool'
    assert 'parameters' in schemas[0]['function']


def test_singleton_pattern():
    """Test that get_tool_registry returns same instance."""
    registry1 = get_tool_registry()
    registry2 = get_tool_registry()
    
    assert registry1 is registry2


@pytest.mark.asyncio
async def test_parameter_validation():
    """Test parameter validation."""
    tool = MockTool()
    
    # Valid parameters
    result = await tool.execute(test_param="value")
    assert "value" in result
    
    # Missing required parameter
    with pytest.raises(ValueError, match="Missing required parameter"):
        await tool.execute()


@pytest.mark.asyncio
async def test_tool_schema_generation():
    """Test tool schema generation for Ollama."""
    tool = MockTool()
    schema = tool.to_schema()
    
    assert schema['type'] == 'function'
    assert schema['function']['name'] == 'mock_tool'
    assert schema['function']['description'] == 'A mock tool for testing'
    assert 'test_param' in schema['function']['parameters']['properties']
    assert 'test_param' in schema['function']['parameters']['required']
