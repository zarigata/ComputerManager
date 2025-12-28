# Model Selection & Performance Guide

This document details how Computer Manager selects the appropriate AI models for your hardware and explains the configuration options available.

## Hardware Tiers

The application automatically detects your system resources to assign a "Hardware Tier". This ensures you get the best performance without crashing your system.

| Tier | Criteria | Text Model | Vision Model | Approx. VRAM/RAM |
|------|----------|------------|--------------|------------------|
| **Low** | < 8GB RAM | `phi3:3b-mini-instruct` | `llama3.2-vision:11b` | ~2.5GB (CPU offload) |
| **Medium** | 8-16GB RAM | `mistral:7b-instruct` | `qwen2.5-vl:7b` | ~6-8GB |
| **High** | > 16GB RAM | `llama3.1:70b-instruct` | `qwen2.5-vl:72b` | ~40GB+ |

> **Note**: Vision models often require significantly more resources. If you lack a dedicated GPU, vision tasks may be slow.

## Quantization

We use **Quantization** to reduce model size and memory usage with minimal loss in quality.

By default, we configure models to use `Q4_K_M` (4-bit quantization).
*   **Original (FP16)**: Huge, slow, accurate.
*   **Q4_K_M**: ~1/4 size, fast, 98% accurate. Recommended.
*   **Q8_0**: ~1/2 size, good balance for high-end.

You can change this in your `.env` file:
```env
MODEL_QUANTIZATION=Q4_K_M
```
Supported values: `Q4_K_M`, `Q8_0`, `Q5_K_M`.

## Manual Override

You can force a specific model regardless of hardware tier in your `.env`:

```env
DEFAULT_TEXT_MODEL=llama3:8b-instruct-q8_0
DEFAULT_VISION_MODEL=llava:latest
```

## Performance Benchmarks

Token generation speed varies by hardware.

*   **Apple M1/M2/M3**: ~50-100 tokens/sec (Fast)
*   **NVIDIA RTX 3060/4060**: ~80-120 tokens/sec (Fast)
*   **Intel CPU (No GPU)**: ~5-15 tokens/sec (Slow but usable)

If you find response times too slow, verify you are using the correct quantization or downgrade to a smaller model (e.g., from Llama 3 8B to Phi-3).
