import pytest

from app.models.plugin import Plugin


async def _create_plugin(session, **kwargs) -> Plugin:
    plugin = Plugin(
        name=kwargs.get("name", "Web Browser"),
        type=kwargs.get("type", "mcp"),
        source_url=kwargs.get("source_url", "http://mcp-playwright:3000/mcp"),
        manifest_id=kwargs.get("manifest_id"),
        status="active",
        config={},
        required_role="user",
        allowed_groups=[],
    )
    session.add(plugin)
    await session.commit()
    await session.refresh(plugin)
    return plugin


@pytest.mark.asyncio
async def test_get_plugin_skill_falls_back_to_source_url(api_client, test_db, admin_user, mocker):
    plugin = await _create_plugin(test_db, manifest_id=None)

    mocker.patch(
        "app.api.plugins._load_plugin_catalog",
        return_value=[
            {
                "id": "official/playwright",
                "source_url": "http://mcp-playwright:3000/mcp",
                "bundled_skills": ["web_browsing"],
            }
        ],
    )
    mocker.patch("app.api.plugins.SkillLoader.load_by_name", return_value="# Web Browsing Skill")
    mocker.patch(
        "app.api.plugins.SkillLoader._extract_metadata",
        return_value={"description": "Browse the web", "domain": "web"},
    )

    response = api_client.get(f"/api/plugins/{plugin.id}/skill", headers={"X-API-Key": "admin_key"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["skill_name"] == "web_browsing"
    assert payload["content"] == "# Web Browsing Skill"
    assert payload["metadata"]["domain"] == "web"


@pytest.mark.asyncio
async def test_get_plugin_schema_falls_back_to_source_url(api_client, test_db, admin_user, mocker):
    plugin = await _create_plugin(test_db, manifest_id=None)

    mocker.patch(
        "app.api.plugins._load_plugin_catalog",
        return_value=[
            {
                "id": "official/playwright",
                "source_url": "http://mcp-playwright:3000/mcp",
                "bundled_skills": ["web_browsing"],
                "env_schema": {"PLAYWRIGHT_HEADLESS": {"type": "text"}},
            }
        ],
    )

    response = api_client.get(f"/api/plugins/{plugin.id}/schema", headers={"X-API-Key": "admin_key"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["bundled_skills"] == ["web_browsing"]
    assert payload["env_schema"] == {"PLAYWRIGHT_HEADLESS": {"type": "text"}}
