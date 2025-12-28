"""
Chat window implementation with streaming support for Ollama responses.

This module provides the main chat interface with real-time message streaming,
conversation history management, and integration with the Ollama client.
"""

import asyncio
import logging
from typing import List, Dict, Optional
from pathlib import Path

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTextEdit, QLineEdit, QPushButton, QScrollArea,
    QLabel, QToolBar, QMessageBox
)
from PyQt6.QtCore import pyqtSignal, Qt, QTimer
from PyQt6.QtGui import QTextCursor, QFont, QAction
from qasync import asyncSlot

from ..ollama.client import OllamaClient, OllamaConnectionError
from ..utils.config import get_config
from ..security.permissions import PermissionManager, PermissionLevel

logger = logging.getLogger(__name__)


class ChatWindow(QMainWindow):
    """Main chat window with streaming message support."""
    
    # Custom signals for thread-safe UI updates
    message_chunk_received = pyqtSignal(str)
    streaming_started = pyqtSignal()
    streaming_finished = pyqtSignal()
    error_occurred = pyqtSignal(str)
    
    def __init__(self, ollama_client: OllamaClient, agent=None):
        super().__init__()
        self.ollama_client = ollama_client
        self.agent = agent  # Optional Agent instance
        self.config = get_config()
        self.conversation_history: List[Dict[str, str]] = []
        self.current_response = ""
        self.is_streaming = False
        
        # Initialize security components
        self.permission_manager = PermissionManager(self.config)
        
        self._init_ui()
        self._connect_signals()
        
        mode = "Agent Mode" if self.agent else "Direct Mode"
        logger.info(f"Chat window initialized in {mode}")
    
    def _init_ui(self):
        """Initialize the user interface."""
        self.setWindowTitle("Computer Manager - AI Assistant")
        
        # Restore window geometry or set default
        self.resize(
            self.config.window_width,
            self.config.window_height
        )
        self.setMinimumSize(600, 400)
        
        # Create central widget and main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Create toolbar
        self._create_toolbar()
        
        # Create message display area
        self.message_display = QTextEdit()
        self.message_display.setReadOnly(True)
        self.message_display.setFont(QFont("Segoe UI", 10))
        self.message_display.setStyleSheet("""
            QTextEdit {
                background-color: #f5f5f5;
                border: none;
                padding: 10px;
            }
        """)
        main_layout.addWidget(self.message_display, stretch=1)
        
        # Create status bar
        self.status_label = QLabel("Ready")
        self.model_label = QLabel(f"Model: {self.config.default_text_model}")
        self.streaming_indicator = QLabel("")
        
        # Add security status indicator
        self.security_status_label = QLabel()
        self._update_security_status()
        
        status_layout = QHBoxLayout()
        status_layout.addWidget(self.status_label)
        status_layout.addStretch()
        status_layout.addWidget(self.security_status_label)
        status_layout.addWidget(self.streaming_indicator)
        status_layout.addWidget(self.model_label)
        status_layout.setContentsMargins(10, 5, 10, 5)
        
        status_widget = QWidget()
        status_widget.setStyleSheet("background-color: #e0e0e0;")
        status_widget.setLayout(status_layout)
        main_layout.addWidget(status_widget)
        
        # Create input area
        input_layout = QHBoxLayout()
        input_layout.setContentsMargins(10, 10, 10, 10)
        input_layout.setSpacing(10)
        
        self.input_field = QTextEdit()
        self.input_field.setMaximumHeight(100)
        self.input_field.setPlaceholderText("Type your message here... (Shift+Enter for new line)")
        self.input_field.setFont(QFont("Segoe UI", 10))
        self.input_field.installEventFilter(self)
        input_layout.addWidget(self.input_field, stretch=1)
        
        self.send_button = QPushButton("Send")
        self.send_button.setMinimumWidth(80)
        self.send_button.setMinimumHeight(40)
        self.send_button.setStyleSheet("""
            QPushButton {
                background-color: #0078d4;
                color: white;
                border: none;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #106ebe;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        self.send_button.clicked.connect(self.send_message)
        input_layout.addWidget(self.send_button)
        
        input_widget = QWidget()
        input_widget.setLayout(input_layout)
        main_layout.addWidget(input_widget)
    
    def _create_toolbar(self):
        """Create the application toolbar."""
        toolbar = QToolBar()
        toolbar.setMovable(False)
        self.addToolBar(toolbar)
        
        # New chat action
        new_chat_action = QAction("New Chat", self)
        new_chat_action.setShortcut("Ctrl+N")
        new_chat_action.triggered.connect(self.clear_chat)
        toolbar.addAction(new_chat_action)
        
        toolbar.addSeparator()
        
        # Settings action
        settings_action = QAction("Settings", self)
        settings_action.setShortcut("Ctrl+,")
        settings_action.triggered.connect(self.open_settings)
        toolbar.addAction(settings_action)
    
    def _connect_signals(self):
        """Connect signals to their respective slots."""
        self.message_chunk_received.connect(self._append_chunk)
        self.streaming_started.connect(self._on_streaming_started)
        self.streaming_finished.connect(self._on_streaming_finished)
        self.error_occurred.connect(self._show_error)
    
    def eventFilter(self, obj, event):
        """Handle keyboard events for the input field."""
        if obj == self.input_field and event.type() == event.Type.KeyPress:
            # Send on Enter, new line on Shift+Enter
            if event.key() == Qt.Key.Key_Return or event.key() == Qt.Key.Key_Enter:
                if event.modifiers() == Qt.KeyboardModifier.ShiftModifier:
                    return False  # Allow default behavior (new line)
                else:
                    asyncio.create_task(self.send_message())
                    return True  # Consume event
        return super().eventFilter(obj, event)
    
    @asyncSlot()
    async def send_message(self):
        """Send user message and stream AI response."""
        if self.is_streaming:
            return
        
        user_message = self.input_field.toPlainText().strip()
        if not user_message:
            return
        
        # Clear input field
        self.input_field.clear()
        
        # Add user message to display and history
        self.add_user_message(user_message)
        
        # Start streaming response
        self.streaming_started.emit()
        
        try:
            if self.agent:
                # Agent mode: use agent for processing (non-streaming)
                self._show_tool_execution("Processing with agent...")
                response = await self.agent.process_message(user_message)
                
                # Display the complete response
                self.current_response = response
                self.message_chunk_received.emit(response)
                
                # Add to history (agent manages its own history internally)
                # We don't need to add to self.conversation_history as agent handles it
            else:
                # Direct mode: stream response from Ollama
                self.current_response = ""
                
                # Stream response from Ollama
                async for chunk in self.ollama_client.chat(
                    model=self.config.default_text_model,
                    messages=self.conversation_history,
                    stream=True
                ):
                    # Parse chunk dict from Ollama - extract content string
                    if chunk:
                        content = chunk.get('message', {}).get('content', '')
                        if content:
                            self.current_response += content
                            self.message_chunk_received.emit(content)
                
                # Add complete response to history
                self.add_assistant_message(self.current_response)
            
        except OllamaConnectionError as e:
            logger.error(f"Ollama connection error: {e}")
            self.error_occurred.emit(
                "Failed to connect to Ollama. Please ensure Ollama is running."
            )
        except Exception as e:
            logger.error(f"Unexpected error during chat: {e}", exc_info=True)
            self.error_occurred.emit(f"An error occurred: {str(e)}")
        finally:
            self.streaming_finished.emit()
    
    def add_user_message(self, message: str):
        """Add user message to display and history."""
        self.conversation_history.append({
            "role": "user",
            "content": message
        })
        
        # Enforce max history limit
        max_history = self.config.max_chat_history
        if len(self.conversation_history) > max_history:
            self.conversation_history = self.conversation_history[-max_history:]
        
        # Display message
        self._append_message("You", message, "#0078d4")
        
        logger.debug(f"User message added: {message[:50]}...")
    
    def add_assistant_message(self, message: str):
        """Add assistant message to history."""
        self.conversation_history.append({
            "role": "assistant",
            "content": message
        })
        
        # Enforce max history limit
        max_history = self.config.max_chat_history
        if len(self.conversation_history) > max_history:
            self.conversation_history = self.conversation_history[-max_history:]
        
        logger.debug(f"Assistant message added: {message[:50]}...")
    
    def _append_message(self, sender: str, message: str, color: str):
        """Append a complete message to the display."""
        cursor = self.message_display.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        
        # Add sender header
        cursor.insertHtml(
            f'<div style="margin: 10px 0;"><b style="color: {color};">{sender}:</b></div>'
        )
        
        # Add message content
        cursor.insertHtml(
            f'<div style="margin: 0 0 10px 20px; white-space: pre-wrap;">{self._format_message(message)}</div>'
        )
        
        # Auto-scroll to bottom
        self.message_display.setTextCursor(cursor)
        self.message_display.ensureCursorVisible()
    
    def _append_chunk(self, chunk: str):
        """Append a streaming chunk to the display."""
        cursor = self.message_display.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.insertText(chunk)
        
        self.message_display.setTextCursor(cursor)
        self.message_display.ensureCursorVisible()
    
    def _format_message(self, message: str) -> str:
        """Format message with basic HTML escaping."""
        return message.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br>")
    
    def _on_streaming_started(self):
        """Handle streaming start."""
        self.is_streaming = True
        self.send_button.setEnabled(False)
        self.input_field.setEnabled(False)
        self.streaming_indicator.setText("● Streaming...")
        self.streaming_indicator.setStyleSheet("color: #0078d4;")
        self.status_label.setText("AI is responding...")
        
        # Add AI header
        cursor = self.message_display.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.insertHtml(
            '<div style="margin: 10px 0;"><b style="color: #107c10;">AI:</b></div>'
            '<div style="margin: 0 0 10px 20px; white-space: pre-wrap;">'
        )
        self.message_display.setTextCursor(cursor)
    
    def _on_streaming_finished(self):
        """Handle streaming completion."""
        self.is_streaming = False
        self.send_button.setEnabled(True)
        self.input_field.setEnabled(True)
        self.streaming_indicator.setText("")
        self.status_label.setText("Ready")
        
        # Close the message div
        cursor = self.message_display.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.insertHtml('</div>')
        self.message_display.setTextCursor(cursor)
    
    def _show_error(self, error_message: str):
        """Show error dialog."""
        QMessageBox.critical(self, "Error", error_message)
        self.status_label.setText("Error occurred")
    
    def clear_chat(self):
        """Clear the chat history and display."""
        reply = QMessageBox.question(
            self,
            "Clear Chat",
            "Are you sure you want to clear the chat history?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.conversation_history.clear()
            self.message_display.clear()
            self.status_label.setText("Chat cleared")
            logger.info("Chat history cleared")
    
    def open_settings(self):
        """Open settings dialog."""
        # Import here to avoid circular dependency
        from .settings_dialog import SettingsDialog
        
        dialog = SettingsDialog(self)
        if dialog.exec():
            # Reload config after settings change
            self.config = get_config()
            self.model_label.setText(f"Model: {self.config.default_text_model}")
            logger.info("Settings updated")
    
    def _show_tool_execution(self, message: str):
        """Show tool execution indicator."""
        self.status_label.setText(message)
        self.status_label.setStyleSheet("color: #ff8c00;")
    
    def _update_security_status(self):
        """Update security status indicator."""
        # Get current permission level
        level = self.permission_manager.get_current_level()
        is_admin = self.permission_manager.is_admin()
        
        # Set icon and color based on level
        if level == PermissionLevel.BASIC:
            icon = "🛡️"
            color = "#107c10"  # Green
            text = "Basic"
        elif level == PermissionLevel.ADVANCED:
            icon = "🛡️"
            color = "#ff8c00"  # Orange
            text = "Advanced"
        else:  # ADMIN
            icon = "🔒" if is_admin else "🛡️"
            color = "#d13438"  # Red
            text = "Admin"
        
        # Add admin indicator if running as admin
        admin_suffix = " (Elevated)" if is_admin else ""
        
        self.security_status_label.setText(
            f"<span style='color: {color}; font-weight: bold;'>{icon} {text}{admin_suffix}</span>"
        )
        self.security_status_label.setToolTip(
            f"Permission Level: {text}\n"
            f"Admin Privileges: {'Yes' if is_admin else 'No'}"
        )
    
    def closeEvent(self, event):
        """Handle window close event."""
        # Save window geometry
        self.config.window_width = self.width()
        self.config.window_height = self.height()
        
        # Let system tray handle the close behavior
        event.ignore()
        self.hide()
