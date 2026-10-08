"""Local API for the Gmail extension's memory-powered drafting agent.

Run it:

    uv run uvicorn server:app --port 8000

The extension posts drafting requests and receives Server-Sent-Events.
"""

import asyncio
import json

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from agent import Session

# One chat session per name: the message history that keeps working
# memory alive while the tab stays open. Long-term memory is the
# database; this is deliberately not it.
sessions: dict[tuple[str, bool], Session] = {}
locks: dict[tuple[str, bool], asyncio.Lock] = {}


class ChatRequest(BaseModel):
    session: str = "web"
    message: str
    memory_enabled: bool = True


def get_session(name: str, memory_enabled: bool = True) -> Session:
    """Return the named session, loading its memories once."""
    key = (name, memory_enabled)
    if key not in sessions:
        sessions[key] = Session(memory_enabled)
    return sessions[key]


def sse(event: dict) -> str:
    """Format one dict as a Server-Sent-Events frame."""
    return f"data: {json.dumps(event, ensure_ascii=False)}\n\n"


async def event_stream(name: str, question: str, memory_enabled: bool = True):
    """Run the agent and yield SSE events as they happen."""
    yield sse({"type": "start"})
    try:
        async with locks.setdefault((name, memory_enabled), asyncio.Lock()):
            session = get_session(name, memory_enabled)
            await asyncio.to_thread(session.refresh, question)
            yield sse({"type": "memories", "items": session.memories,
                       "enabled": memory_enabled})
            async for event in session.events(question):
                yield sse(event)
        yield sse({"type": "done"})
    except Exception as error:  # surface it in the chat, not only the server log
        yield sse({"type": "error", "message": str(error)})


app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/api/chat")
def chat(request: ChatRequest) -> StreamingResponse:
    """Stream one agent turn as Server-Sent-Events."""
    question = request.message.strip()
    if not question:
        return StreamingResponse(iter([sse({"type": "error", "message": "empty"})]))
    return StreamingResponse(
        event_stream(request.session, question, request.memory_enabled),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.delete("/api/session/{name}")
def reset_session(name: str) -> dict:
    """Forget the conversation history; the database memories stay."""
    sessions.pop((name, True), None)
    sessions.pop((name, False), None)
    return {"ok": True}


@app.get("/")
def index() -> dict:
    return {"status": "ok", "service": "mem-hub"}
