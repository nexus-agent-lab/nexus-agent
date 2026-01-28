import os

from fastapi import HTTPException, UploadFile
from openai import AsyncOpenAI

# Configuration
STT_BASE_URL = os.getenv("STT_BASE_URL", "https://api.openai.com/v1")
STT_API_KEY = os.getenv("STT_API_KEY", "sk-proj-...")  # Default to something purely to avoid init errors if not set


async def transcribe_audio(file: UploadFile) -> str:
    """
    Transcribes audio using an OpenAI-compatible API (e.g. Local MLX Server or OpenAI Whisper).
    """
    if not STT_BASE_URL:
        raise HTTPException(status_code=500, detail="STT_BASE_URL is not configured.")

    # Convert UploadFile to a file-like object compatible with OpenAI client
    # We might need to save it temporarily if the client strictly requires it,
    # but AsyncOpenAI usually accepts distinct file-like tuples.

    # Initialize Client
    client = AsyncOpenAI(api_key=STT_API_KEY, base_url=STT_BASE_URL)

    try:
        # Read file content
        content = await file.read()

        # Determine filename (important for format detection by API)
        filename = file.filename or "audio.wav"

        # Call API
        # Note: 'whisper-1' is the standard model name for OpenAI,
        # local servers often ignore it or expect 'whisper-large-v3-mlx' etc.
        # We can make model configurable if needed.
        transcript = await client.audio.transcriptions.create(
            file=(filename, content), model="whisper-1", response_format="text"
        )

        return transcript

    except Exception as e:
        print(f"STT Error: {e}")
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")
