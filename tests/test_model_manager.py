import unittest
from unittest.mock import MagicMock, AsyncMock, patch
import asyncio
from src.ollama.model_manager import ModelManager, ModelInfo
from src.utils.config import get_config

class TestModelManager(unittest.TestCase):
    def setUp(self):
        self.mock_client = AsyncMock()
        # Mocking system detector to return medium tier
        with patch('src.utils.system_info.SystemDetector') as MockDetector:
            instance = MockDetector.return_value
            instance.get_hardware_tier.return_value = "medium"
            instance.get_full_system_info.return_value.total_ram_gb = 16
            
            self.manager = ModelManager(client=self.mock_client)
            # Ensure consistent config for tests
            self.manager.config.model_quantization = "Q4_K_M"

    def test_get_recommended_models_medium_tier(self):
        rec = self.manager.get_recommended_models()
        self.assertIn("mistral:7b-instruct-Q4_K_M", rec["text"])
        self.assertIn("qwen2.5-vl:7b-instruct-Q4_K_M", rec["vision"])

    def test_parse_model_name(self):
        parsed = self.manager.parse_model_name("llama3:8b-instruct-q4_K_M")
        self.assertEqual(parsed["name"], "llama3")
        self.assertEqual(parsed["quantization"], "q4_K_M")
        
        parsed = self.manager.parse_model_name("mistral:latest")
        self.assertEqual(parsed["tag"], "latest")

    def test_estimate_model_size(self):
        size = self.manager.estimate_model_size("llama3.1:70b-instruct-q4_K_M")
        self.assertEqual(size, 39.0)
        
        size = self.manager.estimate_model_size("unknown:7b")
        self.assertEqual(size, 4.5) # Fallback heuristic

    async def async_test_check_installed(self):
        # Setup mock return for list_models
        self.mock_client.list_models.return_value = [
            {'name': 'mistral:7b-instruct-Q4_K_M'},
            {'name': 'other:model'}
        ]
        
        status = await self.manager.check_models_installed()
        # Medium tier recommends mistral, so text should be installed
        self.assertTrue(status["text"]["installed"])
        self.assertFalse(status["vision"]["installed"])

    def test_check_installed_wrapper(self):
        asyncio.run(self.async_test_check_installed())

    async def async_test_download_success(self):
        # Mock pull_model to yield progress
        async def mock_pull(*args, **kwargs):
            yield {'status': 'downloading', 'completed': 50, 'total': 100}
            yield {'status': 'success'}
        
        self.mock_client.pull_model = mock_pull
        
        callback = MagicMock()
        result = await self.manager.download_model("test:model", callback)
        
        self.assertTrue(result)
        callback.assert_called()

    def test_download_success_wrapper(self):
        asyncio.run(self.async_test_download_success())
        
if __name__ == '__main__':
    unittest.main()
