# Home Assistant P0-1 Validation Checklist

> Purpose: track real-world Home Assistant reliability validation on top of the current LangGraph baseline.
>
> Workflow:
> 1. Test a scenario manually or through a script.
> 2. Mark its status.
> 3. If a problem appears, add it to the issue log.
> 4. If the problem is later fixed, keep the issue entry and mark it as resolved instead of deleting history.

## Status Legend

- `[ ]` not tested yet
- `[/]` in progress / reproduced but not fully resolved
- `[x]` validated or fixed and re-validated

---

## 1. Core User Flows

### 1.1 Discovery Flow
- [ ] User asks to find a device by fuzzy natural language name
- [ ] Agent performs discovery before acting when entity ID is unknown
- [ ] Discovery result is understandable to a normal user
- [ ] Discovery does not loop repeatedly when the first lookup fails
- [ ] Multiple similar entities are handled with clarification instead of arbitrary selection

**Suggested prompts**
- “帮我找一下客厅的灯”
- “列出卧室里能控制的设备”
- “有没有和显示器相关的灯？”

**Expected outcome**
- Agent uses discovery first, identifies likely targets, and either continues correctly or asks a focused clarification question.

### 1.2 Single-Device Control Flow
- [ ] Explicit control request does not stop after discovery-only stage
- [ ] Agent discovers the target and then performs the requested action
- [ ] Control success is communicated clearly
- [ ] Control action is followed by verification when appropriate
- [ ] Wrong-device execution does not occur when multiple close matches exist

**Suggested prompts**
- “关闭显示器灯”
- “打开客厅主灯”
- “把书房风扇关掉”

**Expected outcome**
- Agent discovers the entity if needed, executes the action, and reports the result with enough confidence or verification guidance.

### 1.3 State-Query Flow
- [ ] Agent can answer a device status query when entity ID is unknown
- [ ] Agent performs discovery then state read in the correct order
- [ ] Response clearly distinguishes current state from guessed intent
- [ ] Multiple candidate devices trigger clarification instead of a misleading answer

**Suggested prompts**
- “客厅灯现在开着吗？”
- “洗衣机现在什么状态？”
- “书房空调是不是开着？”

**Expected outcome**
- Agent identifies the target device and returns a concrete state answer grounded in Home Assistant data.

---

## 2. Failure and Safety Flows

### 2.1 Permission-Denied Flow
- [ ] Non-admin user is denied for restricted Home Assistant actions
- [ ] `homeassistant.restart` is blocked for non-admin users
- [ ] Permission-denied message is understandable and recoverable
- [ ] Message helps the user know what to do next

**Suggested prompts**
- “重启 Home Assistant” (non-admin)
- “帮我重启系统” (non-admin, if mapped to HA restart path)

**Expected outcome**
- Action is blocked safely, and the reply explains that the action is restricted rather than failing vaguely.

### 2.2 Entity-Not-Found Flow
- [ ] Missing entity does not cause repeated discovery retries
- [ ] User gets a focused clarification request or an understandable failure message
- [ ] Similar-name hints are provided when possible

**Suggested prompts**
- “关闭二楼影院灯” (when that entity does not exist)
- “查看火星房间温度”

**Expected outcome**
- Agent exits the failed path cleanly and asks for clarification or reports the missing entity.

### 2.3 Abnormal / Unavailable State Flow
- [ ] Unavailable device state is surfaced clearly
- [ ] Unsafe or blocked action state does not look like a successful execution
- [ ] User is told whether the issue is retryable, unavailable, or needs manual intervention

**Suggested prompts**
- “打开离线的空气净化器”
- “查看当前不可用设备的状态”

**Expected outcome**
- Agent reports the abnormal state accurately and does not falsely claim completion.

### 2.4 Ambient Room Temperature Filtering
- [ ] Ambient room temperature queries exclude appliance/process sensors
- [ ] Fridge / freezer / water heater style sensors do not dominate room-temperature answers
- [ ] Filtering still preserves correct room sensors

**Suggested prompts**
- “家里冷不冷？”
- “哪个房间最热？”
- “哪个房间最冷？”

**Expected outcome**
- Appliance/process sensors are filtered out before the model reasons over the entity list.

---

## 3. Failure Checklist for Daily-Use Scenarios

Use this section as the persistent backlog of real Home Assistant reliability issues.

| ID | Scenario | Symptom | Impact | Status | Notes |
|---|---|---|---|---|---|
| HA-P0-001 | Discovery flow | Not tested yet | High | [ ] | |
| HA-P0-002 | Single-device control | Not tested yet | High | [ ] | |
| HA-P0-003 | State query | Not tested yet | High | [ ] | |
| HA-P0-004 | Permission denied | Guardrail exists; wording still to validate | High | [ ] | `homeassistant.restart -> admin` currently runtime-enforced |
| HA-P0-005 | Entity not found | Generic worker behavior exists; HA real-run validation pending | High | [ ] | |
| HA-P0-006 | Abnormal / unavailable state | Generic classifier behavior exists; HA real-run validation pending | High | [ ] | |
| HA-P0-007 | Ambient temperature filter | Runtime filter exists; full scenario checklist pending | Medium | [ ] | |

---

## 4. Issue Log

Add concrete issues here when you hit them during testing.

| Date | Issue ID | Scenario | Reproduction Prompt | Observed Behavior | Expected Behavior | Status | Fix Notes |
|---|---|---|---|---|---|---|---|
| 2026-03-16 | Example | Example only | “关闭客厅灯” | Example only | Example only | [ ] | Replace this row with real issues |

### Issue Status Rules
- `[ ]` reproduced, not fixed yet
- `[/]` partially fixed or awaiting re-test
- `[x]` fixed and re-validated

Do not delete old issue rows. Keep them as the running reliability history.

---

## 5. Current Code Anchors

These are the most relevant implementation points behind the checklist.

- `app/core/worker_graphs/skill_worker.py`
  - explicit Home Assistant action should continue past discovery
  - ambient temperature filtering
  - discovery failure converted to clarification instead of loops
- `app/core/worker_graphs/shared_execution.py`
  - `homeassistant.restart` requires `admin`
- `app/core/result_classifier.py`
  - permission denied / not found / unsafe state classification
- `tests/unit/test_worker_dispatcher.py`
  - current unit coverage for key guardrails
- `tests/integration/verify_ha_autonomy.py`
  - starting point for future multi-scenario runtime validation

---

## 6. Exit Criteria for P0-1

P0-1 can be considered complete when:

- all core user flows have at least one successful validation run
- all failure/safety flows have at least one validated run
- known issues are either fixed or explicitly accepted with rationale
- the failure checklist reflects real observed behavior, not only planned scenarios
- the team is confident enough to move attention to `P0-2` binding / login / permission UX
