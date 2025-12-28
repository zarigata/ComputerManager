"""
Model Management Module

Handles model recommendation, selection, and management based on
system hardware specifications.
"""

from typing import Dict, List, Optional, Any
from ..utils.system_info import SystemDetector, SystemInfo
from ..utils.config import get_config
from .client import OllamaClient


class ModelManager:
    """Manages model selection and status"""
    
    # Recommended models based on hardware tier
    # Format: {tier: {type: model_name}}
    RECOMMENDED_MODELS = {
        "low": {
            "text": "phi3:latest",
            "vision": "llama3.2-vision:latest"
        },
        "medium": {
            "text": "mistral:latest",
            "vision": "qwen2.5-vl:7b"
        },
        "high": {
            "text": "llama3.1:8b",
            "vision": "qwen2.5-vl:72b"
        }
    }
    
    def __init__(self, client: Optional[OllamaClient] = None):
        self.client = client or OllamaClient()
        self.detector = SystemDetector()
        self.config = get_config()
        self.system_info = self.detector.get_full_system_info()
        self.hardware_tier = self.detector.get_hardware_tier()
    
    def get_recommended_models(self) -> Dict[str, str]:
        """Get recommended models for the current hardware"""
        return self.RECOMMENDED_MODELS.get(self.hardware_tier, self.RECOMMENDED_MODELS["low"])
    
    async def get_active_models(self) -> Dict[str, str]:
        """
        Get currently configured or recommended models
        
        Returns:
            Dict with 'text' and 'vision' model names
        """
        recommended = self.get_recommended_models()
        
        return {
            "text": self.config.default_text_model or recommended["text"],
            "vision": self.config.default_vision_model or recommended["vision"]
        }
    
    async def check_models_installed(self) -> Dict[str, bool]:
        """Check if required models are installed locally"""
        installed_models = await self.client.list_models()
        installed_names = [m['name'] for m in installed_models]
        
        active_models = await self.get_active_models()
        
        results = {}
        for key, model_name in active_models.items():
            # Ollama models can have tags, check for exact match or base name
            results[key] = any(model_name in name or name in model_name for name in installed_names)
            
        return results
    
    async def ensure_models(self):
        """
        Ensures active models are pulled (logic for background pulling or UI prompts)
        This is a placeholder for future logic where we might auto-pull small models.
        """
        status = await self.check_models_installed()
        active = await self.get_active_models()
        
        for key, is_installed in status.items():
            if not is_installed:
                model_name = active[key]
                print(f"Recommended {key} model '{model_name}' is not installed.")
                # Logic to pull could be added here or triggered from UI
    
    def get_system_summary(self) -> Dict[str, Any]:
        """Get summary of system and recommended models"""
        return {
            "tier": self.hardware_tier,
            "recommended": self.get_recommended_models(),
            "cpu_cores": self.system_info.cpu_count,
            "ram_total_gb": self.system_info.total_ram_gb,
            "gpu_available": self.system_info.gpu_available,
            "gpu_name": self.system_info.gpu_name
        }
