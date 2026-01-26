import asyncio
import os
import sys

# Ensure we can import from app
sys.path.append(os.getcwd())

from sqlmodel import select
from app.core.db import engine, init_db
from app.models.user import User
from sqlmodel.ext.asyncio.session import AsyncSession

async def create_admin():
    print("Initializing Database...")
    await init_db() # Ensure tables exist
    
    async with AsyncSession(engine) as session:
        # Check if admin exists
        stmt = select(User).where(User.username == "admin")
        result = await session.execute(stmt)
        existing_user = result.scalars().first()
        
        if existing_user:
            print("Admin user already exists.")
            return

        print("Creating admin user...")
        admin = User(
            username="admin", 
            api_key="sk-test-123456", 
            role="admin"
        )
        session.add(admin)
        await session.commit()
        print(f"Admin created successfully. API Key: {admin.api_key}")

if __name__ == "__main__":
    try:
        asyncio.run(create_admin())
    except Exception as e:
        print(f"Error: {e}")
