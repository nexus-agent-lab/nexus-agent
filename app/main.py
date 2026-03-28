import asyncio
import json
import logging
import uuid
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from langchain_core.messages import AIMessage, HumanMessage
from pydantic import BaseModel

import app.core.logging_config  # noqa: F401  — Centralized logging (must be first)
from app.api.admin import router as admin_router
from app.api.auth import router as auth_router
from app.api.memories import router as memories_router
from app.api.memskills import router as memskills_router
from app.api.plugins import router as plugins_router
from app.api.roadmap import router as roadmap_router
from app.api.secrets import router as secrets_router
from app.api.secure_input import router as secure_input_router
from app.api.skill_learning import router as skills_learning_router
from app.api.skills import router as skills_router
from app.api.telemetry import router as telemetry_router
from app.api.users import router as users_router
from app.core.agent import create_agent_graph, stream_agent_events
from app.core.auth import get_current_user
from app.core.chat_session_bootstrap import build_session_state
from app.core.db import init_db
from app.core.mcp_manager import get_mcp_tools
from app.core.security import ensure_runtime_security_settings
from app.core.skill_loader import SkillLoader
from app.core.state_watcher import StateWatcher
from app.core.tool_router import tool_router
from app.core.voice import transcribe_audio
from app.interfaces.telegram import run_telegram_bot
from app.interfaces.wechat import run_wechat_bot
from app.models.user import User
from app.tools.registry import get_static_tools

logger = logging.getLogger(__name__)

# Global reference
agent_graph = None


async def restore_settings():
    import os

    from sqlmodel import select

    from app.core.db import AsyncSessionLocal
    from app.models.settings import SystemSetting

    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(SystemSetting))
            settings = result.scalars().all()
            for setting in settings:
                os.environ[setting.key] = setting.value
            logger.info(f"Restored {len(settings)} system settings from DB into os.environ.")
    except Exception as e:
        logger.error(f"Failed to restore settings from DB: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic
    await init_db()
    await restore_settings()
    await ensure_runtime_security_settings()

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

    asyncio.create_task(run_wechat_bot())
    asyncio.create_task(run_feishu_bot())
    asyncio.create_task(InterfaceDispatcher.start())
    asyncio.create_task(AgentWorker.start())
    asyncio.create_task(StateWatcher.get_instance().start())

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
    await StateWatcher.get_instance().stop()
    await AgentWorker.stop()
    await InterfaceDispatcher.stop()
    await stop_mcp()


app = FastAPI(
    title="Nexus Agent API",
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for the OS-like deployment
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

api_router = APIRouter(prefix="/api")

# Register API routers under /api
api_router.include_router(skills_router)
api_router.include_router(plugins_router)
api_router.include_router(secrets_router)
api_router.include_router(skills_learning_router)
api_router.include_router(admin_router)
api_router.include_router(telemetry_router)
api_router.include_router(secure_input_router)
api_router.include_router(memskills_router)
api_router.include_router(roadmap_router)
api_router.include_router(users_router)
api_router.include_router(memories_router)
api_router.include_router(auth_router)


class ChatRequest(BaseModel):
    message: str
    thread_id: Optional[str] = None


class ChatResponse(BaseModel):
    response: str
    tool_calls: List[Dict[str, Any]] = []
    trace_id: str
    thread_id: str
    created_new_thread: bool = False


@api_router.get("/")
async def root():
    return {"message": "Nexus Agent is running"}


@api_router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, current_user: User = Depends(get_current_user)):
    trace_id = uuid.uuid4()
    logger.info(
        "CHAT REQUEST | mode=sync | user_id=%s | requested_thread_id=%s | trace_id=%s | message_preview=%s",
        current_user.id,
        request.thread_id or "-",
        trace_id,
        request.message[:120].replace("\n", " "),
    )
    initial_state, session, created_new_thread = await build_session_state(
        user=current_user,
        incoming_message=request.message,
        thread_id=request.thread_id,
        trace_id=trace_id,
    )

    final_state = await agent_graph.ainvoke(initial_state)

    messages = final_state["messages"]
    last_message = messages[-1]

    response_text = ""
    if isinstance(last_message, AIMessage):
        response_text = str(last_message.content)
    else:
        response_text = "Agent did not return an AI message."

    logger.info(
        "CHAT RESPONSE | mode=sync | user_id=%s | requested_thread_id=%s | resolved_thread_id=%s | "
        "created_new_thread=%s | trace_id=%s | response_preview=%s",
        current_user.id,
        request.thread_id or "-",
        session.session_uuid,
        created_new_thread,
        trace_id,
        response_text[:120].replace("\n", " "),
    )

    return ChatResponse(
        response=response_text,
        trace_id=str(trace_id),
        thread_id=session.session_uuid,
        created_new_thread=created_new_thread,
    )


@api_router.post("/chat/stream")
async def chat_stream(request: ChatRequest, current_user: User = Depends(get_current_user)):
    trace_id = uuid.uuid4()
    logger.info(
        "CHAT REQUEST | mode=stream | user_id=%s | requested_thread_id=%s | trace_id=%s | message_preview=%s",
        current_user.id,
        request.thread_id or "-",
        trace_id,
        request.message[:120].replace("\n", " "),
    )
    initial_state, session, created_new_thread = await build_session_state(
        user=current_user,
        incoming_message=request.message,
        thread_id=request.thread_id,
        trace_id=trace_id,
    )

    async def event_generator():
        logger.info(
            "CHAT STREAM START | user_id=%s | requested_thread_id=%s | resolved_thread_id=%s | "
            "created_new_thread=%s | trace_id=%s",
            current_user.id,
            request.thread_id or "-",
            session.session_uuid,
            created_new_thread,
            trace_id,
        )
        count = 0
        yield (
            "data: "
            + json.dumps(
                {
                    "event": "session",
                    "data": {
                        "thread_id": session.session_uuid,
                        "created_new_thread": created_new_thread,
                        "trace_id": str(trace_id),
                    },
                },
                ensure_ascii=False,
            )
            + "\n\n"
        )
        async for event in stream_agent_events(agent_graph, initial_state):
            try:
                count += 1
                # Format as SSE
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
            except Exception:
                pass
        logger.info(
            "CHAT STREAM END | user_id=%s | resolved_thread_id=%s | trace_id=%s | total_events=%s",
            current_user.id,
            session.session_uuid,
            trace_id,
            count,
        )

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@api_router.post("/voice", response_model=ChatResponse)
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


app.include_router(api_router)
