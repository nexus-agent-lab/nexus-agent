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
        # If it's a local server at 9292, we'll assume a local model name
        default_model = "embedding-3" if "bigmodel" in base_url else "text-embedding-3-small"
        if "9292" in base_url:
            default_model = "local-model"

        model_name = os.getenv("EMBEDDING_MODEL", default_model)

        # Get dimension from env (512 for local bge-small, 1536 for OpenAI)
        dimension = int(os.getenv("EMBEDDING_DIMENSION", "512"))

        if "9292" in base_url:
            # Use a simpler approach for local server to avoid OpenAI-specific tokenization
            # Actually, let's just use a custom simple wrapper or ensure OpenAIEmbeddings doesn't tokenize
            self.embeddings = OpenAIEmbeddings(
                model=model_name,
                api_key=api_key,
                base_url=base_url,
                check_embedding_ctx_length=False,  # Disable internal tokenization checks
            )
        else:
            self.embeddings = OpenAIEmbeddings(
                model=model_name,
                api_key=api_key,
                base_url=base_url,
                dimensions=dimension if dimension == 1536 else None,
            )

    async def add_memory(
        self, user_id: int, content: str, memory_type: str = "knowledge", dedup_threshold: float = 0.90
    ):
        """
        Embeds content and stores it in the database.
        Includes semantic deduplication: if a memory with > 0.90 similarity exists, return that instead.
        """
        vector = await self.embeddings.aembed_query(content)

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
            new_memory = Memory(user_id=user_id, content=content, embedding=vector, memory_type=memory_type)
            session.add(new_memory)
            await session.commit()
            return new_memory

    async def search_memory(self, user_id: int, query: str, limit: int = 3, threshold: float = 0.4):
        """
        Performs vector similarity search.
        """
        query_vector = await self.embeddings.aembed_query(query)

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


# Singleton instance
memory_manager = MemoryManager()
