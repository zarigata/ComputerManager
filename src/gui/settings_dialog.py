"""
Settings dialog for configuring application preferences.

This module provides a tabbed settings interface for model selection,
theme configuration, security settings, and advanced options.
"""

import asyncio
import logging
from typing import Optional

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget,
    QWidget, QLabel, QComboBox, QCheckBox, QPushButton,
    QSpinBox, QLineEdit, QMessageBox, QProgressDialog,
    QGroupBox, QFormLayout, QListWidget, QListWidgetItem
)
from PyQt6.QtCore import Qt, pyqtSignal
from qasync import asyncSlot

from ..ollama.client import OllamaClient, OllamaConnectionError
from ..ollama.model_manager import ModelManager
from ..utils.config import get_config, ConfigManager
from ..utils.system_info import SystemDetector
from ..security.permissions import PermissionManager
from ..security.audit_log import AuditLogger
from .audit_log_viewer import AuditLogViewer

logger = logging.getLogger(__name__)


class SettingsDialog(QDialog):
    """Settings dialog with tabbed interface."""
    
    settings_changed = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.config = get_config()
        self.config_manager = ConfigManager()
        self.ollama_client = OllamaClient()
        self.model_manager = ModelManager(self.ollama_client)
        
        # Initialize security components
        self.permission_manager = PermissionManager(self.config)
        self.audit_logger = AuditLogger(self.config)
        
        self._init_ui()
        self._load_current_settings()
        
        logger.info("Settings dialog opened")
    
    def _init_ui(self):
        """Initialize the user interface."""
        self.setWindowTitle("Settings")
        self.setMinimumSize(600, 500)
        
        layout = QVBoxLayout(self)
        
        # Create tab widget
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)
        
        # Create tabs
        self._create_general_tab()
        self._create_models_tab()
        self._create_security_tab()
        self._create_advanced_tab()
        
        # Create button box
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.apply_button = QPushButton("Apply")
        self.apply_button.clicked.connect(self._apply_settings)
        button_layout.addWidget(self.apply_button)
        
        self.ok_button = QPushButton("OK")
        self.ok_button.clicked.connect(self._ok_clicked)
        button_layout.addWidget(self.ok_button)
        
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_button)
        
        layout.addLayout(button_layout)
    
    def _create_general_tab(self):
        """Create the General settings tab."""
        tab = QWidget()
        layout = QFormLayout(tab)
        
        # Theme selection
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["System", "Light", "Dark"])
        layout.addRow("Theme:", self.theme_combo)
        
        # Window size
        window_group = QGroupBox("Window Size")
        window_layout = QFormLayout()
        
        self.window_width_spin = QSpinBox()
        self.window_width_spin.setRange(600, 3840)
        self.window_width_spin.setSingleStep(50)
        window_layout.addRow("Width:", self.window_width_spin)
        
        self.window_height_spin = QSpinBox()
        self.window_height_spin.setRange(400, 2160)
        self.window_height_spin.setSingleStep(50)
        window_layout.addRow("Height:", self.window_height_spin)
        
        window_group.setLayout(window_layout)
        layout.addRow(window_group)
        
        # Startup options
        self.start_minimized_check = QCheckBox("Start minimized to tray")
        layout.addRow(self.start_minimized_check)
        
        self.close_to_tray_check = QCheckBox("Minimize to tray on close")
        self.close_to_tray_check.setChecked(True)  # Default behavior
        layout.addRow(self.close_to_tray_check)
        
        self.tab_widget.addTab(tab, "General")
    
    def _create_models_tab(self):
        """Create the Models settings tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Hardware tier display
        system_detector = SystemDetector()
        hardware_tier = system_detector.get_hardware_tier()
        
        tier_label = QLabel(f"<b>Detected Hardware Tier:</b> {hardware_tier.upper()}")
        layout.addWidget(tier_label)

        # Performance Profile Selection
        profile_group = QGroupBox("Performance Profile")
        profile_layout = QFormLayout()

        self.profile_combo = QComboBox()
        self.profile_combo.addItems(["Auto", "Low", "Medium", "High"])
        self.profile_combo.currentTextChanged.connect(self._on_profile_changed)
        profile_layout.addRow("Active Profile:", self.profile_combo)

        self.preset_preview_label = QLabel("Recommended: ...")
        self.preset_preview_label.setWordWrap(True)
        self.preset_preview_label.setStyleSheet("color: gray;")
        profile_layout.addRow("Preset Preview:", self.preset_preview_label)
        
        self.apply_preset_button = QPushButton("Download & Apply Preset")
        self.apply_preset_button.clicked.connect(self._apply_profile_preset)
        profile_layout.addRow("", self.apply_preset_button)

        profile_group.setLayout(profile_layout)
        layout.addWidget(profile_group)
        
        # Model selection
        model_group = QGroupBox("Model Selection")
        model_layout = QFormLayout()
        
        self.text_model_combo = QComboBox()
        model_layout.addRow("Text Model:", self.text_model_combo)
        
        self.vision_model_combo = QComboBox()
        model_layout.addRow("Vision Model:", self.vision_model_combo)
        
        model_group.setLayout(model_layout)
        layout.addWidget(model_group)
        
        # Model options
        self.auto_download_check = QCheckBox("Auto-download missing models")
        layout.addWidget(self.auto_download_check)
        
        # Download model button
        download_layout = QHBoxLayout()
        self.download_model_input = QLineEdit()
        self.download_model_input.setPlaceholderText("Enter model name (e.g., llama3.2:3b)")
        download_layout.addWidget(self.download_model_input)
        
        self.download_button = QPushButton("Download")
        self.download_button.clicked.connect(self._download_model)
        download_layout.addWidget(self.download_button)
        
        layout.addLayout(download_layout)
        
        # Refresh models button
        self.refresh_models_button = QPushButton("Refresh Model List")
        self.refresh_models_button.clicked.connect(self._refresh_models)
        layout.addWidget(self.refresh_models_button)
        
        layout.addStretch()
        
        self.tab_widget.addTab(tab, "Models")
    
    def _create_security_tab(self):
        """Create the Security settings tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Privilege status display
        status_group = QGroupBox("Current Status")
        status_layout = QFormLayout()
        
        # Check admin status
        is_admin = self.permission_manager.is_admin()
        admin_status = "Administrator" if is_admin else "Standard User"
        admin_color = "green" if is_admin else "orange"
        
        admin_label = QLabel(f"<span style='color: {admin_color}; font-weight: bold;'>{admin_status}</span>")
        status_layout.addRow("Privilege Level:", admin_label)
        
        current_level = self.config.permission_level.capitalize()
        level_label = QLabel(f"<b>{current_level}</b>")
        status_layout.addRow("Permission Level:", level_label)
        
        status_group.setLayout(status_layout)
        layout.addWidget(status_group)
        
        # Permission level selection
        perm_group = QGroupBox("Permission Settings")
        perm_layout = QFormLayout()
        
        self.permission_combo = QComboBox()
        self.permission_combo.addItems(["Basic", "Advanced", "Admin"])
        perm_layout.addRow("Permission Level:", self.permission_combo)
        
        # Add description label
        desc_label = QLabel(
            "<small><b>Basic:</b> Read-only operations<br>"
            "<b>Advanced:</b> File writes, automation<br>"
            "<b>Admin:</b> System modifications, deletions</small>"
        )
        desc_label.setWordWrap(True)
        perm_layout.addRow(desc_label)
        
        perm_group.setLayout(perm_layout)
        layout.addWidget(perm_group)
        
        # Security options
        options_group = QGroupBox("Security Options")
        options_layout = QVBoxLayout()
        
        self.require_confirmation_check = QCheckBox("Require confirmation for sensitive actions")
        self.require_confirmation_check.setChecked(True)
        options_layout.addWidget(self.require_confirmation_check)
        
        self.enable_audit_check = QCheckBox("Enable audit logging")
        options_layout.addWidget(self.enable_audit_check)
        
        options_group.setLayout(options_layout)
        layout.addWidget(options_group)
        
        # Audit log management
        audit_group = QGroupBox("Audit Log Management")
        audit_layout = QVBoxLayout()
        
        # View audit log button
        self.view_audit_button = QPushButton("View Audit Log")
        self.view_audit_button.clicked.connect(self._view_audit_log)
        audit_layout.addWidget(self.view_audit_button)
        
        # Clear audit log button
        self.clear_audit_button = QPushButton("Clear Audit Log")
        self.clear_audit_button.clicked.connect(self._clear_audit_log)
        audit_layout.addWidget(self.clear_audit_button)
        
        audit_group.setLayout(audit_layout)
        layout.addWidget(audit_group)
        
        # Test admin privileges button
        self.test_admin_button = QPushButton("Test Admin Privileges")
        self.test_admin_button.clicked.connect(self._test_admin_privileges)
        layout.addWidget(self.test_admin_button)
        
        layout.addStretch()
        
        self.tab_widget.addTab(tab, "Security")
    
    def _create_advanced_tab(self):
        """Create the Advanced settings tab."""
        tab = QWidget()
        layout = QFormLayout(tab)
        
        # Ollama host
        self.ollama_host_input = QLineEdit()
        self.ollama_host_input.setPlaceholderText("http://localhost:11434")
        layout.addRow("Ollama Host:", self.ollama_host_input)
        
        # Timeout
        self.timeout_spin = QSpinBox()
        self.timeout_spin.setRange(10, 300)
        self.timeout_spin.setSuffix(" seconds")
        layout.addRow("Request Timeout:", self.timeout_spin)
        
        # Max chat history
        self.max_history_spin = QSpinBox()
        self.max_history_spin.setRange(10, 1000)
        layout.addRow("Max Chat History:", self.max_history_spin)
        
        # Test connection button
        self.test_connection_button = QPushButton("Test Connection")
        self.test_connection_button.clicked.connect(self._test_connection)
        layout.addRow(self.test_connection_button)
        
        self.tab_widget.addTab(tab, "Advanced")
        
        # --- LangChain Integration Section ---
        langchain_group = QGroupBox("LangChain Integration (Optional)")
        langchain_layout = QVBoxLayout()
        
        # Enable toggle
        self.langchain_enabled_check = QCheckBox("Enable LangChain Integration")
        self.langchain_enabled_check.toggled.connect(self._check_langchain_availability)
        langchain_layout.addWidget(self.langchain_enabled_check)
        
        # Info label
        info = QLabel(
            "Enable implementation of popular tools like Wikipedia, Calculator, and Web Search.\n"
            "Requires: pip install -e .[langchain]"
        )
        info.setStyleSheet("color: gray; font-style: italic;")
        langchain_layout.addWidget(info)
        
        # Available tools list
        langchain_layout.addWidget(QLabel("Available Tools:"))
        
        self.langchain_tools_list = QListWidget()
        tools = [
            ("Wikipedia", "wikipedia"), 
            ("Calculator", "calculator"), 
            ("DuckDuckGo Search", "duckduckgo_search"), 
            ("Weather (requires API key)", "weather")
        ]
        
        for name, key in tools:
            item = QListWidgetItem(name)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Unchecked)
            item.setData(Qt.ItemDataRole.UserRole, key)
            self.langchain_tools_list.addItem(item)
            
        langchain_layout.addWidget(self.langchain_tools_list)
        
        langchain_group.setLayout(langchain_layout)
        layout.addRow(langchain_group)
    
    def _load_current_settings(self):
        """Load current settings from config."""
        # General tab
        theme = self.config.theme.capitalize() if self.config.theme else "System"
        index = self.theme_combo.findText(theme)
        if index >= 0:
            self.theme_combo.setCurrentIndex(index)
        
        self.window_width_spin.setValue(self.config.window_width)
        self.window_height_spin.setValue(self.config.window_height)
        self.start_minimized_check.setChecked(self.config.start_minimized)
        self.close_to_tray_check.setChecked(self.config.close_to_tray)
        
        # Models tab - populate with installed models
        # Models tab - populate with installed models
        self._refresh_models()
        self._load_profile_settings()
        
        # Security tab
        permission = self.config.permission_level
        index = self.permission_combo.findText(permission.capitalize())
        if index >= 0:
            self.permission_combo.setCurrentIndex(index)
        
        self.require_confirmation_check.setChecked(
            self.config.require_confirmation
        )
        self.enable_audit_check.setChecked(
            self.config.enable_audit_log
        )
        
        # Advanced tab
        self.ollama_host_input.setText(self.config.ollama_host)
        self.timeout_spin.setValue(self.config.ollama_timeout)
        self.max_history_spin.setValue(self.config.max_chat_history)
        
        # LangChain settings
        self.langchain_enabled_check.setChecked(self.config.langchain_enabled)
        
        current_tools = self.config.langchain_tools
        for i in range(self.langchain_tools_list.count()):
            item = self.langchain_tools_list.item(i)
            key = item.data(Qt.ItemDataRole.UserRole)
            if key in current_tools:
                item.setCheckState(Qt.CheckState.Checked)
            else:
                item.setCheckState(Qt.CheckState.Unchecked)
    
    @asyncSlot()
    async def _refresh_models(self):
        """Refresh the list of installed models."""
        try:
            self.refresh_models_button.setEnabled(False)
            self.refresh_models_button.setText("Refreshing...")
            
            # Get installed models (returns List[ModelInfo])
            model_infos = await self.model_manager.list_all_installed_models()
            
            # Extract model names from ModelInfo objects
            model_names = [m.name for m in model_infos]
            
            # Update text model combo
            current_text_model = self.config.default_text_model
            self.text_model_combo.clear()
            self.text_model_combo.addItems(model_names)
            
            index = self.text_model_combo.findText(current_text_model)
            if index >= 0:
                self.text_model_combo.setCurrentIndex(index)
            
            # Update vision model combo (filter for vision-capable models)
            current_vision_model = self.config.default_vision_model
            vision_models = [name for name in model_names if "vision" in name.lower() or "llava" in name.lower()]
            self.vision_model_combo.clear()
            self.vision_model_combo.addItems(vision_models if vision_models else ["No vision models installed"])
            
            index = self.vision_model_combo.findText(current_vision_model)
            if index >= 0:
                self.vision_model_combo.setCurrentIndex(index)
            
            logger.info(f"Refreshed model list: {len(model_names)} models found")
            
        except Exception as e:
            logger.error(f"Failed to refresh models: {e}")
            QMessageBox.warning(self, "Error", f"Failed to refresh models: {str(e)}")
        finally:
            self.refresh_models_button.setEnabled(True)
            self.refresh_models_button.setText("Refresh Model List")
    
    @asyncSlot()
    async def _download_model(self):
        """Download a model with progress tracking."""
        model_name = self.download_model_input.text().strip()
        if not model_name:
            QMessageBox.warning(self, "Invalid Input", "Please enter a model name.")
            return
        
        # Create progress dialog
        progress = QProgressDialog(f"Downloading {model_name}...", "Cancel", 0, 100, self)
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setMinimumDuration(0)
        progress.setValue(0)
        
        try:
            # Download model
            await self.model_manager.download_model(model_name)
            
            progress.setValue(100)
            QMessageBox.information(self, "Success", f"Model '{model_name}' downloaded successfully!")
            
            # Refresh model list
            await self._refresh_models()
            
            logger.info(f"Model downloaded: {model_name}")
            
        except Exception as e:
            logger.error(f"Failed to download model: {e}")
            QMessageBox.critical(self, "Error", f"Failed to download model: {str(e)}")
        finally:
            progress.close()
    
    @asyncSlot()
    async def _test_connection(self):
        """Test connection to Ollama server."""
        self.test_connection_button.setEnabled(False)
        self.test_connection_button.setText("Testing...")
        
        try:
            # Update host if changed
            host = self.ollama_host_input.text().strip()
            if host:
                self.ollama_client = OllamaClient(host=host)
            
            # Test connection
            await self.ollama_client.check_connection()
            
            QMessageBox.information(self, "Success", "Connection to Ollama server successful!")
            logger.info("Ollama connection test successful")
            
        except OllamaConnectionError as e:
            QMessageBox.critical(self, "Connection Failed", f"Failed to connect to Ollama: {str(e)}")
            logger.error(f"Ollama connection test failed: {e}")
        finally:
            self.test_connection_button.setEnabled(True)
            self.test_connection_button.setText("Test Connection")
    
    def _view_audit_log(self):
        """Open audit log viewer."""
        if not self.config.enable_audit_log:
            QMessageBox.information(
                self,
                "Audit Log Disabled",
                "Audit logging is currently disabled. Enable it in the security settings to start logging."
            )
            return
        
        try:
            viewer = AuditLogViewer(self.audit_logger, self)
            viewer.exec()
        except Exception as e:
            logger.error(f"Failed to open audit log viewer: {e}")
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to open audit log viewer: {str(e)}"
            )
    
    def _clear_audit_log(self):
        """Clear audit log with confirmation."""
        reply = QMessageBox.question(
            self,
            "Clear Audit Log",
            "Are you sure you want to clear the audit log? This action cannot be undone.\n\n"
            "A backup will be created before clearing.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                self.audit_logger.clear_logs()
                QMessageBox.information(
                    self,
                    "Success",
                    "Audit log cleared successfully. A backup was created."
                )
                logger.info("Audit log cleared by user")
            except Exception as e:
                logger.error(f"Failed to clear audit log: {e}")
                QMessageBox.critical(
                    self,
                    "Error",
                    f"Failed to clear audit log: {str(e)}"
                )
    
    def _test_admin_privileges(self):
        """Test if admin privileges are available."""
        is_admin = self.permission_manager.is_admin()
        
        if is_admin:
            QMessageBox.information(
                self,
                "Admin Privileges",
                "You are currently running with administrator privileges."
            )
        else:
            reply = QMessageBox.question(
                self,
                "Admin Privileges",
                "You are not running with administrator privileges.\n\n"
                "Would you like to attempt privilege elevation?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                success = self.permission_manager.request_elevation()
                
                if success:
                    QMessageBox.information(
                        self,
                        "Success",
                        "Privilege elevation successful!"
                    )
                else:
                    QMessageBox.warning(
                        self,
                        "Failed",
                        "Privilege elevation failed or was cancelled.\n\n"
                        "On Windows, you may need to restart the application as administrator.\n"
                        "On Linux/macOS, ensure you have sudo access."
                    )
    
    def _apply_settings(self):
        """Apply settings without closing dialog."""
        if self._validate_settings():
            self._save_settings()
            self.settings_changed.emit()
            QMessageBox.information(self, "Settings Applied", "Settings have been applied successfully.")
    
    def _ok_clicked(self):
        """Handle OK button click."""
        if self._validate_settings():
            self._save_settings()
            self.settings_changed.emit()
            self.accept()
    
    def _validate_settings(self) -> bool:
        """Validate settings before saving."""
        # Validate Ollama host URL
        host = self.ollama_host_input.text().strip()
        if host and not (host.startswith("http://") or host.startswith("https://")):
            QMessageBox.warning(
                self,
                "Invalid URL",
                "Ollama host must start with http:// or https://"
            )
            self.tab_widget.setCurrentIndex(3)  # Switch to Advanced tab
            return False
        
        # Warn if changing to admin permission level
        if self.permission_combo.currentText() == "Admin":
            reply = QMessageBox.question(
                self,
                "Admin Permission",
                "Admin permission level grants full system access. Are you sure?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.No:
                return False
        
        return True
    
    def _save_settings(self):
        """Save settings to config."""
        # General settings
        self.config.theme = self.theme_combo.currentText().lower()
        self.config.window_width = self.window_width_spin.value()
        self.config.window_height = self.window_height_spin.value()
        self.config.start_minimized = self.start_minimized_check.isChecked()
        self.config.close_to_tray = self.close_to_tray_check.isChecked()
        
        # Model settings
        text_model = self.text_model_combo.currentText()
        if text_model:
            self.config.default_text_model = text_model
        
        vision_model = self.vision_model_combo.currentText()
        if vision_model and vision_model != "No vision models installed":
            self.config.default_vision_model = vision_model
        
        self.config.auto_download_models = self.auto_download_check.isChecked()
        self.config.performance_profile = self.profile_combo.currentText().lower()
        
        # Security settings
        self.config.permission_level = self.permission_combo.currentText().lower()
        self.config.require_confirmation = self.require_confirmation_check.isChecked()
        self.config.enable_audit_log = self.enable_audit_check.isChecked()
        
        # Advanced settings
        host = self.ollama_host_input.text().strip()
        if host:
            self.config.ollama_host = host
        
        self.config.ollama_timeout = self.timeout_spin.value()
        self.config.max_chat_history = self.max_history_spin.value()
        
        # LangChain settings
        self.config.langchain_enabled = self.langchain_enabled_check.isChecked()
        
        selected_tools = []
        for i in range(self.langchain_tools_list.count()):
            item = self.langchain_tools_list.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                selected_tools.append(item.data(Qt.ItemDataRole.UserRole))
        self.config.langchain_tools = selected_tools
        
        # Convert AppConfig to dict before saving
        config_dict = self.config_manager.to_dict()
        # Handle list serialization for tools
        config_dict['LANGCHAIN_TOOLS'] = ",".join(self.config.langchain_tools)
        # Handle enabled flag
        config_dict['LANGCHAIN_ENABLED'] = str(self.config.langchain_enabled).lower()
        
        # Remove lowercase keys if present to avoid pollution
        if 'langchain_tools' in config_dict:
            del config_dict['langchain_tools']
        if 'langchain_enabled' in config_dict:
            del config_dict['langchain_enabled']
        
        self.config_manager.save_config(config_dict)
        
        logger.info("Settings saved successfully")

    def _check_langchain_availability(self, enabled: bool):
        """Check if LangChain is installed when enabled."""
        if enabled:
            try:
                import langchain
                # Success
            except ImportError:
                QMessageBox.warning(
                    self,
                    "LangChain Not Found",
                    "LangChain is not installed.\n\n"
                    "Please install it with:\n"
                    "pip install -e .[langchain]"
                )
                self.langchain_enabled_check.setChecked(False)

    def _load_profile_settings(self):
        """Load profile settings and update preview."""
        current_profile = self.config.performance_profile.capitalize()
        index = self.profile_combo.findText(current_profile)
        if index >= 0:
            self.profile_combo.setCurrentIndex(index)
        self._on_profile_changed(current_profile)

    def _on_profile_changed(self, text):
        """Update preview label when profile changes."""
        profile = text.lower()
        if profile == "auto":
            profile = None # Let manager auto-detect
        
        recs = self.model_manager.get_recommended_models(tier=profile)
        self.preset_preview_label.setText(
            f"Text: {recs['text']}\n"
            f"Vision: {recs['vision']}"
        )

    @asyncSlot()
    async def _apply_profile_preset(self):
        """Download and apply the preset models for the selected profile."""
        profile = self.profile_combo.currentText().lower()
        if profile == "auto":
            profile = None

        recs = self.model_manager.get_recommended_models(tier=profile)
        
        # models to ensure
        models = [recs['text'], recs['vision']]
        
        # Disable button
        self.apply_preset_button.setEnabled(False)
        self.apply_preset_button.setText("Processing...")
        
        try:
            for model in models:
                if not model: continue
                
                # Check if installed
                installed = await self.model_manager.check_models_installed()
                is_installed = False
                # Simple check against installed dict keys which are recommendations
                # But here 'model' is the full name. 
                # Let's just use download_model which handles pulling if needed
                
                # Create progress dialog because download_model might take time
                progress = QProgressDialog(f"Ensuring {model}...", "Cancel", 0, 0, self)
                progress.setWindowModality(Qt.WindowModality.WindowModal)
                progress.show()
                
                await self.model_manager.download_model(model)
                progress.close()
            
            # Refresh list
            await self._refresh_models()
            
            # Select them in combos
            index = self.text_model_combo.findText(recs['text'])
            if index >= 0: self.text_model_combo.setCurrentIndex(index)
            
            index = self.vision_model_combo.findText(recs['vision'])
            if index >= 0: self.vision_model_combo.setCurrentIndex(index)
            
            QMessageBox.information(self, "Success", "Profile preset downloaded and applied!")
            
        except Exception as e:
            logger.error(f"Failed to apply preset: {e}")
            QMessageBox.critical(self, "Error", f"Failed to apply preset: {e}")
            
        finally:
            self.apply_preset_button.setEnabled(True)
            self.apply_preset_button.setText("Download & Apply Preset")
