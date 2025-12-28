"""
Computer Manager - Main Entry Point

System entry point for the AI-powered computer automation assistant.
Initializes core components and provides a basic CLI interface for testing.
"""

import asyncio
import sys
from .utils.system_info import SystemDetector
from .utils.config import get_config_manager
from .ollama.client import OllamaClient
from .ollama.model_manager import ModelManager


async def main():
    """Main execution loop"""
    print("=" * 60)
    print("COMPUTER MANAGER - INITIALIZING")
    print("=" * 60)
    
    # 1. Initialize System Detection
    detector = SystemDetector()
    system_info = detector.get_full_system_info()
    detector.print_system_summary()
    
    # 2. Initialize Configuration
    config_manager = get_config_manager()
    config = config_manager.config
    print(f"Ollama Host: {config.ollama_host}")
    print(f"Log Level: {config.log_level}")
    
    # 3. Initialize Ollama Client & Model Manager
    client = OllamaClient()
    model_manager = ModelManager(client=client)
    
    # 4. Check Ollama Connection
    print("\nChecking Ollama connection...")
    is_connected = await client.check_connection()
    if is_connected:
        print("[SUCCESS] Ollama is running and accessible.")
    else:
        print("[WARNING] Could not connect to Ollama. Please ensure 'ollama serve' is running.")
    
    # 5. Model Selection
    active_models = await model_manager.get_active_models()
    print(f"\nTarget Models:")
    print(f"  - Text: {active_models['text']}")
    print(f"  - Vision: {active_models['vision']}")
    
    if is_connected:
        print("\nChecking model installation status...")
        installed_status = await model_manager.check_models_installed()
        for key, is_installed in installed_status.items():
            status_text = "Installed" if is_installed else "NOT INSTALLED"
            print(f"  - {key.capitalize()}: {active_models[key]} ({status_text})")
            
    print("\n" + "=" * 60)
    print("INITIALIZATION COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nShutting down...")
        sys.exit(0)
    except Exception as e:
        print(f"\n[CRITICAL ERROR] {e}")
        sys.exit(1)
