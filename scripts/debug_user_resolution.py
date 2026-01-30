import asyncio
import os
import sys

# Add project root to path
sys.path.append(os.getcwd())

from sqlmodel import select

from app.core.auth_service import AuthService
from app.core.db import get_session
from app.models.user import User, UserIdentity


async def main():
    print("--- Debugging User Resolution ---")

    # 1. Dump All Users
    print("\n[USERS TABLE]")
    async for session in get_session():
        users = await session.execute(select(User))
        for u in users.scalars().all():
            print(f"ID: {u.id}, Username: {u.username}, Role: {u.role}, API Key: {u.api_key}, Lang: {u.language}")

    # 2. Dump All Identities
    print("\n[IDENTITIES TABLE]")
    async for session in get_session():
        ids = await session.execute(select(UserIdentity))
        for i in ids.scalars().all():
            print(
                f"ID: {i.id}, UserID: {i.user_id}, Provider: {i.provider}, ProviderID: {i.provider_user_id}, Username: {i.provider_username}"
            )

    # 3. Simulate Resolution for Known IDs
    print("\n[RESOLUTION SIMULATION]")
    test_ids = ["999888777", "228514831", "999999", "888888"]
    for pid in test_ids:
        user = await AuthService.get_user_by_identity("telegram", pid)
        if user:
            print(f"ProviderID {pid} -> RESOLVED: User {user.id} ({user.role})")
        else:
            print(f"ProviderID {pid} -> NOT FOUND")


if __name__ == "__main__":
    asyncio.run(main())
