# Nexus Agent OS

Nexus Agent is a **Self-Improving, Multimodal AI Operating System** designed for local capabilities and privacy. It serves as a personal control center that runs entirely on your infrastructure (or hybrid), orchestrating tools, memory, and devices.

> **Status**: Beta (v2.0.0)

## 🌟 Key Features

### 🧠 Autonomous Core
- **Self-Generating Skills**: The agent learns from its mistakes. If a tool call fails, it proposes a new rule to fix it in the future, storing this knowledge in its skill registry.
- **Active Memory**: Vectorized long-term memory (PostgreSQL + pgvector) to recall user preferences and past context.
- **Privacy-First**: Native support for **Ollama** (e.g., Qwen2.5, DeepSeek) running locally.

### 🛠️ Universal Connectivity
- **MCP Native**: Built on the **Model Context Protocol**, allowing seamless integration with local resources (files, CLI) and remote APIs.
- **Multimodal**: Voice interaction (STT/TTS) and image generation capabilities.
- **Smart Home**: Deep integration with **Home Assistant** for device control and state monitoring.

### 🛡️ Mission Control
- **Dashboard**: A Streamlit-based command center to monitor agent health, audit logs, and memory state.
- **Audit System**: Every decision and tool execution is logged and auditable.
- **Tailscale Network**: Secure, encrypted remote access via a simplified Docker network mesh.

## 🚀 Quick Start

### Prerequisites
- Docker & Docker Compose
- Python 3.10+ (for local development)
- [Optional] Tailscale account for remote access

### Deployment

1.  **Clone the Repository**
    ```bash
    git clone https://github.com/o3o3o/nexus-agent.git
    cd nexus-agent
    ```

2.  **Configure Environment**
    Copy the example configuration:
    ```bash
    cp .env.example .env
    ```
    Edit `.env` to set your preferences (LLM model, API keys, etc.).

3.  **Launch Stack**
    Start the Agent, Database, Dashboard, and local services:
    ```bash
    docker-compose up -d --build
    ```

4.  **Access Dashboard**
    Open [http://localhost:8501](http://localhost:8501) to view the Mission Control interface.

## 📚 Documentation

- [Architecture Overview](ARCHITECTURE.md)
- [Self-Learning System](skills/README.md) (Coming Soon)
- [Model Context Protocol (MCP)](https://github.com/modelcontextprotocol)

## 🛠️ Development

We use `uv` or `pip` for dependency management.

```bash
# Install dependencies
pip install -r requirements.txt

# Run Tests
pytest

# Code Formatting
ruff check .
```

## 🤝 Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for details.

1.  Fork the Project
2.  Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3.  Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4.  Push to the Branch (`git push origin feature/AmazingFeature`)
5.  Open a Pull Request

## 📄 License

Distributed under the MIT License. See `LICENSE` for more information.
