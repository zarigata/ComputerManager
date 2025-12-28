"""
Audit logging system for Computer Manager.

Provides structured logging of all AI actions, permission denials,
and privilege elevation attempts.
"""

import json
import logging
import logging.handlers
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


class AuditLogger:
    """
    Structured audit logger for security events.
    
    Logs tool executions, permission denials, and elevation attempts
    with full context and automatic log rotation.
    """
    
    # Sensitive parameter keys to redact
    SENSITIVE_KEYS = {
        'password', 'passwd', 'pwd', 'secret', 'token', 'api_key',
        'apikey', 'auth', 'authorization', 'credential', 'private_key'
    }
    
    def __init__(self, config):
        """
        Initialize audit logger.
        
        Args:
            config: AppConfig instance with audit_log_path and enable_audit_log
        """
        self.config = config
        self.enabled = config.enable_audit_log
        
        if self.enabled:
            self._setup_logger()
    
    def _setup_logger(self):
        """Set up the audit logger with file handler and rotation."""
        # Create logger
        self.logger = logging.getLogger('audit')
        self.logger.setLevel(logging.INFO)
        self.logger.propagate = False
        
        # Create audit log directory if it doesn't exist
        log_path = Path(self.config.audit_log_path)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Create rotating file handler (10MB per file, 5 backups)
        handler = logging.handlers.RotatingFileHandler(
            log_path,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        
        # Create formatter for structured JSON logging
        formatter = logging.Formatter('%(message)s')
        handler.setFormatter(formatter)
        
        # Add handler to logger
        self.logger.addHandler(handler)
    
    def sanitize_parameters(self, params: Dict) -> Dict:
        """
        Sanitize parameters by redacting sensitive information.
        
        Args:
            params: Parameters dictionary to sanitize
            
        Returns:
            Sanitized parameters dictionary
        """
        if not params:
            return {}
        
        sanitized = {}
        for key, value in params.items():
            key_lower = key.lower()
            
            # Check if key contains sensitive information
            if any(sensitive in key_lower for sensitive in self.SENSITIVE_KEYS):
                sanitized[key] = '[REDACTED]'
            elif isinstance(value, dict):
                # Recursively sanitize nested dictionaries
                sanitized[key] = self.sanitize_parameters(value)
            elif isinstance(value, list):
                # Sanitize lists
                sanitized[key] = [
                    self.sanitize_parameters(item) if isinstance(item, dict) else item
                    for item in value
                ]
            else:
                sanitized[key] = value
        
        return sanitized
    
    def log_tool_execution(
        self,
        tool_name: str,
        parameters: Dict,
        result: Any,
        success: bool,
        user_confirmed: bool = False,
        execution_time: float = 0.0
    ):
        """
        Log tool execution with full context.
        
        Args:
            tool_name: Name of the executed tool
            parameters: Tool parameters (will be sanitized)
            result: Execution result
            success: Whether execution succeeded
            user_confirmed: Whether user confirmed the action
            execution_time: Execution time in seconds
        """
        if not self.enabled:
            return
        
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'event_type': 'tool_execution',
            'tool_name': tool_name,
            'parameters': self.sanitize_parameters(parameters),
            'success': success,
            'user_confirmed': user_confirmed,
            'execution_time': execution_time,
            'permission_level': self.config.permission_level,
        }
        
        # Add result summary (truncate if too large)
        if success:
            result_str = str(result)
            if len(result_str) > 500:
                result_str = result_str[:500] + '... [truncated]'
            log_entry['result_summary'] = result_str
        else:
            log_entry['error'] = str(result)
        
        self.logger.info(json.dumps(log_entry))
    
    def log_permission_denied(
        self,
        tool_name: str,
        required_level: str,
        current_level: str
    ):
        """
        Log permission denial.
        
        Args:
            tool_name: Name of the tool that was denied
            required_level: Required permission level
            current_level: Current permission level
        """
        if not self.enabled:
            return
        
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'event_type': 'permission_denied',
            'tool_name': tool_name,
            'required_level': required_level,
            'current_level': current_level,
        }
        
        self.logger.warning(json.dumps(log_entry))
    
    def log_elevation_request(self, success: bool, reason: str = ""):
        """
        Log privilege elevation attempt.
        
        Args:
            success: Whether elevation succeeded
            reason: Optional reason for elevation
        """
        if not self.enabled:
            return
        
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'event_type': 'elevation_request',
            'success': success,
            'reason': reason,
        }
        
        self.logger.info(json.dumps(log_entry))
    
    def log_user_confirmation(
        self,
        tool_name: str,
        confirmed: bool,
        cached: bool = False
    ):
        """
        Log user confirmation response.
        
        Args:
            tool_name: Name of the tool requiring confirmation
            confirmed: Whether user confirmed
            cached: Whether this was a cached decision
        """
        if not self.enabled:
            return
        
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'event_type': 'user_confirmation',
            'tool_name': tool_name,
            'confirmed': confirmed,
            'cached': cached,
        }
        
        self.logger.info(json.dumps(log_entry))
    
    def get_recent_logs(self, limit: int = 100) -> List[Dict]:
        """
        Retrieve recent audit log entries.
        
        Args:
            limit: Maximum number of entries to return
            
        Returns:
            List of log entry dictionaries
        """
        if not self.enabled:
            return []
        
        log_path = Path(self.config.audit_log_path)
        if not log_path.exists():
            return []
        
        logs = []
        try:
            with open(log_path, 'r', encoding='utf-8') as f:
                # Read last N lines
                lines = f.readlines()
                for line in lines[-limit:]:
                    try:
                        logs.append(json.loads(line.strip()))
                    except json.JSONDecodeError:
                        continue
        except Exception as e:
            print(f"Error reading audit log: {e}")
        
        return logs
    
    def export_logs(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        format: str = 'json'
    ) -> str:
        """
        Export audit logs for a date range.
        
        Args:
            start_date: Start date filter (inclusive)
            end_date: End date filter (inclusive)
            format: Export format ('json' or 'csv')
            
        Returns:
            Exported logs as formatted string
        """
        if not self.enabled:
            return ""
        
        log_path = Path(self.config.audit_log_path)
        if not log_path.exists():
            return ""
        
        filtered_logs = []
        try:
            with open(log_path, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        entry = json.loads(line.strip())
                        entry_time = datetime.fromisoformat(entry['timestamp'])
                        
                        # Apply date filters
                        if start_date and entry_time < start_date:
                            continue
                        if end_date and entry_time > end_date:
                            continue
                        
                        filtered_logs.append(entry)
                    except (json.JSONDecodeError, KeyError, ValueError):
                        continue
        except Exception as e:
            print(f"Error exporting logs: {e}")
            return ""
        
        if format == 'json':
            return json.dumps(filtered_logs, indent=2)
        elif format == 'csv':
            # Simple CSV export
            if not filtered_logs:
                return ""
            
            # Get all unique keys
            keys = set()
            for entry in filtered_logs:
                keys.update(entry.keys())
            keys = sorted(keys)
            
            # Create CSV
            lines = [','.join(keys)]
            for entry in filtered_logs:
                values = [str(entry.get(key, '')) for key in keys]
                lines.append(','.join(f'"{v}"' for v in values))
            
            return '\n'.join(lines)
        else:
            return ""
    
    def clear_logs(self):
        """Clear all audit logs (use with caution)."""
        if not self.enabled:
            return
        
        log_path = Path(self.config.audit_log_path)
        if log_path.exists():
            # Create backup before clearing
            backup_path = log_path.with_suffix('.bak')
            if backup_path.exists():
                backup_path.unlink()
            log_path.rename(backup_path)
            
            # Create new empty log file
            log_path.touch()
