from app.core.intent_gate import IntentGate


def test_intent_gate_uses_skill_hints_for_skill_worker():
    gate = IntentGate()
    decision = gate.classify_fast(
        "打开客厅的灯",
        available_skills=[
            {
                "skill_name": "homeassistant",
                "keywords": ["灯", "空调", "实体"],
                "discovery_keywords": ["列出设备"],
                "preferred_worker": "skill_worker",
            }
        ],
    )

    assert decision["intent_class"] == "skill_execution"
    assert decision["candidate_workers"] == ["skill_worker"]
    assert decision["candidate_skills"] == ["homeassistant"]
    assert decision["needs_llm_escalation"] is False


def test_intent_gate_routes_code_requests_to_code_worker():
    gate = IntentGate()
    decision = gate.classify_fast("把这段 JSON 过滤出 active=true 的项")

    assert "code_worker" in decision["candidate_workers"]
    assert decision["intent_class"] == "code_execution"


def test_intent_gate_marks_mixed_requests_for_escalation():
    gate = IntentGate()
    decision = gate.classify_fast(
        "打开客厅灯并且分析这个 JSON",
        available_skills=[
            {
                "skill_name": "homeassistant",
                "keywords": ["灯"],
                "discovery_keywords": [],
                "preferred_worker": "skill_worker",
            }
        ],
    )

    assert "skill_worker" in decision["candidate_workers"]
    assert "code_worker" in decision["candidate_workers"]
    assert decision["needs_llm_escalation"] is True
