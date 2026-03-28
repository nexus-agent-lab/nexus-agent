from app.core.skill_routing_store import SkillRoutingStore


def test_build_anchor_payloads_uses_description_keywords_and_examples():
    payloads = SkillRoutingStore.build_anchor_payloads(
        {
            "name": "web_browsing",
            "metadata": {
                "description": "Browse public websites",
                "intent_keywords": ["browse", "website"],
                "routing_examples": ["帮我查一下最新论文", "打开这个网页看看"],
            },
        }
    )

    assert len(payloads) == 5
    assert any(item["anchor_type"] == "description" for item in payloads)
    assert any(item["anchor_type"] == "keyword" and item["text"] == "browse" for item in payloads)
    assert any(item["anchor_type"] == "synthetic_query" and item["text"] == "帮我查一下最新论文" for item in payloads)


def test_aggregate_hits_groups_by_skill_name():
    aggregated = SkillRoutingStore.aggregate_hits(
        [
            {"skill_name": "web_browsing", "weighted_score": 0.91},
            {"skill_name": "web_browsing", "weighted_score": 0.88},
            {"skill_name": "homeassistant", "weighted_score": 0.72},
        ]
    )

    assert aggregated[0]["skill_name"] == "web_browsing"
    assert aggregated[0]["score"] > aggregated[1]["score"]
