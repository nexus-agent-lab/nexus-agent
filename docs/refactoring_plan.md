# Nexus Agent Refactoring Plan

## Executive Summary

After a comprehensive review, I have identified **5 major areas** requiring refactoring to improve code quality, maintainability, and developer experience.

---

## 1. MCP Module Duplication

> [!WARNING]
> Two files serve overlapping MCP purposes, causing confusion.

| File | Purpose | Method |
|------|---------|--------|
| [mcp.py](file:///Users/michael/work/nexus-agent/app/core/mcp.py) | Runtime MCP client (connects to servers, fetches tools, executes calls) | MCP SDK (`ClientSession`) |
| [mcp_manager.py](file:///Users/michael/work/nexus-agent/app/core/mcp_manager.py) | Process lifecycle management (starts/stops subprocesses) | `subprocess.Popen` |

### Recommendation
- **Keep both**, but rename for clarity:
  - `mcp.py` → `mcp_client.py` (SDK connection logic)
  - `mcp_manager.py` → `mcp_process.py` (subprocess management)
- Add `__init__.py` exports to simplify imports.

---

## 2. Scripts Directory Chaos (21 Files)

The `scripts/` folder contains a mix of:
- **One-off debugging scripts** (e.g., `debug_network.py`, `internal_ha_test.py`)
- **Verification tests** (e.g., `verify_mcp.py`, `verify_memory.py`)
- **Operational tools** (e.g., `create_admin.py`, `deploy_local.sh`)
- **Test utilities** (e.g., `test_chat.py`, `smoke_test.py`)

### Proposed Structure
```
scripts/
├── admin/                    # Operational scripts
│   ├── create_admin.py
│   ├── seed_db.py           ← Move from root
│   └── deploy_local.sh
├── dev/                      # Development helpers
│   ├── start_local_server.py
│   ├── start_embedding_server.py
│   ├── start_local_llm.sh
│   └── test_chat.py
└── debug/                    # One-off debugging (can delete after use)
    ├── debug_network.py
    ├── internal_ha_test.py
    └── ...
```

### Old Files to DELETE (Merged into Tests)
- `verify_*.py` → Move logic into `tests/` as proper pytest cases
- `smoke_test.py` → Already superseded by `tests/test_imports.py`

---

## 3. Test Suite Expansion

Currently: **1 test file** (`test_imports.py`)

### Recommended Test Structure
```
tests/
├── conftest.py               # Shared fixtures (mock DB, mock LLM)
├── test_imports.py           # [EXISTS] Syntax/import validation
├── test_api.py               # [NEW] FastAPI endpoint tests
├── test_agent.py             # [NEW] Agent graph execution
├── test_memory.py            # [NEW] Memory storage/retrieval
├── test_policy.py            # [NEW] Permission policy matrix
└── test_mcp.py               # [NEW] MCP tool loading (mocked)
```

### Key Fixtures Needed
```python
# conftest.py
@pytest.fixture
def mock_db():
    """In-memory SQLite for fast tests."""
    ...

@pytest.fixture
def mock_llm():
    """LLM that returns predictable responses."""
    ...
```

---

## 4. Root Directory Clutter

| File | Issue | Action |
|------|-------|--------|
| `seed_db.py` | Should be with admin scripts | Move to `scripts/admin/` |
| `ARCHITECTURE.md` + `ARCHITECTURE_zh.md` | Duplication | Keep in `docs/` folder |

---

## 5. Ruff Code Quality Issues (133 Errors)

Most violations are auto-fixable:
- **95 fixable** with `ruff check --fix`
- **38 manual** (unused imports, bare `except`, etc.)

### Quick Wins
```bash
# Auto-fix safe issues
ruff check app/ scripts/ --fix --select E,F,I --ignore E501

# Remaining manual fixes
ruff check app/ scripts/ --select E,F --ignore E501
```

### Key Manual Fixes Needed
1. `scripts/test_chat.py`: Bare `except:` → use `except Exception:`
2. Multiple files: Unused imports (e.g., `Dict`, `Any`, `asyncio`)
3. Import order violations (auto-fixable but may break logic)

---

## Implementation Priority

| Priority | Task | Effort |
|----------|------|--------|
| 🔴 High | Run `ruff --fix` to clear 95 errors | 5 min |
| 🔴 High | Rename MCP files for clarity | 15 min |
| 🟡 Medium | Reorganize `scripts/` folder | 30 min |
| 🟡 Medium | Add `tests/conftest.py` + 2-3 test files | 1 hr |
| 🟢 Low | Move docs to `docs/` folder | 10 min |
| 🟢 Low | Delete obsolete `verify_*.py` scripts | 10 min |

---

## User Decision Required

> [!IMPORTANT]
> I can proceed with these changes incrementally. Please confirm:
> 1. **Run `ruff --fix`** to auto-clean code style? (Recommended first)
> 2. **Reorganize scripts/** into the proposed structure?
> 3. **Prioritize which test files** to create first?
