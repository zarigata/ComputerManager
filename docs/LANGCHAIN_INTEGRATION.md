# LangChain Integration

This application includes optional integration with [LangChain](https://www.langchain.com/), a powerful framework for building applications with LLMs. This integration allows you to use LangChain's extensive ecosystem of tools directly within Computer Manager.

## Overview

The LangChain integration acts as a bridge, wrapping LangChain tools so they can be used by the internal agent system. This provides a hybrid approach:
- **Core System**: Uses the lightweight, custom agent architecture for speed and control.
- **Extensions**: Uses LangChain to access a vast library of external tools (Wikipedia, Search, Calculator, etc.).

## Installation

To use LangChain tools, you must install the optional dependencies:

```bash
pip install -e .[langchain]
```

This will install:
- `langchain`
- `langchain-community`
- `wikipedia`
- `duckduckgo-search`

## Configuration

### Via Settings Dialog (Recommended)

1. Open **Settings**.
2. Go to the **Advanced** tab.
3. Locate the **LangChain Integration (Optional)** section.
4. Check **Enable LangChain Integration**.
5. Select the tools you wish to enable from the list.
6. Click **Apply** or **OK**.

### Via Environment Variables

You can also configure LangChain in your `.env` file:

```env
# Enable LangChain
LANGCHAIN_ENABLED=true

# Initial tools to load (comma-separated)
LANGCHAIN_TOOLS=wikipedia,calculator,duckduckgo_search
```

### Weather Tool Configuration

To use the Weather tool, you need an OpenWeatherMap API key:

```env
OPENWEATHERMAP_API_KEY=your_api_key_here
```

## Available Tools

The following tools are available out-of-the-box when LangChain integration is enabled:

| Tool | Description | Requirements | Example Usage |
|------|-------------|--------------|---------------|
| **Wikipedia** | Search and retrieve Wikipedia articles | `wikipedia` package | "Search Wikipedia for Python programming" |
| **Calculator** | Evaluate mathematical expressions | None | "Calculate 25 * 4 + 10" |
| **DuckDuckGo Search** | Search the web anonymously | `duckduckgo-search` package | "Search for latest AI news" |
| **Weather** | Get current weather information | API Key | "What's the weather in London?" |

## Troubleshooting

### "LangChain not installed"
If you see this warning, simply run `pip install -e .[langchain]` to install the required packages.

### Tool Not Appearing
- Ensure the tool is checked in the Settings dialog.
- Check the logs for import errors. Some tools may have additional dependencies.
- For the Weather tool, ensure the API key is set in your environment.

## Advanced: Adding Custom Tools

Developers can add more LangChain tools by modifying `src/agent/langchain_bridge.py`.

1. Import the tool class in `load_langchain_tools`.
2. Create a loader function (e.g., `load_custom_tool`).
3. Add the loader to the `loaders` dictionary in `load_langchain_tools`.
