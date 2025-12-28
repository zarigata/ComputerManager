"""
Integration tests for automation tools.

Tests file operations, process management, and web browsing tools.
"""

import asyncio
import json
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from src.automation.file_ops import (
    ReadFileTool, WriteFileTool, DeleteFileTool, MoveFileTool,
    ListDirectoryTool, SearchFilesTool, GetFileInfoTool
)
from src.automation.app_control import (
    LaunchApplicationTool, ListProcessesTool, KillProcessTool,
    GetProcessInfoTool, OpenURLTool, SearchWebTool
)


@pytest.fixture
def temp_test_dir(tmp_path):
    """Create a temporary directory for testing."""
    test_dir = tmp_path / "test_automation"
    test_dir.mkdir()
    return test_dir


class TestFileOperations:
    """Test file operation tools."""

    @pytest.mark.asyncio
    async def test_write_and_read_file(self, temp_test_dir):
        """Test writing and reading a file."""
        write_tool = WriteFileTool()
        read_tool = ReadFileTool()
        
        test_file = temp_test_dir / "test.txt"
        test_content = "Hello, World!"
        
        # Write file
        result = await write_tool.execute(
            path=str(test_file),
            content=test_content
        )
        assert "Success" in result
        assert test_file.exists()
        
        # Read file
        result = await read_tool.execute(path=str(test_file))
        assert result == test_content

    @pytest.mark.asyncio
    async def test_write_file_creates_directories(self, temp_test_dir):
        """Test that write_file creates parent directories."""
        write_tool = WriteFileTool()
        
        test_file = temp_test_dir / "subdir" / "nested" / "test.txt"
        
        result = await write_tool.execute(
            path=str(test_file),
            content="test"
        )
        assert "Success" in result
        assert test_file.exists()

    @pytest.mark.asyncio
    async def test_read_nonexistent_file(self, temp_test_dir):
        """Test reading a file that doesn't exist."""
        read_tool = ReadFileTool()
        
        result = await read_tool.execute(
            path=str(temp_test_dir / "nonexistent.txt")
        )
        assert "Error" in result
        assert "not found" in result.lower()

    @pytest.mark.asyncio
    async def test_delete_file(self, temp_test_dir):
        """Test deleting a file."""
        delete_tool = DeleteFileTool()
        
        # Create a test file
        test_file = temp_test_dir / "to_delete.txt"
        test_file.write_text("delete me")
        
        # Delete it
        result = await delete_tool.execute(path=str(test_file))
        assert "Success" in result
        assert not test_file.exists()

    @pytest.mark.asyncio
    async def test_move_file(self, temp_test_dir):
        """Test moving a file."""
        move_tool = MoveFileTool()
        
        # Create source file
        source = temp_test_dir / "source.txt"
        source.write_text("move me")
        
        # Move it
        dest = temp_test_dir / "destination.txt"
        result = await move_tool.execute(
            source=str(source),
            destination=str(dest)
        )
        assert "Success" in result
        assert not source.exists()
        assert dest.exists()

    @pytest.mark.asyncio
    async def test_list_directory(self, temp_test_dir):
        """Test listing directory contents."""
        list_tool = ListDirectoryTool()
        
        # Create some test files
        (temp_test_dir / "file1.txt").write_text("test")
        (temp_test_dir / "file2.txt").write_text("test")
        (temp_test_dir / "subdir").mkdir()
        
        # List directory
        result = await list_tool.execute(path=str(temp_test_dir))
        items = json.loads(result)
        
        assert len(items) >= 3
        assert any(item["name"] == "file1.txt" for item in items)
        assert any(item["name"] == "file2.txt" for item in items)
        assert any(item["name"] == "subdir" for item in items)

    @pytest.mark.asyncio
    async def test_search_files(self, temp_test_dir):
        """Test searching for files."""
        search_tool = SearchFilesTool()
        
        # Create test files
        (temp_test_dir / "test1.py").write_text("test")
        (temp_test_dir / "test2.py").write_text("test")
        (temp_test_dir / "other.txt").write_text("test")
        
        # Search for .py files
        result = await search_tool.execute(
            root_path=str(temp_test_dir),
            pattern="*.py"
        )
        data = json.loads(result)
        
        assert data["count"] == 2
        assert all(item["name"].endswith(".py") for item in data["results"])

    @pytest.mark.asyncio
    async def test_get_file_info(self, temp_test_dir):
        """Test getting file information."""
        info_tool = GetFileInfoTool()
        
        # Create test file
        test_file = temp_test_dir / "info_test.txt"
        test_file.write_text("test content")
        
        # Get info
        result = await info_tool.execute(path=str(test_file))
        info = json.loads(result)
        
        assert info["name"] == "info_test.txt"
        assert info["type"] == "file"
        assert info["size"] > 0
        assert "created" in info
        assert "modified" in info


class TestProcessManagement:
    """Test process management tools."""

    @pytest.mark.asyncio
    async def test_list_processes(self):
        """Test listing processes."""
        list_tool = ListProcessesTool()
        
        result = await list_tool.execute()
        data = json.loads(result)
        
        assert "count" in data
        assert "processes" in data
        assert data["count"] > 0
        assert len(data["processes"]) > 0

    @pytest.mark.asyncio
    async def test_list_processes_with_filter(self):
        """Test listing processes with name filter."""
        list_tool = ListProcessesTool()
        
        # Filter for python processes (should find pytest)
        result = await list_tool.execute(filter_name="python")
        data = json.loads(result)
        
        assert "processes" in data
        # Should find at least the current Python process
        assert any("python" in proc["name"].lower() for proc in data["processes"])

    @pytest.mark.asyncio
    async def test_get_process_info(self):
        """Test getting process information."""
        import os
        info_tool = GetProcessInfoTool()
        
        # Get info for current process
        current_pid = os.getpid()
        result = await info_tool.execute(pid=current_pid)
        info = json.loads(result)
        
        assert info["pid"] == current_pid
        assert "name" in info
        assert "status" in info

    @pytest.mark.asyncio
    async def test_get_nonexistent_process_info(self):
        """Test getting info for nonexistent process."""
        info_tool = GetProcessInfoTool()
        
        # Use a PID that's unlikely to exist
        result = await info_tool.execute(pid=999999)
        assert "Error" in result


class TestWebBrowsing:
    """Test web browsing tools."""

    @pytest.mark.asyncio
    async def test_open_url_validation(self):
        """Test URL validation."""
        open_tool = OpenURLTool()
        
        # Test invalid URL (no protocol)
        result = await open_tool.execute(url="example.com")
        assert "Error" in result
        assert "protocol" in result.lower()

    @pytest.mark.asyncio
    @patch('webbrowser.open_new_tab')
    async def test_open_valid_url(self, mock_open):
        """Test opening a valid URL."""
        open_tool = OpenURLTool()
        
        result = await open_tool.execute(url="https://example.com")
        assert "Success" in result
        mock_open.assert_called_once_with("https://example.com")

    @pytest.mark.asyncio
    @patch('webbrowser.open_new_tab')
    async def test_search_web_google(self, mock_open):
        """Test web search with Google."""
        search_tool = SearchWebTool()
        
        result = await search_tool.execute(
            query="test query",
            engine="google"
        )
        assert "Success" in result
        assert "google" in result.lower()
        mock_open.assert_called_once()

    @pytest.mark.asyncio
    @patch('webbrowser.open_new_tab')
    async def test_search_web_bing(self, mock_open):
        """Test web search with Bing."""
        search_tool = SearchWebTool()
        
        result = await search_tool.execute(
            query="test query",
            engine="bing"
        )
        assert "Success" in result
        assert "bing" in result.lower()
        mock_open.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_web_invalid_engine(self):
        """Test web search with invalid engine."""
        search_tool = SearchWebTool()
        
        result = await search_tool.execute(
            query="test query",
            engine="invalid"
        )
        assert "Error" in result


class TestToolParameters:
    """Test tool parameter validation."""

    @pytest.mark.asyncio
    async def test_read_file_missing_path(self):
        """Test read_file with missing path parameter."""
        read_tool = ReadFileTool()
        result = await read_tool.execute()
        assert "Error" in result
        assert "required" in result.lower()

    @pytest.mark.asyncio
    async def test_write_file_missing_content(self, temp_test_dir):
        """Test write_file with missing content parameter."""
        write_tool = WriteFileTool()
        result = await write_tool.execute(path=str(temp_test_dir / "test.txt"))
        assert "Error" in result
        assert "required" in result.lower()

    @pytest.mark.asyncio
    @patch('subprocess.Popen')
    async def test_launch_application_string_arguments(self, mock_popen):
        """Test launch_application with string arguments parameter."""
        launch_tool = LaunchApplicationTool()
        
        # Mock the process
        mock_process = Mock()
        mock_process.pid = 12345
        mock_popen.return_value = mock_process
        
        # Test with string arguments (should be wrapped in list)
        result = await launch_tool.execute(
            application="notepad",
            arguments="test.txt"
        )
        
        # Should either succeed (string wrapped in list) or return informative error
        assert "Success" in result or "Error" in result
        
        if "Success" in result:
            # Verify the command was built correctly with wrapped string
            mock_popen.assert_called_once()
            call_args = mock_popen.call_args[0][0]
            assert call_args == ["notepad", "test.txt"]
        else:
            # Verify error message is informative
            assert "arguments" in result.lower()

    @pytest.mark.asyncio
    async def test_launch_application_invalid_arguments_type(self):
        """Test launch_application with invalid arguments type."""
        launch_tool = LaunchApplicationTool()
        
        # Test with invalid type (number)
        result = await launch_tool.execute(
            application="notepad",
            arguments=123
        )
        
        assert "Error" in result
        assert "arguments" in result.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
