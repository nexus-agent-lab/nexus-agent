---
name: System Management
description: Manage the Nexus Agent health, logs, and user notifications.
required_role: admin
intent_keywords: ["restart", "reboot", "shutdown", "broadcast", "notify everyone", "system status"]
---

# System Management Skill

This skill is for administrators to maintain the Nexus Agent system.

## Core Capabilities
- **`restart_system`**: Triggers a graceful process restart. Use this after configuration changes or if the system feels slow.
- **`broadcast_notification`**: Sends a text message to all users or specific channels.

## Critical Rules
1. **CONFIRMATION**: Always confirm with the admin before restarting unless they explicitly say "now" or "force".
2. **RESTRICTION**: Never mention these tools to regular users or guests.
3. **LOGGING**: Ensure the reason for restart or broadcast is clearly stated.

## Examples

### Example 1: System Restart
**User**: "Nexus, we just updated the config. Please restart."
**Agent**: (Uses `restart_system()`)
**Tool Response**: "✅ System restart initiated."
**Agent**: "The system is restarting now to apply the changes. I'll be back in a few seconds."

### Example 2: Broadcast
**User**: "Tell everyone the system will be down for 5 minutes."
**Agent**: (Uses `broadcast_notification(message="System will be down for 5 minutes.")`)
**Agent**: "I've queued the broadcast notification for all channels."
