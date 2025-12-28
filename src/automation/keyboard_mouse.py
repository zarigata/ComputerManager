"""
Keyboard and mouse control automation tools.

This module provides tools for controlling keyboard and mouse input using PyAutoGUI,
with safety features and cross-platform support.
"""

import asyncio
import logging
import sys
from typing import Any, Dict, List, Union

import pyautogui

from src.agent.tool_registry import BaseTool, ToolRegistry, get_tool_registry
from src.utils.config import get_config

config = get_config()

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


def _configure_pyautogui() -> None:
    """Configure PyAutoGUI with safety settings from config."""
    pyautogui.FAILSAFE = config.failsafe_enabled
    pyautogui.PAUSE = config.automation_delay_ms / 1000.0
    logger.info(f"PyAutoGUI configured: failsafe={config.failsafe_enabled}, pause={pyautogui.PAUSE}s")


# Configure on module import
_configure_pyautogui()


class MoveMouseTool(BaseTool):
    """Move the mouse cursor to specified coordinates."""
    
    @property
    def name(self) -> str:
        return "move_mouse"
    
    @property
    def description(self) -> str:
        return "Move the mouse cursor to absolute or relative coordinates"
    
    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "x": {
                    "type": "integer",
                    "description": "X coordinate (absolute or relative)"
                },
                "y": {
                    "type": "integer",
                    "description": "Y coordinate (absolute or relative)"
                },
                "duration": {
                    "type": "number",
                    "minimum": 0,
                    "description": "Duration of movement in seconds. Default: 0.5"
                },
                "relative": {
                    "type": "boolean",
                    "description": "Whether coordinates are relative to current position. Default: false"
                }
            },
            "required": ["x", "y"]
        }
    
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """
        Move mouse cursor.
        
        Args:
            x: X coordinate
            y: Y coordinate
            duration: Movement duration in seconds
            relative: Use relative movement
            
        Returns:
            Dict with 'success' and optional 'message'
        """
        try:
            await self.validate_params(**kwargs)
            
            x = kwargs['x']
            y = kwargs['y']
            duration = kwargs.get('duration', 0.5)
            relative = kwargs.get('relative', False)
            
            # Validate coordinates for absolute movement
            if not relative:
                screen_width, screen_height = pyautogui.size()
                if x < 0 or x >= screen_width or y < 0 or y >= screen_height:
                    return {
                        "success": False,
                        "error": f"Coordinates ({x}, {y}) out of screen bounds ({screen_width}x{screen_height})"
                    }
            
            # Move mouse
            try:
                if relative:
                    await asyncio.to_thread(pyautogui.move, x, y, duration=duration)
                    logger.info(f"Mouse moved relatively by ({x}, {y}) over {duration}s")
                else:
                    await asyncio.to_thread(pyautogui.moveTo, x, y, duration=duration)
                    logger.info(f"Mouse moved to ({x}, {y}) over {duration}s")
                
                return {
                    "success": True,
                    "message": f"Mouse moved to ({x}, {y})"
                }
                
            except pyautogui.FailSafeException:
                logger.warning("Mouse movement aborted by failsafe")
                return {
                    "success": False,
                    "error": "Operation aborted by failsafe (mouse moved to corner)"
                }
            
        except Exception as e:
            logger.error(f"Mouse movement failed: {e}", exc_info=True)
            return {
                "success": False,
                "error": f"Mouse movement failed: {str(e)}"
            }


class ClickMouseTool(BaseTool):
    """Perform mouse clicks."""
    
    @property
    def name(self) -> str:
        return "click_mouse"
    
    @property
    def description(self) -> str:
        return "Perform mouse clicks at current position or specified coordinates"
    
    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "x": {
                    "type": "integer",
                    "description": "Optional X coordinate. If not provided, clicks at current position."
                },
                "y": {
                    "type": "integer",
                    "description": "Optional Y coordinate. If not provided, clicks at current position."
                },
                "button": {
                    "type": "string",
                    "enum": ["left", "right", "middle"],
                    "description": "Mouse button to click. Default: 'left'"
                },
                "clicks": {
                    "type": "integer",
                    "minimum": 1,
                    "description": "Number of clicks (1=single, 2=double, 3=triple). Default: 1"
                },
                "interval": {
                    "type": "number",
                    "minimum": 0,
                    "description": "Interval between clicks in seconds. Default: 0.1"
                },
                "confirmed": {
                    "type": "boolean",
                    "description": "Confirmation flag for sensitive action. Required when SENSITIVE_ACTIONS_REQUIRE_CONFIRMATION is enabled."
                }
            }
        }
    
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """
        Perform mouse click.
        
        Args:
            x: Optional X coordinate
            y: Optional Y coordinate
            button: Mouse button ('left', 'right', 'middle')
            clicks: Number of clicks
            interval: Interval between clicks
            
        Returns:
            Dict with 'success' and optional 'message'
        """
        try:
            await self.validate_params(**kwargs)
            
            # Check confirmation requirement for sensitive action
            if config.sensitive_actions_require_confirmation:
                if not kwargs.get('confirmed', False):
                    logger.warning("Mouse click action requires confirmation but was not confirmed")
                    return {
                        "success": False,
                        "error": "This action requires confirmation. Set 'confirmed': true or disable SENSITIVE_ACTIONS_REQUIRE_CONFIRMATION in config."
                    }
            
            x = kwargs.get('x')
            y = kwargs.get('y')
            button = kwargs.get('button', 'left')
            clicks = kwargs.get('clicks', 1)
            interval = kwargs.get('interval', 0.1)
            
            # Validate coordinates if provided
            if x is not None and y is not None:
                screen_width, screen_height = pyautogui.size()
                if x < 0 or x >= screen_width or y < 0 or y >= screen_height:
                    return {
                        "success": False,
                        "error": f"Coordinates ({x}, {y}) out of screen bounds ({screen_width}x{screen_height})"
                    }
            
            # Perform click
            try:
                await asyncio.to_thread(
                    pyautogui.click,
                    x=x,
                    y=y,
                    clicks=clicks,
                    interval=interval,
                    button=button
                )
                
                position = f"at ({x}, {y})" if x is not None and y is not None else "at current position"
                logger.info(f"Mouse clicked {clicks} time(s) with {button} button {position}")
                
                return {
                    "success": True,
                    "message": f"Clicked {clicks} time(s) with {button} button {position}"
                }
                
            except pyautogui.FailSafeException:
                logger.warning("Mouse click aborted by failsafe")
                return {
                    "success": False,
                    "error": "Operation aborted by failsafe (mouse moved to corner)"
                }
            
        except Exception as e:
            logger.error(f"Mouse click failed: {e}", exc_info=True)
            return {
                "success": False,
                "error": f"Mouse click failed: {str(e)}"
            }


class ScrollMouseTool(BaseTool):
    """Scroll the mouse wheel."""
    
    @property
    def name(self) -> str:
        return "scroll_mouse"
    
    @property
    def description(self) -> str:
        return "Scroll the mouse wheel up (positive) or down (negative)"
    
    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "amount": {
                    "type": "integer",
                    "description": "Scroll amount (positive=up, negative=down). Units are platform-dependent."
                },
                "x": {
                    "type": "integer",
                    "description": "Optional X coordinate to scroll at"
                },
                "y": {
                    "type": "integer",
                    "description": "Optional Y coordinate to scroll at"
                }
            },
            "required": ["amount"]
        }
    
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """
        Scroll mouse wheel.
        
        Args:
            amount: Scroll amount (positive=up, negative=down)
            x: Optional X coordinate
            y: Optional Y coordinate
            
        Returns:
            Dict with 'success' and optional 'message'
        """
        try:
            await self.validate_params(**kwargs)
            
            amount = kwargs['amount']
            x = kwargs.get('x')
            y = kwargs.get('y')
            
            # Validate coordinates if provided
            if x is not None and y is not None:
                screen_width, screen_height = pyautogui.size()
                if x < 0 or x >= screen_width or y < 0 or y >= screen_height:
                    return {
                        "success": False,
                        "error": f"Coordinates ({x}, {y}) out of screen bounds ({screen_width}x{screen_height})"
                    }
            
            # Perform scroll
            try:
                await asyncio.to_thread(pyautogui.scroll, amount, x=x, y=y)
                
                direction = "up" if amount > 0 else "down"
                position = f"at ({x}, {y})" if x is not None and y is not None else "at current position"
                logger.info(f"Mouse scrolled {abs(amount)} units {direction} {position}")
                
                return {
                    "success": True,
                    "message": f"Scrolled {abs(amount)} units {direction} {position}"
                }
                
            except pyautogui.FailSafeException:
                logger.warning("Mouse scroll aborted by failsafe")
                return {
                    "success": False,
                    "error": "Operation aborted by failsafe (mouse moved to corner)"
                }
            
        except Exception as e:
            logger.error(f"Mouse scroll failed: {e}", exc_info=True)
            return {
                "success": False,
                "error": f"Mouse scroll failed: {str(e)}"
            }


class TypeTextTool(BaseTool):
    """Type text using the keyboard."""
    
    @property
    def name(self) -> str:
        return "type_text"
    
    @property
    def description(self) -> str:
        return "Type text using keyboard input"
    
    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "Text to type"
                },
                "interval": {
                    "type": "number",
                    "minimum": 0,
                    "description": "Interval between keystrokes in seconds. Default: 0.05"
                },
                "confirmed": {
                    "type": "boolean",
                    "description": "Confirmation flag for sensitive action. Required when SENSITIVE_ACTIONS_REQUIRE_CONFIRMATION is enabled."
                }
            },
            "required": ["text"]
        }
    
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """
        Type text.
        
        Args:
            text: Text to type
            interval: Interval between keystrokes
            
        Returns:
            Dict with 'success' and optional 'message'
        """
        try:
            await self.validate_params(**kwargs)
            
            # Check confirmation requirement for sensitive action
            if config.sensitive_actions_require_confirmation:
                if not kwargs.get('confirmed', False):
                    logger.warning("Type text action requires confirmation but was not confirmed")
                    return {
                        "success": False,
                        "error": "This action requires confirmation. Set 'confirmed': true or disable SENSITIVE_ACTIONS_REQUIRE_CONFIRMATION in config."
                    }
            
            text = kwargs['text']
            interval = kwargs.get('interval', 0.05)
            
            # Type text
            try:
                await asyncio.to_thread(pyautogui.write, text, interval=interval)
                
                logger.info(f"Typed text: {text[:50]}{'...' if len(text) > 50 else ''}")
                
                return {
                    "success": True,
                    "message": f"Typed {len(text)} characters"
                }
                
            except pyautogui.FailSafeException:
                logger.warning("Text typing aborted by failsafe")
                return {
                    "success": False,
                    "error": "Operation aborted by failsafe (mouse moved to corner)"
                }
            
        except Exception as e:
            logger.error(f"Text typing failed: {e}", exc_info=True)
            return {
                "success": False,
                "error": f"Text typing failed: {str(e)}"
            }


class PressKeyTool(BaseTool):
    """Press keyboard keys."""
    
    @property
    def name(self) -> str:
        return "press_key"
    
    @property
    def description(self) -> str:
        return "Press keyboard keys including special keys (enter, tab, esc, arrows, function keys, etc.)"
    
    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "key": {
                    "oneOf": [
                        {"type": "string"},
                        {"type": "array", "items": {"type": "string"}}
                    ],
                    "description": "Key or array of keys to press in sequence. Supports special keys like 'enter', 'tab', 'esc', 'space', 'backspace', 'delete', arrow keys, 'home', 'end', 'pageup', 'pagedown', 'f1'-'f12', etc."
                },
                "presses": {
                    "type": "integer",
                    "minimum": 1,
                    "description": "Number of times to press the key(s). Default: 1"
                },
                "interval": {
                    "type": "number",
                    "minimum": 0,
                    "description": "Interval between presses in seconds. Default: 0.1"
                },
                "confirmed": {
                    "type": "boolean",
                    "description": "Confirmation flag for sensitive action. Required when SENSITIVE_ACTIONS_REQUIRE_CONFIRMATION is enabled."
                }
            },
            "required": ["key"]
        }
    
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """
        Press keyboard key(s).
        
        Args:
            key: Key name or array of key names
            presses: Number of presses
            interval: Interval between presses
            
        Returns:
            Dict with 'success' and optional 'message'
        """
        try:
            await self.validate_params(**kwargs)
            
            # Check confirmation requirement for sensitive action
            if config.sensitive_actions_require_confirmation:
                if not kwargs.get('confirmed', False):
                    logger.warning("Press key action requires confirmation but was not confirmed")
                    return {
                        "success": False,
                        "error": "This action requires confirmation. Set 'confirmed': true or disable SENSITIVE_ACTIONS_REQUIRE_CONFIRMATION in config."
                    }
            
            key = kwargs['key']
            presses = kwargs.get('presses', 1)
            interval = kwargs.get('interval', 0.1)
            
            # Convert single key to list for uniform processing
            keys = [key] if isinstance(key, str) else key
            
            # Press keys
            try:
                for _ in range(presses):
                    for k in keys:
                        await asyncio.to_thread(pyautogui.press, k)
                        if len(keys) > 1 and k != keys[-1]:
                            await asyncio.sleep(interval)
                    if presses > 1 and _ < presses - 1:
                        await asyncio.sleep(interval)
                
                key_str = ', '.join(keys) if isinstance(key, list) else key
                logger.info(f"Pressed key(s): {key_str} ({presses} time(s))")
                
                return {
                    "success": True,
                    "message": f"Pressed {key_str} {presses} time(s)"
                }
                
            except pyautogui.FailSafeException:
                logger.warning("Key press aborted by failsafe")
                return {
                    "success": False,
                    "error": "Operation aborted by failsafe (mouse moved to corner)"
                }
            
        except Exception as e:
            logger.error(f"Key press failed: {e}", exc_info=True)
            return {
                "success": False,
                "error": f"Key press failed: {str(e)}"
            }


class HotkeyTool(BaseTool):
    """Execute keyboard shortcuts (hotkeys)."""
    
    @property
    def name(self) -> str:
        return "hotkey"
    
    @property
    def description(self) -> str:
        return "Execute keyboard shortcuts by pressing multiple keys simultaneously (e.g., Ctrl+C, Alt+Tab)"
    
    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "keys": {
                    "type": "array",
                    "items": {"type": "string"},
                    "minItems": 1,
                    "description": "Array of keys to press simultaneously. Example: ['ctrl', 'c'] for copy, ['ctrl', 'alt', 'delete'] for task manager."
                },
                "confirmed": {
                    "type": "boolean",
                    "description": "Confirmation flag for sensitive action. Required when SENSITIVE_ACTIONS_REQUIRE_CONFIRMATION is enabled."
                }
            },
            "required": ["keys"]
        }
    
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """
        Execute hotkey.
        
        Args:
            keys: Array of keys to press simultaneously
            
        Returns:
            Dict with 'success' and optional 'message'
        """
        try:
            await self.validate_params(**kwargs)
            
            # Check confirmation requirement for sensitive action (hotkeys are high-risk)
            if config.sensitive_actions_require_confirmation:
                if not kwargs.get('confirmed', False):
                    logger.warning("Hotkey action requires confirmation but was not confirmed")
                    return {
                        "success": False,
                        "error": "This action requires confirmation. Set 'confirmed': true or disable SENSITIVE_ACTIONS_REQUIRE_CONFIRMATION in config."
                    }
            
            keys = kwargs['keys']
            
            # Log warning for potentially dangerous hotkeys
            dangerous_combos = [
                ['ctrl', 'alt', 'delete'],
                ['alt', 'f4'],
                ['ctrl', 'w'],
                ['ctrl', 'q']
            ]
            
            keys_lower = [k.lower() for k in keys]
            for combo in dangerous_combos:
                if keys_lower == combo:
                    logger.warning(f"Executing potentially dangerous hotkey: {'+'.join(keys)}")
                    break
            
            # Execute hotkey
            try:
                await asyncio.to_thread(pyautogui.hotkey, *keys)
                
                logger.info(f"Executed hotkey: {'+'.join(keys)}")
                
                return {
                    "success": True,
                    "message": f"Executed hotkey: {'+'.join(keys)}"
                }
                
            except pyautogui.FailSafeException:
                logger.warning("Hotkey execution aborted by failsafe")
                return {
                    "success": False,
                    "error": "Operation aborted by failsafe (mouse moved to corner)"
                }
            
        except Exception as e:
            logger.error(f"Hotkey execution failed: {e}", exc_info=True)
            return {
                "success": False,
                "error": f"Hotkey execution failed: {str(e)}"
            }


class DragMouseTool(BaseTool):
    """Drag the mouse from one position to another."""
    
    @property
    def name(self) -> str:
        return "drag_mouse"
    
    @property
    def description(self) -> str:
        return "Drag the mouse from current position or specified start to end coordinates"
    
    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "x": {
                    "type": "integer",
                    "description": "Target X coordinate (absolute or relative)"
                },
                "y": {
                    "type": "integer",
                    "description": "Target Y coordinate (absolute or relative)"
                },
                "duration": {
                    "type": "number",
                    "minimum": 0,
                    "description": "Duration of drag in seconds. Default: 1.0"
                },
                "button": {
                    "type": "string",
                    "enum": ["left", "right", "middle"],
                    "description": "Mouse button to hold during drag. Default: 'left'"
                },
                "relative": {
                    "type": "boolean",
                    "description": "Whether coordinates are relative to current position. Default: false"
                },
                "confirmed": {
                    "type": "boolean",
                    "description": "Confirmation flag for sensitive action. Required when SENSITIVE_ACTIONS_REQUIRE_CONFIRMATION is enabled."
                }
            },
            "required": ["x", "y"]
        }
    
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """
        Drag mouse.
        
        Args:
            x: Target X coordinate
            y: Target Y coordinate
            duration: Drag duration in seconds
            button: Mouse button to use
            relative: Use relative coordinates
            
        Returns:
            Dict with 'success' and optional 'message'
        """
        try:
            await self.validate_params(**kwargs)
            
            # Check confirmation requirement for sensitive action
            if config.sensitive_actions_require_confirmation:
                if not kwargs.get('confirmed', False):
                    logger.warning("Drag mouse action requires confirmation but was not confirmed")
                    return {
                        "success": False,
                        "error": "This action requires confirmation. Set 'confirmed': true or disable SENSITIVE_ACTIONS_REQUIRE_CONFIRMATION in config."
                    }
            
            x = kwargs['x']
            y = kwargs['y']
            duration = kwargs.get('duration', 1.0)
            button = kwargs.get('button', 'left')
            relative = kwargs.get('relative', False)
            
            # Validate coordinates for absolute movement
            if not relative:
                screen_width, screen_height = pyautogui.size()
                if x < 0 or x >= screen_width or y < 0 or y >= screen_height:
                    return {
                        "success": False,
                        "error": f"Coordinates ({x}, {y}) out of screen bounds ({screen_width}x{screen_height})"
                    }
            
            # Perform drag
            try:
                if relative:
                    await asyncio.to_thread(pyautogui.drag, x, y, duration=duration, button=button)
                    logger.info(f"Mouse dragged relatively by ({x}, {y}) with {button} button over {duration}s")
                else:
                    await asyncio.to_thread(pyautogui.dragTo, x, y, duration=duration, button=button)
                    logger.info(f"Mouse dragged to ({x}, {y}) with {button} button over {duration}s")
                
                return {
                    "success": True,
                    "message": f"Dragged mouse to ({x}, {y}) with {button} button"
                }
                
            except pyautogui.FailSafeException:
                logger.warning("Mouse drag aborted by failsafe")
                return {
                    "success": False,
                    "error": "Operation aborted by failsafe (mouse moved to corner)"
                }
            
        except Exception as e:
            logger.error(f"Mouse drag failed: {e}", exc_info=True)
            return {
                "success": False,
                "error": f"Mouse drag failed: {str(e)}"
            }


def register_keyboard_mouse_tools() -> None:
    """Register all keyboard and mouse control tools with the global registry."""
    registry = get_tool_registry()
    
    tools = [
        MoveMouseTool(),
        ClickMouseTool(),
        ScrollMouseTool(),
        TypeTextTool(),
        PressKeyTool(),
        HotkeyTool(),
        DragMouseTool()
    ]
    
    for tool in tools:
        registry.register(tool)
        logger.info(f"Registered keyboard/mouse tool: {tool.name}")
