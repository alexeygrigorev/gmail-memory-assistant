"""Web server for the memory chat agent.

The agent comes from agent.py, so this is the same agent as chat.py,
but over HTTP: the browser posts a question and gets a
Server-Sent-Events stream back, so text appears token by token and
every tool call shows up the moment it happens.

Run it:

    uv run uvicorn server:app --port 8000

Then open the Vite dev server (web/, port 5173) or, after
`cd web && npm run build`, the same page directly at http://localhost:8000.
"""

import json

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from agent import Session

# One chat session per name: the message history that keeps working
# memory alive while the tab stays open. Long-term memory is the
# database; this is deliberately not it.
sessions: dict[str, Session] = {}


class ChatRequest(BaseModel):
    session: str = "web"
    message: str


def get_session(name: str) -> Session:
    """Return the named session, loading its memories once."""
    if name not in sessions:
        sessions[name] = Session()
    return sessions[name]


def sse(event: dict) -> str:
    """Format one dict as a Server-Sent-Events frame."""
    return f"data: {json.dumps(event, ensure_ascii=False)}\n\n"


async def event_stream(name: str, question: str):
    """Run the agent and yield SSE events as they happen."""
    session = get_session(name)
    session.refresh()  # the card and the agent must see the current database
    yield sse({"type": "start"})
    yield sse({"type": "memories", "items": session.memories})
    try:
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
        event_stream(request.session, question),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.delete("/api/session/{name}")
def reset_session(name: str) -> dict:
    """Forget the conversation history; the database memories stay."""
    sessions.pop(name, None)
    return {"ok": True}


# Serve the built frontend, so `npm run build` is enough for a
# one-process demo. Directory is created by the Vite build.
app.mount("/assets", StaticFiles(directory="web/dist/assets"), name="assets")


@app.get("/")
def index() -> FileResponse:
    return FileResponse("web/dist/index.html")
