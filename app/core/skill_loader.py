"""
Skill Loader - Manages loading and aggregation of skill cards for System Prompt injection.
"""

import logging
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class SkillLoader:
    """Load and manage skill cards from the skills/ directory."""

    SKILLS_DIR = Path(__file__).parent.parent.parent / "skills"

    @classmethod
    def load_all(cls) -> str:
        """
        Load all .md skill files and format for prompt injection.

        Returns:
            Formatted string containing all skill cards, ready for System Prompt.
        """
        if not cls.SKILLS_DIR.exists():
            logger.warning(f"Skills directory not found: {cls.SKILLS_DIR}")
            return ""

        skills = []
        for skill_file in sorted(cls.SKILLS_DIR.glob("*.md")):
            # Skip template and hidden files
            if skill_file.name.startswith("_") or skill_file.name.startswith("."):
                continue

            try:
                content = skill_file.read_text(encoding="utf-8")
                skills.append(content)
                logger.info(f"Loaded skill: {skill_file.stem}")
            except Exception as e:
                logger.error(f"Failed to load skill {skill_file.name}: {e}")

        if not skills:
            logger.info("No skill cards found")
            return ""

        # Format skills with separators
        formatted = "\n\n---\n\n".join(skills)
        logger.info(f"Loaded {len(skills)} skill cards")
        return formatted

    @classmethod
    def load_by_name(cls, skill_name: str) -> Optional[str]:
        """
        Load a specific skill card by name.

        Args:
            skill_name: Name of the skill (without .md extension)

        Returns:
            Skill card content or None if not found
        """
        skill_file = cls.SKILLS_DIR / f"{skill_name}.md"

        if not skill_file.exists():
            logger.warning(f"Skill not found: {skill_name}")
            return None

        try:
            content = skill_file.read_text(encoding="utf-8")
            logger.info(f"Loaded skill: {skill_name}")
            return content
        except Exception as e:
            logger.error(f"Failed to load skill {skill_name}: {e}")
            return None

    @classmethod
    def list_skills(cls) -> List[Dict[str, str]]:
        """
        List all available skills with metadata.

        Returns:
            List of dicts with skill name and basic info
        """
        if not cls.SKILLS_DIR.exists():
            return []

        skills = []
        for skill_file in sorted(cls.SKILLS_DIR.glob("*.md")):
            if skill_file.name.startswith("_") or skill_file.name.startswith("."):
                continue

            try:
                content = skill_file.read_text(encoding="utf-8")
                # Extract YAML frontmatter if present
                metadata = cls._extract_metadata(content)
                skills.append(
                    {
                        "name": skill_file.stem,
                        "file": skill_file.name,
                        "domain": metadata.get("domain", "unknown"),
                        "priority": metadata.get("priority", "medium"),
                    }
                )
            except Exception as e:
                logger.error(f"Failed to read skill {skill_file.name}: {e}")

        return skills

    @classmethod
    def _extract_metadata(cls, content: str) -> Dict[str, str]:
        """
        Extract YAML frontmatter from skill card.

        Args:
            content: Full skill card content

        Returns:
            Dict of metadata fields
        """
        metadata = {}

        if not content.startswith("---"):
            return metadata

        try:
            # Find the closing ---
            lines = content.split("\n")
            end_idx = None
            for i, line in enumerate(lines[1:], start=1):
                if line.strip() == "---":
                    end_idx = i
                    break

            if end_idx is None:
                return metadata

            # Parse YAML-like frontmatter (simple key: value)
            for line in lines[1:end_idx]:
                if ":" in line:
                    key, value = line.split(":", 1)
                    metadata[key.strip()] = value.strip()
        except Exception as e:
            logger.warning(f"Failed to parse metadata: {e}")

        return metadata

    @classmethod
    def save_skill(cls, skill_name: str, content: str) -> bool:
        """
        Save a skill card to the skills directory.

        Args:
            skill_name: Name of the skill (without .md extension)
            content: Full skill card content

        Returns:
            True if saved successfully
        """
        try:
            cls.SKILLS_DIR.mkdir(parents=True, exist_ok=True)
            skill_file = cls.SKILLS_DIR / f"{skill_name}.md"
            skill_file.write_text(content, encoding="utf-8")
            logger.info(f"Saved skill: {skill_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to save skill {skill_name}: {e}")
            return False
