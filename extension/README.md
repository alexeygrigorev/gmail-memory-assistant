# mem-hub for Gmail

Chrome MV3 extension that adds a memory-powered drafting panel to Gmail's
compose window. Drafts come from the mem-hub agent on
http://localhost:8000 - the server already serves CORS `*`, so no
backend changes are needed.

## Install (unpacked)

1. Start the server: `uv run uvicorn server:app --port 8000`
2. Open `chrome://extensions`, enable "Developer mode".
3. "Load unpacked" and select this `extension/` directory.
4. Open Gmail, hit Compose or Reply - a "mem-hub" panel appears below
   the compose box.

## Use

- Optional instruction line ("keep it short, mention the invoice").
- The **memory** toggle decides whether the agent loads your long-term
  preferences for this generation.
- **Generate draft** streams the reply; **Insert into draft** drops it
  at the cursor in Gmail's compose box.
- **reset** wipes the server-side conversation history for this thread
  (long-term memories stay).

Each Gmail thread gets its own chat session (`gmail-<thread id>`), so
memories accumulate per conversation.
