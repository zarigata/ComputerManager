"""
Permission management system for Computer Manager.

Handles permission levels, privilege elevation, and tool access control.
"""

import os
import sys
import platform
import subprocess
from enum import Enum
from typing import Dict, Optional
from pathlib import Path


class PermissionLevel(Enum):
    """Permission levels for tool execution."""
    BASIC = "basic"
    ADVANCED = "advanced"
    ADMIN = "admin"


class PermissionManager:
    """
    Manages permission levels and privilege elevation.
    
    Provides platform-specific admin detection and elevation,
    and enforces permission requirements for tools.
    """
    
    # Tool permission mappings
    TOOL_PERMISSIONS: Dict[str, PermissionLevel] = {
        # BASIC level tools - read-only operations
        'read_file': PermissionLevel.BASIC,
        'list_directory': PermissionLevel.BASIC,
        'search_files': PermissionLevel.BASIC,
        'get_file_info': PermissionLevel.BASIC,
        'list_processes': PermissionLevel.BASIC,
        'get_process_info': PermissionLevel.BASIC,
        'open_url': PermissionLevel.BASIC,
        'search_web': PermissionLevel.BASIC,
        'capture_screenshot': PermissionLevel.BASIC,
        'describe_screen': PermissionLevel.BASIC,
        'get_screen_size': PermissionLevel.BASIC,
        'get_pixel_color': PermissionLevel.BASIC,
        'locate_image_on_screen': PermissionLevel.BASIC,
        'get_system_info': PermissionLevel.BASIC,
        'echo': PermissionLevel.BASIC,
        'get_time': PermissionLevel.BASIC,
        
        # ADVANCED level tools - write operations and automation
        'write_file': PermissionLevel.ADVANCED,
        'move_file': PermissionLevel.ADVANCED,
        'launch_application': PermissionLevel.ADVANCED,
        'click_mouse': PermissionLevel.ADVANCED,
        'type_text': PermissionLevel.ADVANCED,
        'press_key': PermissionLevel.ADVANCED,
        'hotkey': PermissionLevel.ADVANCED,
        'drag_mouse': PermissionLevel.ADVANCED,
        'move_mouse': PermissionLevel.ADVANCED,
        'scroll_mouse': PermissionLevel.ADVANCED,
        'read_registry_key': PermissionLevel.ADVANCED,
        'get_environment_variable': PermissionLevel.ADVANCED,
        
        # ADMIN level tools - destructive/system operations
        'delete_file': PermissionLevel.ADMIN,
        'kill_process': PermissionLevel.ADMIN,
        'write_registry_key': PermissionLevel.ADMIN,
        'delete_registry_key': PermissionLevel.ADMIN,
        'windows_shutdown': PermissionLevel.ADMIN,
        'windows_service_control': PermissionLevel.ADMIN,
        'windows_volume_control': PermissionLevel.ADMIN,
        'set_environment_variable': PermissionLevel.ADMIN,
        'linux_systemd_control': PermissionLevel.ADMIN,
        'linux_service_control': PermissionLevel.ADMIN,
        'linux_service_status': PermissionLevel.ADMIN,
        'linux_package_manager': PermissionLevel.ADMIN,
        'macos_system_preferences': PermissionLevel.ADMIN,
        'macos_service_control': PermissionLevel.ADMIN,
    }
    
    def __init__(self, config):
        """
        Initialize permission manager.
        
        Args:
            config: AppConfig instance with permission_level setting
        """
        self.config = config
        self._current_level = self._parse_permission_level(config.permission_level)
        self._is_elevated = False
        
    def _parse_permission_level(self, level_str: str) -> PermissionLevel:
        """Parse permission level string to enum."""
        try:
            return PermissionLevel(level_str.lower())
        except ValueError:
            # Default to BASIC if invalid
            return PermissionLevel.BASIC
    
    def get_current_level(self) -> PermissionLevel:
        """Get current permission level."""
        return self._current_level
    
    def get_tool_permission_level(self, tool_name: str) -> PermissionLevel:
        """
        Get required permission level for a tool.
        
        Args:
            tool_name: Name of the tool
            
        Returns:
            Required PermissionLevel (defaults to ADVANCED if unknown)
        """
        return self.TOOL_PERMISSIONS.get(tool_name, PermissionLevel.ADVANCED)
    
    def check_permission(self, tool_name: str, required_level: Optional[PermissionLevel] = None) -> bool:
        """
        Check if current permission level allows tool execution.
        
        Args:
            tool_name: Name of the tool to check
            required_level: Optional override for required level
            
        Returns:
            True if permission granted, False otherwise
        """
        if required_level is None:
            required_level = self.get_tool_permission_level(tool_name)
        
        current = self._current_level
        
        # Permission hierarchy: ADMIN > ADVANCED > BASIC
        level_hierarchy = {
            PermissionLevel.BASIC: 0,
            PermissionLevel.ADVANCED: 1,
            PermissionLevel.ADMIN: 2,
        }
        
        return level_hierarchy[current] >= level_hierarchy[required_level]
    
    def is_admin(self) -> bool:
        """
        Check if running with administrator/root privileges.
        
        Returns:
            True if running as admin/root, False otherwise
        """
        system = platform.system()
        
        if system == "Windows":
            try:
                import pyuac
                return pyuac.isUserAdmin()
            except ImportError:
                # Fallback: try to access a protected registry key
                try:
                    import winreg
                    key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, 
                                        "SOFTWARE\\Microsoft\\Windows\\CurrentVersion",
                                        0, winreg.KEY_READ)
                    winreg.CloseKey(key)
                    return True
                except:
                    return False
        else:
            # Linux/macOS: check if effective user ID is 0 (root)
            return os.geteuid() == 0
    
    def request_elevation(self) -> bool:
        """
        Request privilege elevation (UAC/sudo prompt).
        
        Returns:
            True if elevation successful, False otherwise
        """
        if self.is_admin():
            self._is_elevated = True
            return True
        
        system = platform.system()
        
        try:
            if system == "Windows":
                return self._elevate_windows()
            elif system == "Linux":
                return self._elevate_linux()
            elif system == "Darwin":
                return self._elevate_macos()
            else:
                return False
        except Exception as e:
            print(f"Elevation failed: {e}")
            return False
    
    def _elevate_windows(self) -> bool:
        """
        Elevate privileges on Windows using UAC.
        
        This will restart the application with administrator privileges
        if not already running as admin.
        
        Returns:
            True if already elevated, False if elevation attempt was made
            (app will restart if successful)
        """
        try:
            import pyuac
            if pyuac.isUserAdmin():
                self._is_elevated = True
                return True
            
            # Show message to user about restart requirement
            print("\n" + "="*60)
            print("ADMINISTRATOR PRIVILEGES REQUIRED")
            print("="*60)
            print("This operation requires administrator privileges.")
            print("The application will now restart with elevated privileges.")
            print("Please approve the UAC prompt when it appears.")
            print("="*60 + "\n")
            
            # Restart with admin privileges
            # Note: This will exit the current process and restart elevated
            pyuac.runAsAdmin()
            
            # If we reach here, elevation was denied or failed
            return False
            
        except ImportError:
            print("Error: pyuac module not found. Please install it:")
            print("  pip install pyuac")
            return False
        except Exception as e:
            print(f"UAC elevation failed: {e}")
            return False
    
    def _elevate_linux(self) -> bool:
        """
        Elevate privileges on Linux using sudo.
        
        Returns:
            True if elevation successful, False otherwise
        """
        if os.geteuid() == 0:
            self._is_elevated = True
            return True
        
        try:
            # Check if sudo is available and user has sudo access
            result = subprocess.run(
                ['sudo', '-n', 'true'],
                capture_output=True,
                timeout=1
            )
            
            if result.returncode == 0:
                self._is_elevated = True
                return True
            
            # Try to validate sudo credentials (will prompt for password)
            result = subprocess.run(
                ['sudo', '-v'],
                capture_output=True,
                timeout=30
            )
            
            if result.returncode == 0:
                self._is_elevated = True
                return True
            
            return False
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False
    
    def _elevate_macos(self) -> bool:
        """
        Elevate privileges on macOS using osascript.
        
        Returns:
            True if elevation successful, False otherwise
        """
        if os.geteuid() == 0:
            self._is_elevated = True
            return True
        
        try:
            # Use osascript to show native macOS authentication dialog
            script = 'do shell script "sudo -v" with administrator privileges'
            result = subprocess.run(
                ['osascript', '-e', script],
                capture_output=True,
                timeout=30
            )
            
            if result.returncode == 0:
                self._is_elevated = True
                return True
            
            return False
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False
