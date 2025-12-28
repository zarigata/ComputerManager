![Computer Manager Banner](assets/banner.png)

# Computer Manager - Your Private AI Desktop Assistant

**Automate your digital life without sacrificing your privacy.**

Computer Manager is a powerful, locally-installed AI agent designed to handle the boring, repetitive, and annoying tasks on your computer. Powered by local Large Language Models (LLMs) via Ollama, it sees what you see and does what you tell it to—all while ensuring **zero data leaves your machine**.

We believe in **Data Sovereignty**. We are not evil bureaucrats. We don't collect your data. We don't sell your habits. This tool is Open Source, free to use, and transparent to the core.

## 🚀 Key Features

*   **🔒 Privacy First & "Null Data" Policy**: No telemetry, no cloud processing, no spying. Your data stays on your SSD.
*   **🤖 Local AI Intelligence**: Leverages the power of Ollama (Llama 3, Mistral, Gemma) to understand natural language commands.
*   **👁️ Visual Understanding**: Capable of "seeing" your screen to provide context-aware assistance (requires Vision models).
*   **⚡ Completely Autonomous**: Can organize files, manage system settings, and automate workflows.
*   **🐧 Cross-Platform**: Run it on Windows, Linux, or macOS.

## ✊ Why Computer Manager?

In an era where every "AI" tool demands your personal data as payment, Computer Manager stands apart.
*   **For the Paranoid**: We built this because we don't trust big tech either.
*   **For the Power User**: Automate complex file operations with a single sentence.
*   **For the Lazy**: "Clean up my Downloads folder" should be a voice command, not a 20-minute chore.

## 🛠️ Hardware Requirements

Since this runs **locally**, your hardware dictates performance.

| Level | RAM | Recommended Model | Use Case |
| :--- | :--- | :--- | :--- |
| **Minimum** (<8GB) | <8GB | Phi-3 3B / Llama 3.2 3B | Basic text commands, no vision |
| **Recommended** | 8-16GB | Mistral 7B / Qwen2.5-VL 7B | Standard automation with vision |
| **Powerhouse** | 16GB+ | Llama 3.1 70B / Qwen2.5-VL 72B | Complex reasoning & High-res Vision |

## 📦 Prerequisites

1.  **Ollama**: The heart of the operation.
    *   Windows/Mac: [Download from ollama.com](https://ollama.com)
    *   Linux: `curl -fsSL https://ollama.com/install.sh | sh`
2.  **Modern OS**: Windows 10/11, macOS 12+, or a modern Linux distro.

## 💾 Installation

### Option 1: The "I just want it to work" (Binaries)
*(Coming Soon - Check [Releases](https://github.com/yourusername/computer-manager/releases) for pre-built executables)*

### Option 2: The "Hacker Way" (Source)

```bash
# 1. Clone the repo (you know the drill)
git clone https://github.com/yourusername/computer-manager.git
cd computer-manager

# 2. Set up your environment
python -m venv venv

# 3. Activate
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# 4. Install dependencies
pip install -r requirements.txt

# 5. Launch the Matrix
python src/main.py
```

### Manual Model Installation
If auto-download fails, you can install recommendations manually:

```bash
# Medium Tier (8-16GB RAM)
ollama pull mistral:7b-instruct-q4_K_M
ollama pull qwen2.5-vl:7b-instruct-q4_K_M

# Low Tier (<8GB RAM)
ollama pull phi3:3b-mini-instruct-q4_K_M
ollama pull llama3.2-vision:11b-instruct-q4_K_M
```

## ❓ Troubleshooting

*   **Ollama Connection Failed**: Ensure Ollama is running (`ollama serve`) and reachable at `http://localhost:11434`.
*   **Model Not Found**: Check if `model_quantization` in `.env` matches what is on Ollama registry. Default is `Q4_K_M`.
*   **Download Stuck**: Large models (70B+) can take hours. Use manual `ollama pull` in terminal to see progress bar.

## ⚙️ Configuration

Copy `.env.example` to `.env` and tweak to your liking.

```env
# Point this to your local Ollama instance
OLLAMA_HOST=http://localhost:11434

# Choose your weapon (Model)
DEFAULT_TEXT_MODEL=llama3
DEFAULT_VISION_MODEL=llava

# Safety First
REQUIRE_CONFIRMATION=true
```

## 🎮 Usage

1.  Ensure **Ollama** is running (`ollama serve`).
2.  Run **Computer Manager**.
3.  Type naturally:
    *   *"Sort my Downloads folder by date"*
    *   *"Find all duplicate images in Pictures"*
    *   *"Close all Chrome tabs that are playing audio"* (Coming soon)
    *   *"Take a look at this error message and tell me how to fix it"*

## 🛡️ Security

We take this seriously.
*   **Sandbox Mode**: Actions are isolated.
*   **Human-in-the-loop**: High-risk commands (like deleting files) require your explicit YES.
*   **Local Only**: Did we mention no data leaves your PC? Because it doesn't.

## 🤝 Contributing

We welcome fellow code-wizards. Check out [CONTRIBUTING.md](CONTRIBUTING.md) to join the resistance.

## 📄 License

MIT License. Free forever.

---
*Generated with ❤️ and 0% spyware.*
