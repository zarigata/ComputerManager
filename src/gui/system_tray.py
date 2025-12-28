"""
System tray integration for the Computer Manager application.

This module provides system tray icon, context menu, and notification support
for quick access and minimize-to-tray functionality.
"""

import logging
from pathlib import Path
from typing import Optional

from PyQt6.QtWidgets import QSystemTrayIcon, QMenu
from PyQt6.QtGui import QIcon, QAction
from PyQt6.QtCore import Qt

logger = logging.getLogger(__name__)


class SystemTrayManager:
    """Manages system tray icon and interactions."""
    
    def __init__(self, main_window):
        """
        Initialize system tray manager.
        
        Args:
            main_window: Reference to the main ChatWindow instance
        """
        self.main_window = main_window
        self.tray_icon: Optional[QSystemTrayIcon] = None
        self.first_minimize = True
        
        self._create_tray_icon()
        self._create_context_menu()
        
        logger.info("System tray manager initialized")
    
    def _create_tray_icon(self):
        """Create and configure the system tray icon."""
        # Create tray icon
        self.tray_icon = QSystemTrayIcon(self.main_window)
        
        # Load application icon (use placeholder if not exists)
        icon_path = Path(__file__).parent.parent.parent / "assets" / "icon.png"
        if icon_path.exists():
            icon = QIcon(str(icon_path))
        else:
            # Use default application icon
            icon = self.main_window.style().standardIcon(
                self.main_window.style().StandardPixmap.SP_ComputerIcon
            )
        
        self.tray_icon.setIcon(icon)
        self.tray_icon.setToolTip("Computer Manager - AI Assistant")
        
        # Connect activation signal (double-click)
        self.tray_icon.activated.connect(self._on_tray_activated)
        
        # Show tray icon
        self.tray_icon.show()
    
    def _create_context_menu(self):
        """Create the context menu for the tray icon."""
        menu = QMenu()
        
        # Show/Hide action
        self.show_hide_action = QAction("Show Window", menu)
        self.show_hide_action.triggered.connect(self.toggle_window)
        menu.addAction(self.show_hide_action)
        
        menu.addSeparator()
        
        # New Chat action
        new_chat_action = QAction("New Chat", menu)
        new_chat_action.triggered.connect(self.main_window.clear_chat)
        menu.addAction(new_chat_action)
        
        # Settings action
        settings_action = QAction("Settings", menu)
        settings_action.triggered.connect(self.main_window.open_settings)
        menu.addAction(settings_action)
        
        menu.addSeparator()
        
        # Quit action
        quit_action = QAction("Quit", menu)
        quit_action.triggered.connect(self._quit_application)
        menu.addAction(quit_action)
        
        self.tray_icon.setContextMenu(menu)
    
    def _on_tray_activated(self, reason):
        """
        Handle tray icon activation.
        
        Args:
            reason: Activation reason (click, double-click, etc.)
        """
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.toggle_window()
    
    def toggle_window(self):
        """Toggle main window visibility."""
        if self.main_window.isVisible():
            self.main_window.hide()
            self.show_hide_action.setText("Show Window")
            logger.debug("Main window hidden")
        else:
            self.main_window.show()
            self.main_window.activateWindow()
            self.main_window.raise_()
            self.show_hide_action.setText("Hide Window")
            logger.debug("Main window shown")
    
    def show_notification(self, title: str, message: str, duration: int = 3000):
        """
        Show a system tray notification.
        
        Args:
            title: Notification title
            message: Notification message
            duration: Display duration in milliseconds (default: 3000)
        """
        if self.tray_icon and self.tray_icon.isVisible():
            self.tray_icon.showMessage(
                title,
                message,
                QSystemTrayIcon.MessageIcon.Information,
                duration
            )
            logger.debug(f"Notification shown: {title}")
    
    def show_first_minimize_notification(self):
        """Show notification on first minimize explaining tray behavior."""
        if self.first_minimize:
            self.show_notification(
                "Computer Manager",
                "Application minimized to system tray. Double-click the tray icon to restore.",
                5000
            )
            self.first_minimize = False
    
    def _quit_application(self):
        """Quit the application completely."""
        logger.info("Quitting application from system tray")
        
        # Hide tray icon
        if self.tray_icon:
            self.tray_icon.hide()
        
        # Close main window (this will trigger cleanup)
        self.main_window.close()
        
        # Quit application
        from PyQt6.QtWidgets import QApplication
        QApplication.quit()
