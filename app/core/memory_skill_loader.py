"""
Memory Skill Loader - Load and manage Memory Skills from files and database.
"""

import logging
import re
from pathlib import Path
from typing import Dict, List, Optional

import yaml

logger = logging.getLogger("nexus.memory_skill_loader")

MEMORY_SKILLS_DIR = Path(__file__).parent.parent.parent / "skills" / "memory"


class MemorySkillLoader:
    """
    Loader for Memory Skills.
    Follows hybrid approach: file-based skills synced to DB at startup.
    """

    @classmethod
    def load_all_from_files(cls) -> List[Dict]:
        """
        Load all memory skill definitions from skills/memory/*.md files.
        Returns list of skill metadata dicts.
        """
        skills = []
        if not MEMORY_SKILLS_DIR.exists():
            logger.warning(f"Memory skills directory not found: {MEMORY_SKILLS_DIR}")
            return skills

        for skill_file in MEMORY_SKILLS_DIR.glob("*.md"):
            try:
                skill_data = cls.parse_skill_file(skill_file)
                if skill_data:
                    skills.append(skill_data)
            except Exception as e:
                logger.error(f"Failed to parse memory skill {skill_file.name}: {e}")

        logger.info(f"Loaded {len(skills)} memory skills from files")
        return skills

    @classmethod
    def parse_skill_file(cls, filepath: Path) -> Optional[Dict]:
        """
        Parse a memory skill markdown file.
        Extracts YAML frontmatter and prompt template.
        """
        content = filepath.read_text(encoding="utf-8")

        # Extract YAML frontmatter
        frontmatter_match = re.match(r"^---\s*\n(.*?)\n---\s*\n", content, re.DOTALL)
        if not frontmatter_match:
            logger.warning(f"No frontmatter in {filepath.name}")
            return None

        try:
            metadata = yaml.safe_load(frontmatter_match.group(1))
        except yaml.YAMLError as e:
            logger.error(f"Invalid YAML in {filepath.name}: {e}")
            return None

        # Extract prompt template (content after frontmatter)
        body = content[frontmatter_match.end() :]

        # Find the Prompt Template section
        prompt_match = re.search(r"##\s*Prompt\s*Template\s*\n(.*?)(?=\n##|\Z)", body, re.DOTALL | re.IGNORECASE)
        prompt_template = prompt_match.group(1).strip() if prompt_match else body.strip()

        return {
            "name": metadata.get("name", filepath.stem),
            "description": metadata.get("description", ""),
            "skill_type": metadata.get("skill_type", "encoding"),
            "intent_keywords": metadata.get("intent_keywords", []),
            "prompt_template": prompt_template,
            "version": metadata.get("version", 1),
            "source_file": str(filepath),
        }

    @classmethod
    def get_skill_by_name(cls, name: str) -> Optional[Dict]:
        """Load a specific skill by name."""
        skill_file = MEMORY_SKILLS_DIR / f"{name}.md"
        if skill_file.exists():
            return cls.parse_skill_file(skill_file)
        return None

    @classmethod
    def get_skills_by_type(cls, skill_type: str) -> List[Dict]:
        """Get all skills of a specific type (encoding or retrieval)."""
        all_skills = cls.load_all_from_files()
        return [s for s in all_skills if s.get("skill_type") == skill_type]

    @classmethod
    def update_skill_file(cls, filepath: str, new_prompt: str, new_version: int) -> bool:
        """
        Updates the 'Prompt Template' section and version of a memory skill markdown file.
        Preserves all other sections and metadata.
        """
        try:
            path = Path(filepath)
            if not path.exists():
                logger.error(f"Cannot update skill file, path not found: {filepath}")
                return False

            content = path.read_text(encoding="utf-8")

            content = re.sub(
                r"(^---\s*\n.*?version:\s*)(\d+)(.*?---\s*\n)",
                lambda m: f"{m.group(1)}{new_version}{m.group(3)}",
                content,
                flags=re.DOTALL,
            )

            # We look for ## Prompt Template and capture everything until the next ## or end of file
            pattern = r"(##\s*Prompt\s*Template\s*\n)(.*?)(?=\n##|\Z)"

            def replacement(match):
                header = match.group(1)
                return f"{header}\n{new_prompt.strip()}\n\n"

            new_content = re.sub(pattern, replacement, content, flags=re.DOTALL | re.IGNORECASE)

            path.write_text(new_content, encoding="utf-8")
            logger.info(f"Successfully updated skill file: {path.name} to v{new_version}")
            return True
        except Exception as e:
            logger.error(f"Failed to update skill file {filepath}: {e}")
            return False

    @classmethod
    async def sync_to_database(cls):
        """
        Sync file-based skills to database.
        File version takes precedence over DB if higher.
        """
        from sqlmodel import select

        from app.core.db import AsyncSessionLocal
        from app.models.memory_skill import MemorySkill

        file_skills = cls.load_all_from_files()

        async with AsyncSessionLocal() as session:
            for skill_data in file_skills:
                # Check if exists in DB
                stmt = select(MemorySkill).where(MemorySkill.name == skill_data["name"])
                result = await session.execute(stmt)
                db_skill = result.scalar_one_or_none()

                if not db_skill:
                    # New skill, create
                    new_skill = MemorySkill(
                        name=skill_data["name"],
                        description=skill_data["description"],
                        skill_type=skill_data["skill_type"],
                        prompt_template=skill_data["prompt_template"],
                        version=skill_data["version"],
                        source_file=skill_data["source_file"],
                        is_base=True,
                    )
                    session.add(new_skill)
                    logger.info(f"Created memory skill in DB: {skill_data['name']}")
                elif skill_data["version"] > db_skill.version:
                    # File version is newer, update DB
                    db_skill.description = skill_data["description"]
                    db_skill.prompt_template = skill_data["prompt_template"]
                    db_skill.version = skill_data["version"]
                    db_skill.source_file = skill_data["source_file"]
                    logger.info(f"Updated memory skill in DB: {skill_data['name']} (v{skill_data['version']})")
                # else: DB version is newer (Designer evolved), keep DB

            await session.commit()
        logger.info("Memory skills synced to database")
