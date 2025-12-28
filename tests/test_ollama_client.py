import unittest
from unittest.mock import MagicMock, AsyncMock, patch
import asyncio
from src.ollama.client import OllamaClient, OllamaConnectionError
import httpx

class TestOllamaClient(unittest.TestCase):
    def setUp(self):
        self.client = OllamaClient(host="http://test:11434")
        # Mock the internal ollama async client
        self.client.client = AsyncMock()

    async def async_test_connection_error(self):
        # Simulate connection error
        self.client.client.list.side_effect = httpx.ConnectError("Connection refused")
        
        with self.assertRaises(OllamaConnectionError):
            await self.client.list_models()

    def test_connection_error_wrapper(self):
        asyncio.run(self.async_test_connection_error())

    async def async_test_chat_forwarding(self):
        expected_response = {'message': 'hello'}
        self.client.client.chat.return_value = expected_response
        
        response = await self.client.chat("model", [])
        self.assertEqual(response, expected_response)
        self.client.client.chat.assert_called_once()

    def test_chat_forwarding_wrapper(self):
        asyncio.run(self.async_test_chat_forwarding())

if __name__ == '__main__':
    unittest.main()
