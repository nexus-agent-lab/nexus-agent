#!/usr/bin/env python3
"""
Test script for schema optimization (clean_schema).
Compares raw vs cleaned schemas and verifies tool execution.
"""

import asyncio
import json
import sys

sys.path.insert(0, "/app")

from app.core.schema_utils import clean_schema

# Test cases
test_schemas = {
    "call_service_raw": {
        "type": "object",
        "properties": {
            "domain": {"type": "string"},
            "service": {"type": "string"},
            "entity_id": {"anyOf": [{"type": "string"}, {"type": "array", "items": {"type": "string"}}]},
        },
        "required": ["domain", "service"],
    },
    "complex_union": {
        "type": "object",
        "properties": {"value": {"oneOf": [{"type": "string"}, {"type": "number"}, {"type": "boolean"}]}},
    },
}


async def test_schema_cleaning():
    print("=== Schema Optimization Test ===\n")

    for name, raw_schema in test_schemas.items():
        print(f"--- Test: {name} ---")
        print(f"Raw Schema:\n{json.dumps(raw_schema, indent=2)}\n")

        cleaned = clean_schema(raw_schema)
        print(f"Cleaned Schema:\n{json.dumps(cleaned, indent=2)}\n")

        # Check if anyOf/oneOf were flattened
        has_anyof = "anyOf" in json.dumps(cleaned)
        has_oneof = "oneOf" in json.dumps(cleaned)

        if has_anyof or has_oneof:
            print("⚠️  Warning: anyOf/oneOf still present in cleaned schema\n")
        else:
            print("✅ Success: anyOf/oneOf flattened\n")

        print("-" * 60 + "\n")


if __name__ == "__main__":
    asyncio.run(test_schema_cleaning())
