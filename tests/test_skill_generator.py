from types import SimpleNamespace

import pytest

from app.core.skill_generator import SkillGenerator


@pytest.mark.asyncio
async def test_generate_routing_examples_parses_json_array(monkeypatch):
    class DummyLLM:
        async def ainvoke(self, _messages):
            return SimpleNamespace(content='["帮我查一下最新论文", "帮我总结这个网页"]')

    monkeypatch.setattr(SkillGenerator, "get_llm", classmethod(lambda cls: DummyLLM()))

    examples = await SkillGenerator.generate_routing_examples(
        skill_name="WebBrowsing",
        skill_description="Browse websites and summarize public pages.",
        tools=[{"name": "browser_navigate", "description": "Open a web page"}],
        domain="web",
        constraints=["public read-only"],
        count=2,
    )

    assert examples == ["帮我查一下最新论文", "帮我总结这个网页"]
