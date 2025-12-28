"""
Configuration Management Module

Handles application configuration using environment variables
and .env files with python-dotenv.
"""

import os
from pathlib import Path
from typing import Optional, Dict, Any
from dotenv import load_dotenv
from dataclasses import dataclass, field


@dataclass
class AppConfig:
    """Application configuration data class"""
    
    # Ollama Configuration
    ollama_host: str = "http://localhost:11434"
    ollama_timeout: int = 120
    
    # Model Configuration
    default_text_model: Optional[str] = None  # Auto-detect if None
    default_vision_model: Optional[str] = None  # Auto-detect if None
    model_quantization: str = "Q4_K_M"
    
    # GUI Configuration
    window_width: int = 800
    window_height: int = 600
    theme: str = "system"  # system, light, dark
    
    # Security Configuration
    require_confirmation: bool = True
    permission_level: str = "advanced"  # basic, advanced, admin
    enable_audit_log: bool = True
    audit_log_path: str = "logs/audit.log"
    
    # Automation Configuration
    screenshot_quality: int = 85
    automation_delay_ms: int = 100
    failsafe_enabled: bool = True
    
    # Advanced Configuration
    debug_mode: bool = False
    log_level: str = "INFO"
    max_chat_history: int = 100
    
    # Paths
    config_dir: Path = field(default_factory=lambda: Path.home() / ".computer-manager")
    cache_dir: Path = field(default_factory=lambda: Path.home() / ".computer-manager" / "cache")
    log_dir: Path = field(default_factory=lambda: Path.home() / ".computer-manager" / "logs")


class ConfigManager:
    """Manages application configuration"""
    
    def __init__(self, env_file: Optional[Path] = None):
        """
        Initialize configuration manager
        
        Args:
            env_file: Path to .env file (default: .env in project root)
        """
        self.config = AppConfig()
        self.env_file = env_file or Path(".env")
        self._load_config()
    
    def _load_config(self):
        """Load configuration from environment variables and .env file"""
        # Load .env file if it exists
        if self.env_file.exists():
            load_dotenv(self.env_file)
        
        # Override with environment variables
        self.config.ollama_host = os.getenv("OLLAMA_HOST", self.config.ollama_host)
        self.config.ollama_timeout = int(os.getenv("OLLAMA_TIMEOUT", self.config.ollama_timeout))
        
        self.config.default_text_model = os.getenv("DEFAULT_TEXT_MODEL")
        self.config.default_vision_model = os.getenv("DEFAULT_VISION_MODEL")
        self.config.model_quantization = os.getenv("MODEL_QUANTIZATION", self.config.model_quantization)
        
        self.config.window_width = int(os.getenv("WINDOW_WIDTH", self.config.window_width))
        self.config.window_height = int(os.getenv("WINDOW_HEIGHT", self.config.window_height))
        self.config.theme = os.getenv("THEME", self.config.theme)
        
        self.config.require_confirmation = os.getenv("REQUIRE_CONFIRMATION", "true").lower() == "true"
        self.config.permission_level = os.getenv("PERMISSION_LEVEL", self.config.permission_level)
        self.config.enable_audit_log = os.getenv("ENABLE_AUDIT_LOG", "true").lower() == "true"
        self.config.audit_log_path = os.getenv("AUDIT_LOG_PATH", self.config.audit_log_path)
        
        self.config.screenshot_quality = int(os.getenv("SCREENSHOT_QUALITY", self.config.screenshot_quality))
        self.config.automation_delay_ms = int(os.getenv("AUTOMATION_DELAY_MS", self.config.automation_delay_ms))
        self.config.failsafe_enabled = os.getenv("FAILSAFE_ENABLED", "true").lower() == "true"
        
        self.config.debug_mode = os.getenv("DEBUG_MODE", "false").lower() == "true"
        self.config.log_level = os.getenv("LOG_LEVEL", self.config.log_level)
        self.config.max_chat_history = int(os.getenv("MAX_CHAT_HISTORY", self.config.max_chat_history))
        
        # Create directories if they don't exist
        self.config.config_dir.mkdir(parents=True, exist_ok=True)
        self.config.cache_dir.mkdir(parents=True, exist_ok=True)
        self.config.log_dir.mkdir(parents=True, exist_ok=True)
    
    def save_config(self, config_dict: Dict[str, Any]):
        """
        Save configuration to .env file
        
        Args:
            config_dict: Dictionary of configuration key-value pairs
        """
        lines = []
        
        # Read existing .env file
        if self.env_file.exists():
            with open(self.env_file, 'r') as f:
                lines = f.readlines()
        
        # Update or add new values
        updated_keys = set()
        for i, line in enumerate(lines):
            if '=' in line and not line.strip().startswith('#'):
                key = line.split('=')[0].strip()
                if key in config_dict:
                    lines[i] = f"{key}={config_dict[key]}\n"
                    updated_keys.add(key)
        
        # Add new keys that weren't in the file
        for key, value in config_dict.items():
            if key not in updated_keys:
                lines.append(f"{key}={value}\n")
        
        # Write back to file
        with open(self.env_file, 'w') as f:
            f.writelines(lines)
        
        # Reload configuration
        self._load_config()
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value by key"""
        return getattr(self.config, key, default)
    
    def set(self, key: str, value: Any):
        """Set configuration value"""
        if hasattr(self.config, key):
            setattr(self.config, key, value)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary"""
        return {
            k: str(v) if isinstance(v, Path) else v
            for k, v in self.config.__dict__.items()
        }
    
    def print_config(self):
        """Print current configuration"""
        print("=" * 60)
        print("CURRENT CONFIGURATION")
        print("=" * 60)
        for key, value in self.to_dict().items():
            print(f"{key}: {value}")
        print("=" * 60)


# Global configuration instance
_config_manager: Optional[ConfigManager] = None


def get_config() -> AppConfig:
    """Get global configuration instance"""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager.config


def get_config_manager() -> ConfigManager:
    """Get global configuration manager instance"""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager


if __name__ == "__main__":
    # Test the module
    manager = ConfigManager()
    manager.print_config()
