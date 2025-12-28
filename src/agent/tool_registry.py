"""Tool registry system for agent framework."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Protocol
import logging

logger = logging.getLogger(__name__)


class Tool(Protocol):
    """Protocol defining the interface for all tools."""
    
    name: str
    description: str
    parameters: Dict[str, Any]
    
    async def execute(self, **kwargs) -> Any:
        """Execute the tool with given parameters."""
        ...


class BaseTool(ABC):
    """Abstract base class for tools with common functionality."""
    
    def __init__(self):
        """Initialize the base tool."""
        self._validate_tool_definition()
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Unique tool identifier."""
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """Human-readable description for the LLM."""
        pass
    
    @property
    @abstractmethod
    def parameters(self) -> Dict[str, Any]:
        """JSON schema for parameters (OpenAPI format)."""
        pass
    
    @abstractmethod
    async def execute(self, **kwargs) -> Any:
        """Execute the tool with given parameters."""
        pass
    
    def _validate_tool_definition(self) -> None:
        """Validate that the tool is properly defined."""
        if not self.name:
            raise ValueError("Tool name cannot be empty")
        if not self.description:
            raise ValueError("Tool description cannot be empty")
        if not isinstance(self.parameters, dict):
            raise ValueError("Tool parameters must be a dictionary")
    
    def validate_params(self, **kwargs) -> bool:
        """Validate parameters against the schema.
        
        Args:
            **kwargs: Parameters to validate
            
        Returns:
            True if valid, raises ValueError otherwise
        """
        required_params = self.parameters.get('required', [])
        properties = self.parameters.get('properties', {})
        
        # Check required parameters
        for param in required_params:
            if param not in kwargs:
                raise ValueError(f"Missing required parameter: {param}")
        
        # Check parameter types (basic validation)
        for param_name, param_value in kwargs.items():
            if param_name not in properties:
                logger.warning(f"Unknown parameter: {param_name}")
                continue
            
            expected_type = properties[param_name].get('type')
            if expected_type:
                self._validate_type(param_name, param_value, expected_type)
        
        return True
    
    def _validate_type(self, param_name: str, value: Any, expected_type: str) -> None:
        """Validate parameter type."""
        type_mapping = {
            'string': str,
            'number': (int, float),
            'integer': int,
            'boolean': bool,
            'array': list,
            'object': dict
        }
        
        expected_python_type = type_mapping.get(expected_type)
        if expected_python_type and not isinstance(value, expected_python_type):
            raise ValueError(
                f"Parameter '{param_name}' must be of type {expected_type}, "
                f"got {type(value).__name__}"
            )
    
    def to_schema(self) -> Dict[str, Any]:
        """Convert tool to Ollama-compatible schema.
        
        Returns:
            Dictionary with tool schema in Ollama format
        """
        return {
            'type': 'function',
            'function': {
                'name': self.name,
                'description': self.description,
                'parameters': {
                    'type': 'object',
                    'properties': self.parameters.get('properties', {}),
                    'required': self.parameters.get('required', [])
                }
            }
        }


class ToolRegistry:
    """Registry for managing tools."""
    
    def __init__(self):
        """Initialize the tool registry."""
        self._tools: Dict[str, Tool] = {}
        logger.info("Tool registry initialized")
    
    def register(self, tool: Tool) -> None:
        """Register a tool.
        
        Args:
            tool: Tool instance to register
            
        Raises:
            ValueError: If tool with same name already exists
        """
        if tool.name in self._tools:
            raise ValueError(f"Tool '{tool.name}' is already registered")
        
        self._tools[tool.name] = tool
        logger.info(f"Registered tool: {tool.name}")
    
    def unregister(self, name: str) -> None:
        """Unregister a tool.
        
        Args:
            name: Name of tool to unregister
            
        Raises:
            KeyError: If tool not found
        """
        if name not in self._tools:
            raise KeyError(f"Tool '{name}' not found in registry")
        
        del self._tools[name]
        logger.info(f"Unregistered tool: {name}")
    
    def get(self, name: str) -> Optional[Tool]:
        """Get a tool by name.
        
        Args:
            name: Name of tool to retrieve
            
        Returns:
            Tool instance or None if not found
        """
        tool = self._tools.get(name)
        if tool is None:
            logger.warning(f"Tool '{name}' not found in registry")
        return tool
    
    def list_tools(self) -> List[Tool]:
        """Get list of all registered tools.
        
        Returns:
            List of all tool instances
        """
        return list(self._tools.values())
    
    def get_tools_schema(self) -> List[Dict[str, Any]]:
        """Generate Ollama-compatible tool schemas.
        
        Returns:
            List of tool schemas in Ollama format
        """
        schemas = []
        for tool in self._tools.values():
            if isinstance(tool, BaseTool):
                schemas.append(tool.to_schema())
            else:
                # Fallback for tools not inheriting from BaseTool
                schemas.append({
                    'type': 'function',
                    'function': {
                        'name': tool.name,
                        'description': tool.description,
                        'parameters': {
                            'type': 'object',
                            'properties': tool.parameters.get('properties', {}),
                            'required': tool.parameters.get('required', [])
                        }
                    }
                })
        return schemas
    
    def __contains__(self, name: str) -> bool:
        """Check if tool is registered.
        
        Args:
            name: Tool name to check
            
        Returns:
            True if tool is registered
        """
        return name in self._tools
    
    def __len__(self) -> int:
        """Get number of registered tools."""
        return len(self._tools)


# Global registry instance
_global_registry: Optional[ToolRegistry] = None


def get_tool_registry() -> ToolRegistry:
    """Get the global tool registry instance.
    
    Returns:
        Global ToolRegistry instance
    """
    global _global_registry
    if _global_registry is None:
        _global_registry = ToolRegistry()
    return _global_registry
