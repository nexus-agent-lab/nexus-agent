# Self-Learning & Auto-Correction Mechanism Design

## Objective
Enable Nexus Agent to autonomously learn from tool execution failures and persist this knowledge, with a strict **Audit Log** and **Human-in-the-Loop** control via Dashboard.

## Core Components

### 1. Database Model: `SkillChangelog`
Persist every learning event.
```python
class SkillChangelog(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    skill_name: str
    rule_content: str  # The rule text being added
    reason: str        # Error message or context triggering the learn
    status: str        # "pending", "approved", "rejected", "auto_applied"
    mode: str          # "auto" or "manual" (snapshot of config at time)
    created_at: datetime
    reviewed_at: Optional[datetime]
```

### 2. Configuration (`CoreConfig`)
Global setting to control behavior:
- `SKILL_LEARNING_MODE`: `auto` (Apply immediately) | `manual` (Wait for approval)

### 3. The Learning Tool: `learn_skill_rule`
- **Input**: `skill_name`, `rule_content`, `reason`
- **Logic**:
  1.  Create `SkillChangelog` entry.
  2.  If `mode == "auto"`:
      - Append rule to `skills/{skill}.md`.
      - Update Log status to `auto_applied`.
  3.  If `mode == "manual"`:
      - Log status is `pending`.
      - (Rule is NOT written to file yet).

### 4. Dashboard (Frontend)
New section in **Integrations** page: "Skill Learning Audit".
- **Toggle**: Switch between Auto/Manual mode.
- **Log Table**:
  - Show Timestamp, Skill, Rule, Reason, Status.
  - **Actions** (for Pending items): "✅ Approve", "❌ Reject".
- **History**: View past auto-applied rules.

## Workflow

### Scenario A: Auto-Fix Mode
1.  Agent fails calling `get_entity`.
2.  Agent calls `learn_skill_rule(..., reason="Invalid arg 'detailed'")`.
3.  System writes rule to `homeassistant.md`.
4.  Log created with status `auto_applied`.
5.  User can see this in Dashboard later and revert if needed.

### Scenario B: Audit Mode (Manual)
1.  Agent fails.
2.  Agent calls `learn_skill_rule`.
3.  Log created with status `pending`.
4.  **No file change**.
5.  User sees "1 Pending Rule" in Dashboard.
6.  User clicks "Approve".
7.  System writes rule to `homeassistant.md` and updates log to `approved`.

## API Endpoints
- `GET /api/skills/changelog`: List logs.
- `POST /api/skills/changelog/{id}/approve`: Apply a pending rule.
- `POST /api/skills/changelog/{id}/reject`: discard.
- `GET /api/config/learning-mode`: Get current mode.
- `POST /api/config/learning-mode`: Set mode.

## Integration Steps
1.  **Models**: Create `app/models/skill_log.py`.
2.  **API**: Create `app/api/skill_learning.py`.
3.  **Agent Tool**: Implement `learn_skill_rule` tool in `app/tools/learning_tools.py`.
4.  **Frontend**: Update `dashboard/pages/5_Integrations.py`.
