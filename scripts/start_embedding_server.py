import argparse
import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Union, Optional, Any
from sentence_transformers import SentenceTransformer
import torch

app = FastAPI(title="Local Embedding Server (Nexus)")

# Global model variable
model = None

class EmbeddingRequest(BaseModel):
    input: Any # More lenient to handle token lists from some clients
    model: Optional[str] = "local-embedding-model"

class EmbeddingObject(BaseModel):
    object: str = "embedding"
    index: int
    embedding: List[float]

class EmbeddingResponse(BaseModel):
    object: str = "list"
    data: List[EmbeddingObject]
    model: str
    usage: dict = {"prompt_tokens": 0, "total_tokens": 0}

@app.post("/v1/embeddings", response_model=EmbeddingResponse)
@app.post("/embeddings", response_model=EmbeddingResponse)
async def create_embeddings(request: EmbeddingRequest):
    if model is None:
        raise HTTPException(status_code=500, detail="Model not loaded")
    
    inputs = request.input
    if isinstance(inputs, str):
        inputs = [inputs]
    elif isinstance(inputs, list) and len(inputs) > 0 and isinstance(inputs[0], int):
        # This looks like tokens - we should ideally decode them, 
        # but the model.encode normally wants strings.
        # For now, let's log and try to error gracefully or handle it.
        print(f"Warning: Received tokenized input (integers). This server expects strings.")
        raise HTTPException(status_code=422, detail="This local embedding server requires raw text strings, not tokenized integers.")
    
    try:
        # Generate embeddings
        # convert_to_tensor=False ensures we get a list of floats
        embeddings = model.encode(inputs, convert_to_numpy=True).tolist()
        
        data = [
            EmbeddingObject(index=i, embedding=emb)
            for i, emb in enumerate(embeddings)
        ]
        
        return EmbeddingResponse(
            data=data,
            model=request.model or "local-model"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Start a local embedding server")
    parser.add_argument("--model", type=str, default="BAAI/bge-small-zh-v1.5", help="HuggingFace model name")
    parser.add_argument("--port", type=int, default=9292, help="Port to run the server on")
    parser.add_argument("--device", type=str, default=None, help="Device to use (mps, cuda, cpu)")
    
    args = parser.parse_args()
    
    # Auto-detect MPS for Mac M4
    device = args.device
    if device is None:
        if torch.backends.mps.is_available():
            device = "mps"
        elif torch.cuda.is_available():
            device = "cuda"
        else:
            device = "cpu"
    
    print(f"Loading model: {args.model} on device: {device}...")
    model = SentenceTransformer(args.model, device=device)
    print("Model loaded successfully.")
    
    uvicorn.run(app, host="0.0.0.0", port=args.port)
