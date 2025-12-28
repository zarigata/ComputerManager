
import asyncio
import logging
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.config import get_config
from src.ollama.client import OllamaClient
from src.agent import Agent, get_tool_registry, initialize_builtin_tools
from src.automation import register_file_tools, register_app_control_tools, register_screen_tools, register_keyboard_mouse_tools, register_platform_tools
from src.ollama.vision import register_vision_tools

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("verify_agent")

async def test_agent_initialization():
    logger.info("Starting Agent Verification")
    
    # 1. Load Config
    config = get_config()
    logger.info(f"Config loaded. Platform: {sys.platform}")

    # 2. Register Tools
    logger.info("Registering tools...")
    initialize_builtin_tools()
    register_file_tools()
    register_app_control_tools()
    register_screen_tools()
    register_keyboard_mouse_tools()
    register_vision_tools()
    register_platform_tools()
    
    registry = get_tool_registry()
    tools = [t.name for t in registry.list_tools()]
    logger.info(f"Registered {len(tools)} tools")
    
    # Verify specific tools exist
    expected_tools = [
        "read_file", "write_file", "list_processes", 
        "capture_screenshot", "move_mouse", "describe_screen"
    ]
    for tool_name in expected_tools:
        if tool_name in tools:
            logger.info(f"✓ Found tool: {tool_name}")
        else:
            logger.error(f"✗ Missing tool: {tool_name}")
            return False

    # 3. Initialize Agent
    logger.info("Initializing Agent...")
    ollama_client = OllamaClient(host=config.ollama_host)
    
    try:
        agent = Agent(
            ollama_client=ollama_client,
            tool_registry=registry,
            model="test-model"
        )
        logger.info("✓ Agent initialized successfully")
    except Exception as e:
        logger.error(f"✗ Agent initialization failed: {e}")
        return False
        
    logger.info("Agent verification passed!")
    return True

if __name__ == "__main__":
    try:
        success = asyncio.run(test_agent_initialization())
        if not success:
            sys.exit(1)
    except Exception as e:
        logger.critical(f"Verification script crashed: {e}", exc_info=True)
        sys.exit(1)
