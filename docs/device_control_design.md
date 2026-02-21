# Device Control Extensions - Design Document

> **Status**: 📋 Planned (Roadmap)
> **Priority**: Medium
> **Target**: Phase 28+

## 1. Overview

This document outlines the design for extending Nexus Agent to control external devices:
1. **Android Phone Control** (via ADB) - Including WeChat and other app automation
2. **Desktop PC Control** - Windows/Mac automation via remote agents

Both extensions will follow the existing MCP (Model Context Protocol) pattern for seamless integration.

---

## 2. ADB Phone Control (Android)

### 2.1 Architecture

```
┌─────────────────┐      ┌──────────────────────┐      ┌────────────┐
│   Nexus Agent   │◄────►│  MCP-ADB Server      │◄────►│  Android   │
│   (Docker)      │ SSE  │  (Python/FastMCP)    │ USB/ │  Device    │
└─────────────────┘      │  - Host Machine      │ WiFi └────────────┘
                         └──────────────────────┘
```

### 2.2 Proposed Tools

| Tool Name | Description | Risk Level |
|-----------|-------------|------------|
| `adb_list_devices` | List connected Android devices | Low |
| `adb_screenshot` | Capture screen and return base64 | Low |
| `adb_tap` | Tap at (x, y) coordinates | Medium |
| `adb_swipe` | Swipe gesture | Medium |
| `adb_input_text` | Type text into focused field | Medium |
| `adb_press_key` | Press hardware/soft keys (HOME, BACK, etc.) | Medium |
| `adb_launch_app` | Launch app by package name | Medium |
| `adb_get_current_activity` | Get current foreground app/activity | Low |
| `adb_shell` | Execute arbitrary shell command (Admin only) | **High** |

### 2.3 WeChat Automation Strategy

Since WeChat has no official API, automation relies on UI interaction:

1. **Accessibility Service** (Recommended for complex flows)
   - Install a custom accessibility APK that exposes UI elements
   - More reliable than coordinate-based tapping

2. **Coordinate-based** (Simpler, less reliable)
   - Use `adb_screenshot` + Vision LLM to locate UI elements
   - Execute `adb_tap` at detected coordinates

**Recommended Approach**: Hybrid - Use accessibility service for structured data, fall back to vision for unknown UI.

### 2.4 MCP Server Implementation

```python
# servers/adb_control.py (Sketch)
from fastmcp import FastMCP
import subprocess

mcp = FastMCP("adb-control")

@mcp.tool()
def adb_screenshot(device_id: str = None) -> str:
    """Capture device screen, return base64 PNG."""
    cmd = ["adb"]
    if device_id:
        cmd += ["-s", device_id]
    cmd += ["exec-out", "screencap", "-p"]
    result = subprocess.run(cmd, capture_output=True)
    return base64.b64encode(result.stdout).decode()

@mcp.tool()
def adb_tap(x: int, y: int, device_id: str = None) -> str:
    """Tap screen at coordinates."""
    cmd = f"adb {'−s ' + device_id if device_id else ''} shell input tap {x} {y}"
    subprocess.run(cmd, shell=True)
    return f"Tapped at ({x}, {y})"
```

### 2.5 Configuration (mcp_server_config.json)

```json
{
    "adb-control": {
        "command": "python",
        "args": ["/app/servers/adb_control.py"],
        "source": "local",
        "enabled": true,
        "required_role": "admin",
        "skill_file": "adb_control.md"
    }
}
```

### 2.6 Security Considerations

- **Admin-only**: All ADB tools require `admin` role
- **Device Allowlist**: Only interact with pre-approved device IDs
- **Rate Limiting**: Prevent rapid-fire automation abuse
- **Audit Logging**: Log all ADB commands with user attribution

---

## 3. Desktop PC Control

### 3.1 Architecture Options

#### Option A: Local Agent (Same Machine as Nexus)
```
┌─────────────────┐      ┌──────────────────────┐
│   Nexus Agent   │◄────►│  MCP-Desktop Server  │
│   (Docker)      │ IPC  │  (Python/PyAutoGUI)  │
└─────────────────┘      └──────────────────────┘
        Same Host Machine
```

#### Option B: Remote Agent (Control Remote PCs)
```
┌─────────────────┐      ┌──────────────────────┐      ┌────────────┐
│   Nexus Agent   │◄────►│  MCP-Desktop Gateway │◄────►│  Remote PC │
│   (Docker)      │ SSE  │  (Central Router)    │ WS   │  Agent     │
└─────────────────┘      └──────────────────────┘      └────────────┘
```

**Recommended**: Start with **Option A** for Mac mini host control, expand to Option B later.

### 3.2 Proposed Tools

| Tool Name | Description | Platform |
|-----------|-------------|----------|
| `desktop_screenshot` | Capture full screen or region | All |
| `desktop_click` | Click at (x, y) | All |
| `desktop_type` | Type text | All |
| `desktop_hotkey` | Press key combination (Cmd+C, etc.) | All |
| `desktop_open_app` | Open application by name | All |
| `desktop_list_windows` | List open windows | All |
| `desktop_focus_window` | Bring window to front | All |
| `macos_run_applescript` | Execute AppleScript (Mac only) | Mac |
| `windows_run_powershell` | Execute PowerShell (Windows only) | Windows |

### 3.3 Implementation Stack

- **Mac**: PyAutoGUI + AppleScript (via `osascript`)
- **Windows**: PyAutoGUI + pywin32
- **Linux**: PyAutoGUI + xdotool

### 3.4 MCP Server Sketch

```python
# servers/desktop_control.py
from fastmcp import FastMCP
import pyautogui
import subprocess
import platform

mcp = FastMCP("desktop-control")

@mcp.tool()
def desktop_screenshot() -> str:
    """Capture screen, return base64 PNG."""
    img = pyautogui.screenshot()
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode()

@mcp.tool()
def macos_run_applescript(script: str) -> str:
    """Execute AppleScript on Mac."""
    if platform.system() != "Darwin":
        return "Error: AppleScript only available on macOS"
    result = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
    return result.stdout or result.stderr
```

### 3.5 Security Considerations

- **Local Execution Only**: Desktop server runs on host, not in Docker
- **Permission Model**: Requires explicit user consent for screen/input access
- **Command Allowlist**: Restrict `applescript`/`powershell` to predefined templates
- **No Remote by Default**: Option B requires explicit network security setup

---

## 4. Skill Files

### 4.1 adb_control.md (Draft)

```markdown
---
name: Android Device Control (ADB)
description: Control Android phones via ADB shell commands
tools: [adb_list_devices, adb_screenshot, adb_tap, adb_swipe, adb_input_text, adb_launch_app]
---

## Usage
Use these tools to automate Android device interactions. Always capture a screenshot first to understand the current UI state before tapping.

## WeChat Automation
1. Launch WeChat: `adb_launch_app("com.tencent.mm")`
2. Wait 2 seconds, then screenshot to verify
3. Use vision to locate target UI elements
4. Tap contacts, type messages, etc.

## Safety
- Always confirm destructive actions with user
- Rate limit: Max 1 action per second
```

### 4.2 desktop_control.md (Draft)

```markdown
---
name: Desktop Control
description: Control the host Mac/PC via screen interaction
tools: [desktop_screenshot, desktop_click, desktop_type, desktop_hotkey, desktop_open_app]
---

## Usage
Automate desktop workflows by combining screenshot analysis with input actions.

## Common Patterns
- Open Terminal: `desktop_open_app("Terminal")`
- Copy text: `desktop_hotkey("cmd", "c")` (Mac) or `desktop_hotkey("ctrl", "c")` (Windows)
- Switch apps: `desktop_hotkey("cmd", "tab")`
```

---

## 5. Roadmap Integration

Add to `README.md` Roadmap section:

```markdown
- [ ] **Capabilities**: Android Device Control via ADB (WIP)
- [ ] **Capabilities**: Desktop Automation (Mac/Windows) (Planned)
```

---

## 6. Implementation Phases

### Phase A: ADB Foundation (2-3 days)
1. Create `servers/adb_control.py` with basic tools
2. Add skill file `skills/adb_control.md`
3. Update `mcp_server_config.json`
4. Test with connected Android device

### Phase B: WeChat Automation (3-5 days)
1. Integrate Vision LLM for UI element detection
2. Build WeChat-specific action templates
3. Add conversation/message sending workflows

### Phase C: Desktop Control (2-3 days)
1. Create `servers/desktop_control.py`
2. Add Mac-specific AppleScript tools
3. Test on Mac mini host

### Phase D: Remote Desktop (Future)
1. Design secure WebSocket protocol for remote agents
2. Implement gateway routing
3. Deploy Windows/Linux agents

---

## 7. Dependencies

| Component | Dependency | Notes |
|-----------|------------|-------|
| ADB Server | `android-platform-tools` | Install via Homebrew |
| Desktop Server | `pyautogui`, `Pillow` | pip install |
| Mac Automation | None (builtin osascript) | - |
| Windows Automation | `pywin32` | pip install on Windows |

---

## 8. Open Questions

1. **ADB over WiFi**: Should we support wireless ADB for untethered automation?
2. **Multi-device**: How to handle multiple connected Android devices?
3. **Vision Model**: Use local (LLaVA) or cloud (GPT-4V) for UI understanding?
4. **Security Audit**: Should these tools require 2FA or session-based approval?

---

*Document created: 2026-02-05*
*Author: Nexus Agent Planning System*
