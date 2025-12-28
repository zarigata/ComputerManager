"""
Theme definitions and styling for the GUI application.

This module provides theme management including system, light, and dark themes
with cross-platform native look and feel support.
"""

import logging
from typing import Optional

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QPalette, QColor
from PyQt6.QtCore import Qt

logger = logging.getLogger(__name__)


def apply_theme(app: QApplication, theme_name: str):
    """
    Apply a theme to the application.
    
    Args:
        app: QApplication instance
        theme_name: Theme name ("System", "Light", or "Dark")
    """
    theme_name = theme_name.lower()
    
    if theme_name == "system":
        _apply_system_theme(app)
    elif theme_name == "light":
        _apply_light_theme(app)
    elif theme_name == "dark":
        _apply_dark_theme(app)
    else:
        logger.warning(f"Unknown theme: {theme_name}, using system theme")
        _apply_system_theme(app)
    
    logger.info(f"Applied theme: {theme_name}")


def _apply_system_theme(app: QApplication):
    """Apply system default theme."""
    # Reset to default style
    app.setStyleSheet("")
    app.setPalette(app.style().standardPalette())
    
    # Use platform-specific style
    import platform
    system = platform.system()
    
    if system == "Windows":
        app.setStyle("windowsvista")
    elif system == "Darwin":  # macOS
        app.setStyle("macOS")
    else:  # Linux
        app.setStyle("Fusion")


def _apply_light_theme(app: QApplication):
    """Apply custom light theme."""
    app.setStyle("Fusion")
    
    # Create light palette
    palette = QPalette()
    
    # Base colors
    palette.setColor(QPalette.ColorRole.Window, QColor(240, 240, 240))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(0, 0, 0))
    palette.setColor(QPalette.ColorRole.Base, QColor(255, 255, 255))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor(245, 245, 245))
    palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(255, 255, 220))
    palette.setColor(QPalette.ColorRole.ToolTipText, QColor(0, 0, 0))
    palette.setColor(QPalette.ColorRole.Text, QColor(0, 0, 0))
    palette.setColor(QPalette.ColorRole.Button, QColor(240, 240, 240))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor(0, 0, 0))
    palette.setColor(QPalette.ColorRole.BrightText, QColor(255, 0, 0))
    
    # Highlight colors
    palette.setColor(QPalette.ColorRole.Highlight, QColor(0, 120, 212))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor(255, 255, 255))
    
    # Disabled colors
    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.WindowText, QColor(127, 127, 127))
    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text, QColor(127, 127, 127))
    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText, QColor(127, 127, 127))
    
    app.setPalette(palette)
    
    # Additional stylesheet for modern look
    stylesheet = """
        QMainWindow {
            background-color: #f0f0f0;
        }
        
        QToolBar {
            background-color: #ffffff;
            border-bottom: 1px solid #d0d0d0;
            spacing: 5px;
            padding: 5px;
        }
        
        QMenuBar {
            background-color: #ffffff;
            border-bottom: 1px solid #d0d0d0;
        }
        
        QMenuBar::item:selected {
            background-color: #e0e0e0;
        }
        
        QMenu {
            background-color: #ffffff;
            border: 1px solid #d0d0d0;
        }
        
        QMenu::item:selected {
            background-color: #0078d4;
            color: white;
        }
        
        QPushButton {
            background-color: #ffffff;
            border: 1px solid #d0d0d0;
            border-radius: 4px;
            padding: 5px 15px;
        }
        
        QPushButton:hover {
            background-color: #e0e0e0;
        }
        
        QPushButton:pressed {
            background-color: #d0d0d0;
        }
        
        QLineEdit, QTextEdit, QSpinBox, QComboBox {
            background-color: #ffffff;
            border: 1px solid #d0d0d0;
            border-radius: 4px;
            padding: 4px;
        }
        
        QLineEdit:focus, QTextEdit:focus {
            border: 2px solid #0078d4;
        }
        
        QScrollBar:vertical {
            background-color: #f0f0f0;
            width: 12px;
            margin: 0px;
        }
        
        QScrollBar::handle:vertical {
            background-color: #c0c0c0;
            border-radius: 6px;
            min-height: 20px;
        }
        
        QScrollBar::handle:vertical:hover {
            background-color: #a0a0a0;
        }
    """
    
    app.setStyleSheet(stylesheet)


def _apply_dark_theme(app: QApplication):
    """Apply custom dark theme."""
    app.setStyle("Fusion")
    
    # Create dark palette
    palette = QPalette()
    
    # Base colors
    palette.setColor(QPalette.ColorRole.Window, QColor(45, 45, 48))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(255, 255, 255))
    palette.setColor(QPalette.ColorRole.Base, QColor(30, 30, 30))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor(45, 45, 48))
    palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(255, 255, 255))
    palette.setColor(QPalette.ColorRole.ToolTipText, QColor(255, 255, 255))
    palette.setColor(QPalette.ColorRole.Text, QColor(255, 255, 255))
    palette.setColor(QPalette.ColorRole.Button, QColor(45, 45, 48))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor(255, 255, 255))
    palette.setColor(QPalette.ColorRole.BrightText, QColor(255, 0, 0))
    
    # Highlight colors
    palette.setColor(QPalette.ColorRole.Highlight, QColor(0, 120, 212))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor(255, 255, 255))
    
    # Link colors
    palette.setColor(QPalette.ColorRole.Link, QColor(42, 130, 218))
    
    # Disabled colors
    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.WindowText, QColor(127, 127, 127))
    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text, QColor(127, 127, 127))
    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText, QColor(127, 127, 127))
    
    app.setPalette(palette)
    
    # Additional stylesheet for modern dark look
    stylesheet = """
        QMainWindow {
            background-color: #2d2d30;
        }
        
        QToolBar {
            background-color: #3e3e42;
            border-bottom: 1px solid #1e1e1e;
            spacing: 5px;
            padding: 5px;
        }
        
        QMenuBar {
            background-color: #3e3e42;
            border-bottom: 1px solid #1e1e1e;
        }
        
        QMenuBar::item:selected {
            background-color: #505050;
        }
        
        QMenu {
            background-color: #3e3e42;
            border: 1px solid #1e1e1e;
        }
        
        QMenu::item:selected {
            background-color: #0078d4;
            color: white;
        }
        
        QPushButton {
            background-color: #3e3e42;
            border: 1px solid #555555;
            border-radius: 4px;
            padding: 5px 15px;
            color: white;
        }
        
        QPushButton:hover {
            background-color: #505050;
        }
        
        QPushButton:pressed {
            background-color: #404040;
        }
        
        QLineEdit, QTextEdit, QSpinBox, QComboBox {
            background-color: #1e1e1e;
            border: 1px solid #555555;
            border-radius: 4px;
            padding: 4px;
            color: white;
        }
        
        QLineEdit:focus, QTextEdit:focus {
            border: 2px solid #0078d4;
        }
        
        QScrollBar:vertical {
            background-color: #2d2d30;
            width: 12px;
            margin: 0px;
        }
        
        QScrollBar::handle:vertical {
            background-color: #555555;
            border-radius: 6px;
            min-height: 20px;
        }
        
        QScrollBar::handle:vertical:hover {
            background-color: #666666;
        }
        
        QLabel {
            color: white;
        }
        
        QCheckBox {
            color: white;
        }
        
        QGroupBox {
            color: white;
            border: 1px solid #555555;
            border-radius: 4px;
            margin-top: 10px;
            padding-top: 10px;
        }
        
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 5px;
        }
        
        QTabWidget::pane {
            border: 1px solid #555555;
            background-color: #2d2d30;
        }
        
        QTabBar::tab {
            background-color: #3e3e42;
            border: 1px solid #555555;
            padding: 5px 10px;
            color: white;
        }
        
        QTabBar::tab:selected {
            background-color: #2d2d30;
            border-bottom: 2px solid #0078d4;
        }
        
        QTabBar::tab:hover {
            background-color: #505050;
        }
    """
    
    app.setStyleSheet(stylesheet)


def detect_system_theme() -> str:
    """
    Detect the system's current theme preference.
    
    Returns:
        "light" or "dark" based on system settings
    """
    try:
        import platform
        system = platform.system()
        
        if system == "Windows":
            return _detect_windows_theme()
        elif system == "Darwin":  # macOS
            return _detect_macos_theme()
        else:  # Linux
            return _detect_linux_theme()
    except Exception as e:
        logger.warning(f"Failed to detect system theme: {e}")
        return "light"


def _detect_windows_theme() -> str:
    """Detect Windows theme preference."""
    try:
        import winreg
        registry = winreg.ConnectRegistry(None, winreg.HKEY_CURRENT_USER)
        key = winreg.OpenKey(
            registry,
            r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"
        )
        value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
        winreg.CloseKey(key)
        return "light" if value == 1 else "dark"
    except:
        return "light"


def _detect_macos_theme() -> str:
    """Detect macOS theme preference."""
    try:
        import subprocess
        result = subprocess.run(
            ["defaults", "read", "-g", "AppleInterfaceStyle"],
            capture_output=True,
            text=True
        )
        return "dark" if "Dark" in result.stdout else "light"
    except:
        return "light"


def _detect_linux_theme() -> str:
    """Detect Linux theme preference."""
    try:
        import subprocess
        result = subprocess.run(
            ["gsettings", "get", "org.gnome.desktop.interface", "gtk-theme"],
            capture_output=True,
            text=True
        )
        return "dark" if "dark" in result.stdout.lower() else "light"
    except:
        return "light"
