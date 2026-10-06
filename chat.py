"""A chat assistant with persistent memory.

The agent itself - its tools, instructions, and memory - lives in
agent.py; this file only runs it in the terminal. A new session
starts by loading your facts back, so the agent remembers you
across chats and restarts.

For the demo, run it in two terminals:

    .venv/bin/python chat.py Chat-A
    .venv/bin/python chat.py Chat-B
"""

import sys

from agent import Session


def read_question() -> str:
    """
    Read one line from the terminal; Ctrl+D ends the session.
    """

    try:
        return input("\nYou: ")
    except EOFError:
        return "exit"


def run_conversation(session: Session) -> None:
    """
    Talk to the user until they type 'exit'.
    """

    while True:
        question = read_question()
        if question.strip().lower() == "exit":
            return
        answer = session.run(question)
        print(f"Agent: {answer}", flush=True)


def main() -> None:
    name = "chat"

    if len(sys.argv) > 1:
        name = sys.argv[1]

    print(f"=== {name} (type 'exit' to leave) ===")
    run_conversation(Session())


if __name__ == "__main__":
    main()
