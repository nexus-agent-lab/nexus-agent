import asyncio
import os
import sys

# Ensure app is in pythonpath
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlmodel import desc, select

from app.core.db import AsyncSession, engine
from app.models.audit import AuditLog


async def main():
    print("Connecting to database...")
    async with AsyncSession(engine) as session:
        statement = select(AuditLog).order_by(desc(AuditLog.created_at)).limit(5)
        result = await session.execute(statement)
        logs = result.scalars().all()

        if not logs:
            print("No audit logs found.")
            return

        header = f"{'ID':<5} | {'User ID':<10} | {'Tool Name':<20} | {'Status':<10} | {'Created At'}"
        print("\n" + header)
        print("-" * len(header))

        for log in logs:
            # Handle possible None for user_id
            user_id_str = str(log.user_id) if log.user_id else "None"
            print(f"{log.id:<5} | {user_id_str:<10} | {log.tool_name:<20} | {log.status:<10} | {log.created_at}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"Error: {e}")
