# User Identity & Permission System Design

## 🎯 Objective
1.  **Identity**: Replace static ENV auth with dynamic DB-based User binding (Telegram/Feishu).
2.  **RBAC**: Role-Based Access Control (Admin, User, Guest).
3.  **Tool Policy**: Granular control over which MCP tools/domains a user can access.
4.  **Management**: Friendly Dashboard UI for assigning roles and policies.

---

## 🏗️ Data Model Changes

### 1. Identity & Binding (Existing)
```python
class UserIdentity(Base):
    __tablename__ = "user_identities"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    provider = Column(String)  # telegram, feishu
    provider_user_id = Column(String)
    # ...
```

### 2. Roles & Permissions (New)
We will add a `role` column to `User` and a robust `Policy` system.

```python
class User(Base):
    # ... existing fields ...
    role = Column(String, default="user")  # "admin", "user", "guest"
    
    # JSON-based flexible policy for granular tool control
    # Example: {"allow_domains": ["clock", "weather"], "deny_tools": ["system_shell"]}
    policy = Column(JSON, default={}) 
```

---

## 🛡️ Access Control Logic

### Level 1: System Roles (Broad Access)
-   **Admin**: Full access to all Tools, Dashboard, and System Settings.
-   **User**: Access to Standard Tools. Restricted from "System Control" (e.g., shell, git).
-   **Guest**: Read-only or limited interaction (configurable).

### Level 2: Granular Tool Policy (The Check)
Before executing *any* tool, the `AgentWorker` checks permissions.

```python
def check_permission(user: User, tool_name: str, domain: str) -> bool:
    if user.role == "admin":
        return True
    
    # 1. Block Denied Tools
    if tool_name in user.policy.get("deny_tools", []):
        return False
        
    # 2. Check Allowed Domains
    allowed_domains = user.policy.get("allow_domains", ["standard"]) # standard = default safe tools
    if domain in allowed_domains:
        return True
        
    return False
```

---

## 🔄 The Binding Workflow (Unchanged)
1.  **Dashboard**: Generate Token.
2.  **Chat**: `/bind <token>`.
3.  **Result**: Chat ID linked to User.

---

## 💻 Dashboard Management UI
New Page: **`6_Users_&_Roles.py`**

### Section 1: User List
Table columns: `Avatar`, `Name`, `Role`, `Linked Accounts`, `Last Active`.
Actions: `Edit`, `Delete`, `Unlink Account`.

### Section 2: Permission Editor (Pop-up/Page)
When editing a User, the admin sees:

#### A. Role Selection
-   [ ] Admin
-   [x] Standard User
-   [ ] Guest

#### B. Tool Access (Checkbox Grid)
Grouped by **Domain** (derived from MCP config):

*   **🏠 Smart Home** (Home Assistant)
    *   [x] Control Lights (`call_service`)
    *   [x] View Status (`get_state`)
*   **📂 Office** (Feishu/Lark)
    *   [ ] Read Docs
    *   [ ] Edit Spreadsheets
*   **🖥️ System**
    *   [ ] Terminal (`run_command`) - *Dangerous!*
    *   [ ] Python Sandbox

*On Save: Updates `User.policy` JSON.*

---

## 📅 Implementation Steps

### Step 1: Database Migration
-   Add `role` and `policy` columns to `User` table.
-   Create `UserIdentity` table.

### Step 2: Auth Manager
-   Implement `AuthService.check_tool_access(user, tool_node)`.
-   Inject this check into `AgentNode` or `ToolNode`.

### Step 3: API & Bind Logic
-   Implement `/bind` token generation and verification.

### Step 4: Dashboard UI
-   Build the User Management Interface.
