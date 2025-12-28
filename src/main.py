"""
Computer Manager - Main Entrypoint

A basic entrypoint to initialize the application and check system compatibility.
"""

import sys
import os
from dotenv import load_dotenv

# Add src to python path if running from root
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.utils.system_info import get_system_info, SystemDetector

def main():
    print("\n" + "="*60)
    print("COMPUTER MANAGER - INITIALIZATION")
    print("="*60 + "\n")

    # Load configuration
    load_dotenv()
    print("[*] Configuration loaded")

    # Check System Info
    print("[*] Detecting system hardware...")
    detector = SystemDetector()
    detector.print_system_summary()

    print("\n[*] Initialization complete.")
    print("[*] Ready to accept commands (Mock Mode)")
    print("\nTo run tests: pytest tests/")

if __name__ == "__main__":
    main()
