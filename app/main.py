from fastapi import FastAPI, HTTPException, Security, Depends, File, UploadFile
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
import uuid
import logging

logging.basicConfig(level=logging.INFO)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("openai").setLevel(logging.DEBUG)
logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
logging.getLogger("aiosqlite").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

from app.core.agent import create_agent_graph
from app.core.auth import get_current_user
from app.core.db import init_db
from app.models.user import User
from app.core.voice import transcribe_audio
from app.core.mcp import get_mcp_tools
from app.tools.registry import get_static_tools
from app.core.mcp_manager import MCPManager
from app.interfaces.telegram import run_telegram_bot, set_agent_graph
import asyncio

app = FastAPI(title="Nexus Agent API", version="2.0.0")

# Global reference
agent_graph = None

@app.on_event("startup")
async def startup_event():
    await init_db()
    
    # Start MCP Servers
    MCPManager.start_all()
    
    # Initialize Tools
    static_tools = get_static_tools()
    mcp_tools = await get_mcp_tools()
    all_tools = static_tools + mcp_tools
    
    global agent_graph
    agent_graph = create_agent_graph(all_tools)
    
    # Inject Graph into Telegram Service
    set_agent_graph(agent_graph)
    
    # Start Telegram Bot in Background
    asyncio.create_task(run_telegram_bot())
    
    tool_names = [t.name for t in all_tools]
    logger.info(f"Agent initialized with {len(all_tools)} tools: {tool_names}")

@app.on_event("shutdown")
async def shutdown_event():
    # Stop all child processes
    MCPManager.stop_all()

class ChatRequest(BaseModel):
    message: str
    thread_id: Optional[str] = None

class ChatResponse(BaseModel):
    response: str
    tool_calls: List[Dict[str, Any]] = []
    trace_id: str

@app.get("/")
async def root():
    return {"message": "Nexus Agent is running"}

@app.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    current_user: User = Depends(get_current_user)
):
    user_message = HumanMessage(content=request.message)
    trace_id = uuid.uuid4()
    
    initial_state = {
        "messages": [user_message],
        "user": current_user,
        "trace_id": trace_id
    }
    
    final_state = await agent_graph.ainvoke(initial_state)
    
    messages = final_state["messages"]
    last_message = messages[-1]
    
    response_text = ""
    if isinstance(last_message, AIMessage):
        response_text = str(last_message.content)
    else:
        response_text = "Agent did not return an AI message."
        
    return ChatResponse(response=response_text, trace_id=str(trace_id))

@app.post("/voice", response_model=ChatResponse)
async def voice_chat(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user)
):
    """
    1. Upload Audio
    2. Transcribe (STT)
    3. Send text to Agent
    4. Return text response (and optional audio if TTS were implemented)
    """
    # 1. Transcribe
    transcribed_text = await transcribe_audio(file)
    logger.info(f"Transcribed Text: {transcribed_text}")
    
    # 2. Run Agent
    # Re-use logic from /chat but user message comes from STT
    user_message = HumanMessage(content=transcribed_text)
    trace_id = uuid.uuid4()
    
    initial_state = {
        "messages": [user_message],
        "user": current_user,
        "trace_id": trace_id
    }
    
    final_state = await agent_graph.ainvoke(initial_state)
    
    # Extract last message content
    last_message = final_state["messages"][-1]
    response_text = last_message.content
    
    return ChatResponse(
        response=response_text,
        trace_id=str(trace_id)
    )
