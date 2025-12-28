"""
Security middleware layer for Computer Manager.

Wraps tool execution with permission checks, confirmation dialogs,
and audit logging.
"""

import time
from typing import Any, Dict
from ..agent.tool_registry import BaseTool
from .permissions import PermissionManager, PermissionLevel
from .audit_log import AuditLogger
from .confirmation_dialog import ConfirmationManager


class SecurityMiddleware:
    """
    Security middleware for tool execution.
    
    Implements the complete security pipeline:
    1. Permission level validation
    2. Privilege elevation if needed
    3. User confirmation for sensitive actions
    4. Tool execution
    5. Audit logging
    """
    
    def __init__(
        self,
        permission_manager: PermissionManager,
        audit_logger: AuditLogger,
        confirmation_manager: ConfirmationManager
    ):
        """
        Initialize security middleware.
        
        Args:
            permission_manager: PermissionManager instance
            audit_logger: AuditLogger instance
            confirmation_manager: ConfirmationManager instance
        """
        self.permission_manager = permission_manager
        self.audit_logger = audit_logger
        self.confirmation_manager = confirmation_manager
    
    async def execute_with_security(
        self,
        tool: BaseTool,
        **kwargs
    ) -> Any:
        """
        Execute tool with full security pipeline.
        
        Args:
            tool: Tool to execute
            **kwargs: Tool parameters
            
        Returns:
            Tool execution result
            
        Raises:
            PermissionError: If permission denied
        """
        tool_name = tool.name
        start_time = time.time()
        user_confirmed = False
        
        try:
            # Step 1: Check if audit logging is enabled
            # (it's always checked, but we note it here)
            
            # Step 2: Determine required permission level
            required_level = self.permission_manager.get_tool_permission_level(tool_name)
            
            # Step 3: Validate current permission level
            if not self.permission_manager.check_permission(tool_name, required_level):
                # Step 4: If insufficient permissions and tool requires ADMIN, attempt elevation
                if required_level == PermissionLevel.ADMIN:
                    elevation_success = self.permission_manager.request_elevation()
                    self.audit_logger.log_elevation_request(
                        elevation_success,
                        f"Required for {tool_name}"
                    )
                    
                    if not elevation_success:
                        # Step 5: Log denial and raise error
                        self.audit_logger.log_permission_denied(
                            tool_name,
                            required_level.value,
                            self.permission_manager.get_current_level().value
                        )
                        raise PermissionError(
                            f"Permission denied: {tool_name} requires {required_level.value} "
                            f"level, current level is {self.permission_manager.get_current_level().value}. "
                            f"Privilege elevation failed."
                        )
                    
                    # Re-check configured permission level after elevation
                    # Even if OS-level elevation succeeded, the configured permission_level must be admin
                    if self.permission_manager.get_current_level() != PermissionLevel.ADMIN:
                        self.audit_logger.log_permission_denied(
                            tool_name,
                            required_level.value,
                            self.permission_manager.get_current_level().value
                        )
                        raise PermissionError(
                            f"Permission denied: {tool_name} requires admin permission level. "
                            f"Current configured level is {self.permission_manager.get_current_level().value}. "
                            f"Elevation succeeded but permission level configuration prevents execution."
                        )
                else:
                    # Not ADMIN level, just deny
                    self.audit_logger.log_permission_denied(
                        tool_name,
                        required_level.value,
                        self.permission_manager.get_current_level().value
                    )
                    raise PermissionError(
                        f"Permission denied: {tool_name} requires {required_level.value} "
                        f"level, current level is {self.permission_manager.get_current_level().value}"
                    )
            
            # Step 6: Check if confirmation is required
            if self.confirmation_manager.is_confirmation_required(tool_name):
                # Step 7: Show confirmation dialog
                user_confirmed = await self.confirmation_manager.request_confirmation(
                    tool_name,
                    kwargs,
                    required_level.value.upper()
                )
                
                # Log confirmation
                self.audit_logger.log_user_confirmation(tool_name, user_confirmed)
                
                # Step 8: If user denies, log and return error
                if not user_confirmed:
                    error_msg = f"User denied execution of {tool_name}"
                    self.audit_logger.log_tool_execution(
                        tool_name,
                        kwargs,
                        error_msg,
                        success=False,
                        user_confirmed=False
                    )
                    return {
                        "success": False,
                        "error": error_msg,
                        "message": "Action cancelled by user"
                    }
            
            # Step 9: Execute the tool
            result = await tool.execute(**kwargs)
            
            # Step 10: Log successful execution
            execution_time = time.time() - start_time
            self.audit_logger.log_tool_execution(
                tool_name,
                kwargs,
                result,
                success=True,
                user_confirmed=user_confirmed,
                execution_time=execution_time
            )
            
            # Step 11: Return result
            return result
            
        except PermissionError:
            # Re-raise permission errors
            raise
        except Exception as e:
            # Step 10 (error case): Log failed execution
            execution_time = time.time() - start_time
            self.audit_logger.log_tool_execution(
                tool_name,
                kwargs,
                str(e),
                success=False,
                user_confirmed=user_confirmed,
                execution_time=execution_time
            )
            
            # Re-raise the exception
            raise
    
    def wrap_tool(self, tool: BaseTool) -> BaseTool:
        """
        Wrap a tool with security checks.
        
        This creates a new tool instance that executes through
        the security middleware.
        
        Args:
            tool: Tool to wrap
            
        Returns:
            Wrapped tool instance
        """
        # Create a wrapper class dynamically
        original_execute = tool.execute
        middleware = self
        
        async def secure_execute(**kwargs):
            return await middleware.execute_with_security(tool, **kwargs)
        
        # Replace the execute method
        tool.execute = secure_execute
        
        return tool
