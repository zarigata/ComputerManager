"""Agent core logic for tool-calling and conversation management."""

import asyncio
import logging
from typing import Any, Dict, List, Optional
import json

from ..utils.config import get_config

from ..ollama.client import OllamaClient
from .tool_registry import ToolRegistry

logger = logging.getLogger(__name__)


class Agent:
    """Agent for processing messages with tool-calling capabilities."""
    
    def __init__(
        self,
        ollama_client: OllamaClient,
        tool_registry: ToolRegistry,
        model: str = "llama3.2:3b",
        max_iterations: int = 10,
        system_prompt: Optional[str] = None,
        tool_execution_timeout: Optional[int] = None
    ):
        """Initialize the agent.
        
        Args:
            ollama_client: OllamaClient instance for LLM communication
            tool_registry: ToolRegistry with available tools
            model: Model name to use for chat
            max_iterations: Maximum tool execution loops
            system_prompt: Custom system prompt for tool usage
            tool_execution_timeout: Timeout in seconds for tool execution (default from config)
        """
        self.ollama_client = ollama_client
        self.tool_registry = tool_registry
        self.model = model
        self.max_iterations = max_iterations
        self.conversation_history: List[Dict[str, Any]] = []
        
        # Set tool execution timeout from parameter or config
        if tool_execution_timeout is None:
            self.tool_execution_timeout = get_config().tool_execution_timeout
        else:
            self.tool_execution_timeout = tool_execution_timeout
        
        # Default system prompt if not provided
        if system_prompt is None:
            system_prompt = (
                "You are a helpful AI assistant with access to tools. "
                "When you need to use a tool, specify the tool call in your response. "
                "Use tools when they can help answer the user's question more accurately."
            )
        
        # Initialize conversation with system prompt
        if system_prompt:
            self.conversation_history.append({
                'role': 'system',
                'content': system_prompt
            })
        
        logger.info(f"Agent initialized with model {model} and {len(tool_registry)} tools")
    
    async def process_message(self, user_message: str) -> str:
        """Process a user message with tool-calling support.
        
        Args:
            user_message: User's input message
            
        Returns:
            Final assistant response as string
        """
        # Add user message to history
        self.conversation_history.append({
            'role': 'user',
            'content': user_message
        })
        
        # Tool execution loop
        for iteration in range(self.max_iterations):
            logger.info(f"Agent iteration {iteration + 1}/{self.max_iterations}")
            
            try:
                # Call LLM with tools
                response = await self.ollama_client.chat_with_tools(
                    model=self.model,
                    messages=self.conversation_history,
                    tool_registry=self.tool_registry,
                    stream=False
                )
                
                # Extract message from response
                message = response.get('message', {})
                
                # Add assistant message to history
                self.conversation_history.append(message)
                
                # Check for tool calls
                tool_calls = message.get('tool_calls', [])
                
                if not tool_calls:
                    # No tool calls, return the response
                    content = message.get('content', '')
                    logger.info("Agent completed without tool calls")
                    return content
                
                # Process tool calls
                logger.info(f"Processing {len(tool_calls)} tool call(s)")
                for tool_call in tool_calls:
                    await self._execute_tool_call(tool_call)
                
            except Exception as e:
                logger.error(f"Error in agent iteration: {e}")
                error_message = f"An error occurred: {str(e)}"
                self.conversation_history.append({
                    'role': 'assistant',
                    'content': error_message
                })
                return error_message
        
        # Max iterations reached
        logger.warning(f"Agent reached max iterations ({self.max_iterations})")
        return "I apologize, but I've reached the maximum number of tool execution steps. Please try rephrasing your request."
    
    async def _execute_tool_call(self, tool_call: Dict[str, Any]) -> None:
        """Execute a single tool call and add result to history.
        
        Args:
            tool_call: Tool call dictionary from LLM response
        """
        # Capture tool call ID for correlation
        call_id = tool_call.get('id', '')
        
        function_info = tool_call.get('function', {})
        tool_name = function_info.get('name', '')
        
        # Parse arguments (they come as JSON string)
        arguments_str = function_info.get('arguments', '{}')
        try:
            arguments = json.loads(arguments_str) if isinstance(arguments_str, str) else arguments_str
        except json.JSONDecodeError:
            logger.error(f"Failed to parse tool arguments: {arguments_str}")
            arguments = {}
        
        logger.info(f"Executing tool: {tool_name} with args: {arguments}")
        
        # Get tool from registry
        tool = self.tool_registry.get(tool_name)
        
        if tool is None:
            # Tool not found
            error_msg = f"Tool '{tool_name}' not found in registry"
            logger.error(error_msg)
            result = self._format_tool_error(call_id, tool_name, error_msg)
        else:
            # Execute tool with timeout
            try:
                tool_result = await asyncio.wait_for(
                    tool.execute(**arguments),
                    timeout=self.tool_execution_timeout
                )
                result = self._format_tool_result(call_id, tool_name, tool_result)
                logger.info(f"Tool {tool_name} executed successfully")
            except asyncio.TimeoutError:
                error_msg = f"Tool execution timed out after {self.tool_execution_timeout}s"
                logger.error(f"Tool {tool_name} {error_msg}")
                result = self._format_tool_error(call_id, tool_name, error_msg)
            except Exception as e:
                logger.error(f"Tool {tool_name} execution failed: {e}")
                result = self._format_tool_error(call_id, tool_name, str(e))
        
        # Add tool result to conversation history
        self.conversation_history.append(result)
    
    def _format_tool_result(self, tool_call_id: str, tool_name: str, result: Any) -> Dict[str, str]:
        """Format tool execution result for conversation history.
        
        Args:
            tool_call_id: ID of the tool call for correlation
            tool_name: Name of the executed tool
            result: Tool execution result
            
        Returns:
            Formatted message dictionary with tool_call_id and name
        """
        # Convert result to string if needed
        if isinstance(result, (dict, list)):
            result_str = json.dumps(result, indent=2)
        else:
            result_str = str(result)
        
        return {
            'role': 'tool',
            'tool_call_id': tool_call_id,
            'name': tool_name,
            'content': result_str
        }
    
    def _format_tool_error(self, tool_call_id: str, tool_name: str, error: str) -> Dict[str, str]:
        """Format tool execution error for conversation history.
        
        Args:
            tool_call_id: ID of the tool call for correlation
            tool_name: Name of the tool that failed
            error: Error message
            
        Returns:
            Formatted error message dictionary with tool_call_id and name
        """
        return {
            'role': 'tool',
            'tool_call_id': tool_call_id,
            'name': tool_name,
            'content': f"Error executing tool '{tool_name}': {error}"
        }
    
    def clear_history(self) -> None:
        """Clear conversation history (keeps system prompt if present)."""
        # Keep only system message if it exists
        system_messages = [msg for msg in self.conversation_history if msg.get('role') == 'system']
        self.conversation_history = system_messages
        logger.info("Conversation history cleared")
    
    def get_history(self) -> List[Dict[str, str]]:
        """Get conversation history.
        
        Returns:
            List of message dictionaries
        """
        return self.conversation_history.copy()
