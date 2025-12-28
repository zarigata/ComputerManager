"""
Configuration Management Module

Handles application configuration using environment variables
and .env files with python-dotenv.
"""

import os
import re
import httpx
import logging
from pathlib import Path
from typing import Optional, Dict, Any
from dotenv import load_dotenv
from dataclasses import dataclass, field

# Configure logger
logger = logging.getLogger(__name__)

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
    auto_download_models: bool = False
    preferred_model_size: str = "auto"
    
    # GUI Configuration
    window_width: int = 800
    window_height: int = 600
    theme: str = "system"  # system, light, dark
    start_minimized: bool = False
    close_to_tray: bool = True
    
    # Security Configuration
    require_confirmation: bool = True
    permission_level: str = "advanced"  # basic, advanced, admin
    enable_audit_log: bool = True
    audit_log_path: str = "logs/audit.log"
    
    # Automation Configuration
    screenshot_quality: int = 85
    automation_delay_ms: int = 100
    failsafe_enabled: bool = True
    sensitive_actions_require_confirmation: bool = True
    
    # Vision Configuration
    vision_detail_level: str = "detailed"  # brief, detailed, comprehensive
    vision_analysis_timeout: int = 60  # seconds
    auto_cleanup_screenshots: bool = True
    
    # Advanced Configuration
    debug_mode: bool = False
    log_level: str = "INFO"
    max_chat_history: int = 100
    
    # Agent Configuration
    agent_enabled: bool = True
    agent_max_iterations: int = 10
    agent_system_prompt: Optional[str] = None
    tool_execution_timeout: int = 30
    
    # Paths
    config_dir: Path = field(default_factory=lambda: Path.home() / ".computer-manager")
    cache_dir: Path = field(default_factory=lambda: Path.home() / ".computer-manager" / "cache")
    log_dir: Path = field(default_factory=lambda: Path.home() / ".computer-manager" / "logs")
    model_cache_dir: Path = field(default_factory=lambda: Path.home() / ".computer-manager" / "models")


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
        
        # Validate and set quantization
        quant_env = os.getenv("MODEL_QUANTIZATION", self.config.model_quantization)
        if self.validate_quantization_format(quant_env):
            self.config.model_quantization = quant_env
        else:
            logger.warning(f"Invalid quantization format: {quant_env}. Using default: {self.config.model_quantization}")

        self.config.auto_download_models = os.getenv("AUTO_DOWNLOAD_MODELS", "false").lower() == "true"
        self.config.preferred_model_size = os.getenv("PREFERRED_MODEL_SIZE", self.config.preferred_model_size)
        
        self.config.window_width = int(os.getenv("WINDOW_WIDTH", self.config.window_width))
        self.config.window_height = int(os.getenv("WINDOW_HEIGHT", self.config.window_height))
        self.config.theme = os.getenv("THEME", self.config.theme)
        self.config.start_minimized = os.getenv("START_MINIMIZED", "false").lower() == "true"
        self.config.close_to_tray = os.getenv("CLOSE_TO_TRAY", "true").lower() == "true"
        
        self.config.require_confirmation = os.getenv("REQUIRE_CONFIRMATION", "true").lower() == "true"
        self.config.permission_level = os.getenv("PERMISSION_LEVEL", self.config.permission_level)
        self.config.enable_audit_log = os.getenv("ENABLE_AUDIT_LOG", "true").lower() == "true"
        self.config.audit_log_path = os.getenv("AUDIT_LOG_PATH", self.config.audit_log_path)
        
        self.config.screenshot_quality = int(os.getenv("SCREENSHOT_QUALITY", self.config.screenshot_quality))
        self.config.automation_delay_ms = int(os.getenv("AUTOMATION_DELAY_MS", self.config.automation_delay_ms))
        self.config.failsafe_enabled = os.getenv("FAILSAFE_ENABLED", "true").lower() == "true"
        self.config.sensitive_actions_require_confirmation = os.getenv("SENSITIVE_ACTIONS_REQUIRE_CONFIRMATION", "true").lower() == "true"
        
        # Vision Configuration
        self.config.vision_detail_level = os.getenv("VISION_DETAIL_LEVEL", self.config.vision_detail_level)
        self.config.vision_analysis_timeout = int(os.getenv("VISION_ANALYSIS_TIMEOUT", self.config.vision_analysis_timeout))
        self.config.auto_cleanup_screenshots = os.getenv("AUTO_CLEANUP_SCREENSHOTS", "true").lower() == "true"
        
        self.config.debug_mode = os.getenv("DEBUG_MODE", "false").lower() == "true"
        self.config.log_level = os.getenv("LOG_LEVEL", self.config.log_level)
        self.config.max_chat_history = int(os.getenv("MAX_CHAT_HISTORY", self.config.max_chat_history))
        
        # Agent Configuration
        self.config.agent_enabled = os.getenv("AGENT_ENABLED", "true").lower() == "true"
        self.config.agent_max_iterations = int(os.getenv("AGENT_MAX_ITERATIONS", self.config.agent_max_iterations))
        self.config.agent_system_prompt = os.getenv("AGENT_SYSTEM_PROMPT")
        self.config.tool_execution_timeout = int(os.getenv("TOOL_EXECUTION_TIMEOUT", self.config.tool_execution_timeout))
        
        # Paths - allow overriding via env
        if os.getenv("MODEL_CACHE_DIR"):
            self.config.model_cache_dir = Path(os.getenv("MODEL_CACHE_DIR"))

        # Create directories if they don't exist
        self.config.config_dir.mkdir(parents=True, exist_ok=True)
        self.config.cache_dir.mkdir(parents=True, exist_ok=True)
        self.config.log_dir.mkdir(parents=True, exist_ok=True)
        self.config.model_cache_dir.mkdir(parents=True, exist_ok=True)

    def validate_quantization_format(self, quantization: str) -> bool:
        """
        Validate quantization string format (e.g., Q4_K_M, Q8_0, etc.)
        Allows typical GGML/GGUF quantization patterns.
        """
        # Common patterns: Q4_K_M, Q4_0, Q5_K_S, F16, etc.
        # A simple regex to catch most valid formats
        pattern = r"^(Q[2-8]_[0-9A-Z]_[A-Z0-9]+|Q[2-8]_[0-9]|F16|F32|BF16)$"
        return bool(re.match(pattern, quantization))

    async def validate_ollama_config(self) -> bool:
        """Check if OLLAMA_HOST is reachable"""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(self.config.ollama_host)
                # Ollama typically returns "Ollama is running" on root
                return response.status_code == 200
        except Exception as e:
            logger.error(f"Ollama config validation failed: {e}")
            return False

    def get_recommended_config(self) -> Dict[str, Any]:
        """
        Suggest optimal settings based on checking system resources
        (This is a placeholder that could use SystemDetector logic if imported,
         but usually config is low-level, so we keep it simple or inject dependency)
        """
        # Return generic recommendations for now
        return {
            "model_quantization": "Q4_K_M",
            "auto_download_models": True,
            "automation_delay_ms": 100,
        }

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
