import asyncio
import json
import logging
import uuid
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional

from fastapi import Depends, FastAPI, File, UploadFile
from fastapi.responses import StreamingResponse
from langchain_core.messages import AIMessage, HumanMessage
from pydantic import BaseModel

import app.core.logging_config  # noqa: F401  — Centralized logging (must be first)
from app.api.admin import router as admin_router
from app.api.auth import router as auth_router
from app.api.skill_learning import router as skills_learning_router
from app.api.skills import router as skills_router
from app.core.agent import create_agent_graph, stream_agent_events
from app.core.auth import get_current_user
from app.core.db import init_db
from app.core.mcp_manager import get_mcp_tools
from app.core.skill_loader import SkillLoader
from app.core.tool_router import tool_router
from app.core.voice import transcribe_audio
from app.interfaces.telegram import run_telegram_bot
from app.models.user import User
from app.tools.registry import get_static_tools

logger = logging.getLogger(__name__)

# Global reference
agent_graph = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic
    await init_db()

    # Start MCP Servers (Handled automatically by get_mcp_tools)
    # MCPManager.start_all() - REMOVED

    # Initialize Tools
    static_tools = get_static_tools()
    mcp_tools = await get_mcp_tools()
    all_tools = static_tools + mcp_tools

    # Register Tools & Skills for Semantic Routing
    await tool_router.register_tools(all_tools)
    all_skills = SkillLoader.load_registry_with_metadata(role="admin")
    await tool_router.register_skills(all_skills)

    global agent_graph
    agent_graph = create_agent_graph(all_tools)

    # Inject Graph into Agent Worker (for MQ)
    from app.core.dispatcher import InterfaceDispatcher
    from app.core.worker import AgentWorker

    AgentWorker.set_agent_graph(agent_graph)
    AgentWorker.set_tools(all_tools)

    # Start Background Services
    asyncio.create_task(run_telegram_bot())
    from app.core.scheduler import SchedulerService
    from app.interfaces.feishu import run_feishu_bot

    asyncio.create_task(run_feishu_bot())
    asyncio.create_task(InterfaceDispatcher.start())
    asyncio.create_task(AgentWorker.start())

    # Start Scheduler
    await SchedulerService.get_instance().start()

    # Group tools by category for structured logging
    tool_map = {}
    for tool in all_tools:
        category = "Core/Internal"
        if hasattr(tool, "metadata") and tool.metadata and "category" in tool.metadata:
            category = tool.metadata["category"]

        if category not in tool_map:
            tool_map[category] = []
        tool_map[category].append(tool.name)

    logger.info(f"Agent initialized with {len(all_tools)} tools across {len(tool_map)} categories:")
    for cat, t_names in tool_map.items():
        logger.info(f"  - [{cat.upper()}]: {', '.join(t_names)}")

    yield

    # Shutdown logic
    from app.core.mcp_manager import stop_mcp
    from app.core.scheduler import SchedulerService

    await SchedulerService.get_instance().stop()
    await AgentWorker.stop()
    await InterfaceDispatcher.stop()
    await stop_mcp()


app = FastAPI(title="Nexus Agent API", version="2.0.0", lifespan=lifespan)

# Register API routers

app.include_router(skills_router)
app.include_router(skills_learning_router)
app.include_router(admin_router)

app.include_router(auth_router)


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
async def chat(request: ChatRequest, current_user: User = Depends(get_current_user)):
    user_message = HumanMessage(content=request.message)
    trace_id = uuid.uuid4()

    initial_state = {"messages": [user_message], "user": current_user, "trace_id": trace_id}

    final_state = await agent_graph.ainvoke(initial_state)

    messages = final_state["messages"]
    last_message = messages[-1]

    response_text = ""
    if isinstance(last_message, AIMessage):
        response_text = str(last_message.content)
    else:
        response_text = "Agent did not return an AI message."

    return ChatResponse(response=response_text, trace_id=str(trace_id))


@app.post("/chat/stream")
async def chat_stream(request: ChatRequest, current_user: User = Depends(get_current_user)):
    user_message = HumanMessage(content=request.message)
    trace_id = uuid.uuid4()

    initial_state = {"messages": [user_message], "user": current_user, "trace_id": trace_id}

    async def event_generator():
        logger.info(f"Stream started for trace_id: {trace_id}")
        count = 0
        async for event in stream_agent_events(agent_graph, initial_state):
            try:
                count += 1
                # Format as SSE
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
            except Exception:
                pass
        logger.info(f"Stream finished for trace_id: {trace_id}, total events: {count}")

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.post("/voice", response_model=ChatResponse)
async def voice_chat(file: UploadFile = File(...), current_user: User = Depends(get_current_user)):
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

    initial_state = {"messages": [user_message], "user": current_user, "trace_id": trace_id}

    final_state = await agent_graph.ainvoke(initial_state)

    # Extract last message content
    last_message = final_state["messages"][-1]
    response_text = last_message.content

    return ChatResponse(response=response_text, trace_id=str(trace_id))
