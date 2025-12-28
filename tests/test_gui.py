"""
GUI component tests using pytest-qt.

This module provides tests for the chat window, settings dialog,
and system tray components.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

from src.gui.chat_window import ChatWindow
from src.gui.settings_dialog import SettingsDialog
from src.gui.system_tray import SystemTrayManager
from src.ollama.client import OllamaClient
from src.utils.config import AppConfig


@pytest.fixture
def mock_ollama_client():
    """Create a mock Ollama client."""
    client = Mock(spec=OllamaClient)
    client.check_connection = AsyncMock()
    client.chat = AsyncMock()
    return client


@pytest.fixture
def mock_config():
    """Create a mock configuration."""
    config = Mock(spec=AppConfig)
    config.text_model = "llama3.2:3b"
    config.vision_model = "llava:7b"
    config.ollama_host = "http://localhost:11434"
    config.ollama_timeout = 60
    config.max_chat_history = 100
    config.permission_level = "basic"
    config.gui_settings = {
        "window_width": 800,
        "window_height": 600,
        "theme": "System",
        "start_minimized": False,
        "close_to_tray": True
    }
    config.security_settings = {
        "require_confirmation": True,
        "enable_audit": False
    }
    return config


class TestChatWindow:
    """Tests for ChatWindow component."""
    
    def test_chat_window_initialization(self, qtbot, mock_ollama_client, mock_config):
        """Test chat window initializes correctly."""
        with patch('src.gui.chat_window.get_config', return_value=mock_config):
            window = ChatWindow(mock_ollama_client)
            qtbot.addWidget(window)
            
            assert window.windowTitle() == "Computer Manager - AI Assistant"
            assert window.ollama_client == mock_ollama_client
            assert window.conversation_history == []
            assert not window.is_streaming
    
    def test_add_user_message(self, qtbot, mock_ollama_client, mock_config):
        """Test adding user message to history."""
        with patch('src.gui.chat_window.get_config', return_value=mock_config):
            window = ChatWindow(mock_ollama_client)
            qtbot.addWidget(window)
            
            window.add_user_message("Hello, AI!")
            
            assert len(window.conversation_history) == 1
            assert window.conversation_history[0]["role"] == "user"
            assert window.conversation_history[0]["content"] == "Hello, AI!"
    
    def test_add_assistant_message(self, qtbot, mock_ollama_client, mock_config):
        """Test adding assistant message to history."""
        with patch('src.gui.chat_window.get_config', return_value=mock_config):
            window = ChatWindow(mock_ollama_client)
            qtbot.addWidget(window)
            
            window.add_assistant_message("Hello, human!")
            
            assert len(window.conversation_history) == 1
            assert window.conversation_history[0]["role"] == "assistant"
            assert window.conversation_history[0]["content"] == "Hello, human!"
    
    def test_max_history_limit(self, qtbot, mock_ollama_client, mock_config):
        """Test conversation history respects max limit."""
        mock_config.max_chat_history = 5
        
        with patch('src.gui.chat_window.get_config', return_value=mock_config):
            window = ChatWindow(mock_ollama_client)
            qtbot.addWidget(window)
            
            # Add more messages than the limit
            for i in range(10):
                window.add_user_message(f"Message {i}")
            
            # Should only keep the last 5
            assert len(window.conversation_history) == 5
            assert window.conversation_history[-1]["content"] == "Message 9"
    
    def test_clear_chat(self, qtbot, mock_ollama_client, mock_config):
        """Test clearing chat history."""
        with patch('src.gui.chat_window.get_config', return_value=mock_config):
            window = ChatWindow(mock_ollama_client)
            qtbot.addWidget(window)
            
            # Add some messages
            window.add_user_message("Test message")
            window.add_assistant_message("Test response")
            
            # Mock the confirmation dialog to return Yes
            with patch('PyQt6.QtWidgets.QMessageBox.question', return_value=2):  # Yes button
                window.clear_chat()
            
            assert len(window.conversation_history) == 0
    
    @pytest.mark.asyncio
    async def test_send_message_streaming(self, qtbot, mock_ollama_client, mock_config):
        """Test sending message with streaming response."""
        # Mock streaming response
        async def mock_stream(*args, **kwargs):
            for chunk in ["Hello", " ", "world", "!"]:
                yield chunk
        
        mock_ollama_client.chat.return_value = mock_stream()
        
        with patch('src.gui.chat_window.get_config', return_value=mock_config):
            window = ChatWindow(mock_ollama_client)
            qtbot.addWidget(window)
            
            window.input_field.setPlainText("Test message")
            
            # Send message
            await window.send_message()
            
            # Verify message was added to history
            assert len(window.conversation_history) == 2  # User + assistant
            assert window.conversation_history[0]["role"] == "user"
            assert window.conversation_history[1]["role"] == "assistant"
            assert window.conversation_history[1]["content"] == "Hello world!"


class TestSettingsDialog:
    """Tests for SettingsDialog component."""
    
    def test_settings_dialog_initialization(self, qtbot, mock_config):
        """Test settings dialog initializes correctly."""
        with patch('src.gui.settings_dialog.get_config', return_value=mock_config):
            with patch('src.gui.settings_dialog.OllamaClient'):
                with patch('src.gui.settings_dialog.ModelManager'):
                    dialog = SettingsDialog()
                    qtbot.addWidget(dialog)
                    
                    assert dialog.windowTitle() == "Settings"
                    assert dialog.tab_widget.count() == 4  # 4 tabs
    
    def test_load_current_settings(self, qtbot, mock_config):
        """Test loading current settings into dialog."""
        with patch('src.gui.settings_dialog.get_config', return_value=mock_config):
            with patch('src.gui.settings_dialog.OllamaClient'):
                with patch('src.gui.settings_dialog.ModelManager'):
                    dialog = SettingsDialog()
                    qtbot.addWidget(dialog)
                    
                    # Check values are loaded
                    assert dialog.window_width_spin.value() == 800
                    assert dialog.window_height_spin.value() == 600
                    assert dialog.ollama_host_input.text() == "http://localhost:11434"
                    assert dialog.timeout_spin.value() == 60
    
    def test_validate_ollama_host(self, qtbot, mock_config):
        """Test Ollama host URL validation."""
        with patch('src.gui.settings_dialog.get_config', return_value=mock_config):
            with patch('src.gui.settings_dialog.OllamaClient'):
                with patch('src.gui.settings_dialog.ModelManager'):
                    dialog = SettingsDialog()
                    qtbot.addWidget(dialog)
                    
                    # Invalid URL
                    dialog.ollama_host_input.setText("invalid-url")
                    assert not dialog._validate_settings()
                    
                    # Valid URL
                    dialog.ollama_host_input.setText("http://localhost:11434")
                    assert dialog._validate_settings()


class TestSystemTray:
    """Tests for SystemTrayManager component."""
    
    def test_system_tray_initialization(self, qtbot, mock_ollama_client, mock_config):
        """Test system tray initializes correctly."""
        with patch('src.gui.chat_window.get_config', return_value=mock_config):
            window = ChatWindow(mock_ollama_client)
            qtbot.addWidget(window)
            
            tray = SystemTrayManager(window)
            
            assert tray.main_window == window
            assert tray.tray_icon is not None
            assert tray.tray_icon.isVisible()
    
    def test_toggle_window(self, qtbot, mock_ollama_client, mock_config):
        """Test toggling window visibility."""
        with patch('src.gui.chat_window.get_config', return_value=mock_config):
            window = ChatWindow(mock_ollama_client)
            qtbot.addWidget(window)
            
            tray = SystemTrayManager(window)
            
            # Show window
            window.show()
            assert window.isVisible()
            
            # Toggle to hide
            tray.toggle_window()
            assert not window.isVisible()
            
            # Toggle to show
            tray.toggle_window()
            assert window.isVisible()
    
    def test_show_notification(self, qtbot, mock_ollama_client, mock_config):
        """Test showing system tray notification."""
        with patch('src.gui.chat_window.get_config', return_value=mock_config):
            window = ChatWindow(mock_ollama_client)
            qtbot.addWidget(window)
            
            tray = SystemTrayManager(window)
            
            # Should not raise any exceptions
            tray.show_notification("Test Title", "Test Message")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
