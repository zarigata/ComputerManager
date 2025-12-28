"""
Automation tools for the Computer Manager agent.

This module provides file operations, process management, and web browsing tools.
"""

from .file_ops import register_file_tools
from .app_control import register_app_control_tools
from .screen import register_screen_tools
from .keyboard_mouse import register_keyboard_mouse_tools
from .platform import register_platform_tools

__all__ = [
    'register_file_tools',
    'register_app_control_tools',
    'register_screen_tools',
    'register_keyboard_mouse_tools',
    'register_platform_tools'
]
