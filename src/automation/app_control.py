"""
Application control and web browsing tools for the Computer Manager agent.

This module provides tools for process management (launching, listing, killing processes)
and web browsing automation (opening URLs, searching the web).
"""

import logging
import subprocess
import sys
import time
import webbrowser
from typing import Any, Dict
from urllib.parse import urlparse, quote_plus

import psutil

from src.agent.tool_registry import BaseTool, get_tool_registry

logger = logging.getLogger(__name__)


class LaunchApplicationTool(BaseTool):
    """Tool for launching applications."""

    @property
    def name(self) -> str:
        return "launch_application"

    @property
    def description(self) -> str:
        return (
            "Launch an application or executable. Supports common applications "
            "(notepad, calculator, etc.) and custom executables with arguments. "
            "Returns process ID and success message."
        )

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "application": {
                    "type": "string",
                    "description": "Application name or path to executable"
                },
                "arguments": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional command-line arguments",
                    "default": []
                }
            },
            "required": ["application"]
        }

    async def execute(self, **kwargs) -> str:
        """Execute the launch application operation."""
        try:
            # Validate parameters early
            self.validate_params(**kwargs)
            
            application = kwargs.get("application")
            arguments = kwargs.get("arguments", [])

            if not application:
                return "Error: 'application' parameter is required"

            # Normalize arguments parameter
            if isinstance(arguments, str):
                # Wrap string in single-element list
                arguments = [arguments]
            elif not isinstance(arguments, list):
                return f"Error: 'arguments' must be a list of strings or a single string, got {type(arguments).__name__}"
            
            # Validate all elements are strings
            if not all(isinstance(arg, str) for arg in arguments):
                return "Error: All elements in 'arguments' list must be strings"

            # Build command
            cmd = [application] + arguments

            try:
                # Launch process
                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    creationflags=subprocess.CREATE_NEW_CONSOLE if sys.platform == "win32" else 0
                )

                logger.info(f"Launched application: {application} (PID: {process.pid})")
                return f"Success: Launched {application} with PID {process.pid}"

            except FileNotFoundError:
                return f"Error: Application not found: {application}"
            except PermissionError:
                return f"Error: Permission denied to launch: {application}"
            except OSError as e:
                return f"Error: Unable to launch application: {str(e)}"

        except Exception as e:
            logger.error(f"Error launching application: {str(e)}")
            return f"Error launching application: {str(e)}"


class ListProcessesTool(BaseTool):
    """Tool for listing running processes."""

    @property
    def name(self) -> str:
        return "list_processes"

    @property
    def description(self) -> str:
        return (
            "List all running processes or filter by name. "
            "Can include detailed information like memory usage and CPU percent. "
            "Returns list of processes with PID, name, and optional details."
        )

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "filter_name": {
                    "type": "string",
                    "description": "Optional: filter processes by name (case-insensitive)"
                },
                "include_details": {
                    "type": "boolean",
                    "description": "Include memory usage, CPU percent, and username (default: false)",
                    "default": False
                }
            },
            "required": []
        }

    async def execute(self, **kwargs) -> str:
        """Execute the list processes operation."""
        try:
            filter_name = kwargs.get("filter_name", "").lower()
            include_details = kwargs.get("include_details", False)

            processes = []
            attrs = ['pid', 'name', 'username', 'memory_info', 'cpu_percent']

            for proc in psutil.process_iter(attrs):
                try:
                    info = proc.info
                    proc_name = info['name'] or ""

                    # Apply filter if specified
                    if filter_name and filter_name not in proc_name.lower():
                        continue

                    process_info = {
                        "pid": info['pid'],
                        "name": proc_name
                    }

                    if include_details:
                        try:
                            process_info["username"] = info.get('username', 'N/A')
                            mem_info = info.get('memory_info')
                            if mem_info:
                                process_info["memory_mb"] = round(mem_info.rss / 1024 / 1024, 2)
                            process_info["cpu_percent"] = info.get('cpu_percent', 0.0)
                        except (psutil.AccessDenied, psutil.NoSuchProcess):
                            process_info["details"] = "Access denied"

                    processes.append(process_info)

                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

            # Calculate truncation metadata
            total_count = len(processes)
            returned_processes = processes[:100]  # Limit to 100 to prevent overwhelming output
            is_truncated = total_count > 100
            
            logger.info(f"Listed {total_count} processes (returning {len(returned_processes)})")
            
            import json
            return json.dumps({
                "count": total_count,
                "returned_count": len(returned_processes),
                "truncated": is_truncated,
                "processes": returned_processes
            }, indent=2)

        except Exception as e:
            logger.error(f"Error listing processes: {str(e)}")
            return f"Error listing processes: {str(e)}"


class KillProcessTool(BaseTool):
    """Tool for terminating processes."""

    @property
    def name(self) -> str:
        return "kill_process"

    @property
    def description(self) -> str:
        return (
            "Terminate a process by PID or name. Use with caution as this forcefully "
            "stops the process. Tries graceful termination first, then force kill if needed. "
            "Returns list of killed process IDs and names."
        )

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "pid": {
                    "type": "integer",
                    "description": "Process ID to kill"
                },
                "name": {
                    "type": "string",
                    "description": "Process name to kill (kills all matching processes)"
                }
            },
            "required": []
        }

    async def execute(self, **kwargs) -> str:
        """Execute the kill process operation."""
        try:
            pid = kwargs.get("pid")
            name = kwargs.get("name")

            if not pid and not name:
                return "Error: Either 'pid' or 'name' parameter is required"

            killed = []

            if pid:
                # Kill by PID
                try:
                    proc = psutil.Process(pid)
                    proc_name = proc.name()
                    
                    # Try graceful termination first
                    proc.terminate()
                    try:
                        proc.wait(timeout=3)
                    except psutil.TimeoutExpired:
                        # Force kill if still running
                        proc.kill()
                        proc.wait(timeout=1)

                    killed.append({"pid": pid, "name": proc_name})
                    logger.info(f"Killed process: {proc_name} (PID: {pid})")

                except psutil.NoSuchProcess:
                    return f"Error: No process found with PID {pid}"
                except psutil.AccessDenied:
                    return f"Error: Permission denied to kill process with PID {pid}"

            elif name:
                # Kill by name
                name_lower = name.lower()
                found = False

                for proc in psutil.process_iter(['pid', 'name']):
                    try:
                        if proc.info['name'] and name_lower in proc.info['name'].lower():
                            found = True
                            proc_pid = proc.info['pid']
                            proc_name = proc.info['name']

                            # Try graceful termination first
                            proc.terminate()
                            try:
                                proc.wait(timeout=3)
                            except psutil.TimeoutExpired:
                                # Force kill if still running
                                proc.kill()
                                proc.wait(timeout=1)

                            killed.append({"pid": proc_pid, "name": proc_name})
                            logger.info(f"Killed process: {proc_name} (PID: {proc_pid})")

                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue

                if not found:
                    return f"Error: No processes found matching name '{name}'"

            import json
            return json.dumps({
                "success": True,
                "killed_count": len(killed),
                "killed_processes": killed
            }, indent=2)

        except Exception as e:
            logger.error(f"Error killing process: {str(e)}")
            return f"Error killing process: {str(e)}"


class GetProcessInfoTool(BaseTool):
    """Tool for getting detailed process information."""

    @property
    def name(self) -> str:
        return "get_process_info"

    @property
    def description(self) -> str:
        return (
            "Get detailed information about a specific process by PID. "
            "Returns name, status, CPU percent, memory info, create time, "
            "executable path, and command line arguments."
        )

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "pid": {
                    "type": "integer",
                    "description": "Process ID to get information about"
                }
            },
            "required": ["pid"]
        }

    async def execute(self, **kwargs) -> str:
        """Execute the get process info operation."""
        try:
            pid = kwargs.get("pid")

            if not pid:
                return "Error: 'pid' parameter is required"

            try:
                proc = psutil.Process(pid)

                # Gather process information
                info = {
                    "pid": pid,
                    "name": proc.name(),
                    "status": proc.status(),
                    "create_time": proc.create_time(),
                }

                # Try to get additional info (may fail due to permissions)
                try:
                    info["username"] = proc.username()
                except (psutil.AccessDenied, psutil.NoSuchProcess):
                    info["username"] = "Access denied"

                try:
                    info["cpu_percent"] = proc.cpu_percent(interval=0.1)
                except (psutil.AccessDenied, psutil.NoSuchProcess):
                    info["cpu_percent"] = "Access denied"

                try:
                    mem_info = proc.memory_info()
                    info["memory_mb"] = round(mem_info.rss / 1024 / 1024, 2)
                    info["memory_percent"] = round(proc.memory_percent(), 2)
                except (psutil.AccessDenied, psutil.NoSuchProcess):
                    info["memory_mb"] = "Access denied"
                    info["memory_percent"] = "Access denied"

                try:
                    info["exe"] = proc.exe()
                except (psutil.AccessDenied, psutil.NoSuchProcess):
                    info["exe"] = "Access denied"

                try:
                    info["cmdline"] = " ".join(proc.cmdline())
                except (psutil.AccessDenied, psutil.NoSuchProcess):
                    info["cmdline"] = "Access denied"

                logger.info(f"Got process info for PID {pid}")
                
                import json
                return json.dumps(info, indent=2)

            except psutil.NoSuchProcess:
                return f"Error: No process found with PID {pid}"
            except psutil.AccessDenied:
                return f"Error: Permission denied to access process with PID {pid}"

        except Exception as e:
            logger.error(f"Error getting process info: {str(e)}")
            return f"Error getting process info: {str(e)}"


class OpenURLTool(BaseTool):
    """Tool for opening URLs in the default web browser."""

    @property
    def name(self) -> str:
        return "open_url"

    @property
    def description(self) -> str:
        return (
            "Open a URL in the default web browser. Can open in new window or new tab. "
            "Validates URL format before opening. Returns success message."
        )

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "URL to open (must include protocol, e.g., https://)"
                },
                "new_window": {
                    "type": "boolean",
                    "description": "Open in new window (default: false)",
                    "default": False
                },
                "new_tab": {
                    "type": "boolean",
                    "description": "Open in new tab (default: true)",
                    "default": True
                }
            },
            "required": ["url"]
        }

    async def execute(self, **kwargs) -> str:
        """Execute the open URL operation."""
        try:
            url = kwargs.get("url")
            new_window = kwargs.get("new_window", False)
            new_tab = kwargs.get("new_tab", True)

            if not url:
                return "Error: 'url' parameter is required"

            # Validate URL format
            try:
                parsed = urlparse(url)
                if not parsed.scheme:
                    return "Error: URL must include protocol (e.g., https://)"
                if not parsed.netloc:
                    return "Error: Invalid URL format"
            except Exception:
                return "Error: Invalid URL format"

            try:
                # Open URL based on preferences
                if new_window:
                    webbrowser.open_new(url)
                elif new_tab:
                    webbrowser.open_new_tab(url)
                else:
                    webbrowser.open(url)

                logger.info(f"Opened URL: {url}")
                return f"Success: Opened {url} in browser"

            except Exception as e:
                return f"Error: Unable to open URL: {str(e)}"

        except Exception as e:
            logger.error(f"Error opening URL: {str(e)}")
            return f"Error opening URL: {str(e)}"


class SearchWebTool(BaseTool):
    """Tool for searching the web."""

    @property
    def name(self) -> str:
        return "search_web"

    @property
    def description(self) -> str:
        return (
            "Search the web using a search engine (Google, Bing, or DuckDuckGo). "
            "Opens search results in the default browser. Returns success message with search URL."
        )

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query"
                },
                "engine": {
                    "type": "string",
                    "description": "Search engine to use (default: google)",
                    "enum": ["google", "bing", "duckduckgo"],
                    "default": "google"
                }
            },
            "required": ["query"]
        }

    async def execute(self, **kwargs) -> str:
        """Execute the search web operation."""
        try:
            query = kwargs.get("query")
            engine = kwargs.get("engine", "google").lower()

            if not query:
                return "Error: 'query' parameter is required"

            # Construct search URL based on engine
            encoded_query = quote_plus(query)
            
            search_urls = {
                "google": f"https://www.google.com/search?q={encoded_query}",
                "bing": f"https://www.bing.com/search?q={encoded_query}",
                "duckduckgo": f"https://duckduckgo.com/?q={encoded_query}"
            }

            if engine not in search_urls:
                return f"Error: Unknown search engine '{engine}'. Use google, bing, or duckduckgo."

            search_url = search_urls[engine]

            try:
                webbrowser.open_new_tab(search_url)
                logger.info(f"Searched {engine} for: {query}")
                return f"Success: Opened {engine} search for '{query}' ({search_url})"

            except Exception as e:
                return f"Error: Unable to open search: {str(e)}"

        except Exception as e:
            logger.error(f"Error searching web: {str(e)}")
            return f"Error searching web: {str(e)}"


def register_app_control_tools():
    """Register all application control and web tools with the global registry."""
    registry = get_tool_registry()
    tools = [
        LaunchApplicationTool(),
        ListProcessesTool(),
        KillProcessTool(),
        GetProcessInfoTool(),
        OpenURLTool(),
        SearchWebTool()
    ]
    for tool in tools:
        try:
            registry.register(tool)
            logger.info(f"Registered app control tool: {tool.name}")
        except ValueError as e:
            logger.warning(f"Failed to register tool: {e}")
