import unittest

from app.core.schema_utils import clean_schema


class TestSchemaUtils(unittest.TestCase):
    def test_flatten_literals(self):
        schema = {"anyOf": [{"const": "A"}, {"const": "B"}]}
        cleaned = clean_schema(schema)
        self.assertEqual(cleaned, {"type": "string", "enum": ["A", "B"]})

    def test_remove_unsupported(self):
        schema = {
            "type": "object",
            "properties": {"foo": {"type": "string"}},
            "additionalProperties": False,
            "title": "Useless Title",
        }
        cleaned = clean_schema(schema)
        self.assertNotIn("additionalProperties", cleaned)
        self.assertNotIn("title", cleaned)
        self.assertIn("properties", cleaned)

    def test_nested_anyof(self):
        schema = {"properties": {"action": {"anyOf": [{"const": "turn_on"}, {"const": "turn_off"}]}}}
        cleaned = clean_schema(schema)
        self.assertEqual(cleaned["properties"]["action"], {"type": "string", "enum": ["turn_on", "turn_off"]})


if __name__ == "__main__":
    unittest.main()
