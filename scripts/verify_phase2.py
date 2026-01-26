import asyncio
import httpx
import sys
import os

# Ensure we can import app modules
sys.path.append(os.getcwd())

from sqlmodel import select, desc
from app.core.db import engine
from app.models.audit import AuditLog
from sqlmodel.ext.asyncio.session import AsyncSession

BASE_URL = "http://localhost:8000"

async def verify_system():
    print(f"Testing against {BASE_URL}...")
    
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
        # Scenario 1: Unauthorized Access
        print("\n--- Test 1: Unauthorized Check ---")
        resp = await client.post("/chat", json={"message": "Check weather"})
        print(f"Status Code: {resp.status_code}")
        if resp.status_code == 401 or resp.status_code == 403:
             print("PASS: Request blocked as expected.")
        else:
             print(f"FAIL: Expected 401/403, got {resp.status_code}")
             print(resp.text)

        # Scenario 2: Authorized Access
        print("\n--- Test 2: Authorized Request (Admin) ---")
        headers = {"X-API-Key": "sk-test-123456"}
        payload = {"message": "What is 10 + 20?"}
        
        # We might need to ensure the DB is seeded first if not already done manually.
        # But user said to write test script assuming environment.
        # The create_admin script should have been run.
        
        resp = await client.post("/chat", json=payload, headers=headers)
        print(f"Status Code: {resp.status_code}")
        
        if resp.status_code == 200:
            data = resp.json()
            print(f"Response: {data.get('response')}")
            trace_id = data.get("trace_id")
            print(f"Trace ID: {trace_id}")
            
            # Scenario 3: Audit Log Verification
            print("\n--- Test 3: DB Audit Log Check ---")
            if trace_id:
                # Wait briefly for async log to flush if needed
                await asyncio.sleep(1) 
                
                async with AsyncSession(engine) as session:
                    # Fetch logs for this trace
                    # Note: trace_id in DB is UUID type, might need casting or string check
                    stmt = select(AuditLog).where(str(AuditLog.trace_id) == str(trace_id))
                    # Actually sqlmodel filtering with UUID usually works with string or UUID object.
                    # Let's try fetching latest log generally
                    
                    # Fetch latest log
                    stmt = select(AuditLog).order_by(desc(AuditLog.created_at)).limit(5)
                    # Execute query
                    result = await session.exec(stmt)
                    logs = result.all()
                    
                    found = False
                    print("Recent Audit Logs:")
                    for log in logs:
                        print(f"- [{log.created_at}] Action: {log.action} | Tool: {log.tool_name} | Status: {log.status} | Trace: {log.trace_id}")
                        if str(log.trace_id) == str(trace_id):
                            found = True
                    
                    if found:
                        print("PASS: Verified audit log entry exists for this request.")
                    else:
                        print("FAIL: Could not find audit log for current trace_id.")
            else:
                 print("FAIL: No trace_id returned in response.")
        
        else:
            print(f"FAIL: Request failed with {resp.status_code}")
            print(resp.text)

if __name__ == "__main__":
    asyncio.run(verify_system())
