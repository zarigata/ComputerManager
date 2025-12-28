"""Agent framework for tool-calling capabilities."""

from .tool_registry import Tool, BaseTool, ToolRegistry, get_tool_registry
from .builtin_tools import initialize_builtin_tools
from .core import Agent
import logging

logger = logging.getLogger(__name__)

def initialize_langchain_tools(config) -> None:
    """
    Initialize and register LangChain tools if enabled.
    
    Args:
        config: AppConfig instance
    """
    if not config.langchain_enabled:
        return
        
    try:
        from .langchain_bridge import is_langchain_available, load_langchain_tools
        
        if not is_langchain_available():
            logger.warning("LangChain integration enabled but package not found. Skipping.")
            return
            
        logger.info(f"Initializing LangChain tools: {config.langchain_tools}")
        tools = load_langchain_tools(config.langchain_tools)
        
        registry = get_tool_registry()
        for tool in tools:
            registry.register(tool)
            
        if tools:
            logger.info(f"Registered {len(tools)} LangChain tools")
            
    except Exception as e:
        logger.error(f"Failed to initialize LangChain tools: {e}")

__all__ = [
    'Tool',
    'BaseTool',
    'ToolRegistry',
    'get_tool_registry',
    'initialize_builtin_tools',
    'initialize_langchain_tools',
    'Agent',
]
