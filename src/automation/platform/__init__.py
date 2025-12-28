"""Platform-specific automation tools.

This module provides platform detection and registration of OS-specific tools.
"""

import platform
import logging

logger = logging.getLogger(__name__)

def get_current_platform() -> str:
    """Detect current platform and return normalized name.
    
    Returns:
        str: Platform name ('windows', 'linux', 'macos', or 'unknown')
    """
    system = platform.system().lower()
    if system == "darwin":
        return "macos"
    elif system in ["linux", "windows"]:
        return system
    else:
        logger.warning(f"Unknown platform: {system}")
        return "unknown"

def register_platform_tools():
    """Register platform-specific tools based on current OS.
    
    This function detects the current platform and dynamically imports
    and registers the appropriate platform-specific tools.
    """
    current_platform = get_current_platform()
    
    if current_platform == "windows":
        try:
            from .windows import register_windows_tools
            register_windows_tools()
            logger.info("Registered Windows-specific tools")
        except ImportError as e:
            logger.warning(f"Failed to import Windows tools: {e}")
    
    elif current_platform == "linux":
        try:
            from .linux import register_linux_tools
            register_linux_tools()
            logger.info("Registered Linux-specific tools")
        except ImportError as e:
            logger.warning(f"Failed to import Linux tools: {e}")
    
    elif current_platform == "macos":
        try:
            from .macos import register_macos_tools
            register_macos_tools()
            logger.info("Registered macOS-specific tools")
        except ImportError as e:
            logger.warning(f"Failed to import macOS tools: {e}")
    
    else:
        logger.warning(f"No platform-specific tools available for: {current_platform}")

__all__ = ['get_current_platform', 'register_platform_tools']
