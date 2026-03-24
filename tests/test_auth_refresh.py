import jwt

from app.api.auth import ACCESS_TOKEN_EXPIRE_SECONDS
from app.core.security import get_jwt_secret


class TestRefreshAccessToken:
    def test_refresh_requires_authentication(self, api_client):
        response = api_client.post("/api/auth/refresh")

        assert response.status_code == 401

    def test_refresh_issues_new_bearer_token(self, api_client, test_user):
        token = jwt.encode(
            {
                "sub": str(test_user.id),
                "username": test_user.username,
                "role": test_user.role,
                "exp": 4102444800,
            },
            get_jwt_secret(),
            algorithm="HS256",
        )

        response = api_client.post("/api/auth/refresh", headers={"Authorization": f"Bearer {token}"})

        assert response.status_code == 200
        payload = response.json()
        assert payload["token_type"] == "bearer"
        assert payload["expires_in"] == ACCESS_TOKEN_EXPIRE_SECONDS
        assert payload["user"]["id"] == test_user.id
        assert isinstance(payload["access_token"], str)
