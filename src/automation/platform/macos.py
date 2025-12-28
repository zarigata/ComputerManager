"""macOS-specific automation tools.

This module provides macOS-specific system operations using AppleScript and native commands.
"""

import subprocess
import logging
from typing import Any, Dict

from src.agent.tool_registry import BaseTool, get_tool_registry

logger = logging.getLogger(__name__)


class MacOSAppleScriptTool(BaseTool):
    """Tool to execute AppleScript commands."""
    
    @property
    def name(self) -> str:
        return "macos_applescript"
    
    @property
    def description(self) -> str:
        return "Execute AppleScript commands on macOS"
    
    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "script": {
                    "type": "string",
                    "description": "AppleScript code to execute"
                }
            },
            "required": ["script"]
        }
    
    async def execute(self, **kwargs) -> str:
        """Execute AppleScript."""
        self.validate_params(**kwargs)
        
        script = kwargs["script"]
        
        try:
            result = subprocess.run(
                ["osascript", "-e", script],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                logger.info("AppleScript executed successfully")
                return result.stdout.strip() if result.stdout else "Script executed successfully"
            else:
                return f"Error executing AppleScript: {result.stderr}"
        
        except subprocess.TimeoutExpired:
            return "Error: Script execution timed out after 30 seconds"
        except FileNotFoundError:
            return "Error: osascript command not found. This tool requires macOS."
        except Exception as e:
            logger.error(f"AppleScript error: {e}")
            return f"Error executing AppleScript: {str(e)}"


class MacOSApplicationControlTool(BaseTool):
    """Tool to control macOS applications."""
    
    @property
    def name(self) -> str:
        return "macos_app_control"
    
    @property
    def description(self) -> str:
        return "Control macOS applications (launch, quit, activate, hide)"
    
    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "application": {
                    "type": "string",
                    "description": "Name of the application (e.g., 'Safari', 'Finder', 'Music')"
                },
                "action": {
                    "type": "string",
                    "description": "Action to perform",
                    "enum": ["launch", "quit", "activate", "hide"]
                }
            },
            "required": ["application", "action"]
        }
    
    async def execute(self, **kwargs) -> str:
        """Execute application control."""
        self.validate_params(**kwargs)
        
        application = kwargs["application"]
        action = kwargs["action"]
        
        # Try PyXA first if available
        try:
            import PyXA
            
            app = PyXA.Application(application)
            
            if action == "launch":
                app.launch()
                return f"Launched {application}"
            elif action == "quit":
                app.quit()
                return f"Quit {application}"
            elif action == "activate":
                app.activate()
                return f"Activated {application}"
            elif action == "hide":
                app.hide()
                return f"Hidden {application}"
        
        except ImportError:
            # Fallback to AppleScript
            logger.info("PyXA not available, using AppleScript fallback")
            
            script_map = {
                "launch": f'tell application "{application}" to launch',
                "quit": f'tell application "{application}" to quit',
                "activate": f'tell application "{application}" to activate',
                "hide": f'tell application "System Events" to set visible of process "{application}" to false'
            }
            
            script = script_map.get(action)
            if not script:
                return f"Error: Unknown action '{action}'"
            
            try:
                result = subprocess.run(
                    ["osascript", "-e", script],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                
                if result.returncode == 0:
                    logger.info(f"Application {application} {action}ed")
                    return f"Successfully {action}ed {application}"
                else:
                    return f"Error: {result.stderr}"
            
            except subprocess.TimeoutExpired:
                return "Error: Command timed out"
            except Exception as e:
                logger.error(f"Application control error: {e}")
                return f"Error controlling application: {str(e)}"
        
        except Exception as e:
            logger.error(f"Application control error: {e}")
            return f"Error controlling application: {str(e)}"


class MacOSSystemPreferencesTool(BaseTool):
    """Tool to access macOS system preferences."""
    
    @property
    def name(self) -> str:
        return "macos_system_preferences"
    
    @property
    def description(self) -> str:
        return "Read or write macOS system preferences using defaults command"
    
    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "description": "Action to perform",
                    "enum": ["read", "write", "delete"]
                },
                "domain": {
                    "type": "string",
                    "description": "Preference domain (e.g., 'com.apple.dock', 'NSGlobalDomain')"
                },
                "key": {
                    "type": "string",
                    "description": "Preference key"
                },
                "value": {
                    "description": "Value to write (required for 'write' action)"
                },
                "type": {
                    "type": "string",
                    "description": "Value type for write action",
                    "enum": ["string", "int", "float", "bool", "array", "dict"],
                    "default": "string"
                }
            },
            "required": ["action", "domain", "key"]
        }
    
    async def execute(self, **kwargs) -> str:
        """Execute system preferences operation."""
        self.validate_params(**kwargs)
        
        action = kwargs["action"]
        domain = kwargs["domain"]
        key = kwargs["key"]
        value = kwargs.get("value")
        value_type = kwargs.get("type", "string")
        
        try:
            if action == "read":
                result = subprocess.run(
                    ["defaults", "read", domain, key],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                
                if result.returncode == 0:
                    return f"{key} = {result.stdout.strip()}"
                else:
                    return f"Error reading preference: {result.stderr}"
            
            elif action == "write":
                if value is None:
                    return "Error: 'value' parameter required for write action"
                
                cmd = ["defaults", "write", domain, key]
                
                # Add type flag if needed
                type_flags = {
                    "string": "-string",
                    "int": "-int",
                    "float": "-float",
                    "bool": "-bool",
                    "array": "-array",
                    "dict": "-dict"
                }
                
                if value_type in type_flags:
                    cmd.append(type_flags[value_type])
                
                cmd.append(str(value))
                
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                
                if result.returncode == 0:
                    logger.info(f"Wrote preference: {domain}.{key}")
                    return f"Successfully wrote {key} = {value}"
                else:
                    return f"Error writing preference: {result.stderr}"
            
            elif action == "delete":
                result = subprocess.run(
                    ["defaults", "delete", domain, key],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                
                if result.returncode == 0:
                    logger.info(f"Deleted preference: {domain}.{key}")
                    return f"Successfully deleted {key}"
                else:
                    return f"Error deleting preference: {result.stderr}"
        
        except subprocess.TimeoutExpired:
            return "Error: Command timed out"
        except Exception as e:
            logger.error(f"System preferences error: {e}")
            return f"Error accessing system preferences: {str(e)}"


class MacOSNotificationTool(BaseTool):
    """Tool to send macOS system notifications."""
    
    @property
    def name(self) -> str:
        return "macos_notification"
    
    @property
    def description(self) -> str:
        return "Send a system notification on macOS"
    
    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "Notification title"
                },
                "message": {
                    "type": "string",
                    "description": "Notification message"
                },
                "sound": {
                    "type": "string",
                    "description": "Sound name (optional, e.g., 'default', 'Glass', 'Ping')"
                }
            },
            "required": ["title", "message"]
        }
    
    async def execute(self, **kwargs) -> str:
        """Execute notification."""
        self.validate_params(**kwargs)
        
        title = kwargs["title"]
        message = kwargs["message"]
        sound = kwargs.get("sound")
        
        # Escape quotes in title and message
        title = title.replace('"', '\\"')
        message = message.replace('"', '\\"')
        
        script = f'display notification "{message}" with title "{title}"'
        
        if sound:
            script += f' sound name "{sound}"'
        
        try:
            result = subprocess.run(
                ["osascript", "-e", script],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                logger.info(f"Sent notification: {title}")
                return f"Notification sent: {title}"
            else:
                return f"Error sending notification: {result.stderr}"
        
        except subprocess.TimeoutExpired:
            return "Error: Command timed out"
        except Exception as e:
            logger.error(f"Notification error: {e}")
            return f"Error sending notification: {str(e)}"


class MacOSVolumeControlTool(BaseTool):
    """Tool to control macOS system volume."""
    
    @property
    def name(self) -> str:
        return "macos_volume_control"
    
    @property
    def description(self) -> str:
        return "Control macOS system volume"
    
    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "description": "Volume action",
                    "enum": ["set", "increase", "decrease", "mute", "unmute", "get"]
                },
                "level": {
                    "type": "integer",
                    "description": "Volume level (0-100) for 'set' action",
                    "minimum": 0,
                    "maximum": 100
                }
            },
            "required": ["action"]
        }
    
    async def execute(self, **kwargs) -> str:
        """Execute volume control."""
        self.validate_params(**kwargs)
        
        action = kwargs["action"]
        level = kwargs.get("level")
        
        try:
            if action == "set":
                if level is None:
                    return "Error: 'level' parameter required for 'set' action"
                
                script = f'set volume output volume {level}'
                result = subprocess.run(
                    ["osascript", "-e", script],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                
                if result.returncode == 0:
                    logger.info(f"Set volume to {level}%")
                    return f"Volume set to {level}%"
                else:
                    return f"Error: {result.stderr}"
            
            elif action == "increase":
                # Get current volume and increase
                script = 'output volume of (get volume settings)'
                result = subprocess.run(
                    ["osascript", "-e", script],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                
                if result.returncode == 0:
                    current = int(result.stdout.strip())
                    new_level = min(100, current + 10)
                    
                    subprocess.run(
                        ["osascript", "-e", f'set volume output volume {new_level}'],
                        timeout=5
                    )
                    return f"Volume increased to {new_level}%"
                else:
                    return f"Error: {result.stderr}"
            
            elif action == "decrease":
                script = 'output volume of (get volume settings)'
                result = subprocess.run(
                    ["osascript", "-e", script],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                
                if result.returncode == 0:
                    current = int(result.stdout.strip())
                    new_level = max(0, current - 10)
                    
                    subprocess.run(
                        ["osascript", "-e", f'set volume output volume {new_level}'],
                        timeout=5
                    )
                    return f"Volume decreased to {new_level}%"
                else:
                    return f"Error: {result.stderr}"
            
            elif action == "mute":
                subprocess.run(
                    ["osascript", "-e", "set volume output muted true"],
                    timeout=5
                )
                return "Volume muted"
            
            elif action == "unmute":
                subprocess.run(
                    ["osascript", "-e", "set volume output muted false"],
                    timeout=5
                )
                return "Volume unmuted"
            
            elif action == "get":
                script = 'get volume settings'
                result = subprocess.run(
                    ["osascript", "-e", script],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                
                if result.returncode == 0:
                    return f"Volume settings: {result.stdout.strip()}"
                else:
                    return f"Error: {result.stderr}"
        
        except subprocess.TimeoutExpired:
            return "Error: Command timed out"
        except Exception as e:
            logger.error(f"Volume control error: {e}")
            return f"Error controlling volume: {str(e)}"


class MacOSShutdownTool(BaseTool):
    """Tool to shutdown, restart, sleep, or logout macOS."""
    
    @property
    def name(self) -> str:
        return "macos_shutdown"
    
    @property
    def description(self) -> str:
        return "Shutdown, restart, sleep, or logout macOS system"
    
    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "description": "Action to perform",
                    "enum": ["shutdown", "restart", "sleep", "logout"]
                }
            },
            "required": ["action"]
        }
    
    async def execute(self, **kwargs) -> str:
        """Execute shutdown operation."""
        self.validate_params(**kwargs)
        
        action = kwargs["action"]
        
        script_map = {
            "shutdown": 'tell application "System Events" to shut down',
            "restart": 'tell application "System Events" to restart',
            "sleep": 'tell application "System Events" to sleep',
            "logout": 'tell application "System Events" to log out'
        }
        
        script = script_map.get(action)
        if not script:
            return f"Error: Unknown action '{action}'"
        
        try:
            result = subprocess.run(
                ["osascript", "-e", script],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                logger.info(f"Initiated macOS {action}")
                return f"Successfully initiated {action}"
            else:
                return f"Error: {result.stderr}"
        
        except subprocess.TimeoutExpired:
            return "Error: Command timed out"
        except Exception as e:
            logger.error(f"Shutdown error: {e}")
            return f"Error executing {action}: {str(e)}"


class MacOSFinderTool(BaseTool):
    """Tool to control macOS Finder operations."""
    
    @property
    def name(self) -> str:
        return "macos_finder"
    
    @property
    def description(self) -> str:
        return "Control macOS Finder operations"
    
    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "description": "Finder action to perform",
                    "enum": ["reveal", "open", "get_selection", "empty_trash"]
                },
                "path": {
                    "type": "string",
                    "description": "File path (required for 'reveal' and 'open' actions)"
                }
            },
            "required": ["action"]
        }
    
    async def execute(self, **kwargs) -> str:
        """Execute Finder operation."""
        self.validate_params(**kwargs)
        
        action = kwargs["action"]
        path = kwargs.get("path")
        
        try:
            if action == "reveal":
                if not path:
                    return "Error: 'path' parameter required for 'reveal' action"
                
                script = f'tell application "Finder" to reveal POSIX file "{path}"'
                result = subprocess.run(
                    ["osascript", "-e", script],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                
                if result.returncode == 0:
                    # Activate Finder to bring it to front
                    subprocess.run(
                        ["osascript", "-e", 'tell application "Finder" to activate'],
                        timeout=5
                    )
                    return f"Revealed {path} in Finder"
                else:
                    return f"Error: {result.stderr}"
            
            elif action == "open":
                if not path:
                    return "Error: 'path' parameter required for 'open' action"
                
                result = subprocess.run(
                    ["open", path],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                
                if result.returncode == 0:
                    return f"Opened {path}"
                else:
                    return f"Error: {result.stderr}"
            
            elif action == "get_selection":
                script = 'tell application "Finder" to get selection as alias list'
                result = subprocess.run(
                    ["osascript", "-e", script],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                
                if result.returncode == 0:
                    return f"Selected items: {result.stdout.strip()}"
                else:
                    return f"Error: {result.stderr}"
            
            elif action == "empty_trash":
                script = 'tell application "Finder" to empty trash'
                result = subprocess.run(
                    ["osascript", "-e", script],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                
                if result.returncode == 0:
                    logger.info("Emptied trash")
                    return "Successfully emptied trash"
                else:
                    return f"Error: {result.stderr}"
        
        except subprocess.TimeoutExpired:
            return "Error: Command timed out"
        except Exception as e:
            logger.error(f"Finder error: {e}")
            return f"Error with Finder operation: {str(e)}"


class MacOSClipboardTool(BaseTool):
    """Tool for macOS clipboard operations."""
    
    @property
    def name(self) -> str:
        return "macos_clipboard"
    
    @property
    def description(self) -> str:
        return "Get or set macOS clipboard content"
    
    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "description": "Clipboard action",
                    "enum": ["get", "set"]
                },
                "content": {
                    "type": "string",
                    "description": "Content to set (required for 'set' action)"
                }
            },
            "required": ["action"]
        }
    
    async def execute(self, **kwargs) -> str:
        """Execute clipboard operation."""
        self.validate_params(**kwargs)
        
        action = kwargs["action"]
        content = kwargs.get("content")
        
        try:
            if action == "get":
                result = subprocess.run(
                    ["pbpaste"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                
                if result.returncode == 0:
                    clipboard_content = result.stdout
                    # Limit output length
                    if len(clipboard_content) > 1000:
                        clipboard_content = clipboard_content[:1000] + "\n... (truncated)"
                    return f"Clipboard content:\n{clipboard_content}"
                else:
                    return f"Error reading clipboard: {result.stderr}"
            
            elif action == "set":
                if content is None:
                    return "Error: 'content' parameter required for 'set' action"
                
                result = subprocess.run(
                    ["pbcopy"],
                    input=content,
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                
                if result.returncode == 0:
                    logger.info("Set clipboard content")
                    return "Successfully set clipboard content"
                else:
                    return f"Error setting clipboard: {result.stderr}"
        
        except subprocess.TimeoutExpired:
            return "Error: Command timed out"
        except Exception as e:
            logger.error(f"Clipboard error: {e}")
            return f"Error with clipboard operation: {str(e)}"


def register_macos_tools():
    """Register all macOS-specific tools."""
    registry = get_tool_registry()
    tools = [
        MacOSAppleScriptTool(),
        MacOSApplicationControlTool(),
        MacOSSystemPreferencesTool(),
        MacOSNotificationTool(),
        MacOSVolumeControlTool(),
        MacOSShutdownTool(),
        MacOSFinderTool(),
        MacOSClipboardTool()
    ]
    for tool in tools:
        try:
            registry.register(tool)
            logger.info(f"Registered macOS tool: {tool.name}")
        except ValueError as e:
            logger.warning(f"Failed to register tool: {e}")
