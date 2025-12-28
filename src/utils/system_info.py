"""
System Information Detection Module

Detects CPU, RAM, and GPU (NVIDIA) specifications for model selection.
Uses psutil for universal detection and py3nvml for NVIDIA GPU detection
with graceful fallback if GPU libraries are unavailable.
"""

import psutil
import platform
from typing import Dict, Optional, List
from dataclasses import dataclass

# Optional GPU detection - graceful fallback if not available
try:
    import py3nvml.py3nvml as nvml
    NVML_AVAILABLE = True
except ImportError:
    NVML_AVAILABLE = False

try:
    import GPUtil
    GPUTIL_AVAILABLE = True
except ImportError:
    GPUTIL_AVAILABLE = False


@dataclass
class SystemInfo:
    """System information data class"""
    cpu_count: int
    cpu_freq_mhz: float
    total_ram_gb: float
    available_ram_gb: float
    platform: str
    platform_version: str
    gpu_available: bool
    gpu_name: Optional[str] = None
    gpu_memory_total_gb: Optional[float] = None
    gpu_memory_free_gb: Optional[float] = None
    gpu_count: int = 0


class SystemDetector:
    """Detects system hardware specifications"""
    
    def __init__(self):
        self._gpu_initialized = False
        if NVML_AVAILABLE:
            try:
                nvml.nvmlInit()
                self._gpu_initialized = True
            except Exception as e:
                print(f"Warning: Could not initialize NVML: {e}")
    
    def __del__(self):
        """Cleanup NVML on destruction"""
        if self._gpu_initialized:
            try:
                nvml.nvmlShutdown()
            except:
                pass
    
    def get_cpu_info(self) -> Dict[str, any]:
        """Get CPU information"""
        cpu_freq = psutil.cpu_freq()
        return {
            "count": psutil.cpu_count(logical=True),
            "physical_count": psutil.cpu_count(logical=False),
            "frequency_mhz": cpu_freq.current if cpu_freq else 0,
            "max_frequency_mhz": cpu_freq.max if cpu_freq else 0,
        }
    
    def get_memory_info(self) -> Dict[str, float]:
        """Get RAM information in GB"""
        mem = psutil.virtual_memory()
        return {
            "total_gb": mem.total / (1024 ** 3),
            "available_gb": mem.available / (1024 ** 3),
            "used_gb": mem.used / (1024 ** 3),
            "percent": mem.percent,
        }
    
    def get_gpu_info(self) -> List[Dict[str, any]]:
        """Get GPU information (NVIDIA via NVML or generic via GPUtil)"""
        gpus = []
        
        # Try NVML first (NVIDIA specific, more detailed)
        if self._gpu_initialized:
            try:
                device_count = nvml.nvmlDeviceGetCount()
                for i in range(device_count):
                    handle = nvml.nvmlDeviceGetHandleByIndex(i)
                    name = nvml.nvmlDeviceGetName(handle)
                    memory_info = nvml.nvmlDeviceGetMemoryInfo(handle)
                    
                    gpus.append({
                        "index": i,
                        "name": name.decode('utf-8') if isinstance(name, bytes) else name,
                        "memory_total_gb": memory_info.total / (1024 ** 3),
                        "memory_free_gb": memory_info.free / (1024 ** 3),
                        "memory_used_gb": memory_info.used / (1024 ** 3),
                        "source": "nvml"
                    })
                return gpus
            except Exception as e:
                print(f"Warning: NVML detection failed: {e}")
        
        # Fallback to GPUtil
        if GPUTIL_AVAILABLE:
            try:
                available_gpus = GPUtil.getGPUs()
                for i, gpu in enumerate(available_gpus):
                    gpus.append({
                        "index": i,
                        "name": gpu.name,
                        "memory_total_gb": gpu.memoryTotal / 1024,  # GPUtil returns MB
                        "memory_free_gb": gpu.memoryFree / 1024,
                        "memory_used_gb": gpu.memoryUsed / 1024,
                        "source": "gputil"
                    })
            except Exception as e:
                print(f"Warning: GPUtil detection failed: {e}")
        
        return gpus
    
    def get_platform_info(self) -> Dict[str, str]:
        """Get platform information"""
        return {
            "system": platform.system(),  # Windows, Linux, Darwin
            "release": platform.release(),
            "version": platform.version(),
            "machine": platform.machine(),  # x86_64, arm64, etc.
            "processor": platform.processor(),
        }
    
    def get_full_system_info(self) -> SystemInfo:
        """Get complete system information"""
        cpu_info = self.get_cpu_info()
        mem_info = self.get_memory_info()
        gpu_info = self.get_gpu_info()
        platform_info = self.get_platform_info()
        
        # Primary GPU (first one if multiple)
        primary_gpu = gpu_info[0] if gpu_info else None
        
        return SystemInfo(
            cpu_count=cpu_info["count"],
            cpu_freq_mhz=cpu_info["frequency_mhz"],
            total_ram_gb=mem_info["total_gb"],
            available_ram_gb=mem_info["available_gb"],
            platform=platform_info["system"],
            platform_version=platform_info["version"],
            gpu_available=len(gpu_info) > 0,
            gpu_name=primary_gpu["name"] if primary_gpu else None,
            gpu_memory_total_gb=primary_gpu["memory_total_gb"] if primary_gpu else None,
            gpu_memory_free_gb=primary_gpu["memory_free_gb"] if primary_gpu else None,
            gpu_count=len(gpu_info),
        )
    
    def get_hardware_tier(self) -> str:
        """
        Determine hardware tier for model selection
        Returns: 'low', 'medium', or 'high'
        """
        system_info = self.get_full_system_info()
        ram_gb = system_info.total_ram_gb
        vram_gb = system_info.gpu_memory_total_gb or 0
        
        # High Tier: Capable of running large models (e.g. 70B ~40GB req, or 8B unquantized + context)
        # Criteria: Big RAM, Big VRAM, or Decent RAM + Decent VRAM
        if (ram_gb >= 32) or (vram_gb >= 16) or (ram_gb >= 16 and vram_gb >= 8):
            return "high"
            
        # Medium Tier: Capable of running 7B-8B models comfortably
        if (ram_gb >= 8) or (vram_gb >= 6):
            return "medium"
            
        # Low Tier: Small models only (phi-3, gemma-2b, etc)
        return "low"
    
    def print_system_summary(self):
        """Print a human-readable system summary"""
        info = self.get_full_system_info()
        tier = self.get_hardware_tier()
        
        print("=" * 60)
        print("SYSTEM INFORMATION")
        print("=" * 60)
        print(f"Platform: {info.platform} {info.platform_version}")
        print(f"CPU Cores: {info.cpu_count} @ {info.cpu_freq_mhz:.0f} MHz")
        print(f"RAM: {info.total_ram_gb:.1f} GB total, {info.available_ram_gb:.1f} GB available")
        
        if info.gpu_available:
            print(f"GPU: {info.gpu_name}")
            print(f"VRAM: {info.gpu_memory_total_gb:.1f} GB total, {info.gpu_memory_free_gb:.1f} GB free")
        else:
            print("GPU: Not detected (CPU-only mode)")
        
        print(f"\nHardware Tier: {tier.upper()}")
        print("=" * 60)


# Convenience function for quick access
def get_system_info() -> SystemInfo:
    """Quick function to get system information"""
    detector = SystemDetector()
    return detector.get_full_system_info()


def get_hardware_tier() -> str:
    """Quick function to get hardware tier"""
    detector = SystemDetector()
    return detector.get_hardware_tier()


if __name__ == "__main__":
    # Test the module
    detector = SystemDetector()
    detector.print_system_summary()
