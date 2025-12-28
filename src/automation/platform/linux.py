"""Linux-specific automation tools.

This module provides Linux-specific system operations using subprocess and systemd.
"""

import subprocess
import logging
import os
from typing import Any, Dict, List

from src.agent.tool_registry import BaseTool, get_tool_registry

logger = logging.getLogger(__name__)


class LinuxServiceControlTool(BaseTool):
    """Tool to manage systemd services."""
    
    @property
    def name(self) -> str:
        return "linux_service_control"
    
    @property
    def description(self) -> str:
        return "Manage Linux systemd services (may require sudo privileges)"
    
    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "service_name": {
                    "type": "string",
                    "description": "Name of the systemd service"
                },
                "action": {
                    "type": "string",
                    "description": "Action to perform",
                    "enum": ["start", "stop", "restart", "enable", "disable", "status"]
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
            result = subprocess.run(
                ["systemctl", action, service_name],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                logger.info(f"Service {service_name} {action}ed successfully")
                return f"Successfully {action}ed service: {service_name}\n{result.stdout}"
            else:
                error_msg = result.stderr.strip()
                if "Permission denied" in error_msg or "access denied" in error_msg.lower():
                    return f"Error: Permission denied. Try running with sudo privileges.\n{error_msg}"
                return f"Error {action}ing service: {error_msg}"
        
        except subprocess.TimeoutExpired:
            return f"Error: Command timed out after 30 seconds"
        except FileNotFoundError:
            return "Error: systemctl command not found. This tool requires systemd."
        except Exception as e:
            logger.error(f"Service control error: {e}")
            return f"Error controlling service: {str(e)}"


class LinuxServiceStatusTool(BaseTool):
    """Tool to get detailed systemd service status."""
    
    @property
    def name(self) -> str:
        return "linux_service_status"
    
    @property
    def description(self) -> str:
        return "Get detailed status information for a Linux systemd service"
    
    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "service_name": {
                    "type": "string",
                    "description": "Name of the systemd service"
                }
            },
            "required": ["service_name"]
        }
    
    async def execute(self, **kwargs) -> str:
        """Execute service status query."""
        self.validate_params(**kwargs)
        
        service_name = kwargs["service_name"]
        
        try:
            result = subprocess.run(
                ["systemctl", "status", service_name, "--no-pager"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            # systemctl status returns non-zero for inactive services, but still provides info
            return result.stdout if result.stdout else result.stderr
        
        except subprocess.TimeoutExpired:
            return f"Error: Command timed out"
        except FileNotFoundError:
            return "Error: systemctl command not found"
        except Exception as e:
            logger.error(f"Service status error: {e}")
            return f"Error getting service status: {str(e)}"


class LinuxPackageManagerTool(BaseTool):
    """Tool to query installed packages (read-only)."""
    
    @property
    def name(self) -> str:
        return "linux_package_manager"
    
    @property
    def description(self) -> str:
        return "Query installed Linux packages (read-only, no install/remove)"
    
    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "description": "Action to perform",
                    "enum": ["list", "search", "info"]
                },
                "package_name": {
                    "type": "string",
                    "description": "Package name (required for 'search' and 'info' actions)"
                }
            },
            "required": ["action"]
        }
    
    def _detect_package_manager(self) -> tuple[str, List[str]]:
        """Detect available package manager and return command template."""
        managers = {
            "apt": (["dpkg", "-l"], ["apt", "search"], ["apt", "show"]),
            "yum": (["yum", "list", "installed"], ["yum", "search"], ["yum", "info"]),
            "dnf": (["dnf", "list", "installed"], ["dnf", "search"], ["dnf", "info"]),
            "pacman": (["pacman", "-Q"], ["pacman", "-Ss"], ["pacman", "-Si"]),
            "zypper": (["zypper", "se", "--installed-only"], ["zypper", "se"], ["zypper", "info"])
        }
        
        for pm, commands in managers.items():
            try:
                # Check if package manager exists
                subprocess.run([pm, "--version"], capture_output=True, timeout=5)
                return pm, commands
            except (FileNotFoundError, subprocess.TimeoutExpired):
                continue
        
        return None, None
    
    async def execute(self, **kwargs) -> str:
        """Execute package query operation."""
        self.validate_params(**kwargs)
        
        action = kwargs["action"]
        package_name = kwargs.get("package_name")
        
        if action in ["search", "info"] and not package_name:
            return f"Error: 'package_name' parameter required for '{action}' action"
        
        pm, commands = self._detect_package_manager()
        if not pm:
            return "Error: No supported package manager found (apt, yum, dnf, pacman, zypper)"
        
        try:
            if action == "list":
                cmd = commands[0]
            elif action == "search":
                cmd = commands[1] + [package_name]
            elif action == "info":
                cmd = commands[2] + [package_name]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                output = result.stdout
                # Limit output length
                if len(output) > 5000:
                    output = output[:5000] + "\n... (output truncated)"
                return output
            else:
                return f"Error: {result.stderr}"
        
        except subprocess.TimeoutExpired:
            return "Error: Command timed out"
        except Exception as e:
            logger.error(f"Package manager error: {e}")
            return f"Error querying packages: {str(e)}"


class LinuxSystemInfoTool(BaseTool):
    """Tool to get Linux system information."""
    
    @property
    def name(self) -> str:
        return "linux_system_info"
    
    @property
    def description(self) -> str:
        return "Get comprehensive Linux system information"
    
    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "info_type": {
                    "type": "string",
                    "description": "Type of information to retrieve",
                    "enum": ["all", "os", "kernel", "cpu", "memory", "disk"],
                    "default": "all"
                }
            }
        }
    
    async def execute(self, **kwargs) -> str:
        """Execute system info query."""
        self.validate_params(**kwargs)
        
        info_type = kwargs.get("info_type", "all")
        info_parts = []
        
        try:
            if info_type in ["all", "os"]:
                # OS information
                try:
                    result = subprocess.run(
                        ["lsb_release", "-a"],
                        capture_output=True,
                        text=True,
                        timeout=5
                    )
                    if result.returncode == 0:
                        info_parts.append(f"OS Information:\n{result.stdout}")
                except FileNotFoundError:
                    # Fallback to /etc/os-release
                    try:
                        with open("/etc/os-release", "r") as f:
                            info_parts.append(f"OS Information:\n{f.read()}")
                    except:
                        pass
            
            if info_type in ["all", "kernel"]:
                # Kernel information
                result = subprocess.run(
                    ["uname", "-a"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0:
                    info_parts.append(f"Kernel:\n{result.stdout}")
            
            if info_type in ["all", "cpu"]:
                # CPU information
                try:
                    with open("/proc/cpuinfo", "r") as f:
                        cpu_lines = [line for line in f if line.startswith("model name")]
                        if cpu_lines:
                            info_parts.append(f"CPU:\n{cpu_lines[0]}")
                except:
                    pass
            
            if info_type in ["all", "memory"]:
                # Memory information
                result = subprocess.run(
                    ["free", "-h"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0:
                    info_parts.append(f"Memory:\n{result.stdout}")
            
            if info_type in ["all", "disk"]:
                # Disk usage
                result = subprocess.run(
                    ["df", "-h"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0:
                    info_parts.append(f"Disk Usage:\n{result.stdout}")
            
            if info_parts:
                return "\n\n".join(info_parts)
            else:
                return "Error: Could not retrieve system information"
        
        except Exception as e:
            logger.error(f"System info error: {e}")
            return f"Error getting system info: {str(e)}"


class LinuxKillProcessTool(BaseTool):
    """Tool to terminate Linux processes with signals."""
    
    @property
    def name(self) -> str:
        return "linux_kill_process"
    
    @property
    def description(self) -> str:
        return "Terminate a Linux process using signals"
    
    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "pid": {
                    "type": "integer",
                    "description": "Process ID to terminate"
                },
                "signal": {
                    "type": "string",
                    "description": "Signal to send",
                    "enum": ["SIGTERM", "SIGKILL", "SIGHUP", "SIGINT"],
                    "default": "SIGTERM"
                }
            },
            "required": ["pid"]
        }
    
    async def execute(self, **kwargs) -> str:
        """Execute process termination."""
        self.validate_params(**kwargs)
        
        pid = kwargs["pid"]
        signal = kwargs.get("signal", "SIGTERM")
        
        try:
            result = subprocess.run(
                ["kill", f"-{signal}", str(pid)],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                logger.info(f"Sent {signal} to process {pid}")
                return f"Successfully sent {signal} to process {pid}"
            else:
                error_msg = result.stderr.strip()
                if "No such process" in error_msg:
                    return f"Error: Process {pid} not found"
                elif "Permission denied" in error_msg:
                    return f"Error: Permission denied. Try with sudo."
                return f"Error: {error_msg}"
        
        except subprocess.TimeoutExpired:
            return "Error: Command timed out"
        except Exception as e:
            logger.error(f"Kill process error: {e}")
            return f"Error terminating process: {str(e)}"


class LinuxShutdownTool(BaseTool):
    """Tool to shutdown or reboot Linux system."""
    
    @property
    def name(self) -> str:
        return "linux_shutdown"
    
    @property
    def description(self) -> str:
        return "Shutdown or reboot Linux system (requires sudo privileges)"
    
    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "description": "Action to perform",
                    "enum": ["shutdown", "reboot"]
                },
                "delay": {
                    "type": "integer",
                    "description": "Delay in minutes before action",
                    "default": 1,
                    "minimum": 0
                },
                "message": {
                    "type": "string",
                    "description": "Message to display to users",
                    "default": "System is shutting down"
                }
            },
            "required": ["action"]
        }
    
    async def execute(self, **kwargs) -> str:
        """Execute shutdown operation."""
        self.validate_params(**kwargs)
        
        action = kwargs["action"]
        delay = kwargs.get("delay", 1)
        message = kwargs.get("message", "System is shutting down")
        
        try:
            if action == "shutdown":
                cmd = ["shutdown", "-h", f"+{delay}", message]
            elif action == "reboot":
                cmd = ["shutdown", "-r", f"+{delay}", message]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                logger.info(f"Initiated {action} with {delay} minute delay")
                return f"Successfully initiated {action}. System will {action} in {delay} minute(s)."
            else:
                error_msg = result.stderr.strip()
                if "Permission denied" in error_msg:
                    return "Error: Permission denied. Sudo privileges required."
                return f"Error: {error_msg}"
        
        except subprocess.TimeoutExpired:
            return "Error: Command timed out"
        except Exception as e:
            logger.error(f"Shutdown error: {e}")
            return f"Error executing shutdown: {str(e)}"


class LinuxMountInfoTool(BaseTool):
    """Tool to list mounted filesystems."""
    
    @property
    def name(self) -> str:
        return "linux_mount_info"
    
    @property
    def description(self) -> str:
        return "List mounted filesystems on Linux"
    
    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {}
        }
    
    async def execute(self, **kwargs) -> str:
        """Execute mount info query."""
        self.validate_params(**kwargs)
        
        try:
            # Try using mount command
            result = subprocess.run(
                ["mount"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                return result.stdout
            
            # Fallback to /proc/mounts
            try:
                with open("/proc/mounts", "r") as f:
                    return f.read()
            except:
                return "Error: Could not read mount information"
        
        except subprocess.TimeoutExpired:
            return "Error: Command timed out"
        except Exception as e:
            logger.error(f"Mount info error: {e}")
            return f"Error getting mount info: {str(e)}"


class LinuxDiskUsageTool(BaseTool):
    """Tool to get disk usage statistics."""
    
    @property
    def name(self) -> str:
        return "linux_disk_usage"
    
    @property
    def description(self) -> str:
        return "Get disk usage statistics for Linux filesystems"
    
    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Specific path to check (optional, defaults to all filesystems)"
                }
            }
        }
    
    async def execute(self, **kwargs) -> str:
        """Execute disk usage query."""
        self.validate_params(**kwargs)
        
        path = kwargs.get("path")
        
        try:
            cmd = ["df", "-h"]
            if path:
                cmd.append(path)
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                return result.stdout
            else:
                return f"Error: {result.stderr}"
        
        except subprocess.TimeoutExpired:
            return "Error: Command timed out"
        except Exception as e:
            logger.error(f"Disk usage error: {e}")
            return f"Error getting disk usage: {str(e)}"


def register_linux_tools():
    """Register all Linux-specific tools."""
    registry = get_tool_registry()
    tools = [
        LinuxServiceControlTool(),
        LinuxServiceStatusTool(),
        LinuxPackageManagerTool(),
        LinuxSystemInfoTool(),
        LinuxKillProcessTool(),
        LinuxShutdownTool(),
        LinuxMountInfoTool(),
        LinuxDiskUsageTool()
    ]
    for tool in tools:
        try:
            registry.register(tool)
            logger.info(f"Registered Linux tool: {tool.name}")
        except ValueError as e:
            logger.warning(f"Failed to register tool: {e}")
