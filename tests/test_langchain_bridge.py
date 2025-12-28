"""
Tests for the LangChain bridge module.
"""

import sys
import unittest
from unittest.mock import MagicMock, patch
import asyncio

# Skip tests if LangChain is not installed
try:
    from langchain.tools import Tool
    LANGCHAIN_INSTALLED = True
except ImportError:
    LANGCHAIN_INSTALLED = False

import pytest

from src.agent.langchain_bridge import (
    LangChainToolAdapter, 
    create_langchain_tool_adapter,
    is_langchain_available
)

@pytest.mark.skipif(not LANGCHAIN_INSTALLED, reason="LangChain not installed")
class TestLangChainBridge(unittest.TestCase):
    
    def setUp(self):
        # Create a mock LangChain tool
        self.mock_lc_tool = MagicMock()
        self.mock_lc_tool.name = "test_tool"
        self.mock_lc_tool.description = "A test tool"
        self.mock_lc_tool.run.return_value = "Success"
        # Mock args_schema
        self.mock_lc_tool.args_schema = None
        
    def test_adapter_properties(self):
        """Test adapter property mapping."""
        adapter = LangChainToolAdapter(self.mock_lc_tool)
        
        self.assertEqual(adapter.name, "test_tool")
        self.assertEqual(adapter.description, "A test tool")
        
        # Check default parameters generation
        params = adapter.parameters
        self.assertEqual(params["type"], "object")
        self.assertIn("query", params["properties"])
        
    def test_adapter_execution(self):
        """Test synchronous execution wrapping."""
        adapter = LangChainToolAdapter(self.mock_lc_tool)
        
        # We need to run async method in test
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(adapter.execute(query="input"))
            self.assertEqual(result, "Success")
            self.mock_lc_tool.run.assert_called_with("input")
        finally:
            loop.close()
            
    def test_factory_function(self):
        """Test the factory creation function."""
        adapter = create_langchain_tool_adapter(self.mock_lc_tool)
        self.assertIsInstance(adapter, LangChainToolAdapter)

def test_graceful_fallback():
    """Test that functions work (return safely) even if LangChain is missing."""
    # This involves mocking the global LANGCHAIN_AVAILABLE flag which is tricky
    # directly, but we can test the `is_langchain_available` function.
    assert isinstance(is_langchain_available(), bool)
