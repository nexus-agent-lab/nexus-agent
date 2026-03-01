with open("app/core/tool_router.py", "r") as f:
    content = f.read()

# Replace DOMAIN_ADJACENCY
domain_adj_str = """DOMAIN_ADJACENCY = {
    "home": {"smart_home", "home", "iot", "ha", "home_assistant"},
    "system": {"system", "admin", "coding", "debug", "standard"},
    "work": {"communication", "office", "feishu", "lark", "dingtalk", "lark_feishu"},
}"""
content = content.replace(domain_adj_str, "")

# Replace _domain_multiplier
old_mult = '''    def _domain_multiplier(self, tool: Any, current_context: str) -> float:
        """Calculate domain affinity multiplier."""
        if not current_context or current_context == "home":
            # Default to no penalty in home context, but boost same-domain
            context_family = DOMAIN_ADJACENCY.get("home", {"home"})
        else:
            context_family = DOMAIN_ADJACENCY.get(current_context, {current_context})

        tool_domain = self._get_domain(tool).lower()

        if tool_domain in context_family:
            return DOMAIN_AFFINITY["same"]

        # Check for adjacency
        for family_domains in DOMAIN_ADJACENCY.values():
            if current_context in family_domains and tool_domain in family_domains:
                return DOMAIN_AFFINITY["adjacent"]

        return DOMAIN_AFFINITY["cross"]'''

new_mult = '''    def _domain_multiplier(self, tool: Any, current_context: str) -> float:
        """Calculate domain affinity multiplier based on plugin-declared tags."""
        metadata = getattr(tool, "metadata", {}) or {}
        tags = metadata.get("context_tags", [])

        if not current_context or current_context == "home":
            current_context = "home"

        if current_context in tags:
            return DOMAIN_AFFINITY["same"]

        return DOMAIN_AFFINITY["cross"]'''

content = content.replace(old_mult, new_mult)

# Replace discovery injection logic
old_discovery = """            # Boundary Heuristic Loading (Tier 1)
            # If any tool from a plugin is hit, include its discovery tools (prefix get_, list_, search_)
            discovery_tools = []
            hit_domains = set()
            for tool, adj_score, _, _ in top_results:
                if adj_score >= threshold:
                    domain = self._get_domain(tool)
                    if domain and domain != "standard":
                        hit_domains.add(domain)

            if hit_domains:
                for tool in self.semantic_tools:
                    domain = self._get_domain(tool)
                    if domain in hit_domains:
                        name = tool.name.lower()
                        # Discovery prefixes
                        if name.startswith(("get_", "list_", "search_", "read_", "query_")):
                            if tool not in [tr[0] for tr in top_results]:
                                discovery_tools.append(tool)

            # Limit discovery tools to avoid token bloat
            if len(discovery_tools) > 5:
                discovery_tools = discovery_tools[:5]"""

new_discovery = """            # Context-Aware Discovery Injection
            # Always ensure discovery tools for the CURRENT context are available, bypassing vector search
            discovery_tools = []
            for tool in self.semantic_tools:
                metadata = getattr(tool, "metadata", {}) or {}
                tags = metadata.get("context_tags", [])
                if context in tags:
                    name = getattr(tool, "name", "").lower()
                    if name.startswith(("get_", "list_", "search_", "read_", "query_")):
                        if tool not in [tr[0] for tr in top_results]:
                            discovery_tools.append(tool)

            # Limit discovery tools to avoid token bloat
            if len(discovery_tools) > 5:
                discovery_tools = discovery_tools[:5]"""

content = content.replace(old_discovery, new_discovery)

with open("app/core/tool_router.py", "w") as f:
    f.write(content)

print("Replaced tool_router logic via script")
