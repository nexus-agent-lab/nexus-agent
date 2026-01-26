import asyncio
from app.core.db import engine
from sqlmodel import Session, select
from app.models import User

async def seed_data():
    async with Session(engine) as session:
        # Check if users exist
        stmt = select(User).limit(1)
        result = await session.execute(stmt)
        if result.first():
            print("Users already exist. Skipping seed.")
            return

        # Create Admin
        admin = User(username="admin", api_key="admin-secret", role="admin")
        session.add(admin)
        
        # Create Regular User
        user = User(username="alice", api_key="alice-secret", role="user")
        session.add(user)
        
        await session.commit()
        print("Seeded users: admin (key: admin-secret), alice (key: alice-secret)")

if __name__ == "__main__":
    asyncio.run(seed_data())
