import logging
import os
from typing import Any, List

import numpy as np
from langchain_core.tools import BaseTool

from app.core.config import settings

logger = logging.getLogger(__name__)

# Tools that are ALWAYS available regardless of semantic context
CORE_TOOL_NAMES = {
    "get_current_time",
    "python_sandbox",
    "save_insight",
    "store_preference",
    "query_memory",
}


class SemanticToolRouter:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SemanticToolRouter, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self.embeddings = None
        self.tool_index = None  # numpy array of embeddings (Tools)
        self.skill_index = None  # numpy array of embeddings (Skills)
        self.semantic_tools: List[BaseTool] = []
        self.core_tools: List[BaseTool] = []
        self.all_tools: List[BaseTool] = []
        self.skill_entries: List[dict] = []  # [{name, metadata, rules}]

        try:
            self._setup_embeddings()
            self._initialized = True
        except Exception as e:
            logger.error(f"Failed to initialize embeddings for router: {e}")
            self.embeddings = None

    def _setup_embeddings(self):
        """Initialize embedding model (mirrors MemoryManager config)."""
        base_url = os.getenv("EMBEDDING_BASE_URL") or os.getenv("LLM_BASE_URL", "")
        api_key = os.getenv("EMBEDDING_API_KEY") or os.getenv("LLM_API_KEY")

        # Determine model name
        default_model = "embedding-3" if "bigmodel" in base_url else "text-embedding-3-small"
        model_name = os.getenv("EMBEDDING_MODEL", default_model)
        dimension = int(os.getenv("EMBEDDING_DIMENSION", "1024"))

        logger.info(f"ToolRouter Embeddings: base_url='{base_url}', model='{model_name}'")

        if "11434" in base_url:
            from langchain_ollama import OllamaEmbeddings

            ollama_base = base_url.replace("/v1", "")
            self.embeddings = OllamaEmbeddings(
                model=model_name.replace(":latest", ""),
                base_url=ollama_base,
            )
        elif "9292" in base_url:
            from langchain_openai import OpenAIEmbeddings

            self.embeddings = OpenAIEmbeddings(
                model=model_name,
                api_key=api_key,
                base_url=base_url,
                check_embedding_ctx_length=False,
            )
        else:
            from langchain_openai import OpenAIEmbeddings

            self.embeddings = OpenAIEmbeddings(
                model=model_name,
                api_key=api_key,
                base_url=base_url,
                dimensions=dimension if dimension == 1536 else None,
            )

    async def register_tools(self, tools: List[Any]):
        """
        Register all available tools.
        Separates CORE tools from SEMANTIC tools and builds the index.
        """
        self.all_tools = tools
        self.core_tools = []
        self.semantic_tools = []

        semantic_descriptions = []

        for tool in tools:
            # Handle both BaseTool objects and specific function tools
            name = getattr(tool, "name", "")

            if name in CORE_TOOL_NAMES:
                self.core_tools.append(tool)
            else:
                self.semantic_tools.append(tool)
                semantic_descriptions.append(f"{name}: {getattr(tool, 'description', '')}")

        logger.info(f"Registered {len(self.core_tools)} core tools and {len(self.semantic_tools)} semantic tools.")

        if not self.embeddings or not self.semantic_tools:
            logger.warning("Embeddings not ready or no semantic tools. Routing might be disabled.")
            return

        # Pre-compute embeddings for semantic tools
        try:
            if semantic_descriptions:
                logger.info(f"Embedding {len(semantic_descriptions)} tool descriptions...")
                vectors = await self.embeddings.aembed_documents(semantic_descriptions)
                self.tool_index = np.array(vectors)  # Shape: (N, D)
                logger.info("Tool index built successfully.")
        except Exception as e:
            logger.error(f"Failed to build tool index: {e}")
            self.tool_index = None

    async def register_skills(self, skills: List[dict]):
        """
        Register all available skills for semantic routing.
        skills: List of dicts with {name, metadata, rules}
        """
        self.skill_entries = skills
        if not self.embeddings or not skills:
            logger.warning("Embeddings not ready or no skills. Skill routing disabled.")
            return

        descriptions = []
        for s in skills:
            name = s["name"]
            desc = s["metadata"].get("description", "")
            # Domain and intent keywords can also be part of embedding context
            domain = s["metadata"].get("domain", "")
            keywords = ", ".join(s["metadata"].get("intent_keywords", []))
            descriptions.append(f"Skill: {name}\nDescription: {desc}\nDomain: {domain}\nKeywords: {keywords}")

        try:
            logger.info(f"Embedding {len(descriptions)} skill descriptions...")
            vectors = await self.embeddings.aembed_documents(descriptions)
            self.skill_index = np.array(vectors)
            logger.info("Skill index built successfully.")
        except Exception as e:
            logger.error(f"Failed to build skill index: {e}")
            self.skill_index = None

    def _check_role(self, tool: Any, user_role: str) -> bool:
        """Check if user has permission to use this tool."""
        # 1. Check tool.required_role (pydantic/langchain attribute)
        req_role = getattr(tool, "required_role", None)

        # 2. Check tool.func.required_role (decorator attribute)
        if not req_role and hasattr(tool, "func"):
            req_role = getattr(tool.func, "required_role", None)

        # Default to "user" if not specified
        if not req_role:
            req_role = "user"

        # Admin can access everything
        if user_role == "admin":
            return True

        # User cannot access admin tools
        if req_role == "admin" and user_role != "admin":
            return False

        return True

    async def route_skills(self, query: str, role: str = "user") -> List[dict]:
        """
        Select relevant skills based on query and user role.
        Returns: List of skill entries matched by semantic similarity.
        """
        if not settings.ENABLE_SEMANTIC_ROUTING or self.skill_index is None or not self.embeddings:
            return []

        if not query or not query.strip():
            return []

        try:
            # Embed query (re-use logic or cache if possible layer, but here we just embed)
            # In a real high-perf scenario, we might pass the embedding in.
            query_vec = await self.embeddings.aembed_query(query)
            query_vec = np.array(query_vec)

            # Cosine Similarity
            norm_skills = np.linalg.norm(self.skill_index, axis=1)
            norm_query = np.linalg.norm(query_vec)

            if norm_query == 0:
                return []

            # Avoid division by zero
            norm_skills[norm_skills == 0] = 1e-9

            scores = np.dot(self.skill_index, query_vec) / (norm_skills * norm_query)

            # Select Top-K
            k = min(settings.SKILL_ROUTING_TOP_K, len(self.skill_entries))
            threshold = settings.SKILL_ROUTING_THRESHOLD

            top_indices = np.argsort(scores)[-k:][::-1]

            selected_skills = []
            _wire_log = os.getenv("DEBUG_WIRE_LOG", "false").lower() == "true"

            for idx in top_indices:
                score = scores[idx]
                skill = self.skill_entries[idx]

                # Role Check for Skills
                req_role = skill["metadata"].get("required_role", "user")
                if req_role == "admin" and role != "admin":
                    continue

                if score >= threshold:
                    selected_skills.append(skill)
                    logger.debug(f"Skill Match: {skill['name']} (score={score:.4f})")
                    if _wire_log:
                        print(f"  │   │  ├─ [SKILL MATCH] {skill['name']:<20} (scale={score:.4f})")
                else:
                    if _wire_log:
                        print(f"  │   │  ├─ [SKILL DROP]  {skill['name']:<20} (scale={score:.4f})")

            return selected_skills

        except Exception as e:
            logger.error(f"Skill routing failed: {e}")
            return []

    async def route(self, query: str, role: str = "user") -> List[Any]:
        """
        Select relevant tools based on query and user role.
        Returns: Core Tools + Top-K Semantic Tools
        """
        # If disabled or not ready, return all ALLOWED tools
        if not settings.ENABLE_SEMANTIC_ROUTING or self.tool_index is None or not self.embeddings:
            return [t for t in self.all_tools if self._check_role(t, role)]

        if not query or not query.strip():
            return [t for t in self.core_tools if self._check_role(t, role)]

        try:
            # Embed query
            query_vec = await self.embeddings.aembed_query(query)
            query_vec = np.array(query_vec)

            # Cosine Similarity: (A . B) / (|A| * |B|)
            # Assuming normalized embeddings from models usually, but let's be safe
            norm_tools = np.linalg.norm(self.tool_index, axis=1)
            norm_query = np.linalg.norm(query_vec)

            if norm_query == 0:
                return [t for t in self.core_tools if self._check_role(t, role)]

            # dot product
            scores = np.dot(self.tool_index, query_vec) / (norm_tools * norm_query)

            # Select Top-K
            k = min(settings.ROUTING_TOP_K, len(self.semantic_tools))
            threshold = settings.ROUTING_THRESHOLD

            # Get indices of top K scorers
            # np.argsort returns ascending, so take last k and reverse
            top_indices = np.argsort(scores)[-k:][::-1]

            selected_semantic = []
            _wire_log = os.getenv("DEBUG_WIRE_LOG", "false").lower() == "true"

            for idx in top_indices:
                score = scores[idx]
                tool = self.semantic_tools[idx]

                # Check Permissions FIRST
                if not self._check_role(tool, role):
                    continue

                # Filter by threshold (optional, or just take top K)
                # We log matches to see performance
                if score >= threshold:
                    selected_semantic.append(tool)
                    logger.debug(f"Route Match: {tool.name} (score={score:.4f})")
                    if _wire_log:
                        print(f"  │   │  ├─ [MATCH] {tool.name:<25} (score={score:.4f})")
                else:
                    logger.debug(f"Route Drop: {tool.name} (score={score:.4f} < {threshold})")
                    if _wire_log:
                        print(f"  │   │  ├─ [DROP]  {tool.name:<25} (score={score:.4f})")

            # Always return core tools + selected (filtered by role)
            final_core = [t for t in self.core_tools if self._check_role(t, role)]
            final_tools = final_core + selected_semantic

            # Deduplicate by name just in case
            unique_tools = {getattr(t, "name", str(t)): t for t in final_tools}
            return list(unique_tools.values())

        except Exception as e:
            logger.error(f"Routing failed: {e}")
            # Fallback: return all ALLOWED tools
            return [t for t in self.all_tools if self._check_role(t, role)]


tool_router = SemanticToolRouter()
