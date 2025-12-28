"""
Confirmation dialog system for Computer Manager.

Provides user confirmation dialogs for sensitive operations
with caching and async support.
"""

import time
from typing import Dict, Optional
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QCheckBox, QTextEdit
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon, QPixmap
import qasync


class ConfirmationDialog(QDialog):
    """
    Dialog for confirming sensitive operations.
    
    Shows tool details and allows user to approve/deny actions.
    """
    
    def __init__(self, tool_name: str, parameters: Dict, sensitivity: str, parent=None):
        """
        Initialize confirmation dialog.
        
        Args:
            tool_name: Name of the tool requiring confirmation
            parameters: Tool parameters to display
            sensitivity: Sensitivity level (BASIC/ADVANCED/ADMIN)
            parent: Parent widget
        """
        super().__init__(parent)
        self.tool_name = tool_name
        self.parameters = parameters
        self.sensitivity = sensitivity
        self.remember_choice = False
        self.user_decision = False
        
        self._setup_ui()
    
    def _setup_ui(self):
        """Set up the dialog UI."""
        self.setWindowTitle("Confirm Action")
        self.setModal(True)
        self.setMinimumWidth(500)
        
        layout = QVBoxLayout()
        
        # Warning header
        header_layout = QHBoxLayout()
        
        # Warning icon (using standard icon)
        icon_label = QLabel()
        icon_label.setPixmap(
            self.style().standardIcon(
                self.style().StandardPixmap.SP_MessageBoxWarning
            ).pixmap(48, 48)
        )
        header_layout.addWidget(icon_label)
        
        # Title
        title_label = QLabel(f"<h3>Confirm: {self.tool_name}</h3>")
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        
        layout.addLayout(header_layout)
        
        # Description
        desc_label = QLabel(
            f"<p>The AI wants to execute a <b>{self.sensitivity}</b> level operation.</p>"
            "<p>Please review the details below and confirm if you want to proceed.</p>"
        )
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label)
        
        # Parameters display
        params_label = QLabel("<b>Parameters:</b>")
        layout.addWidget(params_label)
        
        params_text = QTextEdit()
        params_text.setReadOnly(True)
        params_text.setMaximumHeight(150)
        
        # Format parameters nicely
        params_str = self._format_parameters(self.parameters)
        params_text.setPlainText(params_str)
        
        layout.addWidget(params_text)
        
        # Remember choice checkbox
        self.remember_checkbox = QCheckBox("Remember this choice for this session")
        layout.addWidget(self.remember_checkbox)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        deny_button = QPushButton("Deny")
        deny_button.clicked.connect(self._on_deny)
        button_layout.addWidget(deny_button)
        
        allow_button = QPushButton("Allow")
        allow_button.clicked.connect(self._on_allow)
        allow_button.setDefault(True)
        button_layout.addWidget(allow_button)
        
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
    
    def _format_parameters(self, params: Dict) -> str:
        """Format parameters for display."""
        if not params:
            return "(No parameters)"
        
        lines = []
        for key, value in params.items():
            # Truncate long values
            value_str = str(value)
            if len(value_str) > 200:
                value_str = value_str[:200] + "... [truncated]"
            lines.append(f"{key}: {value_str}")
        
        return "\n".join(lines)
    
    def _on_allow(self):
        """Handle allow button click."""
        self.user_decision = True
        self.remember_choice = self.remember_checkbox.isChecked()
        self.accept()
    
    def _on_deny(self):
        """Handle deny button click."""
        self.user_decision = False
        self.remember_choice = self.remember_checkbox.isChecked()
        self.reject()


class ConfirmationManager:
    """
    Manages confirmation dialogs and caches user decisions.
    
    Integrates with config settings to determine when confirmation
    is required and caches decisions temporarily.
    """
    
    def __init__(self, config, parent_widget=None):
        """
        Initialize confirmation manager.
        
        Args:
            config: AppConfig instance
            parent_widget: Parent widget for dialogs
        """
        self.config = config
        self.parent_widget = parent_widget
        self._decision_cache: Dict[str, tuple[bool, float]] = {}
        self._cache_duration = 3600  # 1 hour default
    
    def is_confirmation_required(self, tool_name: str) -> bool:
        """
        Check if confirmation is required for a tool.
        
        Args:
            tool_name: Name of the tool
            
        Returns:
            True if confirmation required, False otherwise
        """
        # Check global confirmation setting
        if not self.config.require_confirmation:
            return False
        
        # Check if tool is in sensitive actions list
        # (for now, we'll use a simple heuristic based on tool name)
        if self.config.sensitive_actions_require_confirmation:
            sensitive_keywords = [
                'delete', 'kill', 'shutdown', 'write', 'move',
                'type', 'click', 'press', 'hotkey', 'drag',
                'registry', 'service', 'system'
            ]
            
            tool_lower = tool_name.lower()
            if any(keyword in tool_lower for keyword in sensitive_keywords):
                return True
        
        return False
    
    def cache_decision(self, tool_name: str, decision: bool, duration: int = 3600):
        """
        Cache user decision for a tool.
        
        Args:
            tool_name: Name of the tool
            decision: User's decision (True=allow, False=deny)
            duration: Cache duration in seconds
        """
        self._decision_cache[tool_name] = (decision, time.time() + duration)
    
    def get_cached_decision(self, tool_name: str) -> Optional[bool]:
        """
        Get cached decision for a tool.
        
        Args:
            tool_name: Name of the tool
            
        Returns:
            Cached decision if available and not expired, None otherwise
        """
        if tool_name not in self._decision_cache:
            return None
        
        decision, expiry = self._decision_cache[tool_name]
        
        # Check if cache expired
        if time.time() > expiry:
            del self._decision_cache[tool_name]
            return None
        
        return decision
    
    def clear_cache(self):
        """Clear all cached decisions."""
        self._decision_cache.clear()
    
    async def request_confirmation(
        self,
        tool_name: str,
        parameters: Dict,
        sensitivity: str
    ) -> bool:
        """
        Request user confirmation for an action.
        
        Args:
            tool_name: Name of the tool
            parameters: Tool parameters
            sensitivity: Sensitivity level
            
        Returns:
            True if user confirmed, False otherwise
        """
        # Check cache first
        cached = self.get_cached_decision(tool_name)
        if cached is not None:
            return cached
        
        # Show confirmation dialog
        dialog = ConfirmationDialog(
            tool_name,
            parameters,
            sensitivity,
            self.parent_widget
        )
        
        # Execute dialog (blocking)
        result = dialog.exec()
        
        # Cache decision if requested
        if dialog.remember_choice:
            self.cache_decision(tool_name, dialog.user_decision, self._cache_duration)
        
        return dialog.user_decision
