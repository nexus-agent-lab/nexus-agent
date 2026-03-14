import asyncio
import logging
import os
import time
import uuid
from typing import Literal

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langgraph.graph import StateGraph

from app.core.config import settings
from app.core.llm_utils import get_llm_client
from app.core.session import SessionManager
from app.core.state import AgentState
from app.core.tool_catalog import ToolCatalog
from app.core.trace_logger import trace_logger
from app.core.worker_dispatcher import WorkerDispatcher

logger = logging.getLogger(__name__)

BASE_SYSTEM_PROMPT = r"""You are Nexus, an AI Operating System connecting physical and digital worlds.

### PROTOCOLS
1. **DISCOVERY FIRST**: Never guess IDs. Use discovery/search tools to locate resources before acting.
2. **SKILL RULES**: Follow rules in LOADED SKILLS section. If a tool is missing, say so.
3. **LARGE DATA**: Use \`python_sandbox\` to filter/summarize large outputs (>100 items) or do calculations.
4. **CRITICAL RULE**: DO NOT INVENT TOOL NAMES or ARGUMENTS. If you lack information or tools, STOP and ASK the user.
5. **LANGUAGE**: Match the user's language. Be concise.
6. **MISSING CAPABILITIES**: If the user requests a capability you lack, assume it's a feature request and call \`submit_suggestion\` with type='feature_request'.
7. **DOMAIN VERIFICATION**: Before executing a tool, verify the tool's PURPOSE matches the user's INTENT. If the user asks about "system logs" but only "Home Assistant logs" tools are available, DO NOT substitute one for the other. Instead, inform the user: "I don't have system log access yet. I do have Home Assistant logs - would you like those instead?"
8. **KEYWORD ≠ INTENT**: The word "logs" can mean system logs, application logs, HA device logs, or audit logs. Always consider the CONTEXT of the request, not just the keyword match.

### SECURITY & ALIGNMENT
- STRICT COMPLIANCE: You must strictly adhere to your defined Role-Based Access Control (RBAC) and tool limits.
- NO BYPASSING: Any attempt to bypass constraints, hallucinate unauthorized tool calls, or fabricate parameters is a severe security violation.
"""


def _should_retry_tool_error(content: str) -> bool:
    """Only retry errors that the model can realistically recover from."""
    if not content:
        return False

    lowered = content.lower()
    non_retryable_markers = (
        "permission denied",
        "internal system error",
        "tool '",
        "tool not found",
        "restricted for user",
    )
    if any(marker in lowered for marker in non_retryable_markers):
        return False

    return "error" in lowered


def _should_retry_classification(state: AgentState) -> bool:
    """Prefer normalized result classification over raw tool text when available."""
    classification = state.get("last_classification") or {}
    selected_worker = state.get("selected_worker")
    attempts_by_worker = state.get("attempts_by_worker") or {}
    if selected_worker == "code_worker" and attempts_by_worker.get("code_worker", 0) >= 3:
        return False

    if classification:
        if classification.get("requires_handoff"):
            return False
        if classification.get("retryable"):
            return True

        next_action = classification.get("suggested_next_action")
        return next_action in {"retry_same_worker", "run_discovery", "switch_worker"}

    return False


def _prefers_chinese(messages) -> bool:
    for msg in reversed(messages or []):
        if isinstance(msg, HumanMessage):
            content = str(msg.content or "")
            return any("\u4e00" <= ch <= "\u9fff" for ch in content)
    return False


def _build_report_message(state: AgentState) -> str:
    classification = state.get("last_classification") or {}
    outcome = state.get("last_outcome") or {}
    summary = classification.get("user_facing_summary") or "Execution failed and needs intervention."
    detail = (
        classification.get("debug_summary") or outcome.get("raw_text") or "No additional error details were captured."
    )

    if len(detail) > 300:
        detail = detail[:300] + "..."

    if _prefers_chinese(state.get("messages", [])):
        return f"本次执行未能完成。\n原因：{summary}\n细节：{detail}\n下一步：请检查输入、权限或外部系统状态后再继续。"

    return (
        f"The execution could not be completed.\n"
        f"Reason: {summary}\n"
        f"Details: {detail}\n"
        f"Next step: check the inputs, permissions, or external system state before trying again."
    )


def _build_verify_context(state: AgentState) -> dict[str, str]:
    classification = state.get("last_classification") or {}
    outcome = state.get("last_outcome") or {}
    execution_mode = state.get("execution_mode") or ""
    selected_worker = state.get("selected_worker") or ""
    selected_skill = state.get("selected_skill") or ""
    previous_hint = state.get("next_execution_hint") or ""
    detail = classification.get("debug_summary") or outcome.get("raw_text") or ""

    if detail and len(detail) > 240:
        detail = detail[:240] + "..."

    return {
        "worker": selected_worker,
        "skill": selected_skill,
        "execution_mode": execution_mode,
        "category": classification.get("category") or "",
        "reason": classification.get("user_facing_summary") or "",
        "detail": detail,
        "previous_hint": previous_hint,
    }


async def _persist_message(session_id: int, message):
    """Persist a single message without adding graph steps."""
    if not session_id or message is None:
        return

    role, msg_type = "user", "human"
    if isinstance(message, AIMessage):
        role, msg_type = "assistant", "ai"
    elif isinstance(message, ToolMessage):
        role, msg_type = "tool", "tool"

    content = message.content
    is_pruned = False
    original_content = None

    if isinstance(message, ToolMessage):
        content, is_pruned, original_content = await SessionManager.prune_tool_output(
            str(message.content), getattr(message, "name", "unknown")
        )

    await SessionManager.save_message(
        session_id=session_id,
        role=role,
        type=msg_type,
        content=str(content),
        tool_call_id=getattr(message, "tool_call_id", None),
        tool_name=getattr(message, "name", None),
        is_pruned=is_pruned,
        original_content=original_content if is_pruned else None,
    )
    asyncio.create_task(SessionManager.maybe_compact(session_id))


async def retrieve_memories(state: AgentState):
    user = state.get("user")
    if not user:
        return {"memories": []}

    # We query for the last user message to find relevant memories
    last_user_msg = ""
    for msg in reversed(state["messages"]):
        if msg.type == "human":
            last_user_msg = msg.content
            break

    if not last_user_msg:
        return {"memories": []}

    # Importing here to avoid potential circular deps
    from app.core.memory import memory_manager

    # Optimization: Skip memory retrieval for short messages (e.g. "hi", "ok", "stop")
    # or simple confirmations to save Embedding calls (which block for 200ms+)
    SKIP_PATTERNS = ["hi", "hello", "ok", "thanks", "thank you", "stop", "exit", "quit", "menu", "help"]
    if len(last_user_msg) < 10 or last_user_msg.strip().lower() in SKIP_PATTERNS:
        return {"memories": []}

    import time

    t0 = time.perf_counter()
    memories = await memory_manager.search_memory(user_id=user.id, query=last_user_msg)
    memory_strings = [f"[{m.memory_type}] {m.content}" for m in memories]

    logger.info(
        f"Retrieved {len(memory_strings)} memories for query '{last_user_msg}' in {(time.perf_counter() - t0) * 1000:.0f}ms"
    )

    return {"memories": memory_strings}


async def save_interaction_node(state: AgentState):
    """
    Saves the LAST message in the state to the history.
    This should be called after every major step (user input, AI response).
    """
    session_id = state.get("session_id")
    if not session_id:
        return {}

    messages = state["messages"]
    if not messages:
        return {}

    last_msg = messages[-1]

    # Determine role and type
    role, msg_type = "user", "human"
    if isinstance(last_msg, AIMessage):
        role, msg_type = "assistant", "ai"
    elif isinstance(last_msg, ToolMessage):
        role, msg_type = "tool", "tool"

    # Pruning check for ToolMessages
    content = last_msg.content
    is_pruned = False
    original_content = None

    if isinstance(last_msg, ToolMessage):
        content, is_pruned, original_content = await SessionManager.prune_tool_output(
            str(last_msg.content), getattr(last_msg, "name", "unknown")
        )

    await SessionManager.save_message(
        session_id=session_id,
        role=role,
        type=msg_type,
        content=str(content),
        tool_call_id=getattr(last_msg, "tool_call_id", None),
        tool_name=getattr(last_msg, "name", None),
        is_pruned=is_pruned,
        original_content=original_content if is_pruned else None,
    )

    # AUTO-COMPACTING: Trigger background compaction
    # Use create_task so we don't block the agent's response loop
    asyncio.create_task(SessionManager.maybe_compact(session_id))

    return {}


async def reflexion_node(state: AgentState):
    messages = state["messages"]
    last_message = messages[-1]

    failures = []
    classification = state.get("last_classification") or {}
    if classification:
        failures.append(
            classification.get("debug_summary") or classification.get("user_facing_summary") or "Unknown failure"
        )

    if isinstance(last_message, ToolMessage):
        if _should_retry_tool_error(last_message.content):
            failures.append(last_message.content)

    retry_count = state.get("retry_count", 0) + 1

    critique = (
        f"REFLECTION (Attempt {retry_count}/3): The previous tool execution failed with: {failures}. "
        f"Please analyze why this happened (e.g., wrong arguments, missing permissions) "
        f"and try a different approach or correct the arguments. "
        f"Do not repeat the exact same invalid call."
    )
    trace_logger.log_wire_event(
        "reflexion",
        trace_id=str(state.get("trace_id", "")),
        summary="Entering reflexion step.",
        details={
            "retry_count": retry_count,
            "last_classification": classification.get("category"),
            "failures": failures,
        },
    )

    reflexion_msg = SystemMessage(content=critique)

    return {"messages": [reflexion_msg], "retry_count": retry_count, "reflexions": [critique]}


def should_reflect(state: AgentState) -> Literal["reflexion", "agent", "report", "__end__"]:
    messages = state["messages"]
    last_message = messages[-1]
    selected_worker = state.get("selected_worker")
    attempts_by_worker = state.get("attempts_by_worker") or {}
    next_execution_hint = state.get("next_execution_hint")

    if selected_worker == "code_worker" and next_execution_hint == "report":
        return "report"

    if selected_worker == "code_worker" and next_execution_hint in {"verify", "ask_user", "complete"}:
        return "agent"

    if selected_worker == "code_worker" and attempts_by_worker.get("code_worker", 0) >= 3:
        return "agent"

    if _should_retry_classification(state):
        if state.get("retry_count", 0) < 3:
            return "reflexion"
        return "agent"

    # Check if the last tool output was an error
    if isinstance(last_message, ToolMessage):
        content = last_message.content
        if _should_retry_tool_error(content):
            # Check retry limit
            if state.get("retry_count", 0) < 3:
                return "reflexion"
            else:
                return "agent"

    return "agent"


def should_continue(state: AgentState) -> Literal["tools", "agent", "verify", "report", "__end__"]:
    messages = state["messages"]
    last_message = messages[-1]
    if last_message.tool_calls:
        return "tools"
    if state.get("selected_worker") == "code_worker" and state.get("next_execution_hint") == "report":
        return "report"
    if state.get("verification_status") == "failed" and state.get("llm_call_count", 0) < 2:
        return "agent"
    if state.get("verification_status") == "required" and state.get("llm_call_count", 0) < 3:
        return "verify"
    return "__end__"


async def report_failure_node(state: AgentState):
    trace_logger.log_wire_event(
        "report_failure",
        trace_id=str(state.get("trace_id", "")),
        summary="Rendering deterministic failure report.",
        details={
            "selected_worker": state.get("selected_worker"),
            "next_execution_hint": state.get("next_execution_hint"),
            "classification": (state.get("last_classification") or {}).get("category"),
        },
    )
    return {
        "messages": [AIMessage(content=_build_report_message(state))],
        "verification_status": "failed",
        "next_execution_hint": "report",
    }


async def reviewer_gate_node(state: AgentState):
    classification = state.get("last_classification") or {}
    trace_logger.log_wire_event(
        "reviewer_gate",
        trace_id=str(state.get("trace_id", "")),
        summary="Evaluating reviewer gate transition.",
        details={
            "selected_worker": state.get("selected_worker"),
            "verification_status": state.get("verification_status"),
            "next_execution_hint": state.get("next_execution_hint"),
            "classification": classification.get("category"),
            "next_action": classification.get("suggested_next_action"),
        },
    )
    return {}


async def verify_followup_node(state: AgentState):
    verify_context = _build_verify_context(state)
    trace_logger.log_wire_event(
        "verify_followup",
        trace_id=str(state.get("trace_id", "")),
        summary="Preparing explicit verify follow-up path.",
        details={
            "selected_worker": state.get("selected_worker"),
            "verification_status": state.get("verification_status"),
            "previous_hint": state.get("next_execution_hint"),
            "verify_reason": verify_context.get("reason"),
            "verify_category": verify_context.get("category"),
        },
    )
    return {
        "next_execution_hint": "verify",
        "verification_status": "required",
        "verify_context": verify_context,
    }


def route_after_review(state: AgentState) -> Literal["reflexion", "agent", "verify", "report", "__end__"]:
    verification_status = state.get("verification_status")
    next_execution_hint = state.get("next_execution_hint")
    selected_worker = state.get("selected_worker")

    if next_execution_hint == "report":
        return "report"
    if verification_status == "failed" and selected_worker == "code_worker":
        return "report"
    if verification_status == "required":
        return "verify"
    if verification_status == "failed":
        return "agent"
    return should_reflect(state)


async def experience_replay_node(state: AgentState):
    """
    JIT Experience Replay: Learns from tool routing failures and user corrections.
    """
    messages = state.get("messages", [])
    if not messages:
        return {}

    # Only trigger if there was a detour (retry or search)
    retry_count = state.get("retry_count", 0)
    search_count = state.get("search_count", 0)

    if retry_count == 0 and search_count == 0:
        return {}

    # Logic: If the last message is from the assistant and it's successful,
    # we summarize the 'lesson learned'.
    last_msg = messages[-1]
    if not isinstance(last_msg, AIMessage) or not last_msg.content:
        return {}

    user = state.get("user")
    if not user:
        return {}

    try:
        from app.core.memory import memory_manager

        lesson = None
        if search_count > 0:
            lesson = f"ROUTING LESSON: Query '{messages[0].content[:50]}...' required additional tool searching. Ensure prerequisite discovery tools are loaded."
        elif retry_count > 0:
            lesson = f"ROUTING LESSON: Query '{messages[0].content[:50]}...' failed initially and required reflexion. Check tool arguments and permissions."

        if lesson:
            logger.info(f"Saving JIT Experience: {lesson}")
            await memory_manager.add_memory(
                user_id=user.id,
                content=lesson,
                memory_type="preference",
            )
    except Exception as e:
        logger.error(f"Experience Replay failed: {e}")

    return {}


def create_agent_graph(tools: list):
    # Standardized LLM initialization
    llm = get_llm_client()
    tools_by_name = {t.name: t for t in tools}

    # Dynamic Instruction Injection from MCP Servers
    from app.core.mcp_manager import MCPManager

    mcp_instructions = MCPManager.get_system_instructions()
    dynamic_system_prompt = BASE_SYSTEM_PROMPT

    # Layer 1: MCP-specific rules (legacy)
    if mcp_instructions:
        dynamic_system_prompt += f"\\n## SPECIFIC DOMAIN RULES\\n{mcp_instructions}\\n"

    async def call_model(state: AgentState):
        messages = list(state["messages"])
        user = state.get("user")
        user_role = user.role if user else "guest"

        # 0. Build Base System Prompt with User Context
        from app.core.prompt_builder import PromptBuilder
        from app.core.skill_loader import SkillLoader

        summaries = SkillLoader.load_summaries(role=user_role)
        # We use BASE_SYSTEM_PROMPT as the "Soul" — the immutable identity core
        base_prompt_with_context = PromptBuilder.build_system_prompt(
            user=user, soul_content=BASE_SYSTEM_PROMPT, skill_summaries=summaries
        )

        # 1. Prepare Semantic Routing Query (Noise-Reduced)
        # Find relevant context for routing (Role-Aware & Context-Aware)
        # We use the last few messages to understand conversational context
        # (e.g. "check logs" means different things after a home error vs. a system error)
        current_context = state.get("context", "home")
        search_count = state.get("search_count", 0)

        context_parts = []
        # Take up to 3 recent human messages (excluding System)
        human_msgs = [m for m in messages if isinstance(m, HumanMessage)][-3:]
        for msg in human_msgs:
            content = str(msg.content)
            # Truncate long messages to avoid noise in semantic matching
            if len(content) > 300:
                content = content[:300] + "..."
            context_parts.append(content)

        routing_query = f"Context: {current_context} | " + " | ".join(context_parts)
        last_human_msg = str(human_msgs[-1].content) if human_msgs else ""

        # 1.5 Fast Intent Gate
        from app.core.intent_gate import IntentGate

        previous_error_category = None
        if state.get("last_classification"):
            previous_error_category = state["last_classification"].get("category")

        skill_hints = SkillLoader.load_routing_hints(role=user_role)
        fast_intent = IntentGate().classify_fast(
            last_human_msg,
            available_skills=skill_hints,
            previous_error_category=previous_error_category,
            context=current_context,
        )
        candidate_workers = fast_intent.get("candidate_workers", [])
        candidate_skills = fast_intent.get("candidate_skills", [])
        trace_logger.log_wire_event(
            "intent_gate",
            trace_id=str(state.get("trace_id", "")),
            summary=fast_intent.get("reason"),
            details={
                "intent_class": fast_intent.get("intent_class"),
                "candidate_workers": candidate_workers,
                "candidate_skills": candidate_skills,
                "confidence": fast_intent.get("confidence"),
                "needs_llm_escalation": fast_intent.get("needs_llm_escalation"),
            },
        )

        # 2. Skill Routing (Hierarchical L0/L1/L2)
        from app.core.tool_router import tool_router

        prompt_with_skills = base_prompt_with_context
        if state.get("verification_status") == "failed":
            messages.append(
                SystemMessage(
                    content=(
                        "VERIFICATION FAILED: Do not continue trying tools. "
                        "Explain briefly what failed, why it could not be verified, "
                        "and what user intervention or next step is needed."
                    )
                )
            )
        if state.get("selected_worker") == "code_worker" and state.get("next_execution_hint") == "report":
            messages.append(
                SystemMessage(
                    content=(
                        "CODE REPORT MODE: Do not execute more code or call more tools. "
                        "Summarize the failure, include the most relevant error, and explain the next manual step."
                    )
                )
            )
        if state.get("selected_worker") == "code_worker" and state.get("next_execution_hint") == "repair":
            messages.append(
                SystemMessage(
                    content=(
                        "CODE REPAIR MODE: Propose a materially different fix from the previous failed attempt. "
                        "Do not rerun the same code unchanged. Prefer using python_sandbox only after you change the approach."
                    )
                )
            )
        if state.get("verification_status") == "required":
            verify_context = state.get("verify_context") or {}
            verify_reason = verify_context.get("reason") or "Confirm the previous action result."
            verify_detail = verify_context.get("detail") or ""
            verify_worker = verify_context.get("worker") or state.get("selected_worker") or "unknown"
            verify_skill = verify_context.get("skill") or state.get("selected_skill") or "unknown"
            messages.append(
                SystemMessage(
                    content=(
                        "VERIFICATION REQUIRED: Do not finalize yet. "
                        "Use an appropriate read/verify/discovery tool to confirm the previous action result.\n"
                        f"Verification focus: {verify_reason}\n"
                        f"Worker: {verify_worker}\n"
                        f"Skill: {verify_skill}\n"
                        + (f"Observed detail: {verify_detail}" if verify_detail else "")
                    )
                )
            )

        t0_skills = time.perf_counter()
        matched_skills = await tool_router.route_skills(routing_query, role=user_role)
        if candidate_skills:
            registry_by_name = {
                entry["name"]: entry for entry in SkillLoader.load_registry_with_metadata(role=user_role)
            }
            hinted_skills = [registry_by_name[name] for name in candidate_skills if name in registry_by_name]
            matched_skills = hinted_skills + matched_skills
            deduped_skills = []
            seen_skill_names = set()
            for skill in matched_skills:
                skill_name = skill.get("name")
                if skill_name and skill_name not in seen_skill_names:
                    seen_skill_names.add(skill_name)
                    deduped_skills.append(skill)
            matched_skills = deduped_skills
        logger.info(f"[TIMING] route_skills took {(time.perf_counter() - t0_skills) * 1000:.0f}ms")
        trace_logger.log_wire_event(
            "skill_routing",
            trace_id=str(state.get("trace_id", "")),
            summary="Skill routing completed.",
            details={
                "matched_skills": [skill.get("name") for skill in matched_skills],
                "selected_skill_hint": candidate_skills[0] if candidate_skills else None,
            },
        )

        if matched_skills:
            active_rules = []
            for i, s in enumerate(matched_skills):
                if i == 0:
                    # L2: Full Content for the most relevant skill (saves tokens vs. loading all)
                    content = s.get("full_content", s["rules"])
                    active_rules.append(f"### {s['name']} (PRIMARY)\\n{content}")
                else:
                    # L1: Critical Rules only for secondary matches
                    active_rules.append(f"### {s['name']} (SECONDARY)\\n{s['rules']}")
            prompt_with_skills += "\\n## ACTIVE SKILL RULES (CONTEXTUAL)\\n" + "\\n\\n".join(active_rules) + "\\n"

        final_system_prompt = prompt_with_skills

        # Ensure System Prompt is present
        if not messages or not isinstance(messages[0], SystemMessage):
            messages.insert(0, SystemMessage(content=final_system_prompt))
        elif isinstance(messages[0], SystemMessage) and "You are Nexus" not in messages[0].content:
            messages[0] = SystemMessage(content=final_system_prompt + "\\n\\n" + messages[0].content)
        else:
            # Find if there's already a system message to append to, or prepend this one
            messages[0] = SystemMessage(content=final_system_prompt)

        memories = state.get("memories", [])
        if memories:
            memory_context = "\\n".join(memories)
            system_msg = SystemMessage(
                content=f"You have the following memories and preferences:\\n{memory_context}\\n"
                f"Use this context to personalize your response or avoid repeating mistakes."
            )
            # Find if there's already a system message to append to, or prepend this one
            if messages and isinstance(messages[0], SystemMessage):
                messages[0] = SystemMessage(content=messages[0].content + "\\n\\n" + system_msg.content)
            else:
                messages.insert(0, system_msg)

        # Dynamic Tool Routing
        from app.core.intent_router import IntentRouter
        from app.core.tool_router import tool_router

        last_msg_content = str(messages[-1].content) if messages else "Unknown"
        prompt_summary = last_msg_content if len(last_msg_content) < 2000 else last_msg_content[:2000]
        cached_intent_queries = state.get("intent_queries")
        should_run_fast_brain = (
            settings.ENABLE_FAST_BRAIN
            and bool(last_human_msg)
            and isinstance(messages[-1], HumanMessage)
            and cached_intent_queries is None
            and fast_intent.get("needs_llm_escalation", False)
        )

        intent_queries = cached_intent_queries or []
        if should_run_fast_brain:
            try:
                fast_brain_t0 = time.perf_counter()
                intent_queries = await asyncio.wait_for(
                    IntentRouter().decompose(last_human_msg), timeout=settings.FAST_BRAIN_TIMEOUT_SECONDS
                )
                fast_brain_latency_ms = (time.perf_counter() - fast_brain_t0) * 1000
                logger.info(
                    "Fast brain completed in %.0fms (queries=%d, input_len=%d)",
                    fast_brain_latency_ms,
                    len(intent_queries),
                    len(last_human_msg),
                )
                asyncio.create_task(
                    trace_logger.log_llm_call(
                        trace_id=str(state.get("trace_id", uuid.uuid4())),
                        model=os.getenv("LLM_MODEL", "unknown"),
                        phase="fast_brain",
                        prompt_summary=last_human_msg[:2000] if last_human_msg else "",
                        response_summary=" | ".join(intent_queries)[:2000] if intent_queries else "(fallback: empty)",
                        latency_ms=fast_brain_latency_ms,
                        tools_bound=[],
                        tool_calls=[],
                        selected_worker=candidate_workers[0] if candidate_workers else None,
                        selected_skill=candidate_skills[0] if candidate_skills else None,
                        intent_class=fast_intent.get("intent_class"),
                        route_confidence=fast_intent.get("confidence"),
                        classification=previous_error_category,
                        session_id=state.get("session_id"),
                        user_id=user.id if user else None,
                    )
                )
            except asyncio.TimeoutError:
                logger.warning(
                    "Fast brain timed out after %ss. Falling back to raw query.",
                    settings.FAST_BRAIN_TIMEOUT_SECONDS,
                )
                asyncio.create_task(
                    trace_logger.log_llm_call(
                        trace_id=str(state.get("trace_id", uuid.uuid4())),
                        model=os.getenv("LLM_MODEL", "unknown"),
                        phase="fast_brain",
                        prompt_summary=last_human_msg[:2000] if last_human_msg else "",
                        response_summary=f"(timeout fallback after {settings.FAST_BRAIN_TIMEOUT_SECONDS}s)",
                        latency_ms=settings.FAST_BRAIN_TIMEOUT_SECONDS * 1000,
                        tools_bound=[],
                        tool_calls=[],
                        selected_worker=candidate_workers[0] if candidate_workers else None,
                        selected_skill=candidate_skills[0] if candidate_skills else None,
                        intent_class=fast_intent.get("intent_class"),
                        route_confidence=fast_intent.get("confidence"),
                        classification=previous_error_category,
                        session_id=state.get("session_id"),
                        user_id=user.id if user else None,
                    )
                )
                intent_queries = []
            except Exception as e:
                logger.warning(f"Intent decomposition failed: {e}")
                asyncio.create_task(
                    trace_logger.log_llm_call(
                        trace_id=str(state.get("trace_id", uuid.uuid4())),
                        model=os.getenv("LLM_MODEL", "unknown"),
                        phase="fast_brain",
                        prompt_summary=last_human_msg[:2000] if last_human_msg else "",
                        response_summary=f"(error fallback: {str(e)[:500]})",
                        latency_ms=0,
                        tools_bound=[],
                        tool_calls=[],
                        selected_worker=candidate_workers[0] if candidate_workers else None,
                        selected_skill=candidate_skills[0] if candidate_skills else None,
                        intent_class=fast_intent.get("intent_class"),
                        route_confidence=fast_intent.get("confidence"),
                        classification=previous_error_category,
                        session_id=state.get("session_id"),
                        user_id=user.id if user else None,
                    )
                )
                intent_queries = []

        if not intent_queries:
            intent_queries = [last_human_msg] if last_human_msg else [routing_query]

        routing_queries = [f"Context: {current_context} | {q}" for q in intent_queries]

        try:
            skill_bound_tools = tool_router.get_skill_bound_tools(matched_skills, role=user_role)

            # Select relevant tools; pass user_role to enforce RBAC at the routing layer
            t0_route = time.perf_counter()
            routed_tools = await tool_router.route_multi(routing_queries, role=user_role, context=current_context)
            logger.info(f"[TIMING] route_multi took {(time.perf_counter() - t0_route) * 1000:.0f}ms")

            current_tools = skill_bound_tools + routed_tools
            current_tools = ToolCatalog.dedupe_by_name(current_tools)
            if not current_tools:
                # Fallback: give the LLM all role-permitted tools rather than nothing
                current_tools = [t for t in tools if tool_router._check_role(t, user_role)]

            if state.get("verification_status") == "failed":
                current_tools = []

            current_tools, worker_decision = await WorkerDispatcher.prepare_tools(
                state,
                current_tools,
                matched_skills,
                fallback_worker=candidate_workers[0] if candidate_workers else None,
            )
            selected_worker = worker_decision.get("selected_worker")
            trace_logger.log_wire_event(
                "toolbelt_selection",
                trace_id=str(state.get("trace_id", "")),
                summary="Selected tools for current turn.",
                details={
                    "selected_worker": selected_worker,
                    "execution_mode": worker_decision.get("execution_mode"),
                    "next_execution_hint": state.get("next_execution_hint"),
                    "selected_skill": state.get("selected_skill")
                    or (candidate_skills[0] if candidate_skills else None),
                    "tool_count": len(current_tools),
                    "tools": [tool.name for tool in current_tools],
                },
            )

            if search_count >= 3:
                current_tools = [t for t in current_tools if t.name != "request_more_tools"]
                final_system_prompt += "\\n\\n## ⚠️ SEARCH LIMIT REACHED\\nYou have reached the limit for tool search retries (3/3). Use existing tools or inform user.\\n"
                messages[0] = SystemMessage(content=final_system_prompt)

        except Exception as e:
            logger.error(f"Error during tool routing: {e}")
            current_tools = tools

        # Bind only selected tools for this turn (not the full registry)
        llm_with_tools = llm.bind_tools(current_tools)

        try:
            t0 = time.time()
            response = await llm_with_tools.ainvoke(messages)
            latency_ms = (time.time() - t0) * 1000

            logger.info(
                f"LLM call completed in {latency_ms:.0f}ms "
                f"(model={os.getenv('LLM_MODEL', 'unknown')}, "
                f"tools={len(current_tools)}, "
                f"input_msgs={len(messages)})"
            )

            response_summary = str(response.content)
            asyncio.create_task(
                trace_logger.log_llm_call(
                    trace_id=str(state.get("trace_id", uuid.uuid4())),
                    model=os.getenv("LLM_MODEL", "unknown"),
                    phase="main",
                    prompt_summary=prompt_summary,
                    response_summary=response_summary,
                    latency_ms=latency_ms,
                    tools_bound=[t.name for t in current_tools],
                    tool_calls=[tc for tc in getattr(response, "tool_calls", [])]
                    if hasattr(response, "tool_calls")
                    else [],
                    selected_worker=state.get("selected_worker")
                    or (candidate_workers[0] if candidate_workers else None),
                    selected_skill=state.get("selected_skill") or (candidate_skills[0] if candidate_skills else None),
                    intent_class=fast_intent.get("intent_class"),
                    route_confidence=fast_intent.get("confidence"),
                    classification=(state.get("last_classification") or {}).get("category"),
                    session_id=state.get("session_id"),
                    user_id=user.id if user else None,
                )
            )
        except Exception as e:
            logger.error("Error calling LLM provider:", exc_info=True)
            return {"messages": [AIMessage(content=f"Error calling LLM provider: {str(e)}")]}

        session_id = state.get("session_id")
        if session_id:
            asyncio.create_task(_persist_message(session_id, response))

        return {
            "messages": [response],
            "intent_queries": intent_queries,
            "intent_class": fast_intent.get("intent_class"),
            "route_confidence": fast_intent.get("confidence"),
            "selected_worker": selected_worker or (candidate_workers[0] if candidate_workers else None),
            "execution_mode": worker_decision.get("execution_mode"),
            "candidate_workers": candidate_workers,
            "selected_skill": state.get("selected_skill") or (candidate_skills[0] if candidate_skills else None),
            "candidate_skills": candidate_skills,
            "llm_call_count": state.get("llm_call_count", 0) + 1,
        }

    async def tool_node_with_permissions(state: AgentState):
        messages = state["messages"]
        last_message = messages[-1]
        user = state.get("user")
        trace_id = state.get("trace_id", uuid.uuid4())
        outputs = []
        last_outcome = None
        last_classification = None
        next_execution_hint = state.get("next_execution_hint")
        attempts_by_worker = dict(state.get("attempts_by_worker") or {})
        attempts_by_tool = dict(state.get("attempts_by_tool") or {})
        blocked_fingerprints = list(state.get("blocked_fingerprints") or [])

        # Should not happen based on edge logic, but safety check
        if not last_message.tool_calls:
            return {"messages": []}

        for tool_call in last_message.tool_calls:
            tool_name = tool_call["name"]

            # 🚑 【Universal Patch】Fix Malformed Tool Names (e.g. "forget_memoryforget_memory")
            # This happens with some local models that repeat the tool name string.
            if tool_name not in tools_by_name:
                half_len = len(tool_name) // 2
                if len(tool_name) % 2 == 0 and tool_name[:half_len] == tool_name[half_len:]:
                    candidate = tool_name[:half_len]
                    if candidate in tools_by_name:
                        logger.warning(
                            f"[Agent Patch] Auto-corrected malformed tool name: '{tool_name}' -> '{candidate}'"
                        )
                        tool_name = candidate

            tool_to_call = tools_by_name.get(tool_name)
            if not tool_to_call:
                outputs.append(
                    ToolMessage(
                        content=f"Error: Tool '{tool_name}' not found.", name=tool_name, tool_call_id=tool_call["id"]
                    )
                )
                continue

            # MCP/StructuredTool calls are sensitive to explicit nulls:
            # if the model emits {"limit": null, "detailed": null}, Pydantic validates the
            # provided None values instead of using schema defaults, which triggers first-fail
            # loops before the agent can recover. Strip None eagerly as a defensive runtime
            # patch for MCP-style schemas. This is not the ideal long-term fix; the better
            # direction is to improve tool-call generation / schema guidance so the model
            # omits unknown optional fields entirely.
            logger.info(f"[DEBUG None] 1. tool_call['args'] 原始值: {tool_call['args']}")
            tool_args = {k: v for k, v in tool_call["args"].items() if v is not None}
            logger.info(f"[DEBUG None] 2. tool_args 清洗后的值: {tool_args}")
            logger.info(f"[DEBUG None] 3. dispatcher.execute_tool_call 前的最终值: {tool_args}")
            execution_patch = await WorkerDispatcher.execute_tool_call(
                state,
                tool_name=tool_name,
                tool_call_id=tool_call["id"],
                tool_args=tool_args,
                tool_to_call=tool_to_call,
                user=user,
                trace_id=trace_id,
            )

            message = execution_patch.get("message")
            if message is not None:
                outputs.append(message)

            last_outcome = execution_patch.get("outcome")
            last_classification = execution_patch.get("classification")
            next_execution_hint = execution_patch.get("next_execution_hint", next_execution_hint)

            if last_outcome:
                selected_worker = state.get("selected_worker") or "chat_worker"
                if last_classification and last_classification.get("category") == "retryable_runtime_error":
                    attempts_by_worker[selected_worker] = attempts_by_worker.get(selected_worker, 0) + 1
                    if selected_worker == "code_worker" and attempts_by_worker[selected_worker] >= 3:
                        last_classification = {
                            **last_classification,
                            "retryable": False,
                            "requires_handoff": True,
                            "suggested_next_action": "handoff",
                            "user_facing_summary": "Code execution failed repeatedly and now needs intervention.",
                            "debug_summary": (
                                last_classification.get("debug_summary")
                                or "Code execution failed repeatedly and exhausted retry budget."
                            ),
                        }
                        trace_logger.log_wire_event(
                            "code_worker.budget",
                            trace_id=str(state.get("trace_id", "")),
                            summary="Code worker retry budget exhausted.",
                            details={
                                "attempts": attempts_by_worker[selected_worker],
                                "tool_name": tool_name,
                            },
                        )

                fingerprint = last_outcome.get("fingerprint")
                if fingerprint:
                    attempts_by_tool[fingerprint] = attempts_by_tool.get(fingerprint, 0) + 1
                    if (
                        selected_worker == "code_worker"
                        and last_classification
                        and last_classification.get("category") == "retryable_runtime_error"
                        and attempts_by_tool[fingerprint] >= 2
                        and fingerprint not in blocked_fingerprints
                    ):
                        blocked_fingerprints.append(fingerprint)
                        trace_logger.log_wire_event(
                            "code_worker.blocklist",
                            trace_id=str(state.get("trace_id", "")),
                            summary="Blocked code fingerprint after repeated runtime failures.",
                            details={
                                "fingerprint": fingerprint[:12],
                                "attempts": attempts_by_tool[fingerprint],
                                "tool_name": tool_name,
                            },
                        )

            if last_outcome:
                review_decision = await WorkerDispatcher.prepare_review(
                    {**state, "last_classification": last_classification}
                )
                trace_logger.log_wire_event(
                    "tool_result",
                    trace_id=str(state.get("trace_id", "")),
                    summary=f"Tool '{tool_name}' finished.",
                    details={
                        "tool_name": tool_name,
                        "selected_worker": state.get("selected_worker"),
                        "execution_mode": execution_patch.get("execution_mode"),
                        "review_mode": review_decision.get("execution_mode"),
                        "selected_skill": state.get("selected_skill"),
                        "status": last_outcome.get("status"),
                        "classification": last_classification.get("category") if last_classification else None,
                        "next_action": last_classification.get("suggested_next_action")
                        if last_classification
                        else None,
                        "next_execution_hint": next_execution_hint,
                        "fingerprint": (last_outcome.get("fingerprint") or "")[:12],
                    },
                )

        session_id = state.get("session_id")
        if session_id:
            for output in outputs:
                asyncio.create_task(_persist_message(session_id, output))

        return {
            "messages": outputs,
            "last_outcome": last_outcome,
            "last_classification": last_classification,
            "execution_mode": execution_patch.get("execution_mode") if last_outcome else state.get("execution_mode"),
            "verification_status": review_decision.get("verification_status")
            if last_outcome
            else state.get("verification_status"),
            "next_execution_hint": next_execution_hint,
            "attempts_by_worker": attempts_by_worker,
            "attempts_by_tool": attempts_by_tool,
            "blocked_fingerprints": blocked_fingerprints,
            "tool_call_count": state.get("tool_call_count", 0) + len(last_message.tool_calls),
        }

    workflow = StateGraph(AgentState)
    workflow.add_node("retrieve_memories", retrieve_memories)
    workflow.add_node("agent", call_model)
    workflow.add_node("tools", tool_node_with_permissions)
    workflow.add_node("reviewer_gate", reviewer_gate_node)
    workflow.add_node("verify_followup", verify_followup_node)
    workflow.add_node("reflexion", reflexion_node)
    workflow.add_node("report_failure", report_failure_node)
    workflow.add_node("experience_replay", experience_replay_node)

    workflow.set_entry_point("retrieve_memories")
    workflow.add_edge("retrieve_memories", "agent")
    workflow.add_conditional_edges(
        "agent",
        should_continue,
        {
            "tools": "tools",
            "agent": "agent",
            "verify": "verify_followup",
            "report": "report_failure",
            "__end__": "experience_replay",
        },
    )
    workflow.add_edge("report_failure", "experience_replay")
    workflow.add_edge("experience_replay", "__end__")
    workflow.add_edge("tools", "reviewer_gate")
    workflow.add_conditional_edges(
        "reviewer_gate",
        route_after_review,
        {"reflexion": "reflexion", "agent": "agent", "verify": "verify_followup", "report": "report_failure"},
    )
    workflow.add_edge("verify_followup", "agent")
    workflow.add_edge("reflexion", "agent")

    return workflow.compile()


async def stream_agent_events(graph, input_state: dict, config: dict = None):
    """
    Standardized wrapper for astream_events.
    Yields events for UI/Telegram consumption.
    """
    if config is None:
        config = {}
    if "recursion_limit" not in config:
        config["recursion_limit"] = settings.AGENT_RECURSION_LIMIT

    trace_id = str(input_state.get("trace_id", "unknown"))
    started_at = time.perf_counter()
    node_counts = {
        "retrieve_memories": 0,
        "agent": 0,
        "tools": 0,
        "reflexion": 0,
        "experience_replay": 0,
    }
    tool_calls_total = 0
    llm_calls_total = 0

    def _log_graph_stats(status: str):
        elapsed_ms = (time.perf_counter() - started_at) * 1000
        graph_steps_total = sum(node_counts.values())
        logger.info(
            "GRAPH STATS | trace=%s | status=%s | steps=%d | retrieve_memories=%d | agent=%d | tools=%d | "
            "reflexion=%d | experience_replay=%d | llm_calls=%d | tool_calls=%d | total_ms=%.0f",
            trace_id,
            status,
            graph_steps_total,
            node_counts["retrieve_memories"],
            node_counts["agent"],
            node_counts["tools"],
            node_counts["reflexion"],
            node_counts["experience_replay"],
            llm_calls_total,
            tool_calls_total,
            elapsed_ms,
        )

    try:
        async for event in graph.astream_events(input_state, config=config, version="v2"):
            kind = event["event"]
            name = event.get("name", "Unknown")
            if kind == "on_chain_start" and name in node_counts:
                node_counts[name] += 1
            # 1. LLM Thoughts (Progressive Tokens)
            if kind == "on_chat_model_stream":
                chunk = event["data"]["chunk"]
                if hasattr(chunk, "content") and chunk.content:
                    yield {"event": "thought", "data": chunk.content}
            elif kind == "on_tool_start":
                yield {"event": "tool_start", "data": {"name": name, "args": event["data"].get("input", {})}}
            elif kind == "on_tool_end":
                output = event["data"].get("output")
                preview = (str(output)[:300] + "...") if len(str(output)) > 300 else str(output)
                yield {"event": "tool_end", "data": {"name": name, "result": preview}}
            elif kind == "on_chain_end" and name == "LangGraph":
                final_state = event["data"]["output"]
                if final_state:
                    llm_calls_total = final_state.get("llm_call_count", llm_calls_total)
                    tool_calls_total = final_state.get("tool_call_count", tool_calls_total)
                _log_graph_stats("success")
                if final_state and "messages" in final_state and final_state["messages"]:
                    last_msg = final_state["messages"][-1]
                    yield {"event": "final_answer", "data": getattr(last_msg, "content", "")}
    except Exception as e:
        error_msg = str(e)
        if "recursion_limit" in error_msg.lower():
            error_msg = "⚠️ Agent 陷入了递归循环。已强制终止任务。"
        _log_graph_stats("error")
        logger.error(f"Error in astream_events: {e}", exc_info=True)
        yield {"event": "error", "data": error_msg}
