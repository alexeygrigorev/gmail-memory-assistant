# mem-hub for Gmail

A Chrome extension that drafts Gmail replies and learns reusable preferences
from your corrections. Its local FastAPI backend uses an OpenAI model, local
embeddings, and Actian VectorAI DB.

## Start the backend

Requirements: Docker, [uv](https://docs.astral.sh/uv/), Python 3.12+, and an
OpenAI API key. Run commands from this repository.

```bash
docker run -d --name vectorai \
  -v ./local_data:/var/lib/actian-vectorai \
  -p 6573-6575:6573-6575 \
  -e ACTIAN_VECTORAI_ACCEPT_EULA=YES \
  actian/vectorai:latest
uv sync
```

If the container already exists, run `docker start vectorai` instead.
Create `.env` with `OPENAI_API_KEY=your-key`, then start the API:

```bash
uv run uvicorn server:app --host 127.0.0.1 --port 8000
```

The first run downloads `all-MiniLM-L6-v2`. The root endpoint at
[localhost:8000](http://localhost:8000) returns the service status.
No frontend build is required.

## Install and use the extension

1. Open `chrome://extensions` and enable Developer mode.
2. Click **Load unpacked** and select this repository's `extension` folder.
3. Refresh Gmail and open a reply or compose window.
4. Click **✦ Draft reply** above the message body and review the generated text.
5. Click **Refine**, enter a correction, and click **✦ Draft again**.

The **⚙** menu controls saved preferences and resets the current conversation.
Click the top-right **Memory** indicator to inspect the rules the agent reports
applying. It also shows when no rules were used or memory was disabled.
You choose when to send the reply using Gmail.

After editing extension files, reload it in `chrome://extensions` and refresh
Gmail. See [extension/README.md](extension/README.md) for details and
[demo.md](demo.md) for the walkthrough.

## Reset memory

Stop the backend, then run:

```bash
uv run python reset.py --dry-run
uv run python reset.py
```

The first command verifies the storage path without changing it. The second
deletes **all collections** in this repository's `local_data` database and
restarts the container. Restart the backend and refresh Gmail afterward.
The default container name is `vectorai`. Use `--container NAME` only if you
deliberately chose a different name.

Gmail's **Reset conversation** clears only that thread's history;
it does not delete saved preferences.

## Architecture and tests

- `extension/`: Gmail controls and background streaming client.
- `server.py`: drafting API, streamed events, and per-thread conversations.
- `agent.py`: drafting instructions and memory tools.
- `memory.py`: embeddings, categorized preference storage, and retrieval.
- `reset.py`: validated local database reset.
- `tests/`: backend and extension regression tests.

Preferences persist in `email_drafting_memories`. Conversation history clears
when the backend restarts. This is a local, single-user application using user
ID `alexey`, without authentication. Email text goes to the configured OpenAI
model; incoming correspondence is not intended to teach preferences.

```bash
uv run python -m unittest discover -s tests -v
npm ci --prefix tests
npm test --prefix tests
```

Node.js is needed only for extension tests.

Based on the [Agent Memory Hub](https://github.com/actian-devs/agent-memory-hub)
persistent-memory pattern.
