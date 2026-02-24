import json
import logging
from typing import Optional

from cryptography.fernet import Fernet
from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.core.auth import get_current_user
from app.core.db import get_session
from app.core.security import encrypt_secret
from app.models.secret import Secret, SecretScope
from app.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/secure", tags=["Secure Input"])

# Ephemeral key that resets on every application restart.
# This guarantees that secure links cannot be used across restarts
# and we don't need to depend on NEXUS_MASTER_KEY being set.
EPHEMERAL_FERNET_KEY = Fernet.generate_key()
ephemeral_fernet = Fernet(EPHEMERAL_FERNET_KEY)


def create_secure_token(user_id: int, secret_key: str) -> str:
    """
    Generate an ephemeral, signed token for the user and the specific secret key.
    """
    payload = json.dumps({"user_id": user_id, "key": secret_key}).encode("utf-8")
    return ephemeral_fernet.encrypt(payload).decode("utf-8")


def decode_secure_token(token: str, max_age: int = 600) -> Optional[dict]:
    """
    Decode an ephemeral token, ensuring it hasn't expired.
    Default max_age is 600 seconds (10 minutes).
    """
    try:
        decrypted = ephemeral_fernet.decrypt(token.encode("utf-8"), ttl=max_age)
        return json.loads(decrypted.decode("utf-8"))
    except Exception as e:
        logger.warning(f"Failed to decode secure token: {e}")
        return None


@router.get("/link", response_model=dict)
async def generate_secure_link(
    request: Request,
    secret_key: str,
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    Generate a signed link for inputting a sensitive secret (e.g., BINANCE_KEY).
    The link is valid for 10 minutes.
    """
    token = create_secure_token(current_user.id, secret_key)
    # Return relative or absolute URL. We can construct an absolute URL using request.url_for
    url = str(request.url_for("serve_secure_form", token=token))

    return {
        "url": url,
        "token": token,
        "expires_in_minutes": 10,
        "message": f"Send this link to the user to securely input {secret_key}",
    }


@router.get("/form/{token}", response_class=HTMLResponse)
async def serve_secure_form(token: str) -> HTMLResponse:
    """
    Serve a simple HTML form where the user can securely input their secret.
    The form's action points to /secure/submit/{token}.
    """
    payload = decode_secure_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="The secure link is invalid or has expired."
        )

    secret_key = payload.get("key", "Secret")

    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Secure Input: {secret_key}</title>
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
                background-color: #f5f5f7;
                display: flex;
                justify-content: center;
                align-items: center;
                height: 100vh;
                margin: 0;
            }}
            .container {{
                background: white;
                padding: 40px;
                border-radius: 12px;
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
                max-width: 400px;
                width: 100%;
                text-align: center;
            }}
            h2 {{ color: #1d1d1f; margin-top: 0; }}
            p {{ color: #515154; line-height: 1.5; }}
            input[type="password"] {{
                width: 100%;
                padding: 12px;
                margin: 20px 0;
                border: 1px solid #d2d2d7;
                border-radius: 8px;
                font-size: 16px;
                box-sizing: border-box;
            }}
            button {{
                width: 100%;
                padding: 12px;
                background-color: #007aff;
                color: white;
                border: none;
                border-radius: 8px;
                font-size: 16px;
                cursor: pointer;
                transition: background-color 0.2s;
            }}
            button:hover {{ background-color: #005bb5; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h2>Secure Input</h2>
            <p>Please provide the value for: <strong>{secret_key}</strong></p>
            <form action="/secure/submit/{token}" method="post">
                <input type="password" name="secret_value" required placeholder="Enter secret here..." autocomplete="off">
                <button type="submit">Submit Securely</button>
            </form>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


@router.post("/submit/{token}", response_class=HTMLResponse)
async def submit_secure_form(
    token: str, secret_value: str = Form(...), session: AsyncSession = Depends(get_session)
) -> HTMLResponse:
    """
    Process the submitted secret, encrypt it, and save it to the DB using the user_id embedded in the token.
    """
    payload = decode_secure_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="The secure link is invalid or has expired."
        )

    user_id = payload.get("user_id")
    secret_key = payload.get("key")

    if not user_id or not secret_key:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid token payload.")

    # Encrypt before saving
    encrypted_val = encrypt_secret(secret_value)

    # Check if a secret already exists for this user and key
    stmt = select(Secret).where(
        Secret.owner_id == user_id, Secret.key == secret_key, Secret.scope == SecretScope.user_scope
    )
    result = await session.execute(stmt)
    existing_secret = result.scalars().first()

    if existing_secret:
        existing_secret.encrypted_value = encrypted_val
    else:
        new_secret = Secret(
            key=secret_key, encrypted_value=encrypted_val, scope=SecretScope.user_scope, owner_id=user_id
        )
        session.add(new_secret)

    await session.commit()

    success_html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Success</title>
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
                background-color: #f5f5f7;
                display: flex;
                justify-content: center;
                align-items: center;
                height: 100vh;
                margin: 0;
            }}
            .container {{
                background: white;
                padding: 40px;
                border-radius: 12px;
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
                text-align: center;
                max-width: 400px;
                width: 100%;
            }}
            h2 {{ color: #34c759; margin-top: 0; }}
            p {{ color: #515154; line-height: 1.5; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h2>Success!</h2>
            <p><strong>{secret_key}</strong> has been securely stored.</p>
            <p>You can now close this window and return to your chat.</p>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=success_html)
