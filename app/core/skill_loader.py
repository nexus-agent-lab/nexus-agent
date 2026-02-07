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
    def load_summaries(cls, role: str = "user") -> str:
        """
        Load a very lightweight summary of all skills appropriate for the role.
        """
        if not cls.SKILLS_DIR.exists():
            return ""

        summaries = []
        for skill_file in sorted(cls.SKILLS_DIR.glob("*.md")):
            if skill_file.name.startswith("_") or skill_file.name.startswith("."):
                continue

            try:
                content = skill_file.read_text(encoding="utf-8")
                metadata = cls._extract_metadata(content)

                # Role Check
                req_role = metadata.get("required_role", "user")
                if req_role == "admin" and role != "admin":
                    continue

                desc = metadata.get("description", "No description available.")
                display_name = metadata.get("name", skill_file.stem)
                summaries.append(f"- **{display_name}** (Domain: {metadata.get('domain', 'general')}): {desc}")
            except Exception as e:
                logger.error(f"Failed to load summary for {skill_file.name}: {e}")

        return "\n".join(summaries)

    @classmethod
    def load_registry_with_metadata(cls, role: str = "user") -> List[Dict]:
        """
        Load all skills with their full rules and metadata for dynamic injection, filtered by role.
        """
        if not cls.SKILLS_DIR.exists():
            return []

        registry = []
        for skill_file in sorted(cls.SKILLS_DIR.glob("*.md")):
            if skill_file.name.startswith("_") or skill_file.name.startswith("."):
                continue

            try:
                content = skill_file.read_text(encoding="utf-8")
                metadata = cls._extract_metadata(content)

                # Role Check
                req_role = metadata.get("required_role", "user")
                if req_role == "admin" and role != "admin":
                    continue

                critical_rules = cls._extract_section(content, "Critical Rules") or "No critical rules defined."
                registry.append({"name": skill_file.stem, "metadata": metadata, "rules": critical_rules})
            except Exception as e:
                logger.error(f"Failed to load skill for registry: {skill_file.name}: {e}")

        return registry

    @classmethod
    def load_registry(cls) -> str:
        """
        Load a lightweight registry of all skills, including only Critical Rules.
        This optimizes context usage by excluding examples and lower-priority text.
        """
        if not cls.SKILLS_DIR.exists():
            return ""

        skills = []
        for skill_file in sorted(cls.SKILLS_DIR.glob("*.md")):
            if skill_file.name.startswith("_") or skill_file.name.startswith("."):
                continue

            try:
                content = skill_file.read_text(encoding="utf-8")
                metadata = cls._extract_metadata(content)
                critical_rules = cls._extract_section(content, "Critical Rules")

                skill_entry = f"### {skill_file.stem} (Domain: {metadata.get('domain', 'general')})\n"
                if critical_rules:
                    skill_entry += f"{critical_rules}\n"
                else:
                    skill_entry += "No critical rules defined.\n"

                skills.append(skill_entry)
            except Exception as e:
                logger.error(f"Failed to load skill {skill_file.name}: {e}")

        if not skills:
            return ""

        return "\n".join(skills)

    @classmethod
    def load_all(cls) -> str:
        """
        Legacy: Load all .md skill files fully.
        Recommended: Use load_registry() for efficiency.
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
    def _extract_section(cls, content: str, section_name: str) -> Optional[str]:
        """
        Extract a specific markdown section (headers matching section_name).
        Uses simple line-based parsing for robustness.
        """
        lines = content.split("\n")
        start_idx = -1
        end_idx = -1

        # Find start
        for i, line in enumerate(lines):
            if line.strip().startswith("##") and section_name.lower() in line.lower():
                start_idx = i + 1
                break

        if start_idx == -1:
            return None

        # Find end (next header or end of file)
        for i in range(start_idx, len(lines)):
            if lines[i].strip().startswith("##"):
                end_idx = i
                break

        if end_idx == -1:
            end_idx = len(lines)

        section_content = "\n".join(lines[start_idx:end_idx]).strip()
        return section_content if section_content else None

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
    def _extract_metadata(cls, content: str) -> Dict:
        """
        Extract YAML frontmatter from skill card.
        """
        metadata = {}
        if not content.startswith("---"):
            return metadata

        try:
            import json

            # Find the closing ---
            lines = content.split("\n")
            end_idx = None
            for i, line in enumerate(lines[1:], start=1):
                if line.strip() == "---":
                    end_idx = i
                    break

            if end_idx is None:
                return metadata

            # Parse YAML-like frontmatter
            for line in lines[1:end_idx]:
                if ":" in line:
                    key, value = line.split(":", 1)
                    key = key.strip()
                    value = value.strip()

                    # Enhanced parsing for lists (intent_keywords)
                    if (value.startswith("[") and value.endswith("]")) or (
                        value.startswith("{") and value.endswith("}")
                    ):
                        try:
                            # Try to parse as JSON for complex types
                            metadata[key] = json.loads(value.replace("'", '"'))
                        except Exception:
                            metadata[key] = value
                    else:
                        metadata[key] = value
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

    @classmethod
    def append_learned_rule(cls, skill_name: str, rule_content: str) -> bool:
        """
        Append a new learned rule to the skill card.
        Only adds if valid and not duplicate.
        """
        content = cls.load_by_name(skill_name)
        if not content:
            logger.error(f"Cannot append rule: Skill {skill_name} not found")
            return False

        learned_header = "## 🧠 Learned Rules"

        # Check if rule already exists (simple substring check for now)
        if rule_content in content:
            logger.info(f"Rule already exists in {skill_name}, skipping.")
            return True

        if learned_header in content:
            # Append to existing section
            # Find the header, then find the next header or end
            lines = content.split("\n")
            insert_idx = -1
            found_header = False

            for i, line in enumerate(lines):
                if learned_header in line:
                    found_header = True
                    continue
                if found_header and line.strip().startswith("##"):
                    insert_idx = i
                    break

            if insert_idx == -1:
                insert_idx = len(lines)

            # Insert before the next header (ensure newline)
            new_lines = lines[:insert_idx] + [f"- {rule_content}"] + lines[insert_idx:]
            new_content = "\n".join(new_lines)
        else:
            # Create new section at the end
            new_content = content.strip() + f"\n\n{learned_header}\n\n- {rule_content}\n"

        return cls.save_skill(skill_name, new_content)

    # =========================================
    # SKILL MARKETPLACE (P2)
    # =========================================

    REGISTRY_FILE = SKILLS_DIR / "skill_registry.json"

    # ClawHub Integration
    CLAWHUB_API_BASE = "https://clawhub.convex.site"  # ClawHub API endpoint
    CLAWHUB_RAW_BASE = "https://raw.githubusercontent.com/openclaw/clawhub/main"

    @classmethod
    def load_marketplace_registry(cls) -> List[Dict]:
        """
        Load the skill marketplace registry JSON.
        """
        if not cls.REGISTRY_FILE.exists():
            logger.warning(f"Skill registry not found: {cls.REGISTRY_FILE}")
            return []

        try:
            import json

            content = cls.REGISTRY_FILE.read_text(encoding="utf-8")
            return json.loads(content)
        except Exception as e:
            logger.error(f"Failed to load skill registry: {e}")
            return []

    @classmethod
    def get_installed_skills(cls) -> List[str]:
        """
        Get list of installed skill IDs (stem names of .md files).
        """
        if not cls.SKILLS_DIR.exists():
            return []
        return [f.stem for f in cls.SKILLS_DIR.glob("*.md") if not f.name.startswith("_")]

    @classmethod
    async def download_skill(cls, skill_id: str) -> bool:
        """
        Download a skill from its registered URL and save it locally.
        """
        registry = cls.load_marketplace_registry()
        skill_entry = next((s for s in registry if s.get("id") == skill_id), None)

        if not skill_entry:
            logger.error(f"Skill '{skill_id}' not found in registry.")
            return False

        source = skill_entry.get("source", "bundled")
        if source == "bundled":
            logger.info(f"Skill '{skill_id}' is bundled, no download needed.")
            return True

        url = skill_entry.get("url")
        if not url:
            logger.error(f"Skill '{skill_id}' has no URL configured.")
            return False

        try:
            import httpx

            async with httpx.AsyncClient() as client:
                response = await client.get(url, timeout=30.0)
                response.raise_for_status()
                content = response.text

                # Save to skills dir
                skill_file = cls.SKILLS_DIR / f"{skill_id}.md"
                skill_file.write_text(content, encoding="utf-8")
                logger.info(f"Downloaded and saved skill: {skill_id}")
                return True

        except Exception as e:
            logger.error(f"Failed to download skill '{skill_id}': {e}")
            return False

    @classmethod
    async def download_from_clawhub(cls, skill_name: str) -> bool:
        """
        Download a skill directly from ClawHub (https://github.com/openclaw/clawhub).
        Fetches the SKILL.md from the skills/ directory.
        """
        try:
            import httpx

            # Try multiple possible locations
            urls = [
                f"{cls.CLAWHUB_RAW_BASE}/skills/{skill_name}/SKILL.md",
                f"{cls.CLAWHUB_RAW_BASE}/skills/{skill_name}.md",
            ]

            async with httpx.AsyncClient() as client:
                for url in urls:
                    try:
                        response = await client.get(url, timeout=30.0, follow_redirects=True)
                        if response.status_code == 200:
                            content = response.text
                            # Save to skills dir
                            cls.SKILLS_DIR.mkdir(parents=True, exist_ok=True)
                            skill_file = cls.SKILLS_DIR / f"{skill_name}.md"
                            skill_file.write_text(content, encoding="utf-8")
                            logger.info(f"Downloaded skill from ClawHub: {skill_name}")
                            return True
                    except Exception:
                        continue

            logger.error(f"Skill '{skill_name}' not found on ClawHub")
            return False

        except Exception as e:
            logger.error(f"Failed to download from ClawHub: {e}")
            return False

    @classmethod
    async def install_skill(cls, skill_id: str) -> str:
        """
        Install a skill from the marketplace.
        Returns a status message.
        """
        installed = cls.get_installed_skills()
        if skill_id in installed:
            return f"✅ Skill `{skill_id}` is already installed."

        success = await cls.download_skill(skill_id)
        if success:
            return f"✅ Skill `{skill_id}` installed successfully! It will be available on next session."
        else:
            return f"❌ Failed to install skill `{skill_id}`. Check logs for details."

    @classmethod
    def uninstall_skill(cls, skill_id: str) -> str:
        """
        Remove a skill from the local skills directory.
        """
        skill_file = cls.SKILLS_DIR / f"{skill_id}.md"
        if not skill_file.exists():
            return f"⚠️ Skill `{skill_id}` is not installed."

        try:
            skill_file.unlink()
            logger.info(f"Uninstalled skill: {skill_id}")
            return f"✅ Skill `{skill_id}` uninstalled."
        except Exception as e:
            logger.error(f"Failed to uninstall skill '{skill_id}': {e}")
            return f"❌ Failed to uninstall skill `{skill_id}`: {e}"

    @classmethod
    def delete_skill(cls, skill_name: str) -> bool:
        """
        Delete a skill file from the skills directory.

        Args:
            skill_name: Name of the skill (without .md extension)

        Returns:
            True if deleted successfully
        """
        skill_file = cls.SKILLS_DIR / f"{skill_name}.md"
        if not skill_file.exists():
            logger.warning(f"Skill not found for deletion: {skill_name}")
            return False

        try:
            skill_file.unlink()
            logger.info(f"Deleted skill: {skill_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete skill {skill_name}: {e}")
            return False
