# Nexus Agent OS

<div align="center">

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Docker](https://img.shields.io/badge/docker-compose-green.svg)](https://www.docker.com/)

[English](#english) | [中文说明](#chinese)

</div>

<a name="english"></a>
## 🇬🇧 English

**Nexus Agent** is a private, intelligent control center designed for the **Apple Silicon** era. It starts as your generic **Home AI Center**, running entirely on your local infrastructure to ensure privacy, and scales seamlessly to **Enterprise Integration**.

### 🚀 Vision
> **"From Local Privacy to Enterprise Intelligence"**

1.  **Home AI Center**: Deploy on a **Mac mini (M4)** to manage your smart home, schedule, and personal knowledge base without data leaving your house.
2.  **Enterprise Connector**: Once trusted, deploy the same agent to enterprise environments to bridge internal tools (Feishu/Lark, DingTalk) with local secure reasoning.

### ⚡ Hardware & Performance
Optimized for **Mac mini M4 (32GB RAM)**:
-   **Inference**: capable of running **GLM-4.7-Flash** (or Qwen2.5-32B) locally with high token/sec rates.
-   **Memory**: vectorized long-term memory accelerated by Metal (MPS).

### 🌟 Key Features
-   **Autonomous Core**: Self-learning agent that proposes rules to fix its own tool usage errors.
-   **Universal Skills**: 
    -   **MCP Native**: Supports Model Context Protocol for file system and API access.
    -   **Smart Home**: Deep integration with Home Assistant.
-   **Mission Control**: Streamlit dashboard for monitoring health, audit logs, and memory state.

---

<a name="chinese"></a>
## 🇨🇳 中文说明

**Nexus Agent** 是专为 **Apple Silicon** 时代打造的隐私优先、智能控制中心。它的愿景是成为您的 **家庭 AI 中枢**，在保障隐私的前提下运行所有推理与记忆，并具备无缝扩展至 **企业级集成** 的能力。

### 🚀 项目愿景
> **“从家庭隐私计算到企业智能中枢”**

1.  **家庭 AI 智能中心**：部署在您的 **Mac mini (M4)** 上，全本地管理智能家居、日程安排和个人知识库，数据不出户。
2.  **企业级对接**：经过验证的 Agent 可无缝接入企业环境，作为安全网关连接 Feishu (飞书)、钉钉等办公流与内部业务系统。

### ⚡ 硬件与性能
专为 **Mac mini M4 (32GB 内存)** 优化：
-   **本地推理**：在 32GB 统一内存上流畅运行 **GLM-4.7-Flash** 等高性能模型。
-   **硬件加速**：利用 Metal (MPS) 实现向量数据库 (pgvector) 的极速检索。

### 🌟 核心特性
-   **自主进化内核**：Agent 具备自我反思能力，能自动纠正工具调用错误并生成新的技能规则。
-   **通用技能协议**：
    -   **MCP 原生支持**：基于 Model Context Protocol 标准，轻松挂载本地文件与 API。
    -   **深度家居互联**：自带 Home Assistant 完美集成。
-   **任务指挥台**：提供可视化 Dashboard，实时监控大脑状态、审计自我学习日志。

---

## 🏗️ Architecture / 架构图

```mermaid
graph TD
    subgraph Interfaces [Interfaces / 触手层]
        TG[Telegram Bot]
        FS[Feishu Bot]
        CLI[Command Line]
    end

    subgraph Core [Nexus Core / 大脑层]
        Router[Router Agent]
        Planner[LangGraph State Machine]
        Sandbox[Python Sandbox]
    end

    subgraph Skills [MCP Servers / 技能层]
        HA[Home Assistant MCP]
        File[FileSystem MCP]
        System[MacOS System Control]
    end

    subgraph Hardware [Infrastructure / 硬件层]
        Ollama[Ollama Service]
        Docker[Docker Containers]
    end

    TG --> Router
    FS --> Router
    Router --> Planner
    Planner --> HA
    Planner --> Sandbox
    Planner --> System
    HA --> Ollama
```

## 🚀 Quick Start / 快速开始

1.  **Install & Configure Ollama** / **安装 Ollama**
    - Download from [Ollama.com](https://ollama.com).
    - Pull the **GLM-4.7-flash** Model (Required for high performance):
      ```bash
      # Mac mini M4 (32GB) Requirement
      # Create custom model with 32k context
      ollama create glm4.7-flash-32k -f ./scripts/glm4-flash-32k.Modelfile
      ```

2.  **Environment Setup** / **环境配置**
    ```bash
    git clone https://github.com/nexus-agent-lab/nexus-agent.git
    cd nexus-agent
    
    # Configure Tailscale & Env (Interactive Script)
    ./scripts/admin/setup_tailscale.sh
    
    # Or manually copy config
    # cp .env.example .env
    ```
    
    > **Tip / 提示**: 
    > To enable Telegram control:
    > 1. Talk to `@BotFather` to create a bot -> Get `TELEGRAM_BOT_TOKEN`.
    > 2. Talk to `@userinfobot` -> Get your ID -> Set `TELEGRAM_ALLOWED_USERS`.
    > 3. Add them to your `.env` file.

3.  **Launch** / **启动服务**
    ```bash
    docker-compose up -d --build
    ```

4.  **Dashboard / 访问控制台**
    Open [http://localhost:8501](http://localhost:8501)

## 🗺️ Roadmap / 路线图

- [x] **Core**: Local LLM Support (Ollama/Qwen2.5/GLM), Active Memory (pgvector)
- [x] **Interfaces**: Telegram Bot, CLI
- [ ] **Enterprise**: Feishu (Lark) Integration (Coming Soon / 即将推出)
- [ ] **Capabilities**: Computer Use / Desktop Automation (WIP)
- [ ] **Capabilities**: Computer Use / Desktop Automation (WIP)

## 🌍 Remote Access & Security / 远程访问与安全

Nexus Agent prioritizes security for home and enterprise deployments:

1.  **Private Network (Tailscale)**: 
    - Built-in Tailscale Sidecar ensures secure, encrypted access without exposing ports.
    - No public IP required; accessible via MagicDNS (e.g., `http://nexus-agent-server:8501`).
    - [Setup Guide](https://tailscale.com/kb/1017/install) | [Admin Console](https://login.tailscale.com/admin/machines)

2.  **Audit Logs**:
    - All tool executions and "Self-Learning" rule changes are recorded in the PostgreSQL audit log.
    - Viewable via the **Mission Control Dashboard**.

3.  **Authentication**:
    - Role-based access control (Admin/User) available for Telegram and API endpoints.

## 📄 License

Distributed under the MIT License.
