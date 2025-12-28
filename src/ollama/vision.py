"""
Vision analysis module for Ollama-powered image understanding.

This module provides vision-powered analysis capabilities by leveraging
the existing OllamaClient and CaptureScreenshotTool. It includes a core
VisionAnalyzer class and four specialized tools for screen analysis:
- DescribeScreenTool: General screen description
- FindElementOnScreenTool: Locate UI elements
- ReadTextFromScreenTool: OCR text extraction
- AnalyzeUIStateTool: UI state analysis
"""

import logging
import os
import tempfile
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
import asyncio

from src.ollama.client import OllamaClient
from src.ollama.model_manager import ModelManager
from src.utils.system_info import SystemDetector
from src.utils.config import get_config
from src.agent.tool_registry import BaseTool, get_tool_registry
from src.automation.screen import CaptureScreenshotTool

logger = logging.getLogger(__name__)


class VisionAnalyzer:
    """Core vision analysis engine using Ollama vision models."""
    
    def __init__(
        self,
        ollama_client: Optional[OllamaClient] = None,
        model_manager: Optional[ModelManager] = None
    ):
        """
        Initialize the VisionAnalyzer.
        
        Args:
            ollama_client: Optional OllamaClient instance. Creates default if not provided.
            model_manager: Optional ModelManager instance. Creates default if not provided.
        """
        self.client = ollama_client or OllamaClient()
        self.model_manager = model_manager or ModelManager(self.client)
        self.system_detector = SystemDetector()
        self.config = get_config()
        self._cached_model: Optional[str] = None
        
        logger.info("VisionAnalyzer initialized")
    
    async def select_vision_model(self) -> str:
        """
        Select the appropriate vision model based on hardware and configuration.
        
        Returns:
            str: The selected vision model name
        """
        if self._cached_model:
            logger.debug(f"Using cached vision model: {self._cached_model}")
            return self._cached_model
        
        # Try to get active vision model from configuration
        active_models = await self.model_manager.get_active_models()
        vision_model = active_models.get('vision')
        
        if vision_model:
            logger.info(f"Using configured vision model: {vision_model}")
            self._cached_model = vision_model
            return vision_model
        
        # Fall back to hardware-based recommendation
        recommended = self.model_manager.get_recommended_models()
        vision_model = recommended.get('vision')
        
        if vision_model:
            logger.info(f"Using recommended vision model for hardware tier: {vision_model}")
            self._cached_model = vision_model
            return vision_model
        
        # Ultimate fallback
        fallback_model = "llama3.2-vision:11b-instruct-q4_K_M"
        logger.warning(f"No vision model configured or recommended, using fallback: {fallback_model}")
        self._cached_model = fallback_model
        return fallback_model
    
    async def verify_vision_model(self, model_name: str) -> bool:
        """
        Verify that a vision model is functional.
        
        Args:
            model_name: Name of the model to verify
            
        Returns:
            bool: True if model is functional, False otherwise
        """
        try:
            # First check if model is generally functional
            is_functional = await self.model_manager.verify_model_functional(model_name)
            if not is_functional:
                logger.error(f"Model {model_name} failed basic functionality check")
                return False
            
            # Vision-specific verification: test with a minimal image
            # Create a 1x1 pixel test image
            test_image_path = None
            try:
                from PIL import Image
                test_image = Image.new('RGB', (1, 1), color='white')
                with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
                    test_image_path = tmp.name
                    test_image.save(tmp.name)
                
                # Try a simple vision query
                response = await self.client.generate(
                    model=model_name,
                    prompt="What color is this image?",
                    images=[test_image_path]
                )
                
                if response and len(response) > 0:
                    logger.info(f"Vision model {model_name} verified successfully")
                    return True
                else:
                    logger.error(f"Vision model {model_name} returned empty response")
                    return False
                    
            finally:
                # Clean up test image
                if test_image_path and os.path.exists(test_image_path):
                    os.unlink(test_image_path)
                    
        except Exception as e:
            logger.error(f"Vision model verification failed for {model_name}: {e}")
            return False
    
    async def analyze_image(
        self,
        image_path: str,
        prompt: str,
        model: Optional[str] = None,
        stream: bool = False
    ) -> str:
        """
        Analyze an image using a vision model.
        
        Args:
            image_path: Path to the image file
            prompt: Analysis prompt/question
            model: Optional model name. Uses select_vision_model() if not provided.
            stream: Whether to stream the response
            
        Returns:
            str: The model's analysis response
            
        Raises:
            FileNotFoundError: If image file doesn't exist
            ValueError: If image file is invalid
            TimeoutError: If analysis exceeds configured timeout
        """
        # Validate image file
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image file not found: {image_path}")
        
        if not os.path.isfile(image_path):
            raise ValueError(f"Path is not a file: {image_path}")
        
        # Select model
        model_name = model or await self.select_vision_model()
        logger.info(f"Analyzing image {image_path} with model {model_name}")
        
        try:
            # Use configured timeout
            timeout = self.config.vision_analysis_timeout
            
            response = await asyncio.wait_for(
                self.client.generate(
                    model=model_name,
                    prompt=prompt,
                    images=[image_path],
                    stream=stream
                ),
                timeout=timeout
            )
            
            logger.debug(f"Analysis complete, response length: {len(response)}")
            return response
            
        except asyncio.TimeoutError:
            error_msg = f"Vision analysis timed out after {self.config.vision_analysis_timeout}s"
            logger.error(error_msg)
            raise TimeoutError(error_msg)
        except Exception as e:
            logger.error(f"Vision analysis failed: {e}")
            raise
    
    async def analyze_screenshot(
        self,
        prompt: str,
        region: Optional[Tuple[int, int, int, int]] = None,
        model: Optional[str] = None
    ) -> str:
        """
        Capture a screenshot and analyze it.
        
        Args:
            prompt: Analysis prompt/question
            region: Optional region tuple (x, y, width, height)
            model: Optional model name
            
        Returns:
            str: The analysis response
        """
        screenshot_path = None
        try:
            # Capture screenshot using CaptureScreenshotTool
            capture_tool = CaptureScreenshotTool()
            
            # Prepare parameters
            params = {}
            if region:
                params['region'] = list(region)
            
            # Execute screenshot capture
            result = await capture_tool.execute(**params)
            
            # Extract path from result
            if isinstance(result, dict):
                # Check if capture was successful
                if not result.get('success', False):
                    error_msg = result.get('error', 'Unknown error')
                    raise ValueError(f"Failed to capture screenshot: {error_msg}")
                
                screenshot_path = result.get('file_path')
            elif isinstance(result, str):
                # Parse JSON string if needed
                import json
                try:
                    result_dict = json.loads(result)
                    if not result_dict.get('success', False):
                        error_msg = result_dict.get('error', 'Unknown error')
                        raise ValueError(f"Failed to capture screenshot: {error_msg}")
                    screenshot_path = result_dict.get('file_path')
                except json.JSONDecodeError:
                    screenshot_path = result
            else:
                screenshot_path = None
            
            if not screenshot_path or not os.path.exists(screenshot_path):
                raise ValueError("Failed to capture screenshot")
            
            logger.info(f"Screenshot captured: {screenshot_path}")
            
            # Analyze the screenshot
            analysis = await self.analyze_image(screenshot_path, prompt, model)
            
            return analysis
            
        finally:
            # Clean up temporary screenshot if configured
            if screenshot_path and self.config.auto_cleanup_screenshots:
                try:
                    if os.path.exists(screenshot_path):
                        os.unlink(screenshot_path)
                        logger.debug(f"Cleaned up screenshot: {screenshot_path}")
                except Exception as e:
                    logger.warning(f"Failed to clean up screenshot {screenshot_path}: {e}")


class DescribeScreenTool(BaseTool):
    """Tool to capture and describe what is currently visible on the screen."""
    
    @property
    def name(self) -> str:
        return "describe_screen"
    
    @property
    def description(self) -> str:
        return "Capture and describe what is currently visible on the screen"
    
    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "region": {
                    "type": "array",
                    "items": {"type": "integer"},
                    "minItems": 4,
                    "maxItems": 4,
                    "description": "Optional region to capture [x, y, width, height]"
                },
                "detail_level": {
                    "type": "string",
                    "enum": ["brief", "detailed", "comprehensive"],
                    "default": "detailed",
                    "description": "Level of detail in the description"
                }
            }
        }
    
    def __init__(self):
        self.analyzer = VisionAnalyzer()
    
    async def execute(self, **kwargs) -> str:
        """Execute screen description."""
        self.validate_params(**kwargs)
        
        region = kwargs.get('region')
        detail_level = kwargs.get('detail_level', 'detailed')
        
        # Convert region list to tuple if provided
        region_tuple = tuple(region) if region else None
        
        # Construct prompt based on detail level
        prompts = {
            "brief": "Briefly describe what you see in this screenshot in 1-2 sentences.",
            "detailed": "Describe what you see in this screenshot in detail, including the main elements, layout, and any notable features.",
            "comprehensive": "Provide a comprehensive description of this screenshot, including all visible elements, their positions, states, colors, text content, and overall layout. Be thorough and precise."
        }
        
        prompt = prompts.get(detail_level, prompts["detailed"])
        
        try:
            result = await self.analyzer.analyze_screenshot(prompt, region_tuple)
            return result
        except Exception as e:
            logger.error(f"DescribeScreenTool failed: {e}")
            return f"Error describing screen: {str(e)}"


class FindElementOnScreenTool(BaseTool):
    """Tool to find a specific UI element on the screen and return its location."""
    
    @property
    def name(self) -> str:
        return "find_element_on_screen"
    
    @property
    def description(self) -> str:
        return "Find a specific UI element on the screen and return its location"
    
    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "element_description": {
                    "type": "string",
                    "description": "Description of the UI element to find"
                },
                "region": {
                    "type": "array",
                    "items": {"type": "integer"},
                    "minItems": 4,
                    "maxItems": 4,
                    "description": "Optional region to search [x, y, width, height]"
                }
            },
            "required": ["element_description"]
        }
    
    def __init__(self):
        self.analyzer = VisionAnalyzer()
    
    async def execute(self, **kwargs) -> str:
        """Execute element finding."""
        self.validate_params(**kwargs)
        
        element_description = kwargs['element_description']
        region = kwargs.get('region')
        
        region_tuple = tuple(region) if region else None
        
        prompt = f"""Find the {element_description} in this screenshot.
Describe its location using:
1. Approximate coordinates (if visible)
2. Relative position (e.g., "top-left corner", "center of screen", "bottom-right")
3. Nearby elements or context
4. Whether the element is visible and accessible

Be specific and precise about the location."""
        
        try:
            result = await self.analyzer.analyze_screenshot(prompt, region_tuple)
            return result
        except Exception as e:
            logger.error(f"FindElementOnScreenTool failed: {e}")
            return f"Error finding element: {str(e)}"


class ReadTextFromScreenTool(BaseTool):
    """Tool to extract and read all visible text from the screen using OCR capabilities."""
    
    @property
    def name(self) -> str:
        return "read_text_from_screen"
    
    @property
    def description(self) -> str:
        return "Extract and read all visible text from the screen using OCR capabilities"
    
    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "region": {
                    "type": "array",
                    "items": {"type": "integer"},
                    "minItems": 4,
                    "maxItems": 4,
                    "description": "Optional region to read from [x, y, width, height]"
                },
                "language": {
                    "type": "string",
                    "default": "english",
                    "description": "Language of the text to extract"
                }
            }
        }
    
    def __init__(self):
        self.analyzer = VisionAnalyzer()
    
    async def execute(self, **kwargs) -> str:
        """Execute text extraction."""
        self.validate_params(**kwargs)
        
        region = kwargs.get('region')
        language = kwargs.get('language', 'english')
        
        region_tuple = tuple(region) if region else None
        
        prompt = f"""Extract and transcribe all visible text from this screenshot.
Language: {language}

Requirements:
1. Preserve the original formatting and structure as much as possible
2. Include all text, even if partially visible
3. Maintain the reading order (top to bottom, left to right)
4. Indicate any text that is unclear or partially obscured
5. Organize text by sections or UI elements if applicable

Provide the extracted text in a clear, readable format."""
        
        try:
            result = await self.analyzer.analyze_screenshot(prompt, region_tuple)
            return result
        except Exception as e:
            logger.error(f"ReadTextFromScreenTool failed: {e}")
            return f"Error reading text: {str(e)}"


class AnalyzeUIStateTool(BaseTool):
    """Tool to analyze the current state of the user interface."""
    
    @property
    def name(self) -> str:
        return "analyze_ui_state"
    
    @property
    def description(self) -> str:
        return "Analyze the current state of the user interface, including active windows, dialogs, and interactive elements"
    
    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "region": {
                    "type": "array",
                    "items": {"type": "integer"},
                    "minItems": 4,
                    "maxItems": 4,
                    "description": "Optional region to analyze [x, y, width, height]"
                },
                "focus_areas": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Specific areas or aspects to focus on during analysis"
                }
            }
        }
    
    def __init__(self):
        self.analyzer = VisionAnalyzer()
    
    async def execute(self, **kwargs) -> str:
        """Execute UI state analysis."""
        self.validate_params(**kwargs)
        
        region = kwargs.get('region')
        focus_areas = kwargs.get('focus_areas', [])
        
        region_tuple = tuple(region) if region else None
        
        # Build prompt with focus areas if provided
        focus_section = ""
        if focus_areas:
            focus_list = "\n".join([f"   - {area}" for area in focus_areas])
            focus_section = f"\n\nPay special attention to:\n{focus_list}"
        
        prompt = f"""Analyze this screenshot and describe the UI state in detail:

1. Active windows and applications:
   - What applications are visible?
   - Which window has focus?
   - Window states (maximized, minimized, overlapping)

2. Interactive elements:
   - Buttons (location, labels, states)
   - Input fields (location, labels, content if visible)
   - Menus and dropdowns (open/closed states)
   - Checkboxes and radio buttons (checked/unchecked)
   - Sliders and progress bars (current values)

3. Current states:
   - Enabled vs disabled elements
   - Selected vs unselected items
   - Expanded vs collapsed sections
   - Loading indicators or progress

4. Dialogs and notifications:
   - Modal dialogs (content, buttons)
   - Toast notifications or alerts
   - Error messages or warnings
   - Confirmation prompts{focus_section}

Provide a structured, detailed analysis of the UI state."""
        
        try:
            result = await self.analyzer.analyze_screenshot(prompt, region_tuple)
            return result
        except Exception as e:
            logger.error(f"AnalyzeUIStateTool failed: {e}")
            return f"Error analyzing UI state: {str(e)}"


def register_vision_tools() -> None:
    """Register all vision tools with the global tool registry."""
    registry = get_tool_registry()
    
    tools = [
        DescribeScreenTool(),
        FindElementOnScreenTool(),
        ReadTextFromScreenTool(),
        AnalyzeUIStateTool()
    ]
    
    for tool in tools:
        try:
            registry.register(tool)
            logger.info(f"Registered vision tool: {tool.name}")
        except ValueError as e:
            logger.warning(f"Failed to register tool {tool.name}: {e}")
    
    logger.info(f"Vision tools registration complete. {len(tools)} tools registered.")
