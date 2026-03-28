from types import SimpleNamespace

import httpx
import openai
import pytest
from langchain_core.messages import HumanMessage, ToolMessage

from app.core import llm_utils


def test_build_token_budget_reports_near_limit(monkeypatch):
    monkeypatch.setattr(llm_utils.settings, "LLM_CONTEXT_WINDOW", 100)
    monkeypatch.setattr(llm_utils.settings, "LLM_OUTPUT_WINDOW", 40)
    monkeypatch.setattr(llm_utils.settings, "LLM_CONTEXT_SOFT_LIMIT_RATIO", 0.6)
    monkeypatch.setattr(llm_utils, "count_prompt_tokens", lambda messages, model_name=None: (80, False))

    budget = llm_utils.build_token_budget([HumanMessage(content="hello")])

    assert budget.estimated_input_tokens == 80
    assert budget.remaining_input_budget == 20
    assert budget.near_context_limit is True
    assert budget.can_afford_structured_postprocess is False


def test_build_large_output_guidance_prefers_narrow_browser_followup(monkeypatch):
    monkeypatch.setattr(
        llm_utils, "build_token_budget", lambda messages, model_name=None: llm_utils.TokenBudget(80, 20, True, False)
    )
    monkeypatch.setattr(llm_utils.settings, "LLM_CONTEXT_WINDOW", 100)

    guidance = llm_utils.build_large_output_guidance(
        [
            HumanMessage(content="查论文"),
            ToolMessage(
                content="SYSTEM_ALERT: OUTPUT_TOO_LARGE\nFORMAT: UNSTRUCTURED TEXT\nPREVIEW: ...",
                name="browser_snapshot",
                tool_call_id="call-1",
            ),
        ]
    )

    assert guidance is not None
    assert "Do not call `python_sandbox`" in guidance
    assert "narrow the browser request" in guidance


@pytest.mark.asyncio
async def test_ainvoke_with_backoff_retries_rate_limit(monkeypatch):
    monkeypatch.setattr(llm_utils.settings, "LLM_RATE_LIMIT_RETRIES", 3)
    monkeypatch.setattr(llm_utils.settings, "LLM_RATE_LIMIT_BASE_DELAY_SECONDS", 0.01)
    monkeypatch.setattr(llm_utils.settings, "LLM_RATE_LIMIT_MAX_DELAY_SECONDS", 0.02)

    class DummyLLM:
        def __init__(self):
            self.calls = 0

        async def ainvoke(self, messages):
            self.calls += 1
            if self.calls == 1:
                request = httpx.Request("POST", "https://example.com/v1/chat/completions")
                response = httpx.Response(status_code=429, request=request)
                raise openai.RateLimitError("rate limited", response=response, body=None)
            return SimpleNamespace(content="ok")

    result = await llm_utils.ainvoke_with_backoff(DummyLLM(), [HumanMessage(content="hi")], operation_name="test")
    assert result.content == "ok"


def test_glm_tokenizer_alias_uses_cl100k_without_degraded(monkeypatch):
    monkeypatch.setattr(llm_utils.settings, "LLM_TOKENIZER", None)
    monkeypatch.setattr(llm_utils.settings, "LLM_MODEL", "glm-5-turbo")
    llm_utils._encoding_for_model.cache_clear()

    count, degraded = llm_utils.count_text_tokens("hello world", model_name="glm-5-turbo")

    assert count > 0
    assert degraded is False


def test_effective_llm_settings_uses_catalog_when_context_not_explicit(monkeypatch):
    monkeypatch.setattr(llm_utils.settings, "LLM_MODEL", "glm-5-turbo")
    monkeypatch.setattr(llm_utils.settings, "LLM_CONTEXT_WINDOW", 200000)
    monkeypatch.setattr(llm_utils.settings, "LLM_OUTPUT_WINDOW", 128000)
    monkeypatch.setattr(llm_utils.settings, "LLM_TOKENIZER", None)
    monkeypatch.setattr(llm_utils, "_is_setting_explicit", lambda field_name: field_name == "LLM_MODEL")

    effective = llm_utils.get_effective_llm_settings("glm-5-turbo")

    assert effective.context_window == 200000
    assert effective.output_window == 128000
    assert effective.tokenizer == "cl100k_base"
    assert effective.source == "catalog"


def test_effective_llm_settings_prefers_explicit_over_catalog(monkeypatch):
    monkeypatch.setattr(llm_utils.settings, "LLM_MODEL", "glm-5-turbo")
    monkeypatch.setattr(llm_utils.settings, "LLM_CONTEXT_WINDOW", 123456)
    monkeypatch.setattr(llm_utils.settings, "LLM_OUTPUT_WINDOW", 65432)
    monkeypatch.setattr(llm_utils.settings, "LLM_TOKENIZER", "o200k_base")
    monkeypatch.setattr(llm_utils, "_is_setting_explicit", lambda field_name: True)

    effective = llm_utils.get_effective_llm_settings("glm-5-turbo")

    assert effective.context_window == 123456
    assert effective.output_window == 65432
    assert effective.tokenizer == "o200k_base"
    assert effective.source == "explicit"
