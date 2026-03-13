from __future__ import annotations

import re
from typing import TypedDict

from langchain_core.messages import HumanMessage, SystemMessage

from app.core.llm_utils import get_llm_client
from app.core.skill_loader import SkillLoader


class FastIntentDecision(TypedDict, total=False):
    """Fast routing decision used before vector or full LLM routing."""

    intent_class: str
    candidate_workers: list[str]
    candidate_skills: list[str]
    confidence: float
    needs_llm_escalation: bool
    needs_discovery: bool
    reason: str


class IntentGate:
    """Deterministic-first worker routing with selective LLM escalation."""

    DISCOVERY_PATTERNS = ("列出", "查找", "搜索", "有哪些", "list", "find", "discover", "available entities")
    CODE_PATTERNS = ("python", "脚本", "代码", "json", "解析", "运行", "sandbox", "计算")
    RESEARCH_PATTERNS = ("文档", "docs", "架构", "设计", "why", "how", "分析", "research", "lookup")
    MIXED_CONNECTORS = ("并且", "然后", "顺便", "and", "then", "also")

    def classify_fast(
        self,
        user_message: str,
        *,
        available_skills: list[dict] | None = None,
        previous_error_category: str | None = None,
        context: str = "home",
    ) -> FastIntentDecision:
        content = (user_message or "").strip().lower()
        if not content:
            return FastIntentDecision(
                intent_class="chat",
                candidate_workers=["chat_worker"],
                candidate_skills=[],
                confidence=0.2,
                needs_llm_escalation=False,
                needs_discovery=False,
                reason="Empty input defaults to chat.",
            )

        matched_workers: list[str] = []
        matched_skills: list[str] = []
        available_skill_hints = available_skills if available_skills is not None else SkillLoader.load_routing_hints()
        needs_discovery = any(pattern in content for pattern in self.DISCOVERY_PATTERNS)

        for hint in available_skill_hints:
            keywords = [str(item).lower() for item in hint.get("keywords", [])]
            discovery_keywords = [str(item).lower() for item in hint.get("discovery_keywords", [])]
            preferred_worker = hint.get("preferred_worker", "skill_worker")
            skill_name = hint.get("skill_name")

            if any(pattern in content for pattern in keywords):
                matched_workers.append(preferred_worker)
                if skill_name:
                    matched_skills.append(str(skill_name))

            if any(pattern in content for pattern in discovery_keywords):
                matched_workers.append(preferred_worker)
                needs_discovery = True
                if skill_name:
                    matched_skills.append(str(skill_name))

        if any(pattern in content for pattern in self.CODE_PATTERNS):
            matched_workers.append("code_worker")
        if any(pattern in content for pattern in self.RESEARCH_PATTERNS):
            matched_workers.append("research_worker")
        if not matched_workers:
            matched_workers.append("chat_worker")

        # Preserve order while removing duplicates.
        candidate_workers = list(dict.fromkeys(matched_workers))
        candidate_skills = list(dict.fromkeys(matched_skills))
        mixed_request = len(candidate_workers) > 1 or any(connector in content for connector in self.MIXED_CONNECTORS)
        low_confidence = len(content) < 3

        needs_llm_escalation = mixed_request or low_confidence or previous_error_category == "wrong_tool_or_domain"
        confidence = 0.9 if len(candidate_workers) == 1 and not needs_llm_escalation else 0.55

        intent_class = self._infer_intent_class(candidate_workers, needs_discovery=needs_discovery)
        reason_parts = [f"workers={candidate_workers}"]
        if candidate_skills:
            reason_parts.append(f"skills={candidate_skills}")
        if needs_discovery:
            reason_parts.append("discovery requested")
        if previous_error_category == "wrong_tool_or_domain":
            reason_parts.append("previous routing mismatch")
        if mixed_request:
            reason_parts.append("mixed request")

        return FastIntentDecision(
            intent_class=intent_class,
            candidate_workers=candidate_workers,
            candidate_skills=candidate_skills,
            confidence=confidence,
            needs_llm_escalation=needs_llm_escalation,
            needs_discovery=needs_discovery,
            reason=", ".join(reason_parts),
        )

    async def escalate_with_llm(self, user_message: str, candidate_workers: list[str]) -> FastIntentDecision:
        """
        Lightweight escalation path for ambiguous requests.

        This is intentionally separate from the fast path so we only pay for it
        when deterministic routing is not confident enough.
        """

        llm = get_llm_client(temperature=0)
        prompt = (
            "You are a routing engine. Choose the best worker for the user request. "
            "Return one token only from: chat_worker, skill_worker, code_worker, research_worker."
        )
        response = await llm.ainvoke(
            [
                SystemMessage(content=prompt),
                HumanMessage(content=f"Candidates: {candidate_workers}\nRequest: {user_message}"),
            ]
        )
        selected = re.sub(r"[^a-z_]", "", str(response.content).strip().lower())
        if selected not in {"chat_worker", "skill_worker", "code_worker", "research_worker"}:
            selected = candidate_workers[0] if candidate_workers else "chat_worker"

        return FastIntentDecision(
            intent_class=self._infer_intent_class([selected], needs_discovery=False),
            candidate_workers=[selected],
            candidate_skills=[],
            confidence=0.75,
            needs_llm_escalation=False,
            needs_discovery=False,
            reason="LLM escalation resolved ambiguous routing.",
        )

    @staticmethod
    def _infer_intent_class(candidate_workers: list[str], *, needs_discovery: bool) -> str:
        if needs_discovery and "skill_worker" in candidate_workers:
            return "skill_discovery"
        if "code_worker" in candidate_workers:
            return "code_execution"
        if "research_worker" in candidate_workers:
            return "research"
        if "skill_worker" in candidate_workers:
            return "skill_execution"
        return "chat"
