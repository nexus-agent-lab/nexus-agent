import logging
from typing import Any, Dict, List, Optional, Set, Union

logger = logging.getLogger(__name__)

# Keywords that are often redundant or unsupported by some LLMs
UNSUPPORTED_KEYWORDS = {
    "patternProperties",
    "additionalProperties",
    "$schema",
    "$id",
    "$ref",
    "$defs",
    "definitions",
    "examples",
    "title",  # Often redundant if description is present
    "minLength",
    "maxLength",
    "minItems",
    "maxItems",
    "uniqueItems",
    "minProperties",
    "maxProperties",
    "pattern",
    "format",
    "multipleOf",
}

def clean_schema(schema: Any) -> Any:
    """
    Recursively cleans and simplifies a JSON schema.
    - Flattens anyOf/oneOf with single options or literals.
    - Removes unsupported or redundant keywords.
    """
    if not isinstance(schema, dict):
        if isinstance(schema, list):
            return [clean_schema(item) for item in schema]
        return schema

    cleaned: Dict[str, Any] = {}

    # 1. Handle anyOf/oneOf flattening
    if "anyOf" in schema:
        flattened = try_flatten_anyof(schema["anyOf"])
        if flattened:
            cleaned.update(flattened)
        else:
            # Recursively clean variants
            cleaned["anyOf"] = [clean_schema(v) for v in schema["anyOf"]]
            
    elif "oneOf" in schema:
        flattened = try_flatten_anyof(schema["oneOf"])
        if flattened:
            cleaned.update(flattened)
        else:
            cleaned["oneOf"] = [clean_schema(v) for v in schema["oneOf"]]

    # 2. Process other properties
    for key, value in schema.items():
        if key in UNSUPPORTED_KEYWORDS:
            continue
        
        # Skip if we already handled it (e.g., via flattening)
        if key in ("anyOf", "oneOf") and (key in cleaned or "type" in cleaned):
            continue

        if key == "properties" and isinstance(value, dict):
            cleaned[key] = {
                k: clean_schema(v) for k, v in value.items()
            }
        elif key == "items":
            cleaned[key] = clean_schema(value)
        elif key == "allOf" and isinstance(value, list):
            cleaned[key] = [clean_schema(v) for v in value]
        else:
            # Copy primitive values or recurse if needed
            cleaned[key] = clean_schema(value) if isinstance(value, (dict, list)) else value

    # 3. Ensure type is present if enum is present (helper)
    if "enum" in cleaned and "type" not in cleaned:
        # Infer type from enum values
        if all(isinstance(x, str) for x in cleaned["enum"]):
            cleaned["type"] = "string"
        elif all(isinstance(x, (int, float)) for x in cleaned["enum"]):
            cleaned["type"] = "number"

    return cleaned

def try_flatten_anyof(variants: List[Any]) -> Optional[Dict[str, Any]]:
    """
    Tries to flatten a list of anyOf/oneOf variants into a single simple schema.
    Especially useful for:
    - {anyOf: [{const: "A"}, {const: "B"}]} -> {type: "string", enum: ["A", "B"]}
    - {anyOf: [{type: "string"}, {type: "null"}]} -> {type: "string"} (nullable implied)
    - {anyOf: [{type: "string"}, {type: "array"}]} -> {type: "string"} (take first non-null)
    """
    if not variants:
        return None

    # Filter out nulls
    non_null_variants = [
        v for v in variants 
        if not is_null_schema(v)
    ]

    # If everything was null (unlikely), return null type
    if not non_null_variants:
        return {"type": "null"}

    # Case 1: All variants are literals (const or enum with 1 item)
    all_values = []
    all_literals = True
    common_type = None

    for v in non_null_variants:
        if not isinstance(v, dict):
            all_literals = False
            break
        
        val = None
        if "const" in v:
            val = v["const"]
        elif "enum" in v and isinstance(v["enum"], list) and len(v["enum"]) == 1:
            val = v["enum"][0]
        else:
            # Not a literal, cannot flatten this way
            all_literals = False
            break
        
        # Check type consistency
        current_type = get_type_of_value(val)
        if common_type is None:
            common_type = current_type
        elif common_type != current_type:
             # Mixed types (e.g. string and int)
             all_literals = False
             break
        
        all_values.append(val)
    
    # If we successfully collected literal values, return as enum
    if all_literals and all_values and common_type:
        return {"type": common_type, "enum": all_values}

    # Case 2: Single non-null variant (e.g. string | null)
    if len(non_null_variants) == 1:
        return clean_schema(non_null_variants[0])

    # Case 3: Multiple type variants (e.g., string | array)
    # Strategy: Take the FIRST non-null variant to simplify
    # This is a pragmatic choice for LLM compatibility
    # For example: {anyOf: [{type: "string"}, {type: "array"}]} -> {type: "string"}
    logger.debug(f"Flattening anyOf by taking first variant from {len(non_null_variants)} options")
    return clean_schema(non_null_variants[0])

def is_null_schema(schema: Any) -> bool:
    """Check if a schema represents 'null'."""
    if not isinstance(schema, dict):
        return False
    if schema.get("type") == "null":
        return True
    if "const" in schema and schema["const"] is None:
        return True
    if "enum" in schema and schema["enum"] == [None]:
        return True
    return False

def get_type_of_value(val: Any) -> str:
    if isinstance(val, str):
        return "string"
    if isinstance(val, (int, float)) and not isinstance(val, bool):
        return "number"
    if isinstance(val, bool):
        return "boolean"
    if val is None:
        return "null"
    return "object"
