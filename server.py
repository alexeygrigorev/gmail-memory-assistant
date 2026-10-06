"""Web server for the memory chat agent.

Same agent as chat.py, but over HTTP: the browser posts a question and
gets a Server-Sent-Events stream back, so text appears token by token
and every tool call shows up the moment it happens.

Run it:

    .venv/bin/uvicorn server:app --port 8000

Then open the Vite dev server (web/, port 5173) or, after
`cd web && npm run build`, the same page directly at http://localhost:8000.
"""

import json
from datetime import datetime

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from pydantic_ai import Agent
from pydantic_ai.messages import (
    FunctionToolCallEvent,
    FunctionToolResultEvent,
    PartDeltaEvent,
    TextPartDelta,
)

import memory

load_dotenv()

MODEL = "openai:gpt-5-mini"


class ChatRequest(BaseModel):
    session: str = "web"
    message: str


def save_memory(content: str) -> str:
    """Save one lasting fact about the user to long-term memory.

    Use it only for stable facts worth remembering for weeks:
    preferences (favorite food, coffee, tools), people close to
    the user, their work, projects and goals.

    Do not use it for small talk, today's mood, temporary plans,
    or anything the user asks to keep just in this chat.
    """
    memory.remember(content)
    return f"Saved to long-term memory: {content}"


def search_memory(query: str) -> list[str]:
    """Search long-term memory for facts related to the query.

    Use it when you are not sure what you already know about
    the user, or when they ask what you remember.
    """
    return memory.recall(query)


def get_current_date() -> str:
    """Return today's date and the current time."""
    return datetime.now().strftime("%Y-%m-%d %H:%M (%A)")


def build_agent(memories: list[str]) -> Agent:
    """Create the chat agent with its memories and tools."""
    known_facts = "\n".join(f"- {item}" for item in memories)
    return Agent(
        MODEL,
        instructions=[
            "You are a friendly assistant with long-term memory about the user.",
            "If you don't know something about the user, say so honestly.",
            "Keep your answers short and conversational.",
            "You have three tools: save_memory, search_memory, get_current_date.",
            "When the user shares a lasting fact about themselves, call "
            "save_memory right away and confirm it in one short sentence.",
            f"Things you already remember about the user:\n{known_facts}",
        ],
        tools=[save_memory, search_memory, get_current_date],
    )


# One chat session per name: the message history that keeps working
# memory alive while the tab stays open. Long-term memory is the
# database; this is deliberately not it.
sessions: dict[str, tuple[Agent, list]] = {}


def get_session(name: str) -> tuple[Agent, list]:
    """Return the session's agent and history, loading memories once."""
    if name not in sessions:
        memories = memory.recall("personal facts and preferences of the user")
        sessions[name] = (build_agent(memories), [])
    return sessions[name]


def sse(event: dict) -> str:
    """Format one dict as a Server-Sent-Events frame."""
    return f"data: {json.dumps(event, ensure_ascii=False)}\n\n"


def tool_args(event: FunctionToolCallEvent) -> dict:
    """Best-effort conversion of the tool call arguments to a dict."""
    args = event.part.args
    if isinstance(args, str):
        try:
            return json.loads(args)
        except json.JSONDecodeError:
            return {"raw": args}
    return dict(args)


def tool_result(content) -> str:
    """Best-effort string version of a tool result."""
    if isinstance(content, str):
        return content
    try:
        return json.dumps(content, ensure_ascii=False)
    except TypeError:
        return str(content)


async def event_stream(name: str, question: str):
    """Run the agent and yield SSE events as they happen."""
    agent, history = get_session(name)
    yield sse({"type": "start"})
    try:
        async with agent.iter(question, message_history=history) as run:
            async for node in run:
                if Agent.is_model_request_node(node):
                    async with node.stream(run.ctx) as stream:
                        async for event in stream:
                            if (
                                isinstance(event, PartDeltaEvent)
                                and isinstance(event.delta, TextPartDelta)
                            ):
                                yield sse(
                                    {"type": "text", "delta": event.delta.content_delta}
                                )
                elif Agent.is_call_tools_node(node):
                    async with node.stream(run.ctx) as stream:
                        async for event in stream:
                            if isinstance(event, FunctionToolCallEvent):
                                yield sse(
                                    {
                                        "type": "tool_call",
                                        "name": event.part.tool_name,
                                        "args": tool_args(event),
                                    }
                                )
                            elif isinstance(event, FunctionToolResultEvent):
                                yield sse(
                                    {
                                        "type": "tool_result",
                                        "name": event.part.tool_name,
                                        "result": tool_result(event.part.content),
                                    }
                                )
        sessions[name] = (agent, run.result.all_messages())
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
