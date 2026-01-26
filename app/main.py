from fastapi import FastAPI, HTTPException, Security, Depends
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
import uuid

from app.core.agent import create_agent_graph
from app.core.auth import get_current_user
from app.core.db import init_db
from app.models.user import User

app = FastAPI(title="Nexus Agent API", version="2.0.0")

agent_graph = create_agent_graph()

class ChatRequest(BaseModel):
    message: str
    thread_id: Optional[str] = None

class ChatResponse(BaseModel):
    response: str
    tool_calls: List[Dict[str, Any]] = []
    trace_id: str

@app.on_event("startup")
async def startup_event():
    await init_db()

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
