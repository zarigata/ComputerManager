"""
Ollama integration package.

Provides Ollama client, model management, and vision analysis capabilities.
"""

from src.ollama.client import OllamaClient
from src.ollama.model_manager import ModelManager
from src.ollama.vision import (
    VisionAnalyzer,
    register_vision_tools,
    DescribeScreenTool,
    FindElementOnScreenTool,
    ReadTextFromScreenTool,
    AnalyzeUIStateTool
)

__all__ = [
    'OllamaClient',
    'ModelManager',
    'VisionAnalyzer',
    'register_vision_tools',
    'DescribeScreenTool',
    'FindElementOnScreenTool',
    'ReadTextFromScreenTool',
    'AnalyzeUIStateTool'
]
