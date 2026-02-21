# Implementation Plan - Admin Management & Role-Based Skills

Enhance the system's administrative capabilities by restricting powerful tools to admins and enabling proactive system notifications.

## Proposed Changes

### 1. Role-Based Skill Filtering
**File**: `app/core/skill_loader.py` & `app/core/agent.py`
- **Metadata**: Support `required_role: "admin"` in skill card frontmatter.
- **Filtering**: Update `SkillLoader` or the Agent injection logic to only load skills matching the current user's role (e.g., non-admins don't see management skills).

### 2. System Management Tools [NEW]
**File**: [NEW] `app/tools/admin_tools.py`
- **Tool**: `restart_system()` (Admin only).
- **Tool**: `broadcast_notification(message: str)` (Admin only) - Send a message to all users or specific channels.

### 3. Admin Notification System
**File**: `app/core/mq.py` or a new service.
- **Goal**: Automatically push critical errors or system status updates to users with the `admin` role via their linked channel.

## Verification Plan

### Automated Tests
- Test skill filtering: Verify a 'guest' user doesn't have 'admin' skills in their prompt.
- Test `restart_system`: Verify the tool is identified as admin-only.

### Manual Verification
- Message the bot as an admin: "What management tools do I have?"
- Message the bot as a regular user: Verify it doesn't know about "restart".
