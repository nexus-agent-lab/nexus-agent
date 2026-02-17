
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
        self.tool_index = None  # numpy array of embeddings
        self.semantic_tools: List[BaseTool] = []
        self.core_tools: List[BaseTool] = []
        self.all_tools: List[BaseTool] = []

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

    async def route(self, query: str) -> List[Any]:
        """
        Select relevant tools based on query.
        Returns: Core Tools + Top-K Semantic Tools
        """
        # If disabled or not ready, return all tools (safe fallback)
        if not settings.ENABLE_SEMANTIC_ROUTING or self.tool_index is None or not self.embeddings:
            return self.all_tools

        if not query or not query.strip():
            return self.core_tools

        try:
            # Embed query
            query_vec = await self.embeddings.aembed_query(query)
            query_vec = np.array(query_vec)

            # Cosine Similarity: (A . B) / (|A| * |B|)
            # Assuming normalized embeddings from models usually, but let's be safe
            norm_tools = np.linalg.norm(self.tool_index, axis=1)
            norm_query = np.linalg.norm(query_vec)

            if norm_query == 0:
                return self.core_tools

            # dot product
            scores = np.dot(self.tool_index, query_vec) / (norm_tools * norm_query)

            # Select Top-K
            k = min(settings.ROUTING_TOP_K, len(self.semantic_tools))
            threshold = settings.ROUTING_THRESHOLD

            # Get indices of top K scorers
            # np.argsort returns ascending, so take last k and reverse
            top_indices = np.argsort(scores)[-k:][::-1]

            selected_semantic = []
            for idx in top_indices:
                score = scores[idx]
                tool = self.semantic_tools[idx]

                # Filter by threshold (optional, or just take top K)
                # We log matches to see performance
                _wire_log = os.getenv("DEBUG_WIRE_LOG", "false").lower() == "true"
                
                if score >= threshold:
                    selected_semantic.append(tool)
                    logger.debug(f"Route Match: {tool.name} (score={score:.4f})")
                    if _wire_log:
                        print(f"  │   │  ├─ [MATCH] {tool.name:<25} (score={score:.4f})")
                else:
                    logger.debug(f"Route Drop: {tool.name} (score={score:.4f} < {threshold})")
                    if _wire_log:
                         print(f"  │   │  ├─ [DROP]  {tool.name:<25} (score={score:.4f})")

            # Always return core tools + selected
            final_tools = self.core_tools + selected_semantic

            # Deduplicate by name just in case
            unique_tools = {getattr(t, "name", str(t)): t for t in final_tools}
            return list(unique_tools.values())

        except Exception as e:
            logger.error(f"Routing failed: {e}")
            return self.all_tools

tool_router = SemanticToolRouter()
