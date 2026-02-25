import argparse
import asyncio
import os
import secrets
import sys

# Ensure we can import from app
sys.path.append(os.getcwd())

from app.core.db import AsyncSessionLocal
from sqlmodel import select

from app.models.user import User


async def list_users():
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User))
        users = result.scalars().all()

        print("\n" + "=" * 60)
        print(f"{'ID':<5} | {'Username':<15} | {'Role':<10} | {'API Key'}")
        print("-" * 60)
        for u in users:
            print(f"{u.id:<5} | {u.username:<15} | {u.role:<10} | {u.api_key}")
        print("=" * 60 + "\n")


async def reset_key(username, new_key=None):
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.username == username))
        user = result.scalars().first()

        if not user:
            print(f"❌ Error: User '{username}' not found.")
            return

        final_key = new_key if new_key else secrets.token_urlsafe(16)
        user.api_key = final_key
        await session.commit()
        print(f"✅ API Key for '{username}' has been reset to: {final_key}")


async def main():
    parser = argparse.ArgumentParser(description="Nexus Agent User Management CLI")
    parser.add_argument("--list", action="store_true", help="List all users and their API keys")
    parser.add_argument("--reset", type=str, help="Reset API key for the specified username")
    parser.add_argument("--key", type=str, help="New API key (optional, random if omitted)")

    args = parser.parse_args()

    if args.list:
        await list_users()
    elif args.reset:
        await reset_key(args.reset, args.key)
    else:
        parser.print_help()


if __name__ == "__main__":
    asyncio.run(main())
