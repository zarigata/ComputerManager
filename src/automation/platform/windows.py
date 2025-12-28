"""Windows-specific automation tools.

This module provides Windows-specific system operations using native APIs.
"""

import winreg
import ctypes
import subprocess
import os
import logging
from typing import Any, Dict

from src.agent.tool_registry import BaseTool, get_tool_registry

logger = logging.getLogger(__name__)


class ReadRegistryKeyTool(BaseTool):
    """Tool to read Windows registry key values."""
    
    @property
    def name(self) -> str:
        return "read_registry_key"
    
    @property
    def description(self) -> str:
        return "Read a value from the Windows registry"
    
    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "hive": {
                    "type": "string",
                    "description": "Registry hive (HKEY_CURRENT_USER, HKEY_LOCAL_MACHINE, HKEY_CLASSES_ROOT, HKEY_USERS, HKEY_CURRENT_CONFIG)",
                    "enum": ["HKEY_CURRENT_USER", "HKEY_LOCAL_MACHINE", "HKEY_CLASSES_ROOT", "HKEY_USERS", "HKEY_CURRENT_CONFIG"]
                },
                "path": {
                    "type": "string",
                    "description": "Registry key path (e.g., 'Software\\Microsoft\\Windows\\CurrentVersion')"
                },
                "value_name": {
                    "type": "string",
                    "description": "Name of the value to read (empty string for default value)"
                }
            },
            "required": ["hive", "path", "value_name"]
        }
    
    async def execute(self, **kwargs) -> str:
        """Execute registry read operation."""
        self.validate_params(**kwargs)
        
        hive_name = kwargs["hive"]
        path = kwargs["path"]
        value_name = kwargs["value_name"]
        
        # Map hive names to winreg constants
        hive_map = {
            "HKEY_CURRENT_USER": winreg.HKEY_CURRENT_USER,
            "HKEY_LOCAL_MACHINE": winreg.HKEY_LOCAL_MACHINE,
            "HKEY_CLASSES_ROOT": winreg.HKEY_CLASSES_ROOT,
            "HKEY_USERS": winreg.HKEY_USERS,
            "HKEY_CURRENT_CONFIG": winreg.HKEY_CURRENT_CONFIG
        }
        
        hive = hive_map.get(hive_name)
        if hive is None:
            return f"Error: Invalid hive '{hive_name}'"
        
        try:
            key = winreg.OpenKey(hive, path, 0, winreg.KEY_READ)
            try:
                value_data, value_type = winreg.QueryValueEx(key, value_name)
                
                # Map type codes to readable names
                type_names = {
                    winreg.REG_SZ: "REG_SZ",
                    winreg.REG_EXPAND_SZ: "REG_EXPAND_SZ",
                    winreg.REG_BINARY: "REG_BINARY",
                    winreg.REG_DWORD: "REG_DWORD",
                    winreg.REG_QWORD: "REG_QWORD",
                    winreg.REG_MULTI_SZ: "REG_MULTI_SZ"
                }
                
                type_name = type_names.get(value_type, f"Unknown({value_type})")
                
                logger.info(f"Read registry value: {hive_name}\\{path}\\{value_name}")
                return f"Value: {value_data}\nType: {type_name}"
            finally:
                winreg.CloseKey(key)
        except FileNotFoundError:
            return f"Error: Registry key or value not found: {hive_name}\\{path}\\{value_name}"
        except PermissionError:
            return f"Error: Permission denied accessing: {hive_name}\\{path}"
        except Exception as e:
            logger.error(f"Registry read error: {e}")
            return f"Error reading registry: {str(e)}"


class WriteRegistryKeyTool(BaseTool):
    """Tool to write Windows registry key values."""
    
    @property
    def name(self) -> str:
        return "write_registry_key"
    
    @property
    def description(self) -> str:
        return "Write a value to the Windows registry (use with caution)"
    
    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "hive": {
                    "type": "string",
                    "description": "Registry hive",
                    "enum": ["HKEY_CURRENT_USER", "HKEY_LOCAL_MACHINE", "HKEY_CLASSES_ROOT", "HKEY_USERS", "HKEY_CURRENT_CONFIG"]
                },
                "path": {
                    "type": "string",
                    "description": "Registry key path"
                },
                "value_name": {
                    "type": "string",
                    "description": "Name of the value to write"
                },
                "value_data": {
                    "description": "Data to write (string, integer, or list for REG_MULTI_SZ)"
                },
                "value_type": {
                    "type": "string",
                    "description": "Registry value type",
                    "enum": ["REG_SZ", "REG_EXPAND_SZ", "REG_DWORD", "REG_QWORD", "REG_MULTI_SZ"],
                    "default": "REG_SZ"
                }
            },
            "required": ["hive", "path", "value_name", "value_data"]
        }
    
    async def execute(self, **kwargs) -> str:
        """Execute registry write operation."""
        self.validate_params(**kwargs)
        
        hive_name = kwargs["hive"]
        path = kwargs["path"]
        value_name = kwargs["value_name"]
        value_data = kwargs["value_data"]
        value_type_name = kwargs.get("value_type", "REG_SZ")
        
        # Safety check: prevent modification of critical system keys
        critical_paths = [
            "SYSTEM\\CurrentControlSet",
            "SOFTWARE\\Microsoft\\Windows NT\\CurrentVersion\\Winlogon",
            "SYSTEM\\ControlSet"
        ]
        
        if hive_name == "HKEY_LOCAL_MACHINE":
            for critical_path in critical_paths:
                if path.upper().startswith(critical_path.upper()):
                    return f"Error: Modification of critical system registry path is not allowed: {path}"
        
        # Map hive and type names
        hive_map = {
            "HKEY_CURRENT_USER": winreg.HKEY_CURRENT_USER,
            "HKEY_LOCAL_MACHINE": winreg.HKEY_LOCAL_MACHINE,
            "HKEY_CLASSES_ROOT": winreg.HKEY_CLASSES_ROOT,
            "HKEY_USERS": winreg.HKEY_USERS,
            "HKEY_CURRENT_CONFIG": winreg.HKEY_CURRENT_CONFIG
        }
        
        type_map = {
            "REG_SZ": winreg.REG_SZ,
            "REG_EXPAND_SZ": winreg.REG_EXPAND_SZ,
            "REG_DWORD": winreg.REG_DWORD,
            "REG_QWORD": winreg.REG_QWORD,
            "REG_MULTI_SZ": winreg.REG_MULTI_SZ
        }
        
        hive = hive_map.get(hive_name)
        value_type = type_map.get(value_type_name)
        
        if hive is None or value_type is None:
            return f"Error: Invalid hive or type"
        
        try:
            key = winreg.CreateKey(hive, path)
            try:
                winreg.SetValueEx(key, value_name, 0, value_type, value_data)
                logger.info(f"Wrote registry value: {hive_name}\\{path}\\{value_name}")
                return f"Successfully wrote registry value: {hive_name}\\{path}\\{value_name}"
            finally:
                winreg.CloseKey(key)
        except PermissionError:
            return f"Error: Permission denied. Administrator privileges may be required."
        except Exception as e:
            logger.error(f"Registry write error: {e}")
            return f"Error writing registry: {str(e)}"


class DeleteRegistryKeyTool(BaseTool):
    """Tool to delete Windows registry keys or values."""
    
    @property
    def name(self) -> str:
        return "delete_registry_key"
    
    @property
    def description(self) -> str:
        return "Delete a Windows registry key or value (use with extreme caution)"
    
    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "hive": {
                    "type": "string",
                    "description": "Registry hive",
                    "enum": ["HKEY_CURRENT_USER", "HKEY_LOCAL_MACHINE", "HKEY_CLASSES_ROOT", "HKEY_USERS", "HKEY_CURRENT_CONFIG"]
                },
                "path": {
                    "type": "string",
                    "description": "Registry key path"
                },
                "value_name": {
                    "type": "string",
                    "description": "Name of the value to delete (omit to delete entire key)"
                }
            },
            "required": ["hive", "path"]
        }
    
    async def execute(self, **kwargs) -> str:
        """Execute registry delete operation."""
        self.validate_params(**kwargs)
        
        hive_name = kwargs["hive"]
        path = kwargs["path"]
        value_name = kwargs.get("value_name")
        
        # Safety check
        critical_paths = [
            "SYSTEM\\CurrentControlSet",
            "SOFTWARE\\Microsoft\\Windows NT\\CurrentVersion\\Winlogon",
            "SYSTEM\\ControlSet"
        ]
        
        if hive_name == "HKEY_LOCAL_MACHINE":
            for critical_path in critical_paths:
                if path.upper().startswith(critical_path.upper()):
                    return f"Error: Deletion of critical system registry path is not allowed: {path}"
        
        hive_map = {
            "HKEY_CURRENT_USER": winreg.HKEY_CURRENT_USER,
            "HKEY_LOCAL_MACHINE": winreg.HKEY_LOCAL_MACHINE,
            "HKEY_CLASSES_ROOT": winreg.HKEY_CLASSES_ROOT,
            "HKEY_USERS": winreg.HKEY_USERS,
            "HKEY_CURRENT_CONFIG": winreg.HKEY_CURRENT_CONFIG
        }
        
        hive = hive_map.get(hive_name)
        if hive is None:
            return f"Error: Invalid hive '{hive_name}'"
        
        try:
            if value_name:
                # Delete value
                key = winreg.OpenKey(hive, path, 0, winreg.KEY_SET_VALUE)
                try:
                    winreg.DeleteValue(key, value_name)
                    logger.info(f"Deleted registry value: {hive_name}\\{path}\\{value_name}")
                    return f"Successfully deleted registry value: {hive_name}\\{path}\\{value_name}"
                finally:
                    winreg.CloseKey(key)
            else:
                # Delete key
                winreg.DeleteKey(hive, path)
                logger.info(f"Deleted registry key: {hive_name}\\{path}")
                return f"Successfully deleted registry key: {hive_name}\\{path}"
        except FileNotFoundError:
            return f"Error: Registry key or value not found"
        except PermissionError:
            return f"Error: Permission denied. Administrator privileges may be required."
        except Exception as e:
            logger.error(f"Registry delete error: {e}")
            return f"Error deleting registry: {str(e)}"


class WindowsShutdownTool(BaseTool):
    """Tool to shutdown, restart, or logoff Windows."""
    
    @property
    def name(self) -> str:
        return "windows_shutdown"
    
    @property
    def description(self) -> str:
        return "Shutdown, restart, or logoff Windows system"
    
    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "description": "Action to perform",
                    "enum": ["shutdown", "restart", "logoff"]
                },
                "force": {
                    "type": "boolean",
                    "description": "Force close applications without saving",
                    "default": False
                },
                "timeout": {
                    "type": "integer",
                    "description": "Timeout in seconds before action",
                    "default": 30,
                    "minimum": 0
                }
            },
            "required": ["action"]
        }
    
    async def execute(self, **kwargs) -> str:
        """Execute shutdown operation."""
        self.validate_params(**kwargs)
        
        action = kwargs["action"]
        force = kwargs.get("force", False)
        timeout = kwargs.get("timeout", 30)
        
        try:
            # Use shutdown command for better control
            cmd = ["shutdown"]
            
            if action == "shutdown":
                cmd.append("/s")
            elif action == "restart":
                cmd.append("/r")
            elif action == "logoff":
                cmd.append("/l")
            
            if force:
                cmd.append("/f")
            
            cmd.extend(["/t", str(timeout)])
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                logger.info(f"Initiated Windows {action} with {timeout}s timeout")
                return f"Successfully initiated {action}. System will {action} in {timeout} seconds."
            else:
                return f"Error: {result.stderr}"
        except Exception as e:
            logger.error(f"Shutdown error: {e}")
            return f"Error executing shutdown: {str(e)}"


class WindowsVolumeControlTool(BaseTool):
    """Tool to control Windows system volume."""
    
    @property
    def name(self) -> str:
        return "windows_volume_control"
    
    @property
    def description(self) -> str:
        return "Control Windows system volume (requires pycaw library for full functionality)"
    
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
        """Execute volume control operation."""
        self.validate_params(**kwargs)
        
        action = kwargs["action"]
        level = kwargs.get("level")
        
        try:
            # Try to use pycaw if available
            from comtypes import CLSCTX_ALL
            from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
            
            devices = AudioUtilities.GetSpeakers()
            interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
            volume = interface.QueryInterface(IAudioEndpointVolume)
            
            if action == "set":
                if level is None:
                    return "Error: 'level' parameter required for 'set' action"
                volume.SetMasterVolumeLevelScalar(level / 100.0, None)
                logger.info(f"Set volume to {level}%")
                return f"Volume set to {level}%"
            
            elif action == "increase":
                current = volume.GetMasterVolumeLevelScalar() * 100
                new_level = min(100, current + 10)
                volume.SetMasterVolumeLevelScalar(new_level / 100.0, None)
                return f"Volume increased to {new_level:.0f}%"
            
            elif action == "decrease":
                current = volume.GetMasterVolumeLevelScalar() * 100
                new_level = max(0, current - 10)
                volume.SetMasterVolumeLevelScalar(new_level / 100.0, None)
                return f"Volume decreased to {new_level:.0f}%"
            
            elif action == "mute":
                volume.SetMute(1, None)
                return "Volume muted"
            
            elif action == "unmute":
                volume.SetMute(0, None)
                return "Volume unmuted"
            
            elif action == "get":
                current = volume.GetMasterVolumeLevelScalar() * 100
                muted = volume.GetMute()
                return f"Current volume: {current:.0f}% (Muted: {bool(muted)})"
            
        except ImportError:
            return "Error: pycaw library not installed. Install with: pip install pycaw"
        except Exception as e:
            logger.error(f"Volume control error: {e}")
            return f"Error controlling volume: {str(e)}"


class WindowsServiceControlTool(BaseTool):
    """Tool to manage Windows services."""
    
    @property
    def name(self) -> str:
        return "windows_service_control"
    
    @property
    def description(self) -> str:
        return "Manage Windows services (may require administrator privileges)"
    
    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "service_name": {
                    "type": "string",
                    "description": "Name of the Windows service"
                },
                "action": {
                    "type": "string",
                    "description": "Action to perform",
                    "enum": ["start", "stop", "restart", "status"]
                }
            },
            "required": ["service_name", "action"]
        }
    
    async def execute(self, **kwargs) -> str:
        """Execute service control operation."""
        self.validate_params(**kwargs)
        
        service_name = kwargs["service_name"]
        action = kwargs["action"]
        
        try:
            if action == "status":
                result = subprocess.run(
                    ["sc", "query", service_name],
                    capture_output=True,
                    text=True
                )
                if result.returncode == 0:
                    return result.stdout
                else:
                    return f"Error querying service: {result.stderr}"
            
            elif action in ["start", "stop"]:
                result = subprocess.run(
                    ["sc", action, service_name],
                    capture_output=True,
                    text=True
                )
                if result.returncode == 0:
                    logger.info(f"Service {service_name} {action}ed")
                    return f"Successfully {action}ed service: {service_name}"
                else:
                    return f"Error: {result.stderr}\nNote: Administrator privileges may be required."
            
            elif action == "restart":
                # Stop then start
                stop_result = subprocess.run(
                    ["sc", "stop", service_name],
                    capture_output=True,
                    text=True
                )
                if stop_result.returncode != 0:
                    return f"Error stopping service: {stop_result.stderr}"
                
                # Wait a moment
                import asyncio
                await asyncio.sleep(2)
                
                start_result = subprocess.run(
                    ["sc", "start", service_name],
                    capture_output=True,
                    text=True
                )
                if start_result.returncode == 0:
                    logger.info(f"Service {service_name} restarted")
                    return f"Successfully restarted service: {service_name}"
                else:
                    return f"Error starting service: {start_result.stderr}"
        
        except Exception as e:
            logger.error(f"Service control error: {e}")
            return f"Error controlling service: {str(e)}"


class GetEnvironmentVariableTool(BaseTool):
    """Tool to read environment variables."""
    
    @property
    def name(self) -> str:
        return "get_environment_variable"
    
    @property
    def description(self) -> str:
        return "Read Windows environment variable"
    
    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "variable_name": {
                    "type": "string",
                    "description": "Name of the environment variable"
                },
                "scope": {
                    "type": "string",
                    "description": "Variable scope (user or system)",
                    "enum": ["user", "system"],
                    "default": "user"
                }
            },
            "required": ["variable_name"]
        }
    
    async def execute(self, **kwargs) -> str:
        """Execute environment variable read."""
        self.validate_params(**kwargs)
        
        variable_name = kwargs["variable_name"]
        scope = kwargs.get("scope", "user")
        
        # First try current process environment
        value = os.environ.get(variable_name)
        if value is not None:
            return f"{variable_name}={value}"
        
        # Try reading from registry for persistent variables
        try:
            if scope == "user":
                key = winreg.OpenKey(
                    winreg.HKEY_CURRENT_USER,
                    "Environment",
                    0,
                    winreg.KEY_READ
                )
            else:
                key = winreg.OpenKey(
                    winreg.HKEY_LOCAL_MACHINE,
                    "SYSTEM\\CurrentControlSet\\Control\\Session Manager\\Environment",
                    0,
                    winreg.KEY_READ
                )
            
            try:
                value, _ = winreg.QueryValueEx(key, variable_name)
                return f"{variable_name}={value}"
            finally:
                winreg.CloseKey(key)
        except FileNotFoundError:
            return f"Environment variable '{variable_name}' not found in {scope} scope"
        except Exception as e:
            return f"Error reading environment variable: {str(e)}"


class SetEnvironmentVariableTool(BaseTool):
    """Tool to set environment variables."""
    
    @property
    def name(self) -> str:
        return "set_environment_variable"
    
    @property
    def description(self) -> str:
        return "Set Windows environment variable (requires admin for system scope)"
    
    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "variable_name": {
                    "type": "string",
                    "description": "Name of the environment variable"
                },
                "value": {
                    "type": "string",
                    "description": "Value to set"
                },
                "scope": {
                    "type": "string",
                    "description": "Variable scope (user or system)",
                    "enum": ["user", "system"],
                    "default": "user"
                }
            },
            "required": ["variable_name", "value"]
        }
    
    async def execute(self, **kwargs) -> str:
        """Execute environment variable write."""
        self.validate_params(**kwargs)
        
        variable_name = kwargs["variable_name"]
        value = kwargs["value"]
        scope = kwargs.get("scope", "user")
        
        try:
            if scope == "user":
                key = winreg.OpenKey(
                    winreg.HKEY_CURRENT_USER,
                    "Environment",
                    0,
                    winreg.KEY_SET_VALUE
                )
            else:
                key = winreg.OpenKey(
                    winreg.HKEY_LOCAL_MACHINE,
                    "SYSTEM\\CurrentControlSet\\Control\\Session Manager\\Environment",
                    0,
                    winreg.KEY_SET_VALUE
                )
            
            try:
                winreg.SetValueEx(key, variable_name, 0, winreg.REG_EXPAND_SZ, value)
                logger.info(f"Set environment variable: {variable_name} ({scope})")
                return f"Successfully set {variable_name}={value} in {scope} scope"
            finally:
                winreg.CloseKey(key)
        except PermissionError:
            return f"Error: Permission denied. Administrator privileges required for system scope."
        except Exception as e:
            logger.error(f"Environment variable write error: {e}")
            return f"Error setting environment variable: {str(e)}"


def register_windows_tools():
    """Register all Windows-specific tools."""
    registry = get_tool_registry()
    tools = [
        ReadRegistryKeyTool(),
        WriteRegistryKeyTool(),
        DeleteRegistryKeyTool(),
        WindowsShutdownTool(),
        WindowsVolumeControlTool(),
        WindowsServiceControlTool(),
        GetEnvironmentVariableTool(),
        SetEnvironmentVariableTool()
    ]
    for tool in tools:
        try:
            registry.register(tool)
            logger.info(f"Registered Windows tool: {tool.name}")
        except ValueError as e:
            logger.warning(f"Failed to register tool: {e}")
