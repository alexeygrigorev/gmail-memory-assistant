# Agent with Memory — demo

A tiny demo of an AI agent that remembers things about you across chats.

The agent has two kinds of memory:

- Working memory — the conversation itself. Lives in the context window.
  Gone when the chat ends.
- Long-term memory — short facts about the user, stored as embeddings in a
  local [VectorAI DB](https://www.actian.com/databases/vectorai-db/) vector
  database. Survives chats and restarts.

The pattern follows the
[Agent Memory Hub](https://github.com/actian-devs/agent-memory-hub) tutorial
["How to Build Persistent Agent Memory Across Sessions"](https://actiandev.hashnode.dev/how-to-build-persistent-agent-memory-across-sessions):
read memories at session start — and, unlike a fixed pipeline, the agent
writes memories itself, with a tool, the moment it notices a fact.

## The demo

Use two terminals.

Step 1 — Chat A, ask something. The agent doesn't know it yet:

```bash
.venv/bin/python chat.py Chat-A
# You: What is my favorite coffee?
# Agent: I don't know — you haven't told me yet.
# exit
```

Step 2 — Chat B, share the fact. The agent decides on its own to call
`save_memory`, and you see it happen live:

```bash
.venv/bin/python chat.py Chat-B
# You: My favorite coffee is a flat white with oat milk. And my daughter Mia just turned 5.
# [memory] SAVED: The user's favorite coffee is a flat white with oat milk.
# Agent: Noted — flat white with oat milk, and happy birthday to Mia!
# [memory] SAVED: The user's daughter Mia is 5 years old.
```

Step 3 — Chat A again (restart!). The working memory is empty, but the
agent loads its long-term memories at startup and now knows:

```bash
.venv/bin/python chat.py Chat-A
# [memory] loaded 2 memories at session start
# You: What is my favorite coffee?
# Agent: Your favorite coffee is a flat white with oat milk.
```

## The web UI

The same agent in the browser, with live streaming: text appears as it
is generated, and every tool call pops up as a card the moment it
happens — `save_memory` included.

```bash
.venv/bin/uvicorn server:app --port 8000    # backend + SSE
cd web && npm install && npm run dev        # Vite dev server on :5173
```

Open http://localhost:5173. After `cd web && npm run build`, the built
site is served by the backend itself, so http://localhost:8000 alone is
enough — one process, no Node.

`server.py` serves the same agent over HTTP: `POST /api/chat` answers with
Server-Sent Events (`start`, `text` deltas, `tool_call`, `tool_result`,
`done`), and each session name (top right) keeps its own conversation
history in memory — "New chat" drops it, the database memories stay.

## How it works

Three small files plus a frontend:

```
memory.py   the long-term memory: write and search facts in VectorAI DB
agent.py    the agent: the memory tools, the instructions, the startup load
chat.py     the terminal chat loop that runs the agent
server.py   the same agent as an HTTP server that streams events
web/        the Vite chat interface for server.py
```

Reading (`load_memories` and `search_memory` in `agent.py`, `recall` in
`memory.py`): every new session starts by embedding the query
*"personal facts and preferences of the user"*, searching the vector database
for the most similar stored facts, and putting them into the agent's
instructions. The agent also has a `search_memory` tool, so it can dig
through memories mid-conversation.

Writing (`save_memory` in `agent.py`, `remember` in `memory.py`): saving is
a tool, not a pipeline step. The model decides when to call it, guided by the
conditions in the tool description: save stable facts (preferences, people,
work, goals); skip small talk, moods, temporary plans, and off-the-record
stuff. Each call is visible in the terminal (`[memory] SAVED: ...`), and the
fact is embedded with a local sentence-transformers model
(`all-MiniLM-L6-v2`) and upserted into VectorAI DB. The fact itself is the
point id, so saving the same thing twice just overwrites it.

Other tools: the agent also has `get_current_date` — deliberately trivial,
to show that the model picks the right tool on its own.

Both memory operations are user-scoped: they filter by `user_id`, so the same
pattern works for many users on one database.

## Setup

```bash
# 1. The vector database (Docker)
docker run -d --name vectorai \
  -v ./local_data:/var/lib/actian-vectorai \
  -p 6573-6575:6573-6575 \
  -e ACTIAN_VECTORAI_ACCEPT_EULA=YES \
  actian/vectorai:latest

# 2. Python dependencies (Python 3.12+)
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

# 3. Your OpenAI key
echo "OPENAI_API_KEY=sk-..." > .env
```

The first run downloads the embedding model (~90 MB) once.

## Rehearsing

Wipe the memories and start over at any time:

```bash
.venv/bin/python reset.py
```

It restarts the database with a fresh storage volume, because this
VectorAI DB version (1.0.3) has unreliable deletes: points can come
back from the write-ahead log after a delete.

## Possible improvements

- Recall per question: at startup, search memories with the user's actual
  first question instead of one fixed query — matters with hundreds of facts.
- Update and forget: detect changed facts ("no, I drink tea now") and
  deduplicate near-identical memories by similarity score.
- Forgetting on request: a `forget` tool that deletes a memory by query.
