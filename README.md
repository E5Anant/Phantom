# Phantom - The Ghost which controls your Computer
<p align="center">
    <img src="phantom/assets/PHANTOM.jpg" alt="Phantom Banner" width="600"/>
</p>

Phantom is a powerful, multi-modal AI assistant framework that combines multiple Large Language Models (LLMs) with advanced automation tools for code generation, web browsing, GUI automation, and computer control.

## ✨ Features

- **Multi-LLM Support**: OpenAI, Gemini, Anthropic Claude, Groq
- **Code Generation**: Automatic Python code generation and execution with error recovery
- **Cross-Platform Computer Control**: Powered by Orgo - works on Windows, macOS, and Linux
- **GUI Automation**: Advanced computer control using AgentS2 and OSWorldACI
- **Web Search**: Intelligent web search and information gathering
- **File Operations**: Read, write, and manipulate files
- **Threaded Execution**: Fast, non-blocking operations with progress indicators
- **Error Recovery**: Automatic code debugging and fixing by AI
- **Modular Architecture**: Easily customizable tools and LLM configurations

## 🛠️ Installation

### Prerequisites

- Python 3.8 or higher
- Cross-platform support: Windows, macOS, Linux (thanks to Orgo)

### Setup

1. **Clone the repository**:
   ```bash
   git clone https://github.com/your-username/phantom.git
   cd phantom
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables**:
   ```bash
   cp .env.example .env
   ```
   Edit the `.env` file with your API keys (see API Keys section below).

## 🔑 API Keys Configuration

### Required API Keys

Copy `.env.example` to `.env` and configure the following:

```bash
# MANDATORY for cross-platform computer control via Orgo
ORGO_API_KEY=your_orgo_api_key_here

# MANDATORY for advanced GUI automation
ANTHROPIC_API_KEY=your_anthropic_api_key_here

# CHOOSE based on your preferred LLM
GEMINI_API_KEY=your_gemini_api_key_here
OPENAI_API_KEY=your_openai_api_key_here  
GROQ_API_KEY=your_groq_api_key_here
```

### Where to Get API Keys

- **Anthropic Claude**: [https://console.anthropic.com/](https://console.anthropic.com/)
- **Google Gemini**: [https://aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey)
- **OpenAI**: [https://platform.openai.com/api-keys](https://platform.openai.com/api-keys)
- **Groq**: [https://console.groq.com/keys](https://console.groq.com/keys)
- **Orgo**: [https://orgo.ai/](https://orgo.ai/) ⭐ **Cross-platform computer control (Windows/macOS/Linux)**

### Minimum Requirements

For basic functionality, you need:
- At least **one LLM API key** (Gemini, OpenAI, Groq, or Anthropic)
- **ORGO_API_KEY** ⭐ **Essential for cross-platform computer control**
- **ANTHROPIC_API_KEY** (for advanced GUI automation)

## 🚀 Quick Start

### Basic Usage

Simply run the main script:

```bash
python main.py
```

This will start Phantom with the default configuration using Gemini as the main LLM.

### Interactive Commands

Once running, you can ask Phantom to:

```
# Code generation and automation
>>> Create a Python script to organize my desktop files by extension

# Web search and research
>>> Search for the latest stock price of tesla

# GUI automation
>>> Open Notepad and write "Hello World"

# File operations
>>> Read the contents of config.txt and explain what it does

# Complex tasks
>>> Create a web scraper for news headlines and save to CSV
```

## 🎛️ Customization

### Changing the Main LLM

Edit `main.py` to use a different LLM:

```python
# Using OpenAI instead of Gemini
llm = Openai('gpt-4')

# Using Anthropic Claude
llm = Anthropic('claude-3-sonnet')

# Using Groq
llm = GroqLLM('llama-3.1-70b-versatile')
```

### Customizing Tools

Add or remove tools in `main.py`:

```python
# Basic setup
tools = [
    CodesmithTool(llm_instance=Gemini()),
    WebSearchTool(),
    ReadFileTool()
]

# Advanced setup with GUI automation
tools = [
    CodesmithTool(llm_instance=Gemini()),
    WebSearchTool(), 
    Orgotool(Computer=Computer(api_key=environ.get('ORGO_API_KEY')), agent=agent_s2),
    ReadFileTool()
]
```

### Advanced Configuration

For advanced GUI automation, configure AgentS2:

```python
# Configure different LLMs for different components
engine_params = {"engine_type": "openai", "model": "gpt-4"}
grounding_params = {"engine_type": "anthropic", "model": "claude-3-sonnet"}

grounding_agent = OSWorldACI(
    platform='windows',
    engine_params_for_generation=engine_params,
    engine_params_for_grounding=grounding_params
)

agent_s2 = AgentS2(
    engine_params=engine_params,
    grounding_agent=grounding_agent,
    platform="windows",
    action_space="pyautogui",
    observation_type="screenshot"
)
```

## 🧰 Available Tools

### CodesmithTool
- **Purpose**: Python code generation and execution
- **Features**: Automatic error recovery, module installation, threaded execution
- **Usage**: "Create a script to...", "Write code that..."

### WebSearchTool
- **Purpose**: Web search and information gathering
- **Features**: Real-time web search, content extraction
- **Usage**: "Search for...", "Find information about..."

### Orgotool ⭐ **Powered by Orgo**
- **Purpose**: Cross-platform computer and GUI automation
- **Features**: Click, type, screenshot, app control on Windows/macOS/Linux
- **Orgo Integration**: Universal computer control API that works seamlessly across all operating systems
- **Usage**: "Open Chrome", "Click the submit button", "Take a screenshot", "Control my desktop"

### ReadFileTool
- **Purpose**: File system operations
- **Features**: Read files, directory listing
- **Usage**: "Read the file...", "Show me the contents of..."

## 🎯 Use Cases

### Development Tasks
```
>>> Create a simple website about Artificial Intelligence
>>> make a calculator in calculator.py file
```

### Research Tasks
```
>>> Research the latest AI developments and create a summary
>>> Find Python libraries for data visualization
>>> Compare different cloud hosting providers
```

## 🔧 Architecture

```
phantom/
├── app.py              # Main PhantomAssistant class
├── codesmith.py        # Code generation and execution
├── tool.py            # Base tool interface
├── func/              # Function tools
│   ├── automation.py  # Basic automation functions
│   ├── orgotool.py    # Advanced GUI automation  
│   └── websearch.py   # Web search capabilities
├── llms/              # LLM interfaces
│   ├── openaillm.py   # OpenAI integration
│   ├── genai.py       # Gemini integration
│   ├── anthropicllm.py # Claude integration
│   └── groqllm.py     # Groq integration
└── prompts/           # System prompts
    ├── base.md        # Main orchestrator prompt
    └── codesmith.md   # Code generation prompt
```

## ⚙️ Configuration Options

### Environment Variables

| Variable | Required | Purpose |
|----------|----------|---------|
| `ORGO_API_KEY` | **YES** | ⭐ **Cross-platform computer control (Windows/macOS/Linux)** |
| `ANTHROPIC_API_KEY` | **YES** | Claude LLM + Advanced GUI automation |
| `GEMINI_API_KEY` | Optional* | Google Gemini LLM |
| `OPENAI_API_KEY` | Optional* | OpenAI GPT models |
| `GROQ_API_KEY` | Optional* | Groq LLM inference |

*At least one LLM API key is required

### Model Configuration

Configure specific models in your setup:

```python
# High-performance setup
llm = Openai('gpt-4-turbo')
codesmith_llm = Gemini('gemini-2.0-flash-lite-001')

# Cost-effective setup  
llm = GroqLLM('llama-3.1-70b-versatile')
codesmith_llm = Gemini('gemini-2.5-flash-lite')

# Balanced setup
llm = Anthropic('claude-3-sonnet')
codesmith_llm = Gemini('gemini-2.0-flash-lite-001')
```

## 🚨 Troubleshooting

### Common Issues

1. **"No API key found"**
   - Ensure your `.env` file is in the root directory
   - Check that API keys are correctly formatted
   - Verify the API key is valid and has credits

2. **"Module not found"**
   - Phantom will automatically prompt to install missing modules
   - Ensure you have pip permissions for installations

3. **GUI automation not working**
   - Verify ORGO_API_KEY is set (required for all computer control)
   - Verify ANTHROPIC_API_KEY is set (for advanced GUI features)
   - Orgo works on Windows, macOS, and Linux
   - Ensure screen resolution is supported
   - Check Orgo service status at [orgo.ai](https://orgo.ai)

4. **Slow execution**
   - Threading is enabled by default for better performance
   - Consider using faster models like Groq for code generation
   - Check your internet connection for API calls

### Debug Mode

Enable verbose logging by modifying the console output in the code or using a more detailed LLM model.

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- ⭐ **Powered by [Orgo](https://orgo.ai/) for universal cross-platform computer control**
- Built with [Rich](https://github.com/Textualize/rich) for beautiful terminal UI
- Uses [AgentS2](https://github.com/SkyworkAI/agent-studio) for advanced GUI automation
- Integrates multiple LLM providers for maximum flexibility

---

**Happy Automating! 🤖✨**