# Nexus Agent 架构文档

## 1. 项目概览

### Nexus Agent 是什么？
Nexus Agent 是一个**私有化、本地优先的智能控制中心**，专为您的数字生活打造。与基于云的助手（如 ChatGPT 或 Claude）不同，Nexus Agent 完全运行在您自己的硬件上（针对 **Apple Silicon M系列芯片** 进行了深度优化），确保您的个人数据、记忆和工具交互永远不会离开您的设备。

### 核心能力与场景

| 能力 | 描述 | 使用场景 |
| :--- | :--- | :--- |
| **主动记忆 (Active Memory)** | 使用向量存储长期记住用户的偏好和事实。 | *反思机制*：“你之前告诉我你偏好 Python，所以我用 Python 写了这个脚本。” |
| **本地推理 (Local Reasoning)** | 通过 Ollama 本地运行强大的 LLM (Qwen2.5-14B)。 | *隐私安全*：总结敏感文档或处理财务数据，无需经过云端 API。 |
| **工具执行 (Tool Execution)** | 通过 MCP (模型上下文协议) 连接本地文件、脚本和 API。 | *自动化*：“读取我最新的日志文件并总结错误信息。” |
| **语音交互 (Voice Interface)** | 支持语音转文字 (STT) 和文字转语音 (TTS)。 | *免提操作*：“嘿 Nexus，帮我记录一下这个会议要点。” |

---

## 2. 高层架构

系统设计为一个模块化的 **Agentic Loop（智能体循环）**。它由四个主要的 Docker 化服务组成，通过私有网络进行通信。

```mermaid
graph TD
    User[用户 / 客户端] -->|HTTP/语音| API[Nexus Agent API (FastAPI)]
    
    subgraph "本地基础设施 (Docker)"
        API -->|生成| LLM[Ollama (Qwen2.5-14B)]
        API -->|嵌入/搜索| Embed[Embedding Server (bge-small-zh)]
        API -->|读/写| DB[(PostgreSQL + pgvector)]
        API -->|缓存| Redis[(Redis)]
    end
    
    subgraph "外部/本地工具"
        API -->|MCP 协议| MCPServer[本地脚本 / MCP 服务器]
        API -->|沙箱执行| Sandbox[Docker Sandbox]
    end
```

### 关键设计决策
1.  **本地优先与隐私**：我们选择 **PostgreSQL + pgvector** 而不是云端向量库，以保持技术栈的简洁和统一。所有推理都在 `localhost` 发生。
2.  **硬件加速**：Embedding Server 利用 **MPS (Metal Performance Shaders)** 在 Mac 芯片上进行高效的语义搜索。
3.  **主动记忆**：这不仅仅是聊天记录。Agent 会主动决定*保存*或*检索*特定的洞察，构建一个不断增长的知识库。

---

## 3. 核心组件详解

### 3.1 Agent 核心 (大脑)
Agent 的逻辑是一个基于 **LangGraph** 构建的状态机。它不只是简单回复，而是遵循循环：
`思考 (Think) -> 检索上下文 (Retrieve) -> 规划 (Plan) -> 行动 (Act) -> 观察 (Observe) -> 回复 (Reply)`。

*   **状态机**：跟踪对话历史、用户上下文和当前的工具输出。
*   **安全**：每一个动作在执行前都会经过 **RBAC 策略** (基于角色的访问控制) 检查。

### 3.2 主动记忆系统 (海马体)
我们将长期记忆分为三种独特的类型，以提高检索质量：

*   **👤 画像 (Profile)**：关于您的静态事实（例如：“住在上海”，“经理角色”）。
*   **💡 反思 (Reflexion)**：行为洞察（例如：“用户更喜欢简洁的代码”）。
*   **📚 知识 (Knowledge)**：一般性存储的事实或文件摘要。

**技术流程**：
1.  用户发送消息。
2.  系统本地生成向量 Embedding (`bge-small-zh`)。
3.  在 `pgvector` 中查询 **相似度 > 0.4** 的记忆。
4.  在 LLM 看到消息之前，将相关记忆注入到提示词中。

### 3.3 模型上下文协议 (双手)
Nexus Agent 使用 **MCP 标准** 来使用工具。这使得它能够：
*   连接标准的 MCP 服务器（如 Postgres 查看器或文件系统访问）。
*   安全运行本地 Python 脚本。
*   **审计拦截器**：一个中间件层，将每一次工具调用都记录到数据库 (`auditlog` 表) 中，确保透明度。

---

## 4. 数据流示例

**场景**：用户说 *“记一下，我下个月要搬去东京了。”*

1.  **摄入**：HTTP POST `/chat` 接收文本。
2.  **认证**：验证 API Key。解析用户 ID。
3.  **检索**：系统检查 `pgvector` 获取现有上下文（例如：“用户现在住在哪里？”）。
4.  **推理 (LLM)**：
    *   LLM 看到输入并决定：*我需要使用 `store_insight` 工具。*
    *   LLM 生成参数：`{"content": "User is moving to Tokyo next month", "type": "profile"}`。
5.  **执行**：
    *   Agent 验证用户权限。
    *   `MemoryManager` 嵌入文本并将其保存到 DB。
6.  **响应**：Agent 确认操作：*“我已经更新了您的画像，记录了您要搬去东京的事。”*

---

## 5. 开发者指南

### 目录结构
*   **`/app/core`**：核心引擎。`agent.py` (图逻辑), `memory.py` (向量逻辑), `mcp.py` (工具)。
*   **`/app/models`**：SQLModel 数据库定义。
*   **`/scripts`**：实用工具。使用 `deploy_local.sh` 启动所有服务。

### 扩展 Agent
要添加新能力：
1.  在 `servers/demo_tool.py` 中创建一个 Python 函数。
2.  将其添加到 `mcp_server_config.json`。
3.  重启 Agent。LLM 将自动发现并学会使用这个新工具。
