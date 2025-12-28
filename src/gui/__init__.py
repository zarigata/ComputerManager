"""GUI package initialization."""

from .chat_window import ChatWindow
from .system_tray import SystemTrayManager
from .settings_dialog import SettingsDialog
from .themes import apply_theme, detect_system_theme

__all__ = [
    "ChatWindow",
    "SystemTrayManager",
    "SettingsDialog",
    "apply_theme",
    "detect_system_theme",
]
