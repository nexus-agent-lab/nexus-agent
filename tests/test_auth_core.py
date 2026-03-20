import jwt
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app.core.auth import get_current_user
from app.models.user import User


def _build_test_app():
    app = FastAPI()

    @app.get("/protected")
    async def protected_route(current_user: User = Depends(get_current_user)):
        return {"user_id": current_user.id, "role": current_user.role}

    return app


class TestCurrentUserAuth:
    def test_get_current_user_accepts_bearer_token(self, test_user):
        app = _build_test_app()
        client = TestClient(app)

        token = jwt.encode(
            {
                "sub": str(test_user.id),
                "username": test_user.username,
                "role": test_user.role,
                "exp": 4102444800,
            },
            "super-secret-default-key-1234",
            algorithm="HS256",
        )

        response = client.get("/protected", headers={"Authorization": f"Bearer {token}"})

        assert response.status_code == 200
        assert response.json()["user_id"] == test_user.id

    def test_get_current_user_rejects_invalid_bearer_token(self, test_user):
        app = _build_test_app()
        client = TestClient(app)

        response = client.get("/protected", headers={"Authorization": "Bearer not-a-real-token"})

        assert response.status_code == 401
        assert response.json()["detail"] == "Invalid bearer token"

    def test_get_current_user_still_accepts_api_key(self, test_user):
        app = _build_test_app()
        client = TestClient(app)

        response = client.get("/protected", headers={"X-API-Key": test_user.api_key})

        assert response.status_code == 200
        assert response.json()["user_id"] == test_user.id
