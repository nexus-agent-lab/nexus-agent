# Nexus Official Home Assistant MCP Fork Plan

> **Objective**: Transition from third-party community MCP to a self-sovereign, audited, and optimized Home Assistant integration layer.

## 1. Source Identification
- **Target Repository**: `modelcontextprotocol/servers` (Home Assistant submodule).
- **Fork Target**: `nexus-mcp/mcp-homeassistant`.

## 2. Phase 1: Security Audit & Hardening
- [ ] **Credential Scoping**: Ensure the MCP only uses the token provided in environment variables and does not leak it in logs.
- [ ] **Method Whitelisting**: Audit the `call_service` implementation. Identify high-risk services (e.g., `hass.stop`, `configurator.display`) and implement a kernel-level toggle to block them unless specifically allowed.
- [ ] **Input Sanitization**: Validate all JSON payloads before passing them to the HA Python API to prevent injection.

## 3. Phase 2: Performance & Caching
- [ ] **Fine-grained TTL**: Implement per-tool caching in the MCP layer. 
    - `get_entity_state`: 5-10s cache (high frequency sensors).
    - `query_entities`: 30min cache (static device list).
- [ ] **Batch Queries**: Add a tool for `get_entities_by_area` to reduce the number of roundtrips the Agent makes when analyzing a whole room.

## 4. Phase 3: AI UX Enhancements
- [ ] **Human-Readable Errors**: Map obscure HA error codes (e.g., "Service not found") to actionable LLM advice ("The light is currently unavailable/offline, check if the physical switch is on").
- [ ] **Metadata Tagging**: Explicitly tag tools with `domain: smart_home` and `category: actuator/sensor` to support Nexus RBAC.
- [ ] **Unit Overrides**: Automatically convert complex HA units (e.g., lux, hPa) into common terms if the Agent is struggling.

## 5. Timeline & Maintenance
- **Week 1**: Forking & Dockerization within Nexus CI/CD.
- **Week 2**: Security Audit & Metadata implementation.
- **Ongoing**: Weekly sync with upstream `modelcontextprotocol/servers` for security patches.
