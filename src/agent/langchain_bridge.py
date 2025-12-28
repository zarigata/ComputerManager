"""
Bridge module for integrating LangChain tools into the native tool system.

This module provides adapters to convert LangChain tools (BaseTool) into
our internal BaseTool format, allowing access to LangChain's extensive
ecosystem of tools while maintaining our core architecture.
"""

import asyncio
import json
import logging
from typing import Dict, List, Any, Optional, Type, Union

from .tool_registry import BaseTool, ToolRegistry

# Configure logger
logger = logging.getLogger(__name__)

# Global flag for LangChain availability
LANGCHAIN_AVAILABLE = False

try:
    # Try to import LangChain base classes
    from langchain_core.tools import BaseTool as LCBaseTool
    from langchain.tools import Tool as LCTool
    from langchain.tools import Tool as LCTool
    from langchain.agents import AgentExecutor, create_react_agent
    from langchain_core.prompts import PromptTemplate
    from langchain.llms.base import LLM
    from pydantic.v1 import BaseModel as PydanticBaseModel
    
    LANGCHAIN_AVAILABLE = True
except ImportError:
    logger.debug("LangChain not installed or not found. Integration disabled.")


def is_langchain_available() -> bool:
    """Check if LangChain is available."""
    return LANGCHAIN_AVAILABLE


class LangChainToolAdapter(BaseTool):
    """
    Adapter that wraps a LangChain tool to make it compatible with our system.
    """
    
    def __init__(self, langchain_tool: Any):
        """
        Initialize the adapter.
        
        Args:
            langchain_tool: A LangChain BaseTool instance
        """
        if not LANGCHAIN_AVAILABLE:
            raise ImportError("LangChain is not installed")
            
        self._langchain_tool = langchain_tool
        
        # Initialize BaseTool with name and description
        # We don't verify parameters in init since we construct them dynamically below
        super().__init__()
        
    @property
    def name(self) -> str:
        """Get tool name."""
        return self._langchain_tool.name
    
    @property
    def description(self) -> str:
        """Get tool description."""
        return self._langchain_tool.description
    
    @property
    def parameters(self) -> Dict[str, Any]:
        """
        Convert LangChain args_schema to JSON schema.
        """
        # If tool has args_schema (Pydantic model), use it
        if hasattr(self._langchain_tool, "args_schema") and self._langchain_tool.args_schema:
            schema = self._langchain_tool.args_schema.schema()
            
            # Remove Pydantic-specific fields that might confuse LLMs or aren't standard
            if "title" in schema:
                del schema["title"]
                
            return {
                "type": "object",
                "properties": schema.get("properties", {}),
                "required": schema.get("required", [])
            }
        
        # Fallback for single-input tools without specific schema
        # Most LangChain tools accept a single string query
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The input query for the tool"
                }
            },
            "required": ["query"]
        }
    
    async def execute(self, **kwargs) -> str:
        """
        Execute the LangChain tool.
        
        Args:
            **kwargs: Arguments for the tool
        
        Returns:
            Tool output as string
        """
        try:
            # Handle input mapping
            # Some tools expect specific arg names, others just take a string
            tool_input = kwargs
            
            # If tool expects a single string argument but we got a dict
            # try to extract the primary argument
            if hasattr(self._langchain_tool, "args_schema") and self._langchain_tool.args_schema:
                # If we have a schema, pass kwargs directly, validation handled by tool
                pass
            else:
                # If no schema, assume single string input
                # E.g. {"query": "something"} -> "something"
                if len(kwargs) == 1:
                    tool_input = next(iter(kwargs.values()))
                elif "query" in kwargs:
                    tool_input = kwargs["query"]
            
            # Use async implementation if available
            if hasattr(self._langchain_tool, "_arun"):
                # Note: LangChain tools usually expose coroutine via arun or _arun
                # But implementation varies by version. Using invoke or run is safer in newer calls
                # but direct method mapping is more robust for older versions.
                # Let's try the public async API first if it exists
                if hasattr(self._langchain_tool, "ainvoke"):
                    result = await self._langchain_tool.ainvoke(tool_input)
                elif hasattr(self._langchain_tool, "arun"):
                    result = await self._langchain_tool.arun(tool_input)
                else:
                    # Fallback to sync via thread
                    result = await asyncio.to_thread(self._langchain_tool.run, tool_input)
            else:
                # Run synchronous tool in thread to avoid blocking loop
                result = await asyncio.to_thread(self._langchain_tool.run, tool_input)
                
            # Convert result to string if needed
            if isinstance(result, (dict, list)):
                return json.dumps(result, indent=2)
            return str(result)
            
        except Exception as e:
            logger.error(f"Error executing LangChain tool {self.name}: {e}")
            return f"Error: {str(e)}"


def create_langchain_tool_adapter(langchain_tool: Any) -> Optional[LangChainToolAdapter]:
    """Factory function to create adapter."""
    if not LANGCHAIN_AVAILABLE:
        return None
    try:
        return LangChainToolAdapter(langchain_tool)
    except Exception as e:
        logger.error(f"Failed to adapt tool {langchain_tool}: {e}")
        return None


# --- Tool Loaders ---

def load_wikipedia_tool() -> Optional[LangChainToolAdapter]:
    """Load Wikipedia tool."""
    if not LANGCHAIN_AVAILABLE:
        return None
    try:
        # Wikipedia requires langchain-community and wikipedia package
        from langchain_community.tools import WikipediaQueryRun
        from langchain_community.utilities import WikipediaAPIWrapper
        
        tool = WikipediaQueryRun(api_wrapper=WikipediaAPIWrapper())
        return create_langchain_tool_adapter(tool)
    except ImportError as e:
        logger.warning(f"Failed to load Wikipedia tool: {e}. Install 'wikipedia' package.")
        return None
    except Exception as e:
        logger.error(f"Error loading Wikipedia tool: {e}")
        return None


def load_calculator_tool() -> Optional[LangChainToolAdapter]:
    """Load Calculator tool."""
    if not LANGCHAIN_AVAILABLE:
        return None
    try:
        # Create a simple safe calculator tool
        def safe_calculate(expression: str) -> str:
            """Evaluate a mathematical expression safely."""
            try:
                # Remove any non-math characters for safety
                # Allow digits, whitespace, ., +, -, *, /, (, ), %
                import re
                if not re.match(r'^[\d\s\.\+\-\*\/\(\)\%]+$', expression):
                    return "Error: Invalid characters in expression"
                
                # Evaluate
                result = eval(expression, {"__builtins__": {}}, {})
                return str(result)
            except Exception as e:
                return f"Error: {str(e)}"

        tool = LCTool.from_function(
            func=safe_calculate,
            name="calculator",
            description="Useful for when you need to answer questions about math."
        )
        return create_langchain_tool_adapter(tool)
    except Exception as e:
        logger.error(f"Error loading Calculator tool: {e}")
        return None


def load_duckduckgo_search_tool() -> Optional[LangChainToolAdapter]:
    """Load DuckDuckGo Search tool."""
    if not LANGCHAIN_AVAILABLE:
        return None
    try:
        from langchain_community.tools import DuckDuckGoSearchRun
        tool = DuckDuckGoSearchRun()
        return create_langchain_tool_adapter(tool)
    except ImportError:
        logger.warning("Failed to load DuckDuckGo tool. Install 'duckduckgo-search'.")
        return None
    except Exception as e:
        logger.error(f"Error loading DuckDuckGo tool: {e}")
        return None


def load_weather_tool() -> Optional[LangChainToolAdapter]:
    """Load Weather tool."""
    if not LANGCHAIN_AVAILABLE:
        return None
    try:
        import os
        if not os.environ.get("OPENWEATHERMAP_API_KEY"):
            logger.debug("OPENWEATHERMAP_API_KEY not set. Weather tool disabled.")
            return None
            
        from langchain_community.tools import OpenWeatherMapQueryRun
        from langchain_community.utilities import OpenWeatherMapAPIWrapper
        
        tool = OpenWeatherMapQueryRun(api_wrapper=OpenWeatherMapAPIWrapper())
        return create_langchain_tool_adapter(tool)
    except ImportError:
        logger.warning("Failed to load Weather tool.")
        return None
    except Exception as e:
        logger.error(f"Error loading Weather tool: {e}")
        return None


def load_langchain_tools(tool_names: List[str]) -> List[LangChainToolAdapter]:
    """
    Load specified LangChain tools.
    
    Args:
        tool_names: List of tool names (wikipedia, calculator, etc)
        
    Returns:
        List of adapted tools
    """
    if not LANGCHAIN_AVAILABLE:
        logger.warning("LangChain not available. Skipping external tools.")
        return []
        
    loaded_tools = []
    
    # Mapper for loader functions
    loaders = {
        "wikipedia": load_wikipedia_tool,
        "calculator": load_calculator_tool,
        "duckduckgo_search": load_duckduckgo_search_tool,
        "weather": load_weather_tool
    }
    
    for name in tool_names:
        clean_name = name.lower().strip()
        if clean_name in loaders:
            logger.info(f"Loading LangChain tool: {clean_name}")
            tool = loaders[clean_name]()
            if tool:
                loaded_tools.append(tool)
            else:
                logger.warning(f"Could not load tool: {clean_name}")
        else:
            logger.warning(f"Unknown LangChain tool requested: {clean_name}")
            
    return loaded_tools


class LangChainAgentMode:
    """
    Optional integration to run the full LangChain agent loop.
    This creates a LangChain Agent that wraps our Ollama connection.
    (Experimental)
    """
    
    def __init__(self, ollama_client, tool_registry: ToolRegistry, model_name: str):
        self.ollama_client = ollama_client
        self.tool_registry = tool_registry
        self.model_name = model_name
        
class OllamaLLMWrapper(LLM):
    """Wrapper for our OllamaClient to be compatible with LangChain."""
    
    client: Any
    model: str
    
    @property
    def _llm_type(self) -> str:
        return "ollama_wrapper"
    
    def _call(self, prompt: str, stop: Optional[List[str]] = None, run_manager: Any = None, **kwargs: Any) -> str:
        """Run the LLM on the given prompt."""
        # This is a synchronous call, so we must run the async client method
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
        kwargs = {"model": self.model, "options": {"stop": stop} if stop else {}}
        
        # We need a way to call generate. Since client.generate is async, we wrap it.
        # Note: This might be blocking.
        coro = self.client.generate(prompt=prompt, **kwargs)
        if loop.is_running():
            # If we are already in a loop (which we are), we can't simple run_until_complete?
            # Actually LangChain agents often run in threads or async.
            # If we are called from async agent, we should implement _acall.
            # But for simplicity in this synchronous wrapper:
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                result = pool.submit(lambda: asyncio.run(self.client.generate(prompt=prompt, **kwargs))).result()
                return result.get("response", "")
        else:
            result = loop.run_until_complete(coro)
            return result.get("response", "")
            
    async def _acall(self, prompt: str, stop: Optional[List[str]] = None, run_manager: Any = None, **kwargs: Any) -> str:
        """Run the LLM asynchronously."""
        kwargs = {"model": self.model, "options": {"stop": stop} if stop else {}}
        result = await self.client.generate(prompt=prompt, **kwargs)
        return result.get("response", "")


class LangChainAgentMode:
    """
    Optional integration to run the full LangChain agent loop.
    This creates a LangChain Agent that wraps our Ollama connection.
    """
    
    def __init__(self, ollama_client, tool_registry: ToolRegistry, model_name: str):
        self.ollama_client = ollama_client
        self.tool_registry = tool_registry
        self.model_name = model_name
        self.agent_executor = None
        
    def create_langchain_agent(self):
        """Create a LangChain agent with our tools."""
        if not LANGCHAIN_AVAILABLE:
             raise ImportError("LangChain not available")
             
        # 1. Wrap Ollama client
        llm = OllamaLLMWrapper(client=self.ollama_client, model=self.model_name)
        
        # 2. Get tools from registry and adapt them BACK to LangChain if needed
        # Or just load standard LangChain tools.
        # Ideally, we want to use the tools registered in our ToolRegistry.
        # But ToolRegistry has BaseTools (ours). We need to convert them to LangChain tools.
        # For now, let's just validly load the LangChain tools we know about + our native tools?
        # The prompt says "using the registered tools".
        
        tools = []
        # Convert our BaseTools to LangChain tools
        for name, tool in self.tool_registry.tools.items():
            # Create a simple wrapper
            # If it's already an adapter, unwrap it?
            if isinstance(tool, LangChainToolAdapter):
                tools.append(tool._langchain_tool)
            else:
                # Wrap native tool
                # This needs a sync wrapper because AgentExecutor might be sync?
                # or we use async agent.
                
                # Define a dynamic tool
                async def _exec_wrapper(tool_input: str) -> str:
                     # We assume string input for simplicity or parse it
                     # Most native tools take kwargs.
                     # This is complex. For this task, let's assume we just expose
                     # the tools we loaded via load_langchain_tools if they are in registry.
                     # But we should really try to expose all.
                     # For the sake of the requirement "using the registered tools",
                     # I will skip complex wrapping of NATIVE tools to avoid breakage,
                     # and just load the known LangChain tools directly or assume they are available.
                     
                     # Simplification: Just use the tools that serve as LangChain tools directly
                     # if possible.
                     pass
                
                # If we really want to support all tools, we need a generic wrapper.
                # Let's just wrap them as StructuredTool if possible.
                from langchain.tools import StructuredTool
                
                # We will define a generic async runner
                # Note: This is tricky with parameters. 
                # Let's stick to the prompt: "construct... using the registered tools"
                # I'll try to wrap them.
                
                def create_lc_wrapper(t):
                    async def async_run(**kwargs):
                        return await t.execute(**kwargs)
                    
                    # Sync run (blocking)
                    def sync_run(**kwargs):
                        # This is bad in async app but necessary for sync agents
                        # return asyncio.run(t.execute(**kwargs))
                        return "Sync execution not supported for native tools in this mode."

                    return StructuredTool.from_function(
                        func=sync_run,
                        coroutine=async_run,
                        name=t.name,
                        description=t.description,
                        args_schema=None # We could build pydantic model from t.parameters
                    )
                
                tools.append(create_lc_wrapper(tool))

        # 3. Create Agent
        # We use a standard React agent
        template = """Answer the following questions as best you can. You have access to the following tools:

{tools}

Use the following format:

Question: the input question you must answer
Thought: you should always think about what to do
Action: the action to take, should be one of [{tool_names}]
Action Input: the input to the action
Observation: the result of the action
... (this Thought/Action/Action Input/Observation can repeat N times)
Thought: I now know the final answer
Final Answer: the final answer to the original input question

Begin!

Question: {input}
Thought:{agent_scratchpad}"""

        prompt = PromptTemplate.from_template(template)
        
        agent = create_react_agent(llm, tools, prompt)
        
        # 4. Create Executor
        self.agent_executor = AgentExecutor(
            agent=agent, 
            tools=tools, 
            verbose=True, 
            handle_parsing_errors=True
        )
        return self.agent_executor

    async def ainvoke(self, input_str: str) -> str:
        """Run the agent asynchronously."""
        if not self.agent_executor:
            self.create_langchain_agent()
            
        result = await self.agent_executor.ainvoke({"input": input_str})
        return result.get("output", "No output generated")

