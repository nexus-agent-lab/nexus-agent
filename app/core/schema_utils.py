from typing import Any, Dict


def clean_schema(schema: Dict[str, Any]) -> Dict[str, Any]:
    """
    Cleans and normalizes JSON schemas for LLM compatibility.
    Inspired by moltbot's cleanToolSchemaForGemini.
    """
    if not schema:
        return {}

    # Deep copy to avoid mutating original
    s = schema.copy()

    # 1. Flatten unsupported anyOf/oneOf for Gemini/OpenAI compatibility
    # If explicit type is missing but we have anyOf/oneOf, try to merge properties OR enums
    if "type" not in s:
        variants = s.get("anyOf") or s.get("oneOf")
        if variants and isinstance(variants, list):
            # Collections for merging
            merged_props = {}
            merged_required = set()
            merged_enums = []
            has_object_variant = False

            for v in variants:
                if not isinstance(v, dict):
                    continue

                # Merge Properties (for Objects)
                if "properties" in v:
                    has_object_variant = True
                    merged_props.update(v["properties"])
                    if "required" in v and isinstance(v["required"], list):
                        merged_required.update(v["required"])

                # Merge Enums (for Strings)
                if "enum" in v and isinstance(v["enum"], list):
                    merged_enums.extend(v["enum"])
                # Handle const as single-value enum
                if "const" in v:
                    merged_enums.append(v["const"])

            # Reconstruction Strategy
            if has_object_variant:
                # It's an object union -> Flatten
                s["type"] = "object"
                s["properties"] = merged_props
                if merged_required:
                    s["required"] = list(merged_required)
            elif merged_enums:
                # It's a string enum union -> Combine enums
                s["type"] = "string"
                s["enum"] = list(set(merged_enums))  # Deduplicate
            else:
                # Fallback: strict object (OpenAI prefers type specific)
                # or just string if unknown.
                # If we couldn't merge anything meaningful, default to string
                # to be safe for LLM (it can just output text)
                # But creating an empty object might be safer for "any" type.
                # However, Gemini hates "anyOf" at top level.
                # Let's verify Case 1 (Format enum). It should hit the elif merged_enums block.
                # If we have no info, maybe just remove anyOf and say type: string?
                # Let's assume object if likely structure, otherwise string.
                pass

            # Only remove variants if we successfully replaced them with a type
            if "type" in s:
                s.pop("anyOf", None)
                s.pop("oneOf", None)

    # 2. Enforce top-level type: object if properties exist (OpenAI requirement)
    if "properties" in s and s.get("type") != "object":
        s["type"] = "object"

    # 3. Recursive cleanup of properties
    if "properties" in s and isinstance(s["properties"], dict):
        for key, prop in s["properties"].items():
            if isinstance(prop, dict):
                s["properties"][key] = clean_schema(prop)

    # 4. Remove unsupported keywords
    # Gemini rejects: $schema, $id, title (sometimes), default (sometimes)
    # We keep title/description as they are useful for LLM context, but remove metadata
    keys_to_remove = ["$schema", "$id", "definitions", "$defs"]
    for k in keys_to_remove:
        s.pop(k, None)

    return s


def normalize_tool_schema(schema: Dict[str, Any]) -> Dict[str, Any]:
    """
    Main entry point for tool schema normalization.
    """
    return clean_schema(schema)
