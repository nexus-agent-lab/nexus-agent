from app.core.audit import mask_secrets


def test_mask_secrets():
    """Test recursive masking of sensitive keys."""
    data = {
        "user_id": 1,
        "api_key": "sk-12345",
        "nested": {"password": "my_password", "safe": "data"},
        "list": [{"token": "abc"}, {"other": "xyz"}],
    }

    masked = mask_secrets(data)

    assert masked["user_id"] == 1
    assert masked["api_key"] == "********"
    assert masked["nested"]["password"] == "********"
    assert masked["nested"]["safe"] == "data"
    assert masked["list"][0]["token"] == "********"
    assert masked["list"][1]["other"] == "xyz"


def test_mask_secrets_empty():
    assert mask_secrets(None) is None
    assert mask_secrets({}) == {}
    assert mask_secrets([]) == []
