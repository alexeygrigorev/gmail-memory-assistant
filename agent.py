"""The memory agent: tools, instructions, memory, and sessions.

All agent definitions live in this one module, so the terminal chat
(chat.py) and the web server (server.py) run exactly the same agent.
The tools print what they do, so every memory operation stays
visible during the demo.
"""

import json
from datetime import datetime

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
from pydantic_ai.models.openai import OpenAIChatModelSettings

import memory

load_dotenv()

MODEL = "openai:gpt-5-mini"
MODEL_SETTINGS = OpenAIChatModelSettings(openai_reasoning_effort="minimal")


def save_memory(content: str) -> str:
    """
    Save one lasting fact about the user to long-term memory.

    Use it only for stable facts worth remembering for weeks:
    preferences (favorite food, coffee, tools), people close to
    the user, their work, projects and goals.

    Do not use it for small talk, today's mood, temporary plans,
    or anything the user asks to keep just in this chat.
    """
    memory.remember(content)
    print(f"[memory] SAVED: {content}")
    return f"Saved to long-term memory: {content}"


def search_memory(query: str) -> list[str]:
    """
    Search long-term memory for facts related to the query.

    Use it when you are not sure what you already know about
    the user, or when they ask what you remember.
    """
    found = memory.recall(query)
    print(f'[memory] SEARCHED "{query}" -> {len(found)} results')
    return found


def get_current_date() -> str:
    """
    Return today's date and the current time.
    """
    print("[tools] CHECKED current date and time")
    return datetime.now().strftime("%Y-%m-%d %H:%M (%A)")


def known_facts_text(memories: list[str]) -> str:
    """
    The user's memories as a bullet list for the instructions.
    """
    lines = []
    for item in memories:
        lines.append(f"- {item}")
    return "\n".join(lines)


def build_instructions(memories: list[str]) -> list[str]:
    """
    The agent's rules plus what it already remembers.
    """

    facts = known_facts_text(memories)

    return [
        "You are a friendly assistant with long-term memory about the user.",
        "If you don't know something about the user, say so honestly.",
        "Keep your answers short and conversational.",
        "Never save a fact that repeats what you already know: each "
        "memory in the database must say something new.",
        f"Things you already remember about the user:\n{facts}",
    ]


def build_agent(memories: list[str]) -> Agent:
    """
    Create the chat agent with its memories and tools.
    """

    return Agent(
        MODEL,
        instructions=build_instructions(memories),
        tools=[save_memory, search_memory, get_current_date],
        model_settings=MODEL_SETTINGS,
    )


def load_memories() -> list[str]:
    """
    Read the user's memories from the database at session start.
    """

    memories = memory.recall("personal facts and preferences of the user")

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
                "args": tool_args(event),
            }
        elif isinstance(event, FunctionToolResultEvent):
            yield {
                "type": "tool_result",
                "name": event.part.tool_name,
                "result": tool_result(event.part.content),
            }


async def node_events(node, run):
    """
    Yield the events of one agent step: text tokens or tool activity.
    """
    if Agent.is_model_request_node(node):
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

    def __init__(self) -> None:
        self.memories = load_memories()
        self.agent = build_agent(self.memories)
        self.history = []

    def run(self, question: str) -> str:
        """
        One synchronous turn; used by the terminal chat.
        """
        result = self.agent.run_sync(question, message_history=self.history)
        self.history = result.all_messages()
        return result.output

    async def events(self, question: str):
        """
        Run one turn and yield everything that happens as plain dicts.
        """
        async with self.agent.iter(question, message_history=self.history) as run:
            async for node in run:
                async for event in node_events(node, run):
                    yield event
            self.history = run.result.all_messages()
