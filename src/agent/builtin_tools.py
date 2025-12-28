"""Built-in example tools for the agent framework."""

from datetime import datetime
from typing import Any, Dict
import logging

from .tool_registry import BaseTool, get_tool_registry
from ..utils.system_info import SystemDetector

logger = logging.getLogger(__name__)


class EchoTool(BaseTool):
    """Tool that echoes back the provided message."""
    
    @property
    def name(self) -> str:
        return "echo"
    
    @property
    def description(self) -> str:
        return "Echoes back the provided message. Useful for testing and verification."
    
    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            'type': 'object',
            'properties': {
                'message': {
                    'type': 'string',
                    'description': 'Message to echo back'
                }
            },
            'required': ['message']
        }
    
    async def execute(self, **kwargs) -> Any:
        """Echo back the message."""
        self.validate_params(**kwargs)
        message = kwargs.get('message', '')
        logger.info(f"Echo tool executed with message: {message}")
        return message


class GetTimeTool(BaseTool):
    """Tool that gets the current date and time."""
    
    @property
    def name(self) -> str:
        return "get_time"
    
    @property
    def description(self) -> str:
        return "Gets the current date and time in the specified format."
    
    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            'type': 'object',
            'properties': {
                'format': {
                    'type': 'string',
                    'description': 'Time format: "iso" for ISO 8601, "readable" for human-readable, "timestamp" for Unix timestamp',
                    'default': 'iso',
                    'enum': ['iso', 'readable', 'timestamp']
                }
            },
            'required': []
        }
    
    async def execute(self, **kwargs) -> Any:
        """Get current time in specified format."""
        self.validate_params(**kwargs)
        time_format = kwargs.get('format', 'iso')
        
        now = datetime.now()
        
        if time_format == 'iso':
            result = now.isoformat()
        elif time_format == 'readable':
            result = now.strftime('%Y-%m-%d %H:%M:%S %Z')
        elif time_format == 'timestamp':
            result = str(int(now.timestamp()))
        else:
            result = now.isoformat()
        
        logger.info(f"Get time tool executed with format: {time_format}")
        return result


class GetSystemInfoTool(BaseTool):
    """Tool that gets system hardware information."""
    
    @property
    def name(self) -> str:
        return "get_system_info"
    
    @property
    def description(self) -> str:
        return "Gets system hardware information including CPU, RAM, and GPU details."
    
    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            'type': 'object',
            'properties': {
                'detailed': {
                    'type': 'boolean',
                    'description': 'Include detailed information about hardware',
                    'default': False
                }
            },
            'required': []
        }
    
    async def execute(self, **kwargs) -> Any:
        """Get system information."""
        self.validate_params(**kwargs)
        detailed = kwargs.get('detailed', False)
        
        detector = SystemDetector()
        
        # Basic information
        info = {
            'cpu_cores': detector.cpu_cores,
            'ram_gb': detector.ram_gb,
            'gpu_info': detector.gpu_info,
            'hardware_tier': detector.get_hardware_tier()
        }
        
        if detailed:
            # Add more detailed information
            info['platform'] = detector.platform
            info['gpu_vram_gb'] = detector.gpu_vram_gb
            info['has_nvidia_gpu'] = detector.has_nvidia_gpu()
            info['recommended_models'] = detector.get_recommended_models()
        
        logger.info(f"Get system info tool executed (detailed={detailed})")
        return info


def initialize_builtin_tools() -> None:
    """Initialize and register all built-in tools."""
    registry = get_tool_registry()
    
    tools = [
        EchoTool(),
        GetTimeTool(),
        GetSystemInfoTool()
    ]
    
    for tool in tools:
        try:
            registry.register(tool)
        except ValueError as e:
            logger.warning(f"Failed to register tool: {e}")
    
    logger.info(f"Initialized {len(tools)} built-in tools")
