"""
Computer Manager - Main Entrypoint

GUI application with async Ollama integration for AI-powered computer management.
"""

import sys
import asyncio
import logging
from pathlib import Path

from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtGui import QIcon
from qasync import QEventLoop

from src.utils.config import get_config
from src.utils.system_info import SystemDetector
from src.ollama.client import OllamaClient, OllamaConnectionError
from src.ollama.model_manager import ModelManager
from src.gui import ChatWindow, SystemTrayManager, apply_theme, detect_system_theme
from src.agent import Agent, get_tool_registry, initialize_builtin_tools, initialize_langchain_tools
from src.automation import register_file_tools, register_app_control_tools, register_screen_tools, register_keyboard_mouse_tools, register_platform_tools
from src.ollama.vision import register_vision_tools

# Configure basic logging (file handler will be added after config init)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


async def startup_checks(ollama_client: OllamaClient, model_manager: ModelManager) -> bool:
    """
    Perform startup checks for Ollama connection and models.
    
    Args:
        ollama_client: OllamaClient instance
        model_manager: ModelManager instance
    
    Returns:
        True if all checks pass, False otherwise
    """
    # Check Ollama connection
    logger.info("Checking Ollama connection...")
    max_retries = 3
    
    for attempt in range(max_retries):
        try:
            await ollama_client.check_connection()
            logger.info("Ollama connection successful")
            break
        except OllamaConnectionError as e:
            logger.warning(f"Ollama connection attempt {attempt + 1}/{max_retries} failed: {e}")
            
            if attempt == max_retries - 1:
                # Show error dialog
                reply = QMessageBox.critical(
                    None,
                    "Ollama Connection Failed",
                    "Failed to connect to Ollama server.\n\n"
                    "Please ensure Ollama is installed and running.\n"
                    "Visit https://ollama.ai for installation instructions.\n\n"
                    "Do you want to continue anyway?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                
                if reply == QMessageBox.StandardButton.No:
                    return False
            else:
                await asyncio.sleep(2)  # Wait before retry
    
    # Check installed models
    logger.info("Checking installed models...")
    try:
        models = await model_manager.list_all_installed_models()
        
        if not models:
            logger.warning("No models installed")
            
            reply = QMessageBox.question(
                None,
                "No Models Installed",
                "No Ollama models are currently installed.\n\n"
                "Would you like to download recommended models now?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                # Download recommended models
                config = get_config()
                try:
                    logger.info(f"Downloading recommended model: {config.text_model}")
                    await model_manager.download_model(config.text_model)
                    logger.info("Model download complete")
                except Exception as e:
                    logger.error(f"Failed to download model: {e}")
                    QMessageBox.warning(
                        None,
                        "Download Failed",
                        f"Failed to download model: {str(e)}\n\n"
                        "You can download models later from Settings."
                    )
        else:
            logger.info(f"Found {len(models)} installed models")
    
    except Exception as e:
        logger.error(f"Failed to check models: {e}")
    
    return True


def main():
    """Main application entry point."""
    try:
        # Create QApplication
        app = QApplication(sys.argv)
        app.setApplicationName("Computer Manager")
        app.setOrganizationName("Computer Manager")
        app.setOrganizationDomain("computermanager.local")
        
        # Set application icon (if exists)
        icon_path = Path(__file__).parent.parent / "assets" / "icon.png"
        if icon_path.exists():
            app.setWindowIcon(QIcon(str(icon_path)))
        
        # Create qasync event loop
        loop = QEventLoop(app)
        asyncio.set_event_loop(loop)
        
        logger.info("Application starting...")
        
        # Load configuration
        config = get_config()
        
        # Add file handler now that config is loaded and log_dir exists
        log_file = config.log_dir / "app.log"
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
        logging.getLogger().addHandler(file_handler)
        
        logger.info("Configuration loaded")
        
        # Detect and apply theme
        theme = config.theme if config.theme else "system"
        if theme.lower() == "system":
            # Auto-detect system theme
            detected_theme = detect_system_theme()
            logger.info(f"Detected system theme: {detected_theme}")
            apply_theme(app, detected_theme)
        else:
            apply_theme(app, theme)
        
        # Initialize Ollama client and model manager
        ollama_client = OllamaClient(
            host=config.ollama_host,
            timeout=config.ollama_timeout
        )
        model_manager = ModelManager(ollama_client)
        
        # Run startup checks
        with loop:
            startup_success = loop.run_until_complete(
                startup_checks(ollama_client, model_manager)
            )
            
            if not startup_success:
                logger.info("Application startup cancelled by user")
                return 0
            
            # Initialize agent framework if enabled
            agent = None
            if config.agent_enabled:
                logger.info("Initializing agent framework...")
                initialize_builtin_tools()
                register_file_tools()
                register_app_control_tools()
                register_screen_tools()
                register_keyboard_mouse_tools()
                register_vision_tools()
                register_platform_tools()

                
                # Initialize LangChain tools (optional)
                try:
                    initialize_langchain_tools(config)
                except Exception as e:
                    logger.error(f"Error initializing LangChain tools: {e}")
                
                registry = get_tool_registry()
                logger.info(f"Registered {len(registry)} tools")
                
                agent = Agent(
                    ollama_client=ollama_client,
                    tool_registry=registry,
                    model=config.default_text_model,
                    max_iterations=config.agent_max_iterations,
                    system_prompt=config.agent_system_prompt,
                    parent_widget=None  # Will be set to chat_window later
                )
                logger.info("Agent initialized successfully")
                
                # Log security configuration
                logger.info(f"Security: Permission level = {config.permission_level}")
                logger.info(f"Security: Audit logging = {'enabled' if config.enable_audit_log else 'disabled'}")
                logger.info(f"Security: Confirmation required = {config.require_confirmation}")
            else:
                logger.info("Agent framework disabled")
            
            # Create main window with optional agent
            chat_window = ChatWindow(ollama_client, agent=agent)
            
            # Create system tray
            system_tray = SystemTrayManager(chat_window)
            
            # Show window (unless start minimized is enabled)
            if config.start_minimized:
                chat_window.hide()
                system_tray.show_notification(
                    "Computer Manager",
                    "Application started in system tray"
                )
            else:
                chat_window.show()
            
            logger.info("Application initialized successfully")
            
            # Run event loop
            loop.run_forever()
        
        return 0
    
    except Exception as e:
        logger.critical(f"Fatal error during startup: {e}", exc_info=True)
        QMessageBox.critical(
            None,
            "Fatal Error",
            f"A fatal error occurred during startup:\n\n{str(e)}\n\n"
            "Please check the logs for more information."
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())
