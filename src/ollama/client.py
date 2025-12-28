"""
Ollama Client Module

Provides an asynchronous wrapper for the Ollama Python library to handle
communication with the local Ollama API.
"""

import ollama
import asyncio
from typing import Dict, Any, List, Optional, AsyncGenerator, Union
from ..utils.config import get_config


class OllamaClient:
    """Wrapper for Ollama API client"""
    
    def __init__(self, host: Optional[str] = None, timeout: Optional[int] = None):
        config = get_config()
        self.host = host or config.ollama_host
        self.timeout = timeout or config.ollama_timeout
        # The ollama-python library uses environment variable OLLAMA_HOST
        # or defaults to localhost if not specified in the constructor.
        self.client = ollama.AsyncClient(host=self.host)
    
    async def list_models(self) -> List[Dict[str, Any]]:
        """List available local models"""
        try:
            response = await self.client.list()
            return response.get('models', [])
        except Exception as e:
            print(f"Error listing models: {e}")
            return []
    
    async def pull_model(self, model_name: str) -> AsyncGenerator[Dict[str, Any], None]:
        """Pull a model from the Ollama registry"""
        try:
            async for progress in await self.client.pull(model=model_name, stream=True):
                yield progress
        except Exception as e:
            print(f"Error pulling model {model_name}: {e}")
    
    async def chat(
        self, 
        model: str, 
        messages: List[Dict[str, str]], 
        stream: bool = False,
        options: Optional[Dict[str, Any]] = None
    ) -> Union[Dict[str, Any], AsyncGenerator[Dict[str, Any], None]]:
        """
        Send a chat request to the model
        
        Args:
            model: Name of the model to use
            messages: List of message objects {'role': 'user/assistant/system', 'content': '...'}
            stream: Whether to stream the response
            options: Additional model parameters (temperature, etc.)
        """
        try:
            if stream:
                return await self.client.chat(model=model, messages=messages, stream=True, options=options)
            else:
                return await self.client.chat(model=model, messages=messages, stream=False, options=options)
        except Exception as e:
            print(f"Error in chat request: {e}")
            return {"error": str(e)}

    async def generate(
        self,
        model: str,
        prompt: str,
        system: Optional[str] = None,
        images: Optional[List[Union[str, bytes]]] = None,
        stream: bool = False,
        options: Optional[Dict[str, Any]] = None
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
        """
        try:
            if stream:
                return await self.client.generate(
                    model=model, 
                    prompt=prompt, 
                    system=system, 
                    images=images, 
                    stream=True, 
                    options=options
                )
            else:
                return await self.client.generate(
                    model=model, 
                    prompt=prompt, 
                    system=system, 
                    images=images, 
                    stream=False, 
                    options=options
                )
        except Exception as e:
            print(f"Error in generation request: {e}")
            return {"error": str(e)}

    async def check_connection(self) -> bool:
        """Check if Ollama server is accessible"""
        try:
            # A simple way to check connection is to list models or ping
            await self.client.list()
            return True
        except Exception:
            return False
