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

from dotenv import load_dotenv
from pydantic_ai import Agent
from pydantic_ai.messages import (
    FunctionToolCallEvent,
    FunctionToolResultEvent,
    PartDeltaEvent,
    PartStartEvent,
    TextPart,
    TextPartDelta,
)

load_dotenv()

import memory
from agent import DraftContext, build_agent


def load_memories(query: str) -> list[str]:
    """
    Read the user's memories from the database at session start.
    """

    memories = memory.recall(query, limit=8)

    print(f"[memory] loaded {len(memories)} memories at session start")
    for item in memories:
        print(f"[memory]   - {item}")

    return memories


def tool_args(event: FunctionToolCallEvent) -> dict:
    """
    The tool call arguments as a dict.
    """
    args = event.part.args
    if isinstance(args, str):
        return json.loads(args)
    return dict(args)


def tool_result(content) -> str:
    """
    String version of a tool result.
    """
    if isinstance(content, str):
        return content
    return json.dumps(content, ensure_ascii=False)


async def text_events(stream):
    """
    Yield one dict per text token of the model's answer.
    """
    async for event in stream:
        if (
            isinstance(event, PartStartEvent)
            and isinstance(event.part, TextPart)
            and event.part.content
        ):
            # the first chunk rides in on a PartStartEvent; without this
            # branch every streamed answer loses its opening word
            yield {"type": "text", "delta": event.part.content}
        elif (
            isinstance(event, PartDeltaEvent)
            and isinstance(event.delta, TextPartDelta)
        ):
            yield {"type": "text", "delta": event.delta.content_delta}


async def tool_events(stream):
    """
    Yield one dict per tool call and one per tool result.
    """
    async for event in stream:
        if isinstance(event, FunctionToolCallEvent):
            yield {
                "type": "tool_call",
                "name": event.part.tool_name,
                "call_id": event.part.tool_call_id,
                "args": tool_args(event),
            }
        elif isinstance(event, FunctionToolResultEvent):
            yield {
                "type": "tool_result",
                "name": event.part.tool_name,
                "call_id": event.part.tool_call_id,
                "result": tool_result(event.part.content),
            }


async def node_events(node, run):
    """
    Yield the events of one agent step: text tokens or tool activity.
    """
    if Agent.is_model_request_node(node):
        # A tool round or validation retry starts a new candidate draft.
        yield {"type": "draft_reset"}
        async with node.stream(run.ctx) as stream:
            async for event in text_events(stream):
                yield event
    elif Agent.is_call_tools_node(node):
        async with node.stream(run.ctx) as stream:
            async for event in tool_events(stream):
                yield event


class Session:
    """
    One conversation: the agent, its history, and its starting memories.
    """

    def __init__(self, memory_enabled: bool = True) -> None:
        self.memory_enabled = memory_enabled
        self.memories = []
        self.context = DraftContext()
        self.agent = build_agent(self.memories, memory_enabled)
        self.history = []

    def refresh(self, question: str) -> None:
        """
        Reload memories from the database and rebuild the agent.

        A long-lived session (the server keeps one per email thread) would
        otherwise keep the snapshot from its start: facts saved since
        then, or by another chat, would be missing from its instructions.
        """
        self.memories = load_memories(question) if self.memory_enabled else []
        self.context = DraftContext(set(self.memories))
        self.agent = build_agent(self.memories, self.memory_enabled)

    def run(self, question: str) -> str:
        """
        One synchronous drafting turn.
        """
        self.refresh(question)
        result = self.agent.run_sync(question, message_history=self.history, deps=self.context)
        self.history = result.all_messages()
        return result.output

    async def events(self, question: str):
        """
        Run one turn and yield everything that happens as plain dicts.
        """
        async with self.agent.iter(question, message_history=self.history, deps=self.context) as run:
            async for node in run:
                async for event in node_events(node, run):
                    yield event
            self.history = run.result.all_messages()

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
