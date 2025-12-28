"""
Ollama Client Module

Provides an asynchronous wrapper for the Ollama Python library to handle
communication with the local Ollama API.
"""

import ollama
import asyncio
import logging
import httpx
from typing import Dict, Any, List, Optional, AsyncGenerator, Union
from ..utils.config import get_config

# Configure logger
logger = logging.getLogger(__name__)

class OllamaError(Exception):
    """Base exception for Ollama client errors"""
    pass

class OllamaConnectionError(OllamaError):
    """Raised when connection to Ollama server fails"""
    pass

class OllamaModelNotFoundError(OllamaError):
    """Raised when a requested model is not found"""
    pass

class OllamaTimeoutError(OllamaError):
    """Raised when a request times out"""
    pass


class OllamaClient:
    """Wrapper for Ollama API client"""
    
    def __init__(self, host: Optional[str] = None, timeout: Optional[int] = None):
        config = get_config()
        self.host = host or config.ollama_host
        self.timeout = timeout or config.ollama_timeout
        # The ollama-python library uses environment variable OLLAMA_HOST
        # or defaults to localhost if not specified in the constructor.
        self.client = ollama.AsyncClient(host=self.host, timeout=self.timeout)
    
    async def list_models(self) -> List[Dict[str, Any]]:
        """List available local models"""
        try:
            response = await self.client.list()
            return response.get('models', [])
        except httpx.ConnectError:
            logger.error(f"Failed to connect to Ollama at {self.host}")
            raise OllamaConnectionError(f"Could not connect to Ollama at {self.host}")
        except Exception as e:
            logger.error(f"Error listing models: {e}")
            raise OllamaError(f"Error listing models: {str(e)}")
    
    async def pull_model(self, model_name: str) -> AsyncGenerator[Dict[str, Any], None]:
        """Pull a model from the Ollama registry"""
        try:
            # We explicitly await the coroutine to get the generator
            stream = await self.client.pull(model=model_name, stream=True)
            async for progress in stream:
                yield progress
        except httpx.ConnectError:
            raise OllamaConnectionError(f"Connection failed while pulling {model_name}")
        except Exception as e:
            logger.error(f"Error pulling model {model_name}: {e}")
            # Identify model not found errors from exception message if possible
            if "pull model manifest" in str(e) and "not found" in str(e):
                 raise OllamaModelNotFoundError(f"Model {model_name} not found in registry")
            raise OllamaError(f"Error pulling model: {str(e)}")
    
    async def chat(
        self, 
        model: str, 
        messages: List[Dict[str, str]], 
        stream: bool = False,
        options: Optional[Dict[str, Any]] = None,
        tools: Optional[List[Dict[str, Any]]] = None
    ) -> Union[Dict[str, Any], AsyncGenerator[Dict[str, Any], None]]:
        """
        Send a chat request to the model
        
        Args:
            model: Name of the model to use
            messages: List of message objects {'role': 'user/assistant/system', 'content': '...'}
            stream: Whether to stream the response
            options: Additional model parameters (temperature, etc.)
            tools: Optional list of tool schemas for function calling
        """
        try:
            kwargs = {
                'model': model,
                'messages': messages,
                'stream': stream,
                'options': options
            }
            if tools is not None:
                kwargs['tools'] = tools
            
            if stream:
                return await self.client.chat(**kwargs)
            else:
                return await self.client.chat(**kwargs)
        except httpx.ConnectError:
            raise OllamaConnectionError(f"Connection failed during chat with {model}")
        except Exception as e:
            logger.error(f"Error in chat request: {e}")
            if "not found" in str(e).lower() and "model" in str(e).lower():
                 raise OllamaModelNotFoundError(f"Model {model} not found")
            raise OllamaError(str(e))

    async def generate(
        self,
        model: str,
        prompt: str,
        system: Optional[str] = None,
        images: Optional[List[Union[str, bytes]]] = None,
        stream: bool = False,
        options: Optional[Dict[str, Any]] = None,
        tools: Optional[List[Dict[str, Any]]] = None
    ) -> Union[Dict[str, Any], AsyncGenerator[Dict[str, Any], None]]:
        """
        Send a generation request to the model
        
        Args:
            model: Name of the model to use
            prompt: Text prompt
            system: Optional system prompt
            images: Optional list of images (file paths or bytes)
            stream: Whether to stream the response
            options: Additional model parameters
            tools: Optional list of tool schemas for function calling
        """
        try:
            kwargs = {
                'model': model,
                'prompt': prompt,
                'system': system,
                'images': images,
                'stream': stream,
                'options': options
            }
            if tools is not None:
                kwargs['tools'] = tools
            
            if stream:
                return await self.client.generate(**kwargs)
            else:
                return await self.client.generate(**kwargs)
        except httpx.ConnectError:
            raise OllamaConnectionError(f"Connection failed during generation with {model}")
        except Exception as e:
            logger.error(f"Error in generation request: {e}")
            raise OllamaError(str(e))

    async def check_connection(self, retry_count: int = 3, retry_delay: float = 1.0) -> bool:
        """
        Check if Ollama server is accessible
        
        Args:
           retry_count: Number of retries
           retry_delay: Delay in seconds between retries
        """
        for i in range(retry_count + 1):
            try:
                # A simple way to check connection is to list models or ping
                # Note: list() is lightweight enough for a health check
                await self.client.list()
                return True
            except (httpx.ConnectError, Exception) as e:
                if i < retry_count:
                    logger.warning(f"Connection check failed, retrying in {retry_delay}s... ({e})")
                    await asyncio.sleep(retry_delay)
                else:
                    logger.error(f"Connection check failed after {retry_count} retries: {e}")
                    return False
        return False
        
    async def get_server_version(self) -> Dict[str, str]:
        """Get the version of the Ollama server"""
        try:
            # Current ollama python client doesn't have a direct 'version' method exposed clearly
            # but we can try to infer or use the 'client.ps()' equivalent if exists, 
            # or just return a placeholder if not supported by the lib yet.
            # Actually, let's try calling the version endpoint manually if needed, 
            # but the ollama library keeps it abstract.
            # We will return a placeholder or parse it if we can get it from an error or header.
            # For now, let's just return basic info we can confirm.
            return {"status": "running", "library_version": ollama.__version__}
        except Exception as e:
            logger.warning(f"Could not get server version: {e}")
            return {"status": "unknown"}

    async def health_check(self) -> Dict[str, Any]:
        """
        Perform a comprehensive health check
        
        Returns:
            Dict with status, version, model_count, etc.
        """
        status = {
            "connected": False,
            "server_version": "unknown",
            "model_count": 0,
            "errors": []
        }
        
        try:
            models = await self.list_models()
            status["connected"] = True
            status["model_count"] = len(models)
            
            # Identify server version if possible
            version_info = await self.get_server_version()
            status["server_version"] = version_info.get("library_version", "unknown")
            
        except OllamaConnectionError:
            status["errors"].append("Could not connect to Ollama server")
        except Exception as e:
            status["errors"].append(str(e))
            
        return status
    
    async def chat_with_tools(
        self,
        model: str,
        messages: List[Dict[str, str]],
        tool_registry,  # Type hint would be circular, so we use duck typing
        stream: bool = False,
        options: Optional[Dict[str, Any]] = None
    ) -> Union[Dict[str, Any], AsyncGenerator[Dict[str, Any], None]]:
        """
        Send a chat request with tools from a ToolRegistry
        
        Args:
            model: Name of the model to use
            messages: List of message objects
            tool_registry: ToolRegistry instance to get tools from
            stream: Whether to stream the response
            options: Additional model parameters
        """
        tools = tool_registry.get_tools_schema()
        return await self.chat(
            model=model,
            messages=messages,
            stream=stream,
            options=options,
            tools=tools if tools else None
        )
