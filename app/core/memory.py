import os

from langchain_openai import OpenAIEmbeddings
from sqlmodel import select

from app.core.db import AsyncSessionLocal
from app.models.memory import Memory


class MemoryManager:
    def __init__(self):
        # Allow separate configuration for embeddings (local or alternative provider)
        base_url = os.getenv("EMBEDDING_BASE_URL") or os.getenv("LLM_BASE_URL", "")
        api_key = os.getenv("EMBEDDING_API_KEY") or os.getenv("LLM_API_KEY")

        # Default to embedding-3 (GLM/v4) if base_url contains bigmodel, else openai default
        default_model = "embedding-3" if "bigmodel" in base_url else "text-embedding-3-small"
        model_name = os.getenv("EMBEDDING_MODEL", default_model)

        # Get dimension from env (1024 for bge-m3, 1536 for OpenAI)
        dimension = int(os.getenv("EMBEDDING_DIMENSION", "1024"))

        from app.core.agent import logger  # Use existing logger

        logger.info(f"MemoryManager Init: base_url='{base_url}', model='{model_name}'")

        # Use OllamaEmbeddings for Ollama backend (port 11434)
        if "11434" in base_url:
            from langchain_ollama import OllamaEmbeddings

            # OllamaEmbeddings expects base_url without /v1 suffix
            ollama_base = base_url.replace("/v1", "")
            self.embeddings = OllamaEmbeddings(
                model=model_name.replace(":latest", ""),  # Ollama models don't need :latest
                base_url=ollama_base,
            )
            logger.info(f"Using OllamaEmbeddings with base_url='{ollama_base}'")
        elif "9292" in base_url:
            # Local custom embedding server
            self.embeddings = OpenAIEmbeddings(
                model=model_name,
                api_key=api_key,
                base_url=base_url,
                check_embedding_ctx_length=False,
            )
        else:
            # OpenAI or other OpenAI-compatible providers
            self.embeddings = OpenAIEmbeddings(
                model=model_name,
                api_key=api_key,
                base_url=base_url,
                dimensions=dimension if dimension == 1536 else None,
            )

    async def add_memory(
        self, user_id: int, content: str, memory_type: str = "knowledge", dedup_threshold: float = 0.90,
        skill_id: int = None,
    ):
        """
        Embeds content and stores it in the database.
        Includes semantic deduplication: if a memory with > 0.90 similarity exists, return that instead.
        """
        if os.getenv("EMBEDDING_PROXY_URL"):
            # Optional: Allow specific proxy for embeddings if needed, otherwise default
            pass

        # Switch to synchronous call in threadpool to avoid async httpx connection issues
        # vector = await self.embeddings.aembed_query(content)
        import asyncio

        vector = await asyncio.to_thread(self.embeddings.embed_query, content)

        async with AsyncSessionLocal() as session:
            # 1. Deduplication Check
            # Using vector_cosine_ops (<=> is cosine distance in pgvector)
            # Distance = 1 - Similarity. So Similarity > 0.92 means Distance < 0.08
            distance_threshold = 1.0 - dedup_threshold

            stmt = (
                select(Memory)
                .where(Memory.user_id == user_id)
                .where(Memory.embedding.cosine_distance(vector) < distance_threshold)
                .order_by(Memory.embedding.cosine_distance(vector))
                .limit(1)
            )
            existing = await session.execute(stmt)
            duplicate = existing.scalar_one_or_none()

            if duplicate:
                # Retrieve the actual distance for logging (if needed, or just return)
                # Ideally we log this "cache hit"
                return duplicate

            # 2. Add New Memory
            new_memory = Memory(user_id=user_id, content=content, embedding=vector, memory_type=memory_type, skill_id=skill_id)
            session.add(new_memory)
            await session.commit()
            return new_memory

    async def search_memory(self, user_id: int, query: str, limit: int = 3, threshold: float = 0.4):
        """
        Performs vector similarity search.
        """
        # Switch to synchronous call in threadpool
        # query_vector = await self.embeddings.aembed_query(query)
        import asyncio

        query_vector = await asyncio.to_thread(self.embeddings.embed_query, query)

        async with AsyncSessionLocal() as session:
            # Using vector_cosine_ops (<=> is cosine distance in pgvector)
            # Distance = 1 - Similarity. So Similarity > 0.7 means Distance < 0.3
            distance_threshold = 1.0 - threshold

            statement = (
                select(Memory)
                .where(Memory.user_id == user_id)
                .where(Memory.embedding.cosine_distance(query_vector) < distance_threshold)
                .order_by(Memory.embedding.cosine_distance(query_vector))
                .limit(limit)
            )

            results = await session.execute(statement)
            return results.scalars().all()

    async def list_memories(self, user_id: int, memory_type: str = None, limit: int = 10):
        """
        List memories by type without vector search.
        """
        async with AsyncSessionLocal() as session:
            statement = select(Memory).where(Memory.user_id == user_id)
            if memory_type:
                statement = statement.where(Memory.memory_type == memory_type)

            statement = statement.order_by(Memory.created_at.desc()).limit(limit)

            results = await session.execute(statement)
            return results.scalars().all()

    async def delete_memory(self, user_id: int, memory_id: int):
        """
        Delete a specific memory by ID.
        """
        async with AsyncSessionLocal() as session:
            statement = select(Memory).where(Memory.user_id == user_id, Memory.id == memory_id)
            result = await session.execute(statement)
            memory = result.scalar_one_or_none()
            if memory:
                await session.delete(memory)
                await session.commit()
                return True
            return False

    async def delete_all_memories(self, user_id: int, memory_type: str = None) -> int:
        """
        Delete all memories for a user, optionally filtered by type.
        Returns the count of deleted items.
        """
        from sqlmodel import delete

        async with AsyncSessionLocal() as session:
            statement = delete(Memory).where(Memory.user_id == user_id)
            if memory_type:
                statement = statement.where(Memory.memory_type == memory_type)

            # Note: delete() with execution doesn't return count directly in all drivers easily
            # We can select count first or use RETURNING.
            # Simpler: just execute. Actually expected rowcount is available.
            result = await session.execute(statement)
            await session.commit()
            return result.rowcount


    async def add_memory_with_skill(
        self, user_id: int, content: str, context: str = "", skill_name: str = None, memory_type: str = "knowledge"
    ):
        """
        Add memory with automatic skill processing (Encoding).
        1. Selects best 'encoding' skill (or uses provided skill_name).
        2. Processes content via LLM.
        3. Saves processed content to vector DB.
        """
        from langchain_core.messages import HumanMessage

        from app.core.agent import logger
        from app.core.llm_utils import get_llm_client
        from app.core.memory_controller import MemoryController
        from app.core.memory_skill_loader import MemorySkillLoader

        # 1. Determine Skill
        skill = None
        if skill_name:
            skill = MemorySkillLoader.get_skill_by_name(skill_name)
        else:
            # Only use auto-selection if content is long enough or complex?
            # For now, always try to match if keywords match.
            skill = await MemoryController.select_skill(content, "encoding")

        processed_content = content

        # 2. Apply Skill (if found)
        if skill:
            logger.info(f"Applying memory skill '{skill['name']}' to content")
            try:
                # Render Prompt
                # Simple replacement for now (safer than eval)
                # Ensure we handle potential missing variables gracefully
                prompt = skill["prompt_template"]
                prompt = prompt.replace("{{ content }}", content)
                prompt = prompt.replace("{{ context }}", context or "")

                # Call LLM
                llm = get_llm_client()
                response = await llm.ainvoke([HumanMessage(content=prompt)])

                # Check directly for string content or object
                if hasattr(response, "content"):
                    processed_content = response.content.strip()
                else:
                    processed_content = str(response).strip()

                logger.info(f"Skill '{skill['name']}' processed memory. Original: {len(content)} chars -> New: {len(processed_content)} chars")
            except Exception as e:
                logger.error(f"Failed to apply skill '{skill['name']}': {e}")
                # Fallback to original content

        # 3. Resolve skill_id from DB for feedback tracking
        resolved_skill_id = None
        if skill:
            try:
                from app.core.db import AsyncSessionLocal
                from app.models.memory_skill import MemorySkill as MemorySkillModel

                async with AsyncSessionLocal() as db_session:
                    stmt = select(MemorySkillModel).where(MemorySkillModel.name == skill["name"])
                    result = await db_session.execute(stmt)
                    db_skill = result.scalar_one_or_none()
                    if db_skill:
                        resolved_skill_id = db_skill.id
            except Exception as e:
                logger.warning(f"Could not resolve skill_id for '{skill['name']}': {e}")

        # 4. Save to Vector DB
        return await self.add_memory(user_id, processed_content, memory_type=memory_type, skill_id=resolved_skill_id)

    async def search_memory_with_skill(
        self, user_id: int, query: str, context: str = "", limit: int = 3, threshold: float = 0.4
    ):
        """
        Search memory with automatic query refinement (Retrieval).
        """
        from langchain_core.messages import HumanMessage

        from app.core.agent import logger
        from app.core.llm_utils import get_llm_client
        from app.core.memory_controller import MemoryController

        # 1. Determine Skill
        skill = await MemoryController.select_skill(query, "retrieval")

        search_query = query

        # 2. Apply Skill (if found)
        if skill:
            logger.info(f"Applying retrieval skill '{skill['name']}' to query")
            try:
                prompt = skill["prompt_template"]
                prompt = prompt.replace("{{ query }}", query) # Assuming retrieval skills use {{ query }}
                prompt = prompt.replace("{{ context }}", context or "")

                llm = get_llm_client()
                response = await llm.ainvoke([HumanMessage(content=prompt)])

                if hasattr(response, "content"):
                    search_query = response.content.strip()
                else:
                    search_query = str(response).strip()

                logger.info(f"Refined search query: '{query}' -> '{search_query}'")
            except Exception as e:
                logger.error(f"Failed to apply retrieval skill '{skill['name']}': {e}")

        # 3. Search
        return await self.search_memory(user_id, search_query, limit=limit, threshold=threshold)


# Singleton instance
memory_manager = MemoryManager()
