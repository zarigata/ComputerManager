# Computer Manager - AI-Powered Desktop Automation

An intelligent desktop assistant powered by Ollama that can control and automate your computer through natural language commands. Works on Windows, Linux, and macOS.

## Features

- 🤖 **AI-Powered Control**: Use natural language to control your computer
- 👁️ **Vision Capabilities**: AI can see and understand your screen
- 🖥️ **Cross-Platform**: Works on Windows, Linux, and macOS
- 🎯 **Smart Model Selection**: Automatically selects optimal AI models based on your hardware
- 🔒 **Secure**: Built-in permission system and audit logging
- 📦 **Easy Installation**: Single executable download, no Python required

## Hardware Requirements

### Minimum (Low-End)
- **RAM**: 4-8 GB
- **Recommended Model**: Phi-3 Mini (3B) or Gemma 3:4B
- **Vision Model**: Llama 3.2 Vision 11B

### Recommended (Mid-Range)
- **RAM**: 8-16 GB
- **Recommended Model**: Mistral 7B or Llama 3.2 7B
- **Vision Model**: Qwen 2.5 VL 7B

### High-End
- **RAM**: 16+ GB
- **Recommended Model**: Llama 3.2 70B
- **Vision Model**: Qwen 2.5 VL 72B

## Prerequisites

1. **Ollama**: Install Ollama on your system
   - Windows/Mac: Download from [ollama.com](https://ollama.com)
   - Linux: `curl -fsSL https://ollama.com/install.sh | sh`

2. **Python 3.9+** (for development only, not required for pre-built executables)

## Installation

### Option 1: Download Pre-built Executable (Recommended)

1. Go to [Releases](https://github.com/yourusername/computer-manager/releases)
2. Download the executable for your platform:
   - Windows: `ComputerManager-Windows.exe`
   - Linux: `ComputerManager-Linux.AppImage`
   - macOS: `ComputerManager-macOS.app`
3. Run the executable

### Option 2: Install from Source

```bash
# Clone the repository
git clone https://github.com/yourusername/computer-manager.git
cd computer-manager

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run the application
python src/main.py
```

## Configuration

Create a `.env` file in the project root (copy from `.env.example`):

```env
# Ollama Configuration
OLLAMA_HOST=http://localhost:11434

# Model Configuration (leave empty for auto-detection)
DEFAULT_TEXT_MODEL=
DEFAULT_VISION_MODEL=

# Security Configuration
REQUIRE_CONFIRMATION=true
PERMISSION_LEVEL=advanced
```

## Usage

1. **Start Ollama**: Make sure Ollama is running on your system
2. **Launch Computer Manager**: Run the executable or `python src/main.py`
3. **First Run**: The app will detect your hardware and recommend optimal models
4. **Chat**: Type commands in natural language:
   - "Take a screenshot and describe what you see"
   - "Open my browser and search for Python tutorials"
   - "Create a new folder called 'Projects' on my desktop"
   - "Find all PDF files in my Documents folder"

## Capabilities

### Current Features
- ✅ System information detection
- ✅ Configuration management
- ✅ Ollama integration

### Upcoming Features (In Development)
- 🔄 Chat interface with PyQt6
- 🔄 File operations (read, write, move, delete)
- 🔄 Application launching and control
- 🔄 Screenshot capture and analysis
- 🔄 Keyboard and mouse automation
- 🔄 Platform-specific system control
- 🔄 Security and audit logging

## Security

Computer Manager includes multiple security layers:

- **Permission Levels**: Basic, Advanced, Admin
- **User Confirmation**: Prompts for sensitive operations
- **Audit Logging**: Tracks all AI-initiated actions
- **Sandboxing**: Configurable operation restrictions

## Development

### Project Structure

```
ComputerManager/
├── src/
│   ├── gui/              # PyQt6 interface
│   ├── ollama/           # Ollama integration
│   ├── agent/            # AI agent core
│   ├── automation/       # System automation
│   ├── security/         # Security layer
│   └── utils/            # Utilities (system_info, config)
├── tests/                # Unit tests
├── docs/                 # Documentation
└── build/                # Build scripts
```

### Running Tests

```bash
pytest tests/
```

### Code Formatting

```bash
black src/
ruff check src/
```

## Troubleshooting

### Ollama Connection Error
- Ensure Ollama is running: `ollama serve`
- Check Ollama host in `.env`: `OLLAMA_HOST=http://localhost:11434`

### GPU Not Detected
- Install NVIDIA drivers if you have an NVIDIA GPU
- The app will automatically fall back to CPU mode

### Permission Errors
- Windows: Run as Administrator for system-level operations
- Linux/macOS: Use `sudo` for privileged operations

## Contributing

Contributions are welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

This project is licensed under the MIT License - see [LICENSE](LICENSE) file for details.

## Acknowledgments

- [Ollama](https://ollama.com) - Local AI model runtime
- [PyQt6](https://www.riverbankcomputing.com/software/pyqt/) - GUI framework
- [psutil](https://github.com/giampaolo/psutil) - System monitoring
- [py3nvml](https://github.com/fbcotter/py3nvml) - NVIDIA GPU monitoring

## Roadmap

- [x] Phase 1: Project setup and system detection
- [ ] Phase 2: Ollama integration and model management
- [ ] Phase 3: PyQt6 chat interface
- [ ] Phase 4: Custom agent core
- [ ] Phase 5: Basic automation tools
- [ ] Phase 6: Advanced automation (keyboard/mouse)
- [ ] Phase 7: Vision integration
- [ ] Phase 8: Platform-specific control
- [ ] Phase 9: Security layer
- [ ] Phase 10: LangChain integration
- [ ] Phase 11: Cross-platform packaging

## Support

- 📧 Email: support@example.com
- 💬 Discord: [Join our community](https://discord.gg/example)
- 🐛 Issues: [GitHub Issues](https://github.com/yourusername/computer-manager/issues)

---

**⚠️ Warning**: This application can perform system-level operations. Always review actions before confirming, especially with Admin permission level.
