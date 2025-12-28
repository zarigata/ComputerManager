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
    QGroupBox, QFormLayout
)
from PyQt6.QtCore import Qt, pyqtSignal
from qasync import asyncSlot

from ..ollama.client import OllamaClient, OllamaConnectionError
from ..ollama.model_manager import ModelManager
from ..utils.config import get_config, ConfigManager
from ..utils.system_info import SystemDetector

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
        self.download_button.clicked.connect(lambda: asyncio.create_task(self._download_model()))
        download_layout.addWidget(self.download_button)
        
        layout.addLayout(download_layout)
        
        # Refresh models button
        self.refresh_models_button = QPushButton("Refresh Model List")
        self.refresh_models_button.clicked.connect(lambda: asyncio.create_task(self._refresh_models()))
        layout.addWidget(self.refresh_models_button)
        
        layout.addStretch()
        
        self.tab_widget.addTab(tab, "Models")
    
    def _create_security_tab(self):
        """Create the Security settings tab."""
        tab = QWidget()
        layout = QFormLayout(tab)
        
        # Permission level
        self.permission_combo = QComboBox()
        self.permission_combo.addItems(["Basic", "Advanced", "Admin"])
        layout.addRow("Permission Level:", self.permission_combo)
        
        # Security options
        self.require_confirmation_check = QCheckBox("Require confirmation for sensitive actions")
        self.require_confirmation_check.setChecked(True)
        layout.addRow(self.require_confirmation_check)
        
        self.enable_audit_check = QCheckBox("Enable audit logging")
        layout.addRow(self.enable_audit_check)
        
        # View audit log button
        self.view_audit_button = QPushButton("View Audit Log")
        self.view_audit_button.clicked.connect(self._view_audit_log)
        layout.addRow(self.view_audit_button)
        
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
        self.test_connection_button.clicked.connect(lambda: asyncio.create_task(self._test_connection()))
        layout.addRow(self.test_connection_button)
        
        self.tab_widget.addTab(tab, "Advanced")
    
    def _load_current_settings(self):
        """Load current settings from config."""
        # General tab
        theme = self.config.gui_settings.get("theme", "System")
        index = self.theme_combo.findText(theme)
        if index >= 0:
            self.theme_combo.setCurrentIndex(index)
        
        self.window_width_spin.setValue(self.config.gui_settings.get("window_width", 800))
        self.window_height_spin.setValue(self.config.gui_settings.get("window_height", 600))
        self.start_minimized_check.setChecked(self.config.gui_settings.get("start_minimized", False))
        self.close_to_tray_check.setChecked(self.config.gui_settings.get("close_to_tray", True))
        
        # Models tab - populate with installed models
        asyncio.create_task(self._refresh_models())
        
        # Security tab
        permission = self.config.permission_level
        index = self.permission_combo.findText(permission.capitalize())
        if index >= 0:
            self.permission_combo.setCurrentIndex(index)
        
        self.require_confirmation_check.setChecked(
            self.config.security_settings.get("require_confirmation", True)
        )
        self.enable_audit_check.setChecked(
            self.config.security_settings.get("enable_audit", False)
        )
        
        # Advanced tab
        self.ollama_host_input.setText(self.config.ollama_host)
        self.timeout_spin.setValue(self.config.ollama_timeout)
        self.max_history_spin.setValue(self.config.max_chat_history)
    
    @asyncSlot()
    async def _refresh_models(self):
        """Refresh the list of installed models."""
        try:
            self.refresh_models_button.setEnabled(False)
            self.refresh_models_button.setText("Refreshing...")
            
            # Get installed models
            models = await self.model_manager.list_all_installed_models()
            
            # Update text model combo
            current_text_model = self.config.text_model
            self.text_model_combo.clear()
            self.text_model_combo.addItems(models)
            
            index = self.text_model_combo.findText(current_text_model)
            if index >= 0:
                self.text_model_combo.setCurrentIndex(index)
            
            # Update vision model combo (filter for vision-capable models)
            current_vision_model = self.config.vision_model
            vision_models = [m for m in models if "vision" in m.lower() or "llava" in m.lower()]
            self.vision_model_combo.clear()
            self.vision_model_combo.addItems(vision_models if vision_models else ["No vision models installed"])
            
            index = self.vision_model_combo.findText(current_vision_model)
            if index >= 0:
                self.vision_model_combo.setCurrentIndex(index)
            
            logger.info(f"Refreshed model list: {len(models)} models found")
            
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
        # TODO: Implement audit log viewer
        QMessageBox.information(self, "Audit Log", "Audit log viewer not yet implemented.")
    
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
        self.config.gui_settings["theme"] = self.theme_combo.currentText()
        self.config.gui_settings["window_width"] = self.window_width_spin.value()
        self.config.gui_settings["window_height"] = self.window_height_spin.value()
        self.config.gui_settings["start_minimized"] = self.start_minimized_check.isChecked()
        self.config.gui_settings["close_to_tray"] = self.close_to_tray_check.isChecked()
        
        # Model settings
        text_model = self.text_model_combo.currentText()
        if text_model:
            self.config.text_model = text_model
        
        vision_model = self.vision_model_combo.currentText()
        if vision_model and vision_model != "No vision models installed":
            self.config.vision_model = vision_model
        
        # Security settings
        self.config.permission_level = self.permission_combo.currentText().lower()
        self.config.security_settings["require_confirmation"] = self.require_confirmation_check.isChecked()
        self.config.security_settings["enable_audit"] = self.enable_audit_check.isChecked()
        
        # Advanced settings
        host = self.ollama_host_input.text().strip()
        if host:
            self.config.ollama_host = host
        
        self.config.ollama_timeout = self.timeout_spin.value()
        self.config.max_chat_history = self.max_history_spin.value()
        
        # Save to file
        self.config_manager.save_config(self.config)
        
        logger.info("Settings saved successfully")
