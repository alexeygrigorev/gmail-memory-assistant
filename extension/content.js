// mem-hub for Gmail - content script.
// Watches for compose windows, attaches a drafting panel to each, and
// talks to the local mem-hub server through the background worker.

const COMPOSE_SELECTOR = ".AD"; // whole compose/reply window
const EDITABLE_SELECTOR = ".Am.Al.editable, div[aria-label^='Message Body']";

function threadId() {
  // Gmail URLs look like #inbox/18f2...; use the id as the chat session
  // so memories accumulate per conversation.
  const match = location.hash.match(/\/([0-9a-f]{16,})/);
  return match ? `gmail-${match[1]}` : "gmail-drafts";
}

function subjectText() {
  const input = document.querySelector('input[name="subjectbox"]');
  if (input && input.value.trim()) return input.value.trim();
  const heading = [...document.querySelectorAll("h2.hP")].find((h) => h.offsetParent !== null);
  return heading ? heading.textContent.trim() : "(no subject)";
}

function threadText() {
  // Visible message bodies on the page, oldest first, capped for the prompt.
  const parts = [...document.querySelectorAll(".ii.gt")]
    .filter((el) => el.offsetParent !== null)
    .map((el) => el.innerText.trim())
    .filter(Boolean);
  const text = parts.join("\n---\n");
  return text.length > 6000 ? text.slice(-6000) : text;
}

function buildPrompt(instruction) {
  return [
    `Draft a reply to this email thread. ${instruction}`,
    "Answer with the email body text only - no subject line, no signature block.",
    "",
    `Subject: ${subjectText()}`,
    "",
    "Thread:",
    threadText() || "(empty)",
  ].join("\n");
}

function attachPanel(compose) {
  if (compose.dataset.memHubPanel) return;
  const editable = compose.querySelector(EDITABLE_SELECTOR);
  if (!editable) return;
  compose.dataset.memHubPanel = "1";

  const panel = document.createElement("div");
  panel.className = "memhub-panel";
  panel.innerHTML = `
    <div class="memhub-head">
      <span class="memhub-title">mem-hub</span>
      <label class="memhub-mem-wrap"><input type="checkbox" class="memhub-mem" checked> memory</label>
      <button class="memhub-reset" title="Forget this conversation on the server">reset</button>
    </div>
    <textarea class="memhub-instr" rows="2"
      placeholder="Instructions (optional) - e.g. keep it short and friendly"></textarea>
    <button class="memhub-go">Generate draft</button>
    <div class="memhub-log"></div>
    <pre class="memhub-out"></pre>
    <button class="memhub-insert" hidden>Insert into draft</button>`;
  compose.appendChild(panel);
  wire(panel, editable);
}

function wire(panel, editable) {
  const out = panel.querySelector(".memhub-out");
  const log = panel.querySelector(".memhub-log");
  const btn = panel.querySelector(".memhub-go");
  const insertBtn = panel.querySelector(".memhub-insert");
  const memBox = panel.querySelector(".memhub-mem");
  let draft = "";

  const port = chrome.runtime.connect({ name: "mem-hub" });
  port.onMessage.addListener((event) => {
    switch (event.type) {
      case "text":
        draft += event.delta;
        out.textContent = draft;
        break;
      case "memories":
        log.textContent = event.enabled
          ? `memory: ${event.items.length} preference(s) loaded`
          : "memory off for this generation";
        break;
      case "tool_call":
        log.textContent =
          event.name === "save_memory" ? "saving preference..." : "searching memory...";
        break;
      case "error":
        log.textContent = event.message;
        btn.disabled = false;
        break;
      case "done":
        btn.disabled = false;
        insertBtn.hidden = !draft;
        if (!draft) log.textContent = "no draft produced";
        break;
      case "stream-end":
        btn.disabled = false;
        break;
      case "reset-ok":
        log.textContent = "session reset (memories kept)";
        break;
    }
  });

  btn.addEventListener("click", () => {
    const instruction =
      panel.querySelector(".memhub-instr").value.trim() || "Write a polite, concise reply.";
    draft = "";
    out.textContent = "";
    insertBtn.hidden = true;
    btn.disabled = true;
    log.textContent = "asking mem-hub...";
    port.postMessage({
      type: "chat",
      session: threadId(),
      message: buildPrompt(instruction),
      memory_enabled: memBox.checked,
    });
  });

  insertBtn.addEventListener("click", () => {
    editable.focus();
    document.execCommand("insertText", false, draft);
  });

  panel.querySelector(".memhub-reset").addEventListener("click", () => {
    port.postMessage({ type: "reset", session: threadId() });
  });
}

function scan() {
  document.querySelectorAll(COMPOSE_SELECTOR).forEach(attachPanel);
}

let timer;
new MutationObserver(() => {
  clearTimeout(timer);
  timer = setTimeout(scan, 300); // Gmail is a SPA; watch for new compose windows
}).observe(document.body, { childList: true, subtree: true });
scan();
