"""
Tests for the Skill Loader system.
"""

import pytest

from app.core.skill_loader import SkillLoader


class TestSkillLoader:
    """Tests for SkillLoader functionality."""

    def test_skills_directory_exists(self):
        """Skills directory should exist."""
        assert SkillLoader.SKILLS_DIR.exists()
        assert SkillLoader.SKILLS_DIR.is_dir()

    def test_load_all_skills(self):
        """Should load all skill cards."""
        skills = SkillLoader.load_all()

        # Should return a string (even if empty)
        assert isinstance(skills, str)

        # If skills exist, should contain markdown content
        if skills:
            assert "##" in skills  # Markdown headers

    def test_load_homeassistant_skill(self):
        """Should load Home Assistant skill card."""
        skill = SkillLoader.load_by_name("homeassistant")

        if skill:  # Only test if skill exists
            assert "Home Assistant" in skill
            assert "盲人规则" in skill
            assert "query_entities" in skill

    def test_load_nonexistent_skill(self):
        """Should return None for non-existent skill."""
        skill = SkillLoader.load_by_name("nonexistent_skill_xyz")
        assert skill is None

    def test_list_skills(self):
        """Should list all available skills."""
        skills = SkillLoader.list_skills()

        assert isinstance(skills, list)

        # Each skill should have required fields
        for skill in skills:
            assert "name" in skill
            assert "file" in skill
            assert "domain" in skill
            assert "priority" in skill

    def test_extract_metadata(self):
        """Should extract YAML frontmatter from skill card."""
        content = """---
name: TestSkill
domain: test
priority: high
---

# Test Skill
"""
        metadata = SkillLoader._extract_metadata(content)

        assert metadata["name"] == "TestSkill"
        assert metadata["domain"] == "test"
        assert metadata["priority"] == "high"

    def test_extract_metadata_supports_yaml_lists(self):
        """Should parse multiline YAML lists used by skill frontmatter."""
        content = """---
name: TestSkill
intent_keywords:
  - alpha
  - beta
routing_examples:
  - 帮我搜一下最新论文
  - 打开这个网页
---

# Test Skill
"""
        metadata = SkillLoader._extract_metadata(content)

        assert metadata["intent_keywords"] == ["alpha", "beta"]
        assert metadata["routing_examples"] == ["帮我搜一下最新论文", "打开这个网页"]

    def test_extract_metadata_no_frontmatter(self):
        """Should handle skill cards without frontmatter."""
        content = "# Test Skill\n\nNo frontmatter here."
        metadata = SkillLoader._extract_metadata(content)

        assert isinstance(metadata, dict)
        assert len(metadata) == 0

    def test_strip_routing_metadata_keeps_prompt_clean(self):
        """Routing-only metadata should not be injected into the LLM prompt copy."""
        content = """---
name: TestSkill
domain: web
routing_examples:
  - 帮我搜一下最新论文
  - 打开网页看看
priority: high
---

# Test Skill

## Critical Rules
Only use facts from tools.
"""
        stripped = SkillLoader._strip_routing_metadata(content)

        assert "routing_examples" not in stripped
        assert "帮我搜一下最新论文" not in stripped
        assert "Only use facts from tools." in stripped

    def test_load_routing_hints_uses_existing_intent_keywords(self):
        hints = SkillLoader.load_routing_hints()

        assert isinstance(hints, list)
        assert hints

        homeassistant_hint = next((hint for hint in hints if hint.get("skill_name") == "homeassistant"), None)
        assert homeassistant_hint is not None
        assert "keywords" in homeassistant_hint
        assert isinstance(homeassistant_hint["keywords"], list)
        assert homeassistant_hint.get("preferred_worker") == "skill_worker"

    @pytest.mark.asyncio
    async def test_save_and_delete_skill(self):
        """Should save and delete skill cards."""
        test_skill_name = "test_skill_temp"
        test_content = """---
name: TestSkill
domain: test
---

# Test Skill
"""

        # Save
        success = SkillLoader.save_skill(test_skill_name, test_content)
        assert success is True

        # Verify it exists
        skill_file = SkillLoader.SKILLS_DIR / f"{test_skill_name}.md"
        assert skill_file.exists()

        # Load it back
        loaded = SkillLoader.load_by_name(test_skill_name)
        assert loaded == test_content

        # Cleanup
        skill_file.unlink()


class TestSkillIntegration:
    """Integration tests for skill system."""

    def test_skills_injected_into_prompt(self):
        """Skills should be loaded and available for agent."""
        from app.core.agent import create_agent_graph

        # Create a minimal agent graph
        graph = create_agent_graph([])

        # Graph should be created successfully
        assert graph is not None

        # Note: We can't easily test the prompt content without
        # invoking the graph, but we can verify it doesn't crash
