from app.api.plugins import _get_bundled_skills_for_plugin
from app.models.plugin import Plugin


def test_get_bundled_skills_for_plugin_matches_manifest_id():
    plugin = Plugin(id=1, name="Web Browser", type="mcp", source_url="http://mcp-playwright:3000/mcp")
    plugin.manifest_id = "official/playwright"
    catalog = [
        {
            "id": "official/playwright",
            "source_url": "http://mcp-playwright:3000/mcp",
            "bundled_skills": ["web_browsing"],
        }
    ]

    assert _get_bundled_skills_for_plugin(plugin, catalog) == ["web_browsing"]


def test_get_bundled_skills_for_plugin_falls_back_to_source_url():
    plugin = Plugin(id=2, name="Home Assistant", type="mcp", source_url="http://mcp-homeassistant:8080/sse")
    catalog = [
        {
            "id": "official/homeassistant",
            "source_url": "http://mcp-homeassistant:8080/sse",
            "bundled_skills": ["homeassistant"],
        }
    ]

    assert _get_bundled_skills_for_plugin(plugin, catalog) == ["homeassistant"]
