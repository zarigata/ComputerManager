"""Tests for agent components."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from src.agent.core import Agent
from src.agent.builtin_tools import EchoTool, GetTimeTool, GetSystemInfoTool
from src.agent.tool_registry import ToolRegistry


@pytest.mark.asyncio
async def test_echo_tool():
    """Test echo tool execution."""
    tool = EchoTool()
    result = await tool.execute(message="Hello, World!")
    
    assert result == "Hello, World!"


@pytest.mark.asyncio
async def test_get_time_tool():
    """Test get_time tool execution."""
    tool = GetTimeTool()
    
    # Test ISO format
    result = await tool.execute(format="iso")
    assert isinstance(result, str)
    assert "T" in result or "-" in result
    
    # Test readable format
    result = await tool.execute(format="readable")
    assert isinstance(result, str)
    
    # Test timestamp format
    result = await tool.execute(format="timestamp")
    assert isinstance(result, str)
    assert result.isdigit()


@pytest.mark.asyncio
async def test_get_system_info_tool():
    """Test get_system_info tool execution."""
    tool = GetSystemInfoTool()
    
    # Test basic info
    result = await tool.execute(detailed=False)
    assert isinstance(result, dict)
    assert 'cpu_cores' in result
    assert 'ram_gb' in result
    assert 'hardware_tier' in result
    
    # Test detailed info
    result = await tool.execute(detailed=True)
    assert isinstance(result, dict)
    assert 'platform' in result
    assert 'recommended_models' in result


@pytest.mark.asyncio
async def test_agent_initialization():
    """Test agent initialization."""
    mock_client = MagicMock()
    registry = ToolRegistry()
    
    agent = Agent(
        ollama_client=mock_client,
        tool_registry=registry,
        model="test-model"
    )
    
    assert agent.model == "test-model"
    assert agent.max_iterations == 10
    assert len(agent.conversation_history) == 1  # System prompt


@pytest.mark.asyncio
async def test_agent_process_message_no_tools():
    """Test agent processing message without tool calls."""
    mock_client = MagicMock()
    mock_client.chat_with_tools = AsyncMock(return_value={
        'message': {
            'role': 'assistant',
            'content': 'Hello! How can I help you?',
            'tool_calls': []
        }
    })
    
    registry = ToolRegistry()
    agent = Agent(mock_client, registry, model="test-model")
    
    response = await agent.process_message("Hello")
    
    assert response == 'Hello! How can I help you?'
    assert len(agent.conversation_history) == 3  # System, user, assistant


@pytest.mark.asyncio
async def test_agent_process_message_with_tool():
    """Test agent processing message with tool call."""
    mock_client = MagicMock()
    
    # First call: LLM decides to use echo tool
    # Second call: LLM responds with final answer
    mock_client.chat_with_tools = AsyncMock(side_effect=[
        {
            'message': {
                'role': 'assistant',
                'content': '',
                'tool_calls': [{
                    'function': {
                        'name': 'echo',
                        'arguments': '{"message": "test"}'
                    }
                }]
            }
        },
        {
            'message': {
                'role': 'assistant',
                'content': 'The echo returned: test',
                'tool_calls': []
            }
        }
    ])
    
    registry = ToolRegistry()
    echo_tool = EchoTool()
    registry.register(echo_tool)
    
    agent = Agent(mock_client, registry, model="test-model")
    response = await agent.process_message("Echo test")
    
    assert response == 'The echo returned: test'
    # Should have: system, user, assistant (tool call), tool result, assistant (final)
    assert len(agent.conversation_history) == 5


@pytest.mark.asyncio
async def test_agent_tool_not_found():
    """Test agent handling of non-existent tool."""
    mock_client = MagicMock()
    mock_client.chat_with_tools = AsyncMock(side_effect=[
        {
            'message': {
                'role': 'assistant',
                'content': '',
                'tool_calls': [{
                    'function': {
                        'name': 'nonexistent_tool',
                        'arguments': '{}'
                    }
                }]
            }
        },
        {
            'message': {
                'role': 'assistant',
                'content': 'Sorry, that tool is not available',
                'tool_calls': []
            }
        }
    ])
    
    registry = ToolRegistry()
    agent = Agent(mock_client, registry, model="test-model")
    
    response = await agent.process_message("Use nonexistent tool")
    
    assert response == 'Sorry, that tool is not available'


@pytest.mark.asyncio
async def test_agent_max_iterations():
    """Test agent respects max iterations."""
    mock_client = MagicMock()
    
    # Always return tool calls to trigger max iterations
    mock_client.chat_with_tools = AsyncMock(return_value={
        'message': {
            'role': 'assistant',
            'content': '',
            'tool_calls': [{
                'function': {
                    'name': 'echo',
                    'arguments': '{"message": "loop"}'
                }
            }]
        }
    })
    
    registry = ToolRegistry()
    registry.register(EchoTool())
    
    agent = Agent(mock_client, registry, model="test-model", max_iterations=3)
    response = await agent.process_message("Loop forever")
    
    assert "maximum number of tool execution steps" in response


def test_agent_clear_history():
    """Test clearing conversation history."""
    mock_client = MagicMock()
    registry = ToolRegistry()
    
    agent = Agent(mock_client, registry)
    agent.conversation_history.append({'role': 'user', 'content': 'test'})
    
    assert len(agent.conversation_history) == 2  # System + user
    
    agent.clear_history()
    
    assert len(agent.conversation_history) == 1  # Only system prompt


def test_agent_get_history():
    """Test getting conversation history."""
    mock_client = MagicMock()
    registry = ToolRegistry()
    
    agent = Agent(mock_client, registry)
    agent.conversation_history.append({'role': 'user', 'content': 'test'})
    
    history = agent.get_history()
    
    assert len(history) == 2
    assert history[-1]['content'] == 'test'
    # Ensure it's a copy
    assert history is not agent.conversation_history
