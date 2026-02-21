from unittest.mock import AsyncMock

import pytest

from app.core.tool_router import SemanticToolRouter


@pytest.mark.asyncio
async def test_skill_routing_logic():
    # 1. Setup
    router = SemanticToolRouter()
    router._initialized = True
    router.embeddings = AsyncMock()

    # Mock Embeddings
    # Suppose we have 3 skills: [HomeAssistant, PythonSandbox, Memory]
    # And query is "Turn on light".
    # We'll mock return values for aembed_documents (indexing) and aembed_query (searching).

    # Mock Vectors (Dimension 3 for simplicity)
    # Skill 0 (HA): [1, 0, 0]
    # Skill 1 (Python): [0, 1, 0]
    # Skill 2 (Memory): [0, 0, 1]

    router.embeddings.aembed_documents.return_value = [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]

    skills = [
        {
            "name": "home_assistant",
            "metadata": {"description": "Control smart home", "domain": "iot"},
            "rules": "rule1",
        },
        {"name": "python_sandbox", "metadata": {"description": "Run python code", "domain": "dev"}, "rules": "rule2"},
        {"name": "memory", "metadata": {"description": "Manage memory", "domain": "system"}, "rules": "rule3"},
    ]

    # 2. Register
    await router.register_skills(skills)

    assert router.skill_index is not None
    assert len(router.skill_entries) == 3

    # 3. Route (Match HomeAssistant)
    # Query: "Turn on light" -> Vector similar to HA
    # Let's say query embedding is [0.9, 0.1, 0.0]
    router.embeddings.aembed_query.return_value = [0.9, 0.1, 0.0]

    # Threshold check
    # Score for HA = (1*0.9 + 0*0.1) = 0.9. > 0.30 (default threshold).
    # Score for Python = (0*0.9 + 1*0.1) = 0.1. < 0.30.

    results = await router.route_skills("Turn on light", role="user")

    assert len(results) >= 1
    assert results[0]["name"] == "home_assistant"

    # 4. Route (No Match)
    # Query: "Random noise" -> Orthogonal/Negative
    # Use negative matching to ensure score < 0.30
    router.embeddings.aembed_query.return_value = [-0.5, -0.5, -0.5]

    results = await router.route_skills("noise", role="user")
    # Should get nothing if threshold is 0.30
    # 0.1 < 0.30
    assert len(results) == 0


@pytest.mark.asyncio
async def test_skill_routing_permissions():
    router = SemanticToolRouter()
    router._initialized = True
    router.embeddings = AsyncMock()

    # Mock Vectors
    router.embeddings.aembed_documents.return_value = [[1.0, 0.0]]

    skills = [
        {
            "name": "admin_skill",
            "metadata": {"description": "Delete database", "required_role": "admin"},
            "rules": "danger",
        }
    ]

    await router.register_skills(skills)

    # Query matches perfectly
    router.embeddings.aembed_query.return_value = [1.0, 0.0]

    # User role -> Should NOT get skill
    results = await router.route_skills("delete db", role="user")
    assert len(results) == 0

    # Admin role -> Should GET skill
    results_admin = await router.route_skills("delete db", role="admin")
    assert len(results_admin) == 1
    assert results_admin[0]["name"] == "admin_skill"
