# MCP Governance & Maintenance Policy

> **Status**: Strategic Policy Draft
> **Scope**: Managing external tool integrations within Nexus Agent ecosystem.

## 1. The Core Problem
Relying on direct third-party MCP images (e.g., from community Hubs) introduces three primary risks for an AI Operating System:
1.  **Security**: Unvetted code executing in the same network context.
2.  **Reliability**: Upstream breaking changes causing sudden Agent failure.
3.  **Performance**: Standard MCPs often lack fine-grained caching needed for high-frequency AI loops.

## 2. The Maintenance Strategy: "Official Fork"
Nexus Agent adopts a **Self-Sovereign Integration** model. 

### 2.1 Tier 1: System Integrations (Critical)
Integrations that control physical hardware (Home Assistant) or private data (Feishu, FileSystem) MUST follow this flow:
- **Fork**: Clone the community repo to `nexus-mcp/mcp-xxx`.
- **Audit**: Conduct a security pass on `call_tool` implementations.
- **Enhance**: Add standard Nexus metadata (domains, categories) and caching logic.
- **Deploy**: Pin to a specific versioned container image built by our CI.

### 2.2 Tier 2: Community Tools
Generic tools (Calculator, Weather, Google Search) can use community images but should be wrapped in an internal permission domain.

## 3. Mandatory Enhancements for Forks
Any forked MCP server should be updated to support:
-   **Structured Metadata**: Tools must include `domain` and `category` in their metadata for RBAC.
-   **Error Recovery**: Return clear, descriptive error strings (not stack traces) to enable LLM self-correction.
-   **Schema Optimization**: Clean up redundant JSON-schema properties to save LLM tokens.
