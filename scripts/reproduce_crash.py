
import sys
import asyncio
import logging
from pathlib import Path
from PyQt6.QtWidgets import QApplication
from qasync import QEventLoop

# Add src to path
sys.path.append(str(Path(__file__).parent.parent))

from src.utils.config import get_config
from src.gui.settings_dialog import SettingsDialog
from src.ollama.client import OllamaClient

# Setup logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

async def run_test():
    try:
        logger.info("Starting reproduction test...")
        app = QApplication(sys.argv)
        
        # Need to init config
        config = get_config()
        
        # Need a dummy parent or None
        logger.info("Initializing SettingsDialog...")
        dialog = SettingsDialog(None)
        
        logger.info("Showing SettingsDialog (simulated)...")
        # We won't call exec() because it blocks, but we check if init crashed
        # If we reached here, __init__ passed.
        
        # Let's try to trigger the load_current_settings logic if it wasn't valid
        # It's called in __init__ so we should be good.
        
        logger.info("SettingsDialog initialized successfully.")
        
    except Exception as e:
        import traceback
        with open("crash.txt", "w") as f:
            f.write(traceback.format_exc())
        logger.critical(f"CRASH DETECTED: {e}", exc_info=True)

if __name__ == "__main__":
    loop = QEventLoop(QApplication(sys.argv))
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(run_test())
    except Exception as e:
         print(f"OUTER CRASH: {e}")
