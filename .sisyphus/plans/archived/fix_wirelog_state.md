# Work Plan: Fix WireLogToggle State Persistence

## Objective
Fix the issue where the `WireLogToggle` component on the Frontend resets to `false` when navigating away from and back to the `/audit` page. The solution involves creating a GET endpoint to fetch the current runtime configuration from the backend and syncing the frontend component's state on mount.

## Scope
- **IN**: Adding a `GET /admin/config` endpoint in `app/api/admin.py`.
- **IN**: Updating `web/src/components/WireLogToggle.tsx` to fetch the current state on mount via `useEffect`.
- **OUT**: Changes to the core logging logic or other frontend pages.

## Context & Architecture
Currently, `app/api/admin.py` only has a `POST /admin/config` endpoint. The frontend uses a local `useState(false)` which is lost on component unmount. We must synchronize the UI with the backend's true `os.environ["DEBUG_WIRE_LOG"]` state.

## Implementation Steps

### Task 1: Add Backend GET Endpoint
**File**: `app/api/admin.py`
**Actions**:
1. Add a new `GET` route `@router.get("/config", dependencies=[Depends(require_admin)])`.
2. Inside the route, return a JSON object containing the current state of `DEBUG_WIRE_LOG` and `LOG_LEVEL`.
3. Use `os.environ.get("DEBUG_WIRE_LOG", "false").lower() == "true"` to return a boolean value.

```python
# Expected implementation reference:
@router.get("/config", dependencies=[Depends(require_admin)])
async def get_config():
    """Get current runtime configuration."""
    return {
        "DEBUG_WIRE_LOG": os.environ.get("DEBUG_WIRE_LOG", "false").lower() == "true",
        "LOG_LEVEL": os.environ.get("LOG_LEVEL", "INFO")
    }
```

### Task 2: Update Frontend Component
**File**: `web/src/components/WireLogToggle.tsx`
**Actions**:
1. Add a `useEffect` hook that triggers on mount.
2. Inside the effect, fetch from `GET /admin/config` using the provided `apiKey`.
3. Parse the JSON response and set the `isEnabled` state based on the `DEBUG_WIRE_LOG` boolean.
4. Add a minor loading state or gracefully handle fetch errors so the toggle doesn't flicker aggressively.

```typescript
// Expected implementation reference:
  useEffect(() => {
    const fetchConfig = async () => {
      try {
        const backendUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
        const response = await fetch(`${backendUrl}/admin/config`, {
          headers: { "X-API-Key": apiKey },
        });
        if (response.ok) {
          const data = await response.json();
          setIsEnabled(data.DEBUG_WIRE_LOG);
        }
      } catch (e) {
        console.error("Failed to fetch initial config", e);
      }
    };
    fetchConfig();
  }, [apiKey]);
```

### Task 3: Quality Assurance
**Actions**:
1. Run `bash scripts/dev_check.sh` to ensure Python syntax, Ruff formatting, and Frontend builds are successful.

## Final Verification Wave
- [x] Manual QA: Navigate to `/audit`, toggle the switch, navigate to `/dashboard`, navigate back to `/audit` -> verify the switch retains its correct state.
- [x] Confirm `dev_check.sh` passes 100%.

- [ ] Confirm `dev_check.sh` passes 100%.