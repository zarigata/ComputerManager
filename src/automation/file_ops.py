"""
File operation tools for the Computer Manager agent.

This module provides tools for file system operations including reading,
writing, deleting, moving, listing, searching, and getting file information.
"""

import json
import logging
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from src.agent.tool_registry import BaseTool, get_tool_registry

logger = logging.getLogger(__name__)


class ReadFileTool(BaseTool):
    """Tool for reading file contents."""

    @property
    def name(self) -> str:
        return "read_file"

    @property
    def description(self) -> str:
        return (
            "Read the contents of a file. Returns the file content as a string. "
            "Supports various text encodings. Use this when you need to view file contents."
        )

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path to the file to read (absolute or relative)"
                },
                "encoding": {
                    "type": "string",
                    "description": "File encoding (default: utf-8)",
                    "default": "utf-8"
                }
            },
            "required": ["path"]
        }

    async def execute(self, **kwargs) -> str:
        """Execute the read file operation."""
        try:
            path_str = kwargs.get("path")
            encoding = kwargs.get("encoding", "utf-8")

            if not path_str:
                return "Error: 'path' parameter is required"

            file_path = Path(path_str).resolve()

            if not file_path.exists():
                return f"Error: File not found: {file_path}"

            if not file_path.is_file():
                return f"Error: Path is not a file: {file_path}"

            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    content = f.read()
                logger.info(f"Read file: {file_path} ({len(content)} characters)")
                return content
            except UnicodeDecodeError as e:
                return f"Error: Unable to decode file with encoding '{encoding}': {str(e)}"
            except PermissionError:
                return f"Error: Permission denied to read file: {file_path}"

        except Exception as e:
            logger.error(f"Error reading file: {str(e)}")
            return f"Error reading file: {str(e)}"


class WriteFileTool(BaseTool):
    """Tool for writing content to a file."""

    @property
    def name(self) -> str:
        return "write_file"

    @property
    def description(self) -> str:
        return (
            "Write or append content to a file. Creates parent directories if needed. "
            "Use mode 'w' to overwrite or 'a' to append. Returns success message with file path."
        )

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path to the file to write (absolute or relative)"
                },
                "content": {
                    "type": "string",
                    "description": "Content to write to the file"
                },
                "mode": {
                    "type": "string",
                    "description": "Write mode: 'w' for write (overwrite), 'a' for append (default: w)",
                    "enum": ["w", "a"],
                    "default": "w"
                },
                "encoding": {
                    "type": "string",
                    "description": "File encoding (default: utf-8)",
                    "default": "utf-8"
                }
            },
            "required": ["path", "content"]
        }

    async def execute(self, **kwargs) -> str:
        """Execute the write file operation."""
        try:
            path_str = kwargs.get("path")
            content = kwargs.get("content")
            mode = kwargs.get("mode", "w")
            encoding = kwargs.get("encoding", "utf-8")

            if not path_str:
                return "Error: 'path' parameter is required"
            if content is None:
                return "Error: 'content' parameter is required"

            file_path = Path(path_str).resolve()

            # Create parent directories if needed
            file_path.parent.mkdir(parents=True, exist_ok=True)

            try:
                with open(file_path, mode, encoding=encoding) as f:
                    f.write(content)
                
                action = "Appended to" if mode == "a" else "Wrote to"
                logger.info(f"{action} file: {file_path} ({len(content)} characters)")
                return f"Success: {action} file {file_path}"
            except PermissionError:
                return f"Error: Permission denied to write to file: {file_path}"
            except OSError as e:
                return f"Error: Unable to write to file: {str(e)}"

        except Exception as e:
            logger.error(f"Error writing file: {str(e)}")
            return f"Error writing file: {str(e)}"


class DeleteFileTool(BaseTool):
    """Tool for deleting a file."""

    @property
    def name(self) -> str:
        return "delete_file"

    @property
    def description(self) -> str:
        return (
            "Delete a file from the file system. Use with caution as this operation "
            "cannot be undone. Returns success message or error."
        )

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path to the file to delete (absolute or relative)"
                }
            },
            "required": ["path"]
        }

    async def execute(self, **kwargs) -> str:
        """Execute the delete file operation."""
        try:
            path_str = kwargs.get("path")

            if not path_str:
                return "Error: 'path' parameter is required"

            file_path = Path(path_str).resolve()

            if not file_path.exists():
                return f"Error: File not found: {file_path}"

            if not file_path.is_file():
                return f"Error: Path is not a file (use a directory tool instead): {file_path}"

            try:
                file_path.unlink()
                logger.info(f"Deleted file: {file_path}")
                return f"Success: Deleted file {file_path}"
            except PermissionError:
                return f"Error: Permission denied to delete file: {file_path}"
            except OSError as e:
                return f"Error: Unable to delete file: {str(e)}"

        except Exception as e:
            logger.error(f"Error deleting file: {str(e)}")
            return f"Error deleting file: {str(e)}"


class MoveFileTool(BaseTool):
    """Tool for moving or renaming a file."""

    @property
    def name(self) -> str:
        return "move_file"

    @property
    def description(self) -> str:
        return (
            "Move or rename a file. Can move files across directories. "
            "Returns success message with new path or error."
        )

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "source": {
                    "type": "string",
                    "description": "Source file path (absolute or relative)"
                },
                "destination": {
                    "type": "string",
                    "description": "Destination file path (absolute or relative)"
                }
            },
            "required": ["source", "destination"]
        }

    async def execute(self, **kwargs) -> str:
        """Execute the move file operation."""
        try:
            source_str = kwargs.get("source")
            dest_str = kwargs.get("destination")

            if not source_str:
                return "Error: 'source' parameter is required"
            if not dest_str:
                return "Error: 'destination' parameter is required"

            source_path = Path(source_str).resolve()
            dest_path = Path(dest_str).resolve()

            if not source_path.exists():
                return f"Error: Source file not found: {source_path}"

            if not source_path.is_file():
                return f"Error: Source path is not a file: {source_path}"

            try:
                # Create destination parent directories if needed
                dest_path.parent.mkdir(parents=True, exist_ok=True)
                
                shutil.move(str(source_path), str(dest_path))
                logger.info(f"Moved file from {source_path} to {dest_path}")
                return f"Success: Moved file to {dest_path}"
            except PermissionError:
                return f"Error: Permission denied to move file"
            except shutil.Error as e:
                return f"Error: Unable to move file: {str(e)}"

        except Exception as e:
            logger.error(f"Error moving file: {str(e)}")
            return f"Error moving file: {str(e)}"


class ListDirectoryTool(BaseTool):
    """Tool for listing directory contents."""

    @property
    def name(self) -> str:
        return "list_directory"

    @property
    def description(self) -> str:
        return (
            "List contents of a directory. Can list recursively and filter by pattern. "
            "Returns list of files and directories with metadata (size, modified time, type)."
        )

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Directory path to list (absolute or relative)"
                },
                "recursive": {
                    "type": "boolean",
                    "description": "Whether to list recursively (default: false)",
                    "default": False
                },
                "pattern": {
                    "type": "string",
                    "description": "Glob pattern to filter results (default: *)",
                    "default": "*"
                }
            },
            "required": ["path"]
        }

    async def execute(self, **kwargs) -> str:
        """Execute the list directory operation."""
        try:
            path_str = kwargs.get("path")
            recursive = kwargs.get("recursive", False)
            pattern = kwargs.get("pattern", "*")

            if not path_str:
                return "Error: 'path' parameter is required"

            dir_path = Path(path_str).resolve()

            if not dir_path.exists():
                return f"Error: Directory not found: {dir_path}"

            if not dir_path.is_dir():
                return f"Error: Path is not a directory: {dir_path}"

            try:
                # Get matching paths
                if recursive:
                    paths = list(dir_path.rglob(pattern))
                else:
                    paths = list(dir_path.glob(pattern))

                # Build result list with metadata
                results = []
                for path in sorted(paths):
                    try:
                        stat = path.stat()
                        item = {
                            "path": str(path),
                            "name": path.name,
                            "type": "directory" if path.is_dir() else "file",
                            "size": stat.st_size if path.is_file() else None,
                            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat()
                        }
                        results.append(item)
                    except (PermissionError, OSError):
                        # Skip files we can't access
                        continue

                logger.info(f"Listed directory: {dir_path} ({len(results)} items)")
                return json.dumps(results, indent=2)

            except PermissionError:
                return f"Error: Permission denied to list directory: {dir_path}"

        except Exception as e:
            logger.error(f"Error listing directory: {str(e)}")
            return f"Error listing directory: {str(e)}"


class SearchFilesTool(BaseTool):
    """Tool for searching files by pattern."""

    @property
    def name(self) -> str:
        return "search_files"

    @property
    def description(self) -> str:
        return (
            "Recursively search for files matching a pattern. "
            "Returns list of matching file paths with metadata. "
            "Limited to max_results to prevent overwhelming responses."
        )

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "root_path": {
                    "type": "string",
                    "description": "Root directory to start search from"
                },
                "pattern": {
                    "type": "string",
                    "description": "Glob pattern to match (e.g., '*.py', '**/*.txt')"
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of results to return (default: 100)",
                    "default": 100
                }
            },
            "required": ["root_path", "pattern"]
        }

    async def execute(self, **kwargs) -> str:
        """Execute the search files operation."""
        try:
            root_str = kwargs.get("root_path")
            pattern = kwargs.get("pattern")
            max_results = kwargs.get("max_results", 100)

            if not root_str:
                return "Error: 'root_path' parameter is required"
            if not pattern:
                return "Error: 'pattern' parameter is required"

            root_path = Path(root_str).resolve()

            if not root_path.exists():
                return f"Error: Root path not found: {root_path}"

            if not root_path.is_dir():
                return f"Error: Root path is not a directory: {root_path}"

            try:
                # Search for matching files
                results = []
                for path in root_path.rglob(pattern):
                    if len(results) >= max_results:
                        break

                    try:
                        if path.is_file():
                            stat = path.stat()
                            item = {
                                "path": str(path),
                                "name": path.name,
                                "size": stat.st_size,
                                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat()
                            }
                            results.append(item)
                    except (PermissionError, OSError):
                        # Skip files we can't access
                        continue

                logger.info(f"Searched for '{pattern}' in {root_path} ({len(results)} results)")
                
                response = {
                    "results": results,
                    "count": len(results),
                    "truncated": len(results) >= max_results
                }
                return json.dumps(response, indent=2)

            except PermissionError:
                return f"Error: Permission denied to search in: {root_path}"

        except Exception as e:
            logger.error(f"Error searching files: {str(e)}")
            return f"Error searching files: {str(e)}"


class GetFileInfoTool(BaseTool):
    """Tool for getting detailed file information."""

    @property
    def name(self) -> str:
        return "get_file_info"

    @property
    def description(self) -> str:
        return (
            "Get detailed metadata about a file or directory. "
            "Returns size, created time, modified time, type, and permissions."
        )

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path to the file or directory"
                }
            },
            "required": ["path"]
        }

    async def execute(self, **kwargs) -> str:
        """Execute the get file info operation."""
        try:
            path_str = kwargs.get("path")

            if not path_str:
                return "Error: 'path' parameter is required"

            file_path = Path(path_str).resolve()

            if not file_path.exists():
                return f"Error: Path not found: {file_path}"

            try:
                stat = file_path.stat()
                
                info = {
                    "path": str(file_path),
                    "name": file_path.name,
                    "type": "directory" if file_path.is_dir() else "file",
                    "size": stat.st_size,
                    "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                    "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    "accessed": datetime.fromtimestamp(stat.st_atime).isoformat(),
                    "permissions": oct(stat.st_mode)[-3:],
                    "is_file": file_path.is_file(),
                    "is_dir": file_path.is_dir(),
                    "is_symlink": file_path.is_symlink()
                }

                logger.info(f"Got file info: {file_path}")
                return json.dumps(info, indent=2)

            except PermissionError:
                return f"Error: Permission denied to access: {file_path}"

        except Exception as e:
            logger.error(f"Error getting file info: {str(e)}")
            return f"Error getting file info: {str(e)}"


def register_file_tools():
    """Register all file operation tools with the global registry."""
    registry = get_tool_registry()
    tools = [
        ReadFileTool(),
        WriteFileTool(),
        DeleteFileTool(),
        MoveFileTool(),
        ListDirectoryTool(),
        SearchFilesTool(),
        GetFileInfoTool()
    ]
    for tool in tools:
        try:
            registry.register(tool)
            logger.info(f"Registered file tool: {tool.name}")
        except ValueError as e:
            logger.warning(f"Failed to register tool: {e}")
