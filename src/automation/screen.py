"""
Screen capture and image detection automation tools.

This module provides tools for capturing screenshots, detecting screen properties,
and locating images on screen using PyAutoGUI and PIL.
"""

import asyncio
import logging
import os
import sys
import tempfile
from typing import Any, Dict, Optional, Tuple

import pyautogui
from PIL import ImageGrab

from src.agent.tool_registry import BaseTool, ToolRegistry
from src.utils.config import config

logger = logging.getLogger(__name__)


def _get_platform() -> str:
    """
    Detect the current platform.
    
    Returns:
        str: 'windows', 'linux', or 'macos'
    """
    if sys.platform.startswith('win'):
        return 'windows'
    elif sys.platform.startswith('linux'):
        return 'linux'
    elif sys.platform.startswith('darwin'):
        return 'macos'
    return 'unknown'


class CaptureScreenshotTool(BaseTool):
    """Capture full screen or specific region as screenshot."""
    
    @property
    def name(self) -> str:
        return "capture_screenshot"
    
    @property
    def description(self) -> str:
        return "Capture a screenshot of the entire screen or a specific region"
    
    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "region": {
                    "type": "array",
                    "items": {"type": "integer"},
                    "minItems": 4,
                    "maxItems": 4,
                    "description": "Optional region to capture as [x, y, width, height]. If not provided, captures full screen."
                },
                "save_path": {
                    "type": "string",
                    "description": "Optional path to save the screenshot. If not provided, saves to temporary file."
                },
                "quality": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 100,
                    "description": "JPEG quality (1-100). Defaults to config setting."
                }
            }
        }
    
    @property
    def parameters_json_schema(self) -> Dict[str, Any]:
        """Alias for parameters property for backward compatibility."""
        return self.parameters
    
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """
        Execute screenshot capture.
        
        Args:
            region: Optional tuple of (x, y, width, height)
            save_path: Optional path to save screenshot
            quality: Optional JPEG quality (1-100)
            
        Returns:
            Dict with 'success', 'file_path', and optional 'message'
        """
        try:
            await self.validate_params(**kwargs)
            
            region = kwargs.get('region')
            save_path = kwargs.get('save_path')
            quality = kwargs.get('quality', config.screenshot_quality)
            
            # Validate region if provided
            if region:
                if len(region) != 4:
                    return {
                        "success": False,
                        "error": "Region must be [x, y, width, height]"
                    }
                
                screen_width, screen_height = pyautogui.size()
                x, y, width, height = region
                
                if x < 0 or y < 0 or width <= 0 or height <= 0:
                    return {
                        "success": False,
                        "error": "Invalid region coordinates"
                    }
                
                if x + width > screen_width or y + height > screen_height:
                    return {
                        "success": False,
                        "error": f"Region exceeds screen bounds ({screen_width}x{screen_height})"
                    }
                
                region_tuple = (x, y, x + width, y + height)
            else:
                region_tuple = None
            
            # Capture screenshot
            platform = _get_platform()
            if platform == 'windows' and region_tuple:
                # Use PIL ImageGrab for Windows with region
                screenshot = await asyncio.to_thread(ImageGrab.grab, bbox=region_tuple)
            else:
                # Use PyAutoGUI for cross-platform support
                if region_tuple:
                    x, y, x2, y2 = region_tuple
                    screenshot = await asyncio.to_thread(
                        pyautogui.screenshot,
                        region=(x, y, x2 - x, y2 - y)
                    )
                else:
                    screenshot = await asyncio.to_thread(pyautogui.screenshot)
            
            # Determine save path
            if not save_path:
                temp_dir = tempfile.gettempdir()
                save_path = os.path.join(temp_dir, f"screenshot_{os.getpid()}.png")
            
            # Ensure directory exists
            os.makedirs(os.path.dirname(os.path.abspath(save_path)), exist_ok=True)
            
            # Save screenshot
            if save_path.lower().endswith('.jpg') or save_path.lower().endswith('.jpeg'):
                await asyncio.to_thread(screenshot.save, save_path, 'JPEG', quality=quality)
            else:
                await asyncio.to_thread(screenshot.save, save_path)
            
            logger.info(f"Screenshot captured: {save_path} (region: {region})")
            
            return {
                "success": True,
                "file_path": os.path.abspath(save_path),
                "message": f"Screenshot saved to {save_path}"
            }
            
        except Exception as e:
            logger.error(f"Screenshot capture failed: {e}", exc_info=True)
            return {
                "success": False,
                "error": f"Screenshot capture failed: {str(e)}"
            }


class GetScreenSizeTool(BaseTool):
    """Get the dimensions of the primary screen."""
    
    @property
    def name(self) -> str:
        return "get_screen_size"
    
    @property
    def description(self) -> str:
        return "Get the width and height of the primary screen in pixels"
    
    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {}
        }
    
    @property
    def parameters_json_schema(self) -> Dict[str, Any]:
        """Alias for parameters property for backward compatibility."""
        return self.parameters
    
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """
        Get screen dimensions.
        
        Returns:
            Dict with 'success', 'width', 'height'
        """
        try:
            width, height = pyautogui.size()
            
            logger.info(f"Screen size: {width}x{height}")
            
            return {
                "success": True,
                "width": width,
                "height": height
            }
            
        except Exception as e:
            logger.error(f"Failed to get screen size: {e}", exc_info=True)
            return {
                "success": False,
                "error": f"Failed to get screen size: {str(e)}"
            }


class LocateImageOnScreenTool(BaseTool):
    """Locate an image on the screen."""
    
    @property
    def name(self) -> str:
        return "locate_image_on_screen"
    
    @property
    def description(self) -> str:
        return "Find an image on the screen and return its coordinates"
    
    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "image_path": {
                    "type": "string",
                    "description": "Path to the image file to locate on screen"
                },
                "confidence": {
                    "type": "number",
                    "minimum": 0,
                    "maximum": 1,
                    "description": "Confidence level for image matching (0-1). Default: 0.9"
                },
                "grayscale": {
                    "type": "boolean",
                    "description": "Whether to use grayscale matching for better performance. Default: true"
                }
            },
            "required": ["image_path"]
        }
    
    @property
    def parameters_json_schema(self) -> Dict[str, Any]:
        """Alias for parameters property for backward compatibility."""
        return self.parameters
    
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """
        Locate image on screen.
        
        Args:
            image_path: Path to image file
            confidence: Matching confidence (0-1)
            grayscale: Use grayscale matching
            
        Returns:
            Dict with 'success', and if found: 'x', 'y', 'width', 'height'
        """
        try:
            await self.validate_params(**kwargs)
            
            image_path = kwargs['image_path']
            confidence = kwargs.get('confidence', 0.9)
            grayscale = kwargs.get('grayscale', True)
            
            # Validate image file exists
            if not os.path.exists(image_path):
                return {
                    "success": False,
                    "error": f"Image file not found: {image_path}"
                }
            
            # Check OpenCV availability for confidence-based matching
            opencv_available = False
            try:
                import cv2
                opencv_available = True
            except ImportError:
                pass
            
            # Locate image on screen
            try:
                if opencv_available:
                    # Use confidence parameter when OpenCV is available
                    location = await asyncio.to_thread(
                        pyautogui.locateOnScreen,
                        image_path,
                        confidence=confidence,
                        grayscale=grayscale
                    )
                else:
                    # Fallback without confidence when OpenCV is not installed
                    if confidence != 0.9:  # User explicitly set confidence
                        logger.warning(
                            f"OpenCV not available. Confidence parameter ({confidence}) will be ignored. "
                            "Install opencv-python for confidence-based matching: pip install opencv-python"
                        )
                    location = await asyncio.to_thread(
                        pyautogui.locateOnScreen,
                        image_path,
                        grayscale=False  # Disable grayscale without OpenCV
                    )
            except pyautogui.ImageNotFoundException:
                location = None
            
            if location:
                logger.info(f"Image found at: {location}")
                return {
                    "success": True,
                    "found": True,
                    "x": location.left,
                    "y": location.top,
                    "width": location.width,
                    "height": location.height
                }
            else:
                logger.info(f"Image not found: {image_path}")
                return {
                    "success": True,
                    "found": False,
                    "message": "Image not found on screen"
                }
            
        except Exception as e:
            logger.error(f"Image location failed: {e}", exc_info=True)
            return {
                "success": False,
                "error": f"Image location failed: {str(e)}"
            }


class GetPixelColorTool(BaseTool):
    """Get the RGB color of a pixel at specific coordinates."""
    
    @property
    def name(self) -> str:
        return "get_pixel_color"
    
    @property
    def description(self) -> str:
        return "Get the RGB color values of a pixel at the specified screen coordinates"
    
    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "x": {
                    "type": "integer",
                    "description": "X coordinate of the pixel"
                },
                "y": {
                    "type": "integer",
                    "description": "Y coordinate of the pixel"
                }
            },
            "required": ["x", "y"]
        }
    
    @property
    def parameters_json_schema(self) -> Dict[str, Any]:
        """Alias for parameters property for backward compatibility."""
        return self.parameters
    
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """
        Get pixel color at coordinates.
        
        Args:
            x: X coordinate
            y: Y coordinate
            
        Returns:
            Dict with 'success', 'r', 'g', 'b' values
        """
        try:
            await self.validate_params(**kwargs)
            
            x = kwargs['x']
            y = kwargs['y']
            
            # Validate coordinates
            screen_width, screen_height = pyautogui.size()
            if x < 0 or x >= screen_width or y < 0 or y >= screen_height:
                return {
                    "success": False,
                    "error": f"Coordinates ({x}, {y}) out of screen bounds ({screen_width}x{screen_height})"
                }
            
            # Get pixel color
            color = await asyncio.to_thread(pyautogui.pixel, x, y)
            
            logger.info(f"Pixel color at ({x}, {y}): RGB{color}")
            
            return {
                "success": True,
                "x": x,
                "y": y,
                "r": color[0],
                "g": color[1],
                "b": color[2]
            }
            
        except Exception as e:
            logger.error(f"Get pixel color failed: {e}", exc_info=True)
            return {
                "success": False,
                "error": f"Get pixel color failed: {str(e)}"
            }


def register_screen_tools() -> None:
    """Register all screen capture tools with the global registry."""
    registry = ToolRegistry.get_instance()
    
    tools = [
        CaptureScreenshotTool(),
        GetScreenSizeTool(),
        LocateImageOnScreenTool(),
        GetPixelColorTool()
    ]
    
    for tool in tools:
        registry.register(tool)
        logger.info(f"Registered screen tool: {tool.name}")
