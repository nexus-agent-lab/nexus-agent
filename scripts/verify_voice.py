import asyncio
import os
import sys
import httpx
from gtts import gTTS

# Ensure app is in pythonpath
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.db import AsyncSession, engine
from sqlmodel import select
from app.models.user import User

async def get_admin_key():
    async with AsyncSession(engine) as session:
        result = await session.execute(select(User).where(User.username == "admin"))
        user = result.scalars().first()
        return user.api_key if user else None

def generate_chinese_audio(text, filename="test_audio.mp3"):
    """
    Generates a Chinese audio file using Google TTS.
    """
    print(f"Generating Chinese TTS for: '{text}'...")
    tts = gTTS(text=text, lang='zh')
    tts.save(filename)
    print(f"Saved audio to {filename}")
    return filename

async def test_voice():
    # 1. Get Authentication
    print("Obtaining Admin Key...")
    api_key = await get_admin_key()
    if not api_key:
        print("FAIL: Could not find admin user.")
        return
    print(f"Using API Key: {api_key[:5]}***")
    
    # 2. Generate Audio (Chinese Question)
    # Question: "Please calculate 50 plus 30" -> Expecting "80" or similar in response.
    # Using a tool-triggering phrase to verify full pipeline (STT -> Agent -> Tool -> Agent).
    text = "你好，请计算五十加三十等于多少" 
    audio_path = generate_chinese_audio(text)
    
    # 3. Send Request
    # Note: Ensure Docker container has internet access for gTTS and API access.
    async with httpx.AsyncClient(timeout=60.0) as client:
        print(f"\n--- Sending {audio_path} to /voice ---")
        
        with open(audio_path, "rb") as f:
            # Send as mp3
            files = {'file': (audio_path, f, 'audio/mpeg')}
            headers = {"X-API-Key": api_key}
            
            try:
                # The agent (in Docker) talks to host.docker.internal (Local Server)
                response = await client.post("http://localhost:8000/voice", files=files, headers=headers)
                
                print(f"Status Code: {response.status_code}")
                if response.status_code == 200:
                    data = response.json()
                    print("\n>>> SUCCESS! Response from Agent:")
                    print(f"Trace ID: {data.get('trace_id')}")
                    print(f"Agent Reply: {data.get('response')}")
                    
                    reply = data.get('response', '')
                    if "80" in reply:
                        print("✅ VERIFIED: Agent correctly calculated the result.")
                    else:
                        print("⚠️ NOTICE: Agent replied, but maybe didn't trigger calculation (Check if STT recognized '50+30').")
                        
                    print("-" * 30)
                else:
                    print("\n>>> FAIL: API returned error.")
                    print("Status:", response.status_code)
                    print("Body:", response.text)
                    
            except httpx.RequestError as e:
                print(f"FAIL: Network error connecting to Nexus Agent API: {e}")
            except Exception as e:
                print(f"FAIL: Unexpected error: {e}")
    
    # Cleanup
    if os.path.exists(audio_path):
        os.remove(audio_path)

if __name__ == "__main__":
    try:
        asyncio.run(test_voice())
    except Exception as e:
        print(f"Error: {e}")
