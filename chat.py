"""A chat assistant with persistent memory.

Start it, talk to it, and type "exit" to leave. The agent has tools:
when it notices a lasting fact about you it saves it to the vector
database right away, and it can search its memories at any time. A new
session starts by loading your facts back, so the agent remembers you
across chats and restarts.

For the demo, run it in two terminals:

    .venv/bin/python chat.py Chat-A
    .venv/bin/python chat.py Chat-B
"""

import sys
from datetime import datetime

from dotenv import load_dotenv
from pydantic_ai import Agent

import memory

load_dotenv()

MODEL = "openai:gpt-5-mini"


def save_memory(content: str) -> str:
    """Save one lasting fact about the user to long-term memory.

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
    """Search long-term memory for facts related to the query.

    Use it when you are not sure what you already know about
    the user, or when they ask what you remember.
    """
    found = memory.recall(query)
    print(f'[memory] SEARCHED "{query}" -> {len(found)} results')
    return found


def get_current_date() -> str:
    """Return today's date and the current time."""
    print("[tools] CHECKED current date and time")
    return datetime.now().strftime("%Y-%m-%d %H:%M (%A)")


def known_facts_text(memories: list[str]) -> str:
    """The user's memories as a bullet list for the instructions."""
    lines = []
    for item in memories:
        lines.append(f"- {item}")
    return "\n".join(lines)


def build_agent(memories: list[str]) -> Agent:
    """Create the chat agent with its memories and tools."""
    return Agent(
        MODEL,
        instructions=[
            "You are a friendly assistant with long-term memory about the user.",
            "If you don't know something about the user, say so honestly.",
            "Keep your answers short and conversational.",
            "You have three tools: save_memory, search_memory, get_current_date.",
            "When the user shares a lasting fact about themselves, call "
            "save_memory right away and confirm it in one short sentence.",
            "Never save a fact that repeats what you already know: each "
            "memory in the database must say something new.",
            f"Things you already remember about the user:\n{known_facts_text(memories)}",
        ],
        tools=[save_memory, search_memory, get_current_date],
    )


def load_memories() -> list[str]:
    """Read the user's memories from the database at session start."""
    memories = memory.recall("personal facts and preferences of the user")
    print(f"[memory] loaded {len(memories)} memories at session start")
    for item in memories:
        print(f"[memory]   - {item}")
    return memories


def read_question() -> str:
    """Read one line from the terminal; Ctrl+D ends the session."""
    try:
        return input("\nYou: ")
    except EOFError:
        return "exit"


def run_conversation(agent: Agent) -> None:
    """Talk to the user until they type 'exit'."""
    history = None
    while True:
        question = read_question()
        if question.strip().lower() == "exit":
            return
        result = agent.run_sync(question, message_history=history)
        history = result.all_messages()
        print(f"Agent: {result.output}", flush=True)


def main() -> None:
    name = "chat"
    if len(sys.argv) > 1:
        name = sys.argv[1]
    print(f"=== {name} (type 'exit' to leave) ===")
    memories = load_memories()
    agent = build_agent(memories)
    run_conversation(agent)


if __name__ == "__main__":
    main()
