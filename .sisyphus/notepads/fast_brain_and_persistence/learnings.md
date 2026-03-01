- Implemented robust singleton pattern using __new__ to set _initialized flag to avoid re-initialization of LLM client across multiple instantiations of IntentRouter.
- Used temperature=0.1 for LLM intent decomposition to get strict JSON while accommodating models like glm4.7-flash.
- Extracted markdown code block removal logic for robust JSON parsing from LLM output.

### Multi-Query Tool Routing Pattern
- Implemented `route_multi` in `tool_router.py` to handle batch query processing.
- Uses `aembed_documents` for efficient batch embedding of multiple queries.
- Merges results across queries using **max-score deduplication**: for each tool, its maximum score among all query matches is used.
- Maintains consistency with single-query `route` logic (role checks, domain affinity, threshold filtering, core tool injection).
- Efficiently calculates similarity using matrix multiplication: `np.dot(query_vecs, self.tool_index.T) / np.outer(norm_queries, norm_tools)`.
Learned that the IntentRouter is initialized as a singleton using IntentRouter() and decompose returns a list of strings.
- Implemented TraceLogger in `app/core/trace_logger.py` using an async session and deferred imports to avoid circular dependencies.
- Implemented `/config` to persist settings to the database (`SystemSetting`), rather than just `os.environ`, giving persistence to Admin config settings. Added an LLM traces readout endpoint (`/traces`).
- System-wide integration of Fast Brain and persistent LLM traces verified successfully.
- IntentRouter decompose method changed to async, utilizing ainvoke instead of invoke, solving an issue where it would block the main event loop.
