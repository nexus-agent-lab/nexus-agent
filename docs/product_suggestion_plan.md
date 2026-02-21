# Product Suggestion System Implementation Plan

## Goal
Establish a structured way to collect, manage, and eventually act upon user product suggestions. This system will serve as the "backlog" for the Agent's future self-improvement capabilities.

## User Review Required
> [!IMPORTANT]
> The "Self-Execution" part (Phase 2) where the agent modifies its own code based on suggestions is a high-risk feature. For Phase 1, we will focus strictly on **Collection** and **Dashboard Management**. The agent will NOT automatically implement changes yet.

## Proposed Changes

### 1. Database Schema
#### [NEW] `app/models/product.py`
Create a `ProductSuggestion` model:
- `id`: int (PK)
- `user_id`: str (FK to User, optional)
- `content`: str (The suggestion text)
- `category`: str (feature, bug, improvement)
- `status`: str (pending, approved, rejected, implemented) - Default: "pending"
- `priority`: str (low, medium, high) - Default: "medium"
- `created_at`: datetime
- `updated_at`: datetime

Add to `app/core/db.py` imports.

### 2. Tools
#### [NEW] `app/tools/suggestion_tools.py`
- `submit_suggestion(content: str, category: str = "feature")`: Saves a new suggestion.
- `list_suggestions(status: str = "pending")`: (Admin only) Lists suggestions.
- `update_suggestion_status(suggestion_id: int, status: str)`: (Admin only) Approves/Rejects items.

### 3. Dashboard Integration
#### [NEW] `dashboard/pages/6_Roadmap.py`
- A new Streamlit page to visualize the "Product Backlog".
- **Kanban Board** or **List View**:
  - Columns: Pending, Approved, Implemented.
  - Actions: Approve, Reject, Delete.

## Verification Plan

### Automated Tests
- Create `tests/test_suggestion.py`:
  - Test submission saves to DB.
  - Test status updates.
  - Test RBAC (only admins can update status).

### Manual Verification
1. User says: "I have a suggestion: Add a weather tool."
2. Agent calls `submit_suggestion`.
3. Admin views the suggestion in the new "Roadmap" dashboard page.
