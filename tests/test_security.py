"""
Security system tests for Computer Manager.

Tests permission management, audit logging, confirmation dialogs,
and security middleware integration.
"""

import pytest
import asyncio
import tempfile
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from src.security.permissions import PermissionManager, PermissionLevel
from src.security.audit_log import AuditLogger
from src.security.confirmation_dialog import ConfirmationManager
from src.security.middleware import SecurityMiddleware
from src.agent.tool_registry import BaseTool
from src.utils.config import AppConfig


class MockConfig:
    """Mock configuration for testing."""
    def __init__(self):
        self.permission_level = "advanced"
        self.require_confirmation = True
        self.enable_audit_log = True
        self.audit_log_path = tempfile.mktemp(suffix=".log")
        self.sensitive_actions_require_confirmation = True


class MockTool(BaseTool):
    """Mock tool for testing."""
    def __init__(self, name="test_tool"):
        self._name = name
        self.executed = False
        self.execution_kwargs = None
    
    @property
    def name(self) -> str:
        return self._name
    
    @property
    def description(self) -> str:
        return "Test tool"
    
    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "test_param": {"type": "string"}
            }
        }
    
    async def execute(self, **kwargs):
        self.executed = True
        self.execution_kwargs = kwargs
        return {"success": True, "result": "test result"}


class TestPermissionManager:
    """Test permission management system."""
    
    def test_permission_level_parsing(self):
        """Test permission level string parsing."""
        config = MockConfig()
        config.permission_level = "basic"
        pm = PermissionManager(config)
        assert pm.get_current_level() == PermissionLevel.BASIC
        
        config.permission_level = "ADMIN"
        pm = PermissionManager(config)
        assert pm.get_current_level() == PermissionLevel.ADMIN
    
    def test_tool_permission_levels(self):
        """Test tool permission level mappings."""
        config = MockConfig()
        pm = PermissionManager(config)
        
        # Basic level tools
        assert pm.get_tool_permission_level("read_file") == PermissionLevel.BASIC
        assert pm.get_tool_permission_level("list_processes") == PermissionLevel.BASIC
        assert pm.get_tool_permission_level("capture_screenshot") == PermissionLevel.BASIC
        
        # Advanced level tools
        assert pm.get_tool_permission_level("write_file") == PermissionLevel.ADVANCED
        assert pm.get_tool_permission_level("click_mouse") == PermissionLevel.ADVANCED
        assert pm.get_tool_permission_level("launch_application") == PermissionLevel.ADVANCED
        
        # Admin level tools
        assert pm.get_tool_permission_level("delete_file") == PermissionLevel.ADMIN
        assert pm.get_tool_permission_level("kill_process") == PermissionLevel.ADMIN
        assert pm.get_tool_permission_level("write_registry_key") == PermissionLevel.ADMIN
    
    def test_permission_check_basic(self):
        """Test permission checks for basic level."""
        config = MockConfig()
        config.permission_level = "basic"
        pm = PermissionManager(config)
        
        # Should allow basic tools
        assert pm.check_permission("read_file") == True
        assert pm.check_permission("list_processes") == True
        
        # Should deny advanced tools
        assert pm.check_permission("write_file") == False
        assert pm.check_permission("click_mouse") == False
        
        # Should deny admin tools
        assert pm.check_permission("delete_file") == False
        assert pm.check_permission("kill_process") == False
    
    def test_permission_check_advanced(self):
        """Test permission checks for advanced level."""
        config = MockConfig()
        config.permission_level = "advanced"
        pm = PermissionManager(config)
        
        # Should allow basic and advanced tools
        assert pm.check_permission("read_file") == True
        assert pm.check_permission("write_file") == True
        assert pm.check_permission("click_mouse") == True
        
        # Should deny admin tools
        assert pm.check_permission("delete_file") == False
        assert pm.check_permission("kill_process") == False
    
    def test_permission_check_admin(self):
        """Test permission checks for admin level."""
        config = MockConfig()
        config.permission_level = "admin"
        pm = PermissionManager(config)
        
        # Should allow all tools
        assert pm.check_permission("read_file") == True
        assert pm.check_permission("write_file") == True
        assert pm.check_permission("delete_file") == True
        assert pm.check_permission("kill_process") == True


class TestAuditLogger:
    """Test audit logging system."""
    
    def test_audit_logger_initialization(self):
        """Test audit logger initialization."""
        config = MockConfig()
        logger = AuditLogger(config)
        assert logger.enabled == True
    
    def test_parameter_sanitization(self):
        """Test sensitive parameter sanitization."""
        config = MockConfig()
        logger = AuditLogger(config)
        
        params = {
            "username": "test_user",
            "password": "secret123",
            "api_key": "abc123",
            "normal_param": "normal_value"
        }
        
        sanitized = logger.sanitize_parameters(params)
        
        assert sanitized["username"] == "test_user"
        assert sanitized["password"] == "[REDACTED]"
        assert sanitized["api_key"] == "[REDACTED]"
        assert sanitized["normal_param"] == "normal_value"
    
    def test_tool_execution_logging(self):
        """Test tool execution logging."""
        config = MockConfig()
        logger = AuditLogger(config)
        
        logger.log_tool_execution(
            tool_name="test_tool",
            parameters={"param": "value"},
            result={"success": True},
            success=True,
            user_confirmed=True,
            execution_time=0.5
        )
        
        # Verify log file was created
        log_path = Path(config.audit_log_path)
        assert log_path.exists()
        
        # Read and verify log entry
        logs = logger.get_recent_logs(limit=1)
        assert len(logs) == 1
        assert logs[0]["tool_name"] == "test_tool"
        assert logs[0]["success"] == True
        assert logs[0]["user_confirmed"] == True
        
        # Cleanup
        log_path.unlink()
    
    def test_permission_denied_logging(self):
        """Test permission denial logging."""
        config = MockConfig()
        logger = AuditLogger(config)
        
        logger.log_permission_denied(
            tool_name="delete_file",
            required_level="admin",
            current_level="basic"
        )
        
        logs = logger.get_recent_logs(limit=1)
        assert len(logs) == 1
        assert logs[0]["event_type"] == "permission_denied"
        assert logs[0]["tool_name"] == "delete_file"
        
        # Cleanup
        Path(config.audit_log_path).unlink()


class TestConfirmationManager:
    """Test confirmation dialog system."""
    
    def test_confirmation_required_check(self):
        """Test confirmation requirement detection."""
        config = MockConfig()
        cm = ConfirmationManager(config)
        
        # Sensitive tools should require confirmation
        assert cm.is_confirmation_required("delete_file") == True
        assert cm.is_confirmation_required("kill_process") == True
        assert cm.is_confirmation_required("write_registry_key") == True
        assert cm.is_confirmation_required("click_mouse") == True
        
        # Non-sensitive tools should not require confirmation
        assert cm.is_confirmation_required("read_file") == False
        assert cm.is_confirmation_required("get_system_info") == False
    
    def test_decision_caching(self):
        """Test decision caching mechanism."""
        config = MockConfig()
        cm = ConfirmationManager(config)
        
        # Cache a decision
        cm.cache_decision("test_tool", True, duration=10)
        
        # Should retrieve cached decision
        assert cm.get_cached_decision("test_tool") == True
        
        # Should return None for non-cached tool
        assert cm.get_cached_decision("other_tool") is None
        
        # Clear cache
        cm.clear_cache()
        assert cm.get_cached_decision("test_tool") is None


class TestSecurityMiddleware:
    """Test security middleware integration."""
    
    @pytest.mark.asyncio
    async def test_basic_tool_execution(self):
        """Test execution of basic tool without restrictions."""
        config = MockConfig()
        config.permission_level = "basic"
        config.require_confirmation = False
        
        pm = PermissionManager(config)
        al = AuditLogger(config)
        cm = ConfirmationManager(config)
        middleware = SecurityMiddleware(pm, al, cm)
        
        tool = MockTool("read_file")
        result = await middleware.execute_with_security(tool, test_param="value")
        
        assert tool.executed == True
        assert result["success"] == True
        
        # Cleanup
        Path(config.audit_log_path).unlink()
    
    @pytest.mark.asyncio
    async def test_permission_denied(self):
        """Test permission denial for insufficient level."""
        config = MockConfig()
        config.permission_level = "basic"
        
        pm = PermissionManager(config)
        al = AuditLogger(config)
        cm = ConfirmationManager(config)
        middleware = SecurityMiddleware(pm, al, cm)
        
        tool = MockTool("delete_file")
        
        with pytest.raises(PermissionError):
            await middleware.execute_with_security(tool, test_param="value")
        
        assert tool.executed == False
        
        # Verify denial was logged
        logs = al.get_recent_logs(limit=1)
        assert len(logs) == 1
        assert logs[0]["event_type"] == "permission_denied"
        
        # Cleanup
        Path(config.audit_log_path).unlink()
    
    @pytest.mark.asyncio
    async def test_advanced_tool_with_permission(self):
        """Test execution of advanced tool with sufficient permission."""
        config = MockConfig()
        config.permission_level = "advanced"
        config.require_confirmation = False
        
        pm = PermissionManager(config)
        al = AuditLogger(config)
        cm = ConfirmationManager(config)
        middleware = SecurityMiddleware(pm, al, cm)
        
        tool = MockTool("write_file")
        result = await middleware.execute_with_security(tool, test_param="value")
        
        assert tool.executed == True
        assert result["success"] == True
        
        # Cleanup
        Path(config.audit_log_path).unlink()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
