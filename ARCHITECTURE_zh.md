# Nexus Agent 架构文档

## 1. 系统概览

Nexus Agent 是一个专为 **Apple Silicon (M4)** 硬件设计的私有化高性能智能控制中心。它通过在本地运行核心推理和记忆操作，最大限度地保护数据隐私。

**核心理念：**
- **本地优先 (Local-First)**：LLM 和 Embedding 模型完全运行在设备端 (Ollama, Metal/MPS 加速)。
- **主动记忆 (Active Memory)**：Agent 不仅仅是“记录”聊天，还会主动提炼并检索“洞察 (Insights)”和“偏好 (Preferences)”。
- **安全 (Secure)**：对所有工具执行实施应用级权限控制 (RBAC) 和审计日志记录 (Audit Logging)。

---

## 2. 高层架构

系统由四个主要的 Docker 化服务组成，通过私有网络进行通信：

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

---

## 3. 核心组件

### 3.1 Agent 核心 (LangGraph)
Agent 的“大脑”是一个基于 **LangGraph** 构建的状态机，遵循 `思考 (Think) -> 行动 (Act) -> 观察 (Observe)` 循环。

*   **状态 (State)**：`messages` (消息), `user_context` (用户上下文), `memories` (记忆), `trace_id` (追踪ID)。
*   **节点 (Nodes)**：
    1.  **检索记忆 (Retrieve Memories)**：根据用户最新的查询，从 `pgvector` 中获取相关上下文。
    2.  **模型 (Model)**：调用本地 LLM (Qwen2.5)，传入注入了上下文的提示词和可用工具。
    3.  **工具 (Tools)**：执行请求的工具（通过权限检查后）并返回结果。
*   **边 (Edge)**：如果调用了工具，则循环回 **模型**；如果生成了最终答案，则结束。

### 3.2 主动记忆系统 (Active Memory System)
与标准的 RAG 不同，该系统对记忆类型进行了区分：
*   **画像 (Profile)**：关于用户的静态事实（例如：“住在上海”，“使用 Python”）。
*   **反思 (Reflexion)**：从过去交互中得出的洞察（例如：“用户更喜欢简洁的回答”）。
*   **知识 (Knowledge)**：存储的一般性事实。

**技术栈**：
*   **存储**：PostgreSQL 配合 `pgvector` 扩展。
*   **索引**：HNSW (Hierarchical Navigable Small World) 用于快速近似最近邻搜索。
*   **Embedding**：`BAAI/bge-small-zh-v1.5` 托管在本地 FastAPI 服务器上，由 Mac Metal (MPS) 加速。
*   **检索**：余弦相似度搜索（默认阈值：0.4）。

### 3.3 模型上下文协议 (MCP)
Agent 通过 MCP 连接外部能力。
*   **注册表**：工具在 `mcp_server_config.json` 中定义。
*   **安全**：每个工具的执行都由 **审计拦截器 (Audit Interceptor)** 把关，该拦截器记录尝试操作、检查 RBAC 权限（例如：特定工具需要 `admin` 角色），并记录结果。

---

## 4. 数据流

### 聊天请求生命周期
1.  **摄入**：用户通过 HTTP POST `/chat` 发送消息。
2.  **认证**：验证 API Key；将用户身份附加到请求中。
3.  **记忆检索**：
    *   系统使用本地 Embedding Server 对用户消息进行向量化。
    *   在 `pgvector` 中查询前 k 个相关记忆（相似度 > 0.4）。
    *   将记忆注入系统提示词 (System Prompt)：*“你了解关于用户的以下信息...”*
4.  **推理**：
    *   LLM 接收消息 + 记忆上下文。
    *   决定调用工具（例如 `save_insight`）或直接回答。
5.  **执行（如果选择了工具）**：
    *   Agent 检查用户是否有权使用该工具。
    *   执行工具（例如：向 DB 保存新向量）。
    *   结果反馈给 LLM。
6.  **响应**：将最终答案返回给用户。

---

## 5. 目录结构

```text
/app
  /core
    agent.py       # LangGraph 定义
    memory.py      # MemoryManager (向量数据库逻辑)
    mcp.py         # MCP 客户端与工具加载
    audit.py       # 审计日志拦截器
  /models
    user.py        # 用户/认证相关的 SQLModel
    memory.py      # 向量相关的 SQLModel
  /tools
    memory_tools.py # save_insight, store_preference
    registry.py     # 静态工具注册
/scripts
    deploy_local.sh # 一键启动脚本 (Ollama + Embedding + App)
    verify_memory_zh.py # 中文验证脚本
/servers
    demo_tool.py    # MCP 服务器示例
```
