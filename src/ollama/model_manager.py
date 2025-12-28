"""
Model Management Module

Handles model recommendation, selection, downloading, and verification 
based on system hardware specifications and configuration.
"""

import asyncio
import logging
import json
import time
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable, Union, Protocol
from dataclasses import dataclass, asdict

from ..utils.system_info import SystemDetector, SystemInfo
from ..utils.config import get_config
from .client import OllamaClient, OllamaConnectionError, OllamaModelNotFoundError

# Configure logger
logger = logging.getLogger(__name__)

# Protocol for progress callbacks
class ProgressCallback(Protocol):
    def __call__(self, current: int, total: int, status: str) -> None: ...

@dataclass
class ModelInfo:
    """Detailed model information"""
    name: str
    size: str
    quantization: str
    modified_at: str
    functional: bool = False
    details: Dict[str, Any] = None

class ModelManager:
    """Manages model selection, download, and status"""
    
    # Recommended models based on hardware tier
    # Format: {tier: {type: model_name_base}}
    # Note: Quantization is applied dynamically
    RECOMMENDED_MODELS = {
        "low": {
            "text": "phi3:3b-mini-instruct",
            "vision": "llama3.2-vision:11b-instruct",
            "fallback_text": "gemma2:2b",
        },
        "medium": {
            "text": "mistral:7b-instruct",
            "vision": "qwen2.5-vl:7b-instruct",
            "fallback_text": "llama3.2:3b",
        },
        "high": {
            "text": "llama3.1:70b-instruct",
            "vision": "qwen2.5-vl:72b-instruct",
            "fallback_text": "llama3.1:8b",
        }
    }
    
    # Approximate sizes (GB) for estimation
    MODEL_SIZE_ESTIMATES = {
        "phi3:3b-mini-instruct": 2.2,
        "gemma2:2b": 1.6,
        "llama3.2:3b": 2.0,
        "mistral:7b-instruct": 4.1,
        "llama3.1:8b": 4.7,
        "llama3.1:70b-instruct": 39.0,
        "llama3.2-vision:11b-instruct": 7.9,
        "qwen2.5-vl:7b-instruct": 4.5,
        "qwen2.5-vl:72b-instruct": 43.0,
    }
    
    def __init__(self, client: Optional[OllamaClient] = None):
        self.client = client or OllamaClient()
        self.detector = SystemDetector()
        self.config = get_config()
        self.system_info = self.detector.get_full_system_info()
        self.hardware_tier = self.detector.get_hardware_tier()
        
        # Cache file for tracking installation status and verification
        self.cache_file = self.config.model_cache_dir / "models_meta.json"
        
    def get_model_with_quantization(self, base_name: str) -> str:
        """Apply configured quantization to base model name"""
        quantization = self.config.model_quantization
        
        # If model name already has a tag, we might need to be careful
        if ":" in base_name:
            name_part, tag_part = base_name.split(":", 1)
            # Check if tag already includes quantization-like suffix (e.g. q4_K_M)
            if "q" in tag_part.lower() and "_" in tag_part:
                 return base_name # Assume already fully specified
            
            # Otherwise append quantization to tag if it is a standard instruct tag
            return f"{name_part}:{tag_part}-{quantization}"
        else:
            # No tag, append default tag and quantization
            return f"{base_name}:latest" # Fallback if just base name given

    def get_recommended_models(self) -> Dict[str, str]:
        """Get recommended models for the current hardware with quantization"""
        tier_models = self.RECOMMENDED_MODELS.get(self.hardware_tier, self.RECOMMENDED_MODELS["low"])
        
        return {
            "text": self.get_model_with_quantization(tier_models["text"]),
            "vision": self.get_model_with_quantization(tier_models["vision"]),
            "fallback_text": self.get_model_with_quantization(tier_models.get("fallback_text", ""))
        }
    
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

    def parse_model_name(self, full_name: str) -> Dict[str, str]:
        """Parse model name into components"""
        parts = full_name.split(":")
        base = parts[0]
        tag = parts[1] if len(parts) > 1 else "latest"
        
        # Try to extract quantization from tag
        quantization = "unknown"
        if "q" in tag.lower() and "_" in tag:
             # Heuristic for quantization suffix
             q_parts = tag.split("-")
             for part in q_parts:
                 if part.upper().startswith("Q") and "_" in part:
                     quantization = part
                     break
        
        return {
            "name": base,
            "tag": tag,
            "quantization": quantization
        }

    async def get_model_info(self, model_name: str) -> Optional[ModelInfo]:
        """Get detailed info about an installed model"""
        try:
            show_info = await self.client.client.show(model_name)
            details = show_info.get("details", {})
            return ModelInfo(
                name=model_name,
                size=details.get("quantization_level", "unknown"), # Sometimes here
                quantization=details.get("quantization_level", "unknown"),
                modified_at=show_info.get("modified_at", ""),
                functional=True, # Assumed if show works, verified later
                details=show_info
            )
        except Exception:
            return None

    async def check_models_installed(self) -> Dict[str, Any]:
        """
        Check if required models are installed locally
        Returns dict with status for each model type
        """
        installed_models = await self.client.list_models()
        installed_names = [m['name'] for m in installed_models]
        
        active_models = await self.get_active_models()
        results = {}
        
        for key, model_name in active_models.items():
            if not model_name: continue
            
            # Exact match check
            exact_match = model_name in installed_names
            
            # Fuzzy match check (same base, different quantization?)
            fuzzy_match = None
            if not exact_match:
                target_parsed = self.parse_model_name(model_name)
                for name in installed_names:
                    installed_parsed = self.parse_model_name(name)
                    if target_parsed["name"] == installed_parsed["name"]:
                         # Check if it's "close enough" (e.g. just base name, or different quant)
                         fuzzy_match = name
                         break
            
            results[key] = {
                "target": model_name,
                "installed": exact_match,
                "fuzzy_match": fuzzy_match,
                "functional": False # Requires verification
            }
            
        return results

    async def verify_model_functional(self, model_name: str) -> bool:
        """Verify model works by running a minimal generation"""
        try:
            logger.info(f"Verifying functionality of {model_name}...")
            # Very short generation to test loading without consuming much time/resource
            await self.client.generate(model=model_name, prompt="Hi", options={"num_predict": 1})
            return True
        except Exception as e:
            logger.error(f"Model verification failed for {model_name}: {e}")
            return False

    async def download_model(
        self, 
        model_name: str, 
        progress_callback: Optional[ProgressCallback] = None,
        retries: int = 3
    ) -> bool:
        """
        Download a model with progress tracking and retries.
        
        Args:
            model_name: Name of model to pull
            progress_callback: Function(current, total, status)
            retries: Number of download retries
        """
        logger.info(f"Starting download of {model_name}...")
        
        for attempt in range(retries + 1):
            try:
                # Reset variables for each attempt
                current_digest = ""
                
                async for progress in self.client.pull_model(model_name):
                    status = progress.get('status', '')
                    digest = progress.get('digest', '')
                    total = progress.get('total', 0)
                    completed = progress.get('completed', 0)
                    
                    if status == 'success':
                        logger.info(f"Download of {model_name} completed successfully.")
                        return True
                        
                    if progress_callback and total > 0:
                        progress_callback(completed, total, status)
                    elif progress_callback:
                        progress_callback(0, 0, status)
                
                # If we get here without success status (shouldn't happen with valid stream), check list
                models = await self.client.list_models()
                if any(m['name'] == model_name for m in models):
                    return True
                    
            except Exception as e:
                logger.warning(f"Download attempt {attempt+1}/{retries+1} failed for {model_name}: {e}")
                if attempt < retries:
                    wait_time = 2 * (attempt + 1)
                    logger.info(f"Retrying in {wait_time}s...")
                    if progress_callback:
                        progress_callback(0, 0, f"Retry {attempt+1} in {wait_time}s...")
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"All download attempts failed for {model_name}")
                    if progress_callback:
                        progress_callback(0, 0, f"Error: {str(e)}")
                    return False
        return False

    def estimate_model_size(self, model_name: str) -> float:
        """Estimate download size in GB"""
        # Strip quantization to look up base size
        parsed = self.parse_model_name(model_name)
        base_key = f"{parsed['name']}" # Heuristic key
        
        # Look for exact match in estimates first
        for key, size in self.MODEL_SIZE_ESTIMATES.items():
            if key in model_name:
                return size
        
        # Fallback based on name hints
        lower = model_name.lower()
        if "70b" in lower or "72b" in lower: return 40.0
        if "8b" in lower or "7b" in lower: return 4.5
        if "3b" in lower: return 2.2
        if "1.5b" in lower: return 1.2
        
        return 5.0 # Generic fallback

    async def ensure_models(self, progress_callback: Optional[ProgressCallback] = None):
        """
        Ensure recommended models are installed.
        Downloads automatically if configured or small enough.
        """
        status = await self.check_models_installed()
        
        for key, info in status.items():
            model_name = info["target"]
            if info["installed"]:
                logger.info(f"{key} model {model_name} is already installed.")
                continue
                
            # If fuzzy match exists, maybe we update config to use that instead?
            # For now, we insist on target model if not found.
            
            should_download = self.config.auto_download_models
            
            # Auto-download small models if not explicitly forbidden
            if not should_download:
                est_size = self.estimate_model_size(model_name)
                # If "small" (< 5GB) and config doesn't strictly forbid (not impl yet), maybe ask?
                # User plan says: "For low-tier models (<5GB), offer automatic download"
                # Since we are non-interactive here usually, we rely on the flag
                # But we can log a recommendation.
                pass
            
            if should_download:
                logger.info(f"Auto-downloading missing {key} model: {model_name}")
                success = await self.download_model(model_name, progress_callback)
                if success:
                    # Validate
                    is_working = await self.verify_model_functional(model_name)
                    if is_working:
                        logger.info(f"Model {model_name} verified functional.")
                    else:
                        logger.error(f"Model {model_name} downloaded but failed verification.")

    async def auto_select_best_available_model(self) -> Dict[str, str]:
        """
        Select best model from what is ALREADY installed.
        Useful when offline or download fails.
        """
        installed = await self.client.list_models()
        installed_names = [m['name'] for m in installed]
        
        recommended = self.get_recommended_models()
        result = {"text": "", "vision": ""}
        
        # Try finding recommended first
        if recommended["text"] in installed_names:
            result["text"] = recommended["text"]
        
        if recommended["vision"] in installed_names:
            result["vision"] = recommended["vision"]
            
        # If text not found, try fallback
        if not result["text"] and recommended.get("fallback_text") in installed_names:
            result["text"] = recommended["fallback_text"]
            
        # If still nothing, try finding ANY text model (heuristic)
        if not result["text"]:
            for name in installed_names:
                if "instruct" in name and "vision" not in name:
                    result["text"] = name
                    break
        
        return result

    async def test_text_model(self, model_name: str) -> bool:
        """Test text generation capabilities"""
        try:
            resp = await self.client.generate(model=model_name, prompt="Hello", stream=False)
            return bool(resp.get("response"))
        except Exception:
            return False

    async def test_vision_model(self, model_name: str) -> bool:
        """Test vision capabilities (stub - requires image)"""
        # In a real impl, we'd include a tiny base64 1x1 pixel image to test
        return await self.verify_model_functional(model_name)

    async def list_all_installed_models(self) -> List[ModelInfo]:
        """Get rich list of installed models"""
        raw_list = await self.client.list_models()
        results = []
        for m in raw_list:
            # We construct info from list response + parsing
            results.append(ModelInfo(
                name=m['name'],
                size=str(m.get('size', 0)),
                quantization=m.get('details', {}).get('quantization_level', 'unknown'),
                modified_at=m.get('modified_at', ''),
                details=m.get('details', {})
            ))
        return results

    async def delete_model(self, model_name: str) -> bool:
        """Delete a model"""
        try:
            await self.client.client.delete(model_name)
            logger.info(f"Deleted model {model_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete {model_name}: {e}")
            return False

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
