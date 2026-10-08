# mem-hub for Gmail

Chrome MV3 extension that adds a memory-powered drafting panel to Gmail's
compose window. Drafts come from the mem-hub agent on
http://localhost:8000 - the server already serves CORS `*`, so no
backend changes are needed.

## Install (unpacked)

1. Start the server: `uv run uvicorn server:app --port 8000`
2. Open `chrome://extensions`, enable "Developer mode".
3. "Load unpacked" and select this `extension/` directory.
4. Refresh Gmail, then hit Compose or Reply. **✦ Draft reply** appears
   above the message body.

## Use

- **✦ Draft reply** generates a reply directly in Gmail's message body.
- **Refine** opens an optional instruction box. Enter a correction and click
  **✦ Draft again** to revise the current reply.
- **⚙** contains **Use saved preferences** and **Reset conversation**.
  Reset clears this thread's server-side history; long-term memories stay.
- Expand the preference count to inspect the rules used for the reply.
- If you edit the message while generation is running, your edits are kept.
  Review the proposed reply and click **Use this draft** to replace them.

Gmail can rebuild reply editors during navigation. The extension restores
controls on replacement editors and removes abandoned controls automatically.

Run extension regression tests with `npm install --prefix tests` followed by
`npm test --prefix tests` from the repository root.

Each Gmail thread gets its own chat session (`gmail-<thread id>`), so
memories accumulate per conversation.

## Demo in Gmail

Send the fictional messages from demo.md between two accounts you control.
Open the received invitation in Gmail and click Reply. Use memory off for
an honest baseline when the database already contains preferences. Enable
memory, enter the correction from demo.md, and generate again. Expand
Preferences used to inspect the actual reported rule.

Open the other invitation and generate without repeating the correction.
Each conversation uses its Gmail thread ID, including modern alphanumeric
IDs. Compare with memory off and check the sponsorship email for relevance.
Insert into draft verifies Gmail editing; sending the reply is optional.

After editing extension files, reload mem-hub on chrome://extensions and
refresh Gmail. Preferences persist in the database.
