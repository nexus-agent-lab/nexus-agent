import uvicorn
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import shutil
import os
import tempfile
import sys
import argparse

# Try importing mlx_whisper
try:
    import mlx_whisper
except ImportError:
    print("Error: mlx-whisper not installed. Please run: pip install mlx-whisper")
    sys.exit(1)

# Argument Parsing for Server Configuration
parser = argparse.ArgumentParser(description="Local MLX Whisper Server")
parser.add_argument("--model", type=str, default="mlx-community/whisper-large-v3-mlx", help="HuggingFace model repo")
parser.add_argument("--host", type=str, default="0.0.0.0", help="Host to bind")
parser.add_argument("--port", type=int, default=9191, help="Port to bind")
parser.add_argument("--device", type=str, default="auto", help="Device (ignored for MLX, uses Metal)")
parser.add_argument("--quant", type=str, default=None, help="Quantization (e.g. 4bit, 8bit) - requires selecting correct model repo usually")
args, unknown = parser.parse_known_args()

app = FastAPI(title="Local MLX Whisper Server")

# Allow CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

print(f"Server configured with Default Model: {args.model}")

@app.post("/v1/audio/transcriptions")
async def transcribe_audio(
    file: UploadFile = File(...),
    model: str = Form(default=None),
    language: str = Form(default=None), # Auto-detect if None
    temperature: float = Form(default=0.0),
    response_format: str = Form(default="json")
):
    """
    OpenAI-compatible transcription endpoint.
    Supports 'language' and 'temperature' params.
    """
    target_model = model or args.model
    # Handle generic 'whisper-1' from OpenAI clients by falling back to server default
    if target_model == "whisper-1":
        target_model = args.model

    print(f"Received request: File={file.filename}, Model={target_model}, Lang={language or 'Auto'}")
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1] or ".wav") as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name
    
    try:
        # Prepare arguments for mlx_whisper
        transcribe_args = {
            "path_or_hf_repo": target_model,
            "verbose": True
        }
        
        # Add optional parameters if provided
        if language:
            transcribe_args["language"] = language
        if temperature:
            transcribe_args["temperature"] = temperature
            
        # Execute Transcription
        result = mlx_whisper.transcribe(tmp_path, **transcribe_args)
        
        text = result["text"].strip()
        print(f"Result: {text[:50]}...")
        
        if response_format == "text":
            return text
        else:
            return {"text": text}
            
    except Exception as e:
        print(f"Error during transcription: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

if __name__ == "__main__":
    # If run directly via python, use uvicorn
    # Note: args are parsed at top level
    uvicorn.run(app, host=args.host, port=args.port)
