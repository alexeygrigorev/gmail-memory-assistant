// mem-hub for Gmail - content script.
// Watches for compose windows, attaches a drafting panel to each, and
// talks to the local mem-hub server through the background worker.

const EDITABLE_SELECTOR = '.Am.Al.editable[contenteditable="true"], div[contenteditable="true"][aria-label^="Message Body"], div[contenteditable="true"][role="textbox"][aria-multiline="true"]';
// Gmail reuses compose containers and can replace their editor or its siblings.
// Track live editor/panel pairs instead of permanent flags on Gmail's nodes.
const panels = new Map();
const syncEditors = new WeakMap();

function threadId(editable) {
  // Gmail URLs look like #inbox/18f2...; use the id as the chat session
  // so memories accumulate per conversation.
  const match = location.hash.match(/\/([a-zA-Z0-9_-]{16,})/);
  if (match) return `gmail-${match[1]}`;
  if (editable && !editable.dataset.memhubSession) editable.dataset.memhubSession = crypto.randomUUID();
  return `gmail-draft-${editable?.dataset.memhubSession || 'default'}`;
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

function buildPrompt(instruction, previousDraft = "") {
  return [
    previousDraft
      ? `Revise the previous draft using my correction. Save reusable drafting preferences from my correction. My correction: ${instruction}`
      : `Draft a reply to this email thread. ${instruction}`,
    "Answer with the email body text only - no subject line, no signature block.",
    "",
    `Subject: ${subjectText()}`,
    "",
    "Thread:",
    threadText() || "(empty)",
    ...(previousDraft ? ["", "Previous draft:", previousDraft] : []),
  ].join("\n");
}

function attachPanel(editable) {
  const existing = panels.get(editable);
  if (existing?.isConnected && existing.nextElementSibling === editable) {
    syncEditors.get(editable)?.();
    return;
  }
  existing?.remove();
  editable.classList.add('memhub-editor');

  const panel = document.createElement("div");
  panel.className = "memhub-panel";
  // Gmail's delegated compose handlers otherwise cancel checkbox clicks and
  // redirect focus from extension controls back into the message body.
  for (const type of ['mousedown', 'click', 'keydown', 'keyup', 'input', 'change']) {
    panel.addEventListener(type, event => event.stopPropagation());
  }
  panel.innerHTML = `
    <div class="memhub-bar">
      <button type="button" class="memhub-go">✦ Draft reply</button>
      <button type="button" class="memhub-refine" aria-expanded="false" hidden>Refine</button>
      <span class="memhub-log" role="status" aria-live="polite"></span>
      <details class="memhub-used" data-state="idle">
        <summary aria-label="Memory usage for this draft">Memory on</summary>
        <div class="memhub-memory-popover">
          <strong>Memories used for this draft</strong>
          <p class="memhub-memory-note">Generate a reply to see which saved preferences the assistant applies.</p>
          <ul></ul>
        </div>
      </details>
      <details class="memhub-settings"><summary aria-label="Drafting settings" title="mem-hub settings">⚙</summary>
        <div class="memhub-popover">
          <span class="memhub-title">mem-hub</span>
          <label class="memhub-mem-wrap"><input type="checkbox" class="memhub-mem" checked> Use saved preferences</label>
          <button type="button" class="memhub-reset">Reset conversation</button>
        </div>
      </details>
    </div>
    <div class="memhub-refinement" hidden><textarea class="memhub-instr" rows="2"
      aria-label="Refine your reply" placeholder="What would you like to change?"></textarea></div>
    <pre class="memhub-out" hidden></pre>
    <button type="button" class="memhub-insert" hidden>Use this draft</button>`;
  // Anchor controls above the editor so Gmail's minimum editor height does
  // not leave them floating in the middle of an empty reply.
  editable.insertAdjacentElement('beforebegin', panel);
  panels.set(editable, panel);
  wire(panel, editable);
}

function wire(panel, editable) {
  const out = panel.querySelector(".memhub-out");
  const log = panel.querySelector(".memhub-log");
  const btn = panel.querySelector(".memhub-go");
  const insertBtn = panel.querySelector(".memhub-insert");
  const memBox = panel.querySelector(".memhub-mem");
  let draft = "";
  let originalBody = "";
  const used = panel.querySelector('.memhub-used');
  const settings = panel.querySelector('.memhub-settings');
  let usageReported = false;
  let generationStarted = false;
  function showMemory(state, label, note, items = []) {
    used.dataset.state = state;
    used.querySelector('summary').textContent = label;
    used.querySelector('.memhub-memory-note').textContent = note;
    used.querySelector('ul').replaceChildren(...items.map(content => {
      const item = document.createElement('li'); item.textContent = content; return item;
    }));
  }
  for (const [details, other] of [[used, settings], [settings, used]]) {
    details.addEventListener('toggle', () => { if (details.open) other.open = false; });
  }
  memBox.addEventListener('change', () => {
    if (!generationStarted) showMemory(memBox.checked ? 'idle' : 'off', memBox.checked ? 'Memory on' : 'Memory off',
      memBox.checked ? 'Generate a reply to see which saved preferences the assistant applies.' : 'Saved preferences are disabled for the next draft.');
  });
  const instructionBox = panel.querySelector('.memhub-instr');
  const refinement = panel.querySelector('.memhub-refinement');
  const refine = panel.querySelector('.memhub-refine');
  function syncRefine() {
    // Gmail inserts the Gemini writing hint into the editor as a noneditable
    // span. innerText includes that hint even though the reply is empty.
    const body = editable.cloneNode(true);
    body.querySelectorAll('[contenteditable="false"], [aria-hidden="true"]').forEach(node => node.remove());
    refine.hidden = !body.textContent.replace(/[\u200B-\u200D\uFEFF]/g, '').trim();
    if (refine.hidden) {
      refinement.hidden = true;
      refine.setAttribute('aria-expanded', 'false');
      instructionBox.value = '';
    }
  }
  syncEditors.set(editable, syncRefine);
  editable.addEventListener('input', syncRefine);
  syncRefine();
  refine.addEventListener('click', () => {
    refinement.hidden = !refinement.hidden;
    refine.setAttribute('aria-expanded', String(!refinement.hidden));
    if (!refinement.hidden) instructionBox.focus();
  });
  function applyDraft() {
    editable.focus();
    const selection = window.getSelection();
    const range = document.createRange();
    range.selectNodeContents(editable);
    selection.removeAllRanges();
    selection.addRange(range);
    document.execCommand('insertText', false, draft);
    syncRefine();
    out.hidden = true;
    insertBtn.hidden = true;
    btn.textContent = '✦ Draft again';
  }

  let port;
  function getPort() {
    if (!port) {
      port = chrome.runtime.connect({ name: 'mem-hub' });
      port.onMessage.addListener(onMessage);
      const connectedPort = port;
      port.onDisconnect.addListener(() => {
        void chrome.runtime.lastError;
        if (port !== connectedPort) return;
        port = null;
        if (btn.disabled) {
          log.textContent = 'Connection interrupted. Try again, or refresh Gmail after reloading the extension.';
          showMemory('error', 'Memory · unavailable', 'The connection was interrupted before the draft completed.');
        }
        btn.disabled = false;
      });
    }
    return port;
  }
  function sendMessage(message) {
    try { getPort().postMessage(message); }
    catch {
      port = null;
      try { getPort().postMessage(message); }
      catch {
        port = null;
        btn.disabled = false;
        log.textContent = 'Refresh Gmail to reconnect to the extension.';
        showMemory('error', 'Memory · unavailable', 'Refresh Gmail to reconnect before generating a draft.');
      }
    }
  }
  function onMessage(event) {
    switch (event.type) {
      case "draft_reset":
        draft = "";
        out.textContent = "";
        insertBtn.hidden = true;
        break;
      case "text":
        draft += event.delta;
        out.textContent = draft;
        break;
      case "memories":
        log.textContent = "Drafting…";
        break;
      case "tool_call":
        if (event.name === "save_memory") log.textContent = "Saving preference…";
        break;
      case "tool_result":
        if (event.name === 'report_memory_usage') {
          try {
            const report = typeof event.result === 'string' ? JSON.parse(event.result) : event.result;
            if (Array.isArray(report.used)) {
              const items = [...new Set(report.used.filter(item => typeof item === 'string'))];
              usageReported = true;
              showMemory(items.length ? 'used' : 'empty', `Memory · ${items.length}`,
                items.length ? 'The assistant reports applying these saved preferences.' : 'No saved preferences were used for this draft.', items);
            }
          } catch { /* A failed tool result is shown by subsequent stream events. */ }
        }
        break;
      case "error":
        log.textContent = event.message;
        showMemory('error', 'Memory · unavailable', 'Drafting failed. Memory usage for this attempt could not be confirmed.');
        btn.disabled = false;
        break;
      case "done":
        btn.disabled = false;
        if (!usageReported && used.dataset.state === 'pending') {
          showMemory('error', 'Memory · unavailable', 'The assistant did not provide a memory usage report for this draft.');
        }
        if (draft && editable.innerText === originalBody) {
          applyDraft();
          log.textContent = "Draft ready";
        } else if (draft) {
          out.hidden = false;
          insertBtn.hidden = false;
          log.textContent = "Your edits were kept. Review the proposed draft.";
        } else log.textContent = "No draft produced";
        break;
      case "stream-end":
        btn.disabled = false;
        break;
      case "reset-ok":
        log.textContent = "Conversation reset";
        break;
    }
  }

  btn.addEventListener("click", () => {
    const instruction =
      panel.querySelector(".memhub-instr").value.trim() || "Write a polite, concise reply.";
    const previousDraft = instructionBox.value.trim() ? editable.innerText.trim() : "";
    originalBody = editable.innerText;
    draft = "";
    out.textContent = "";
    out.hidden = true;
    insertBtn.hidden = true;
    btn.disabled = true;
    log.textContent = "Drafting…";
    usageReported = false;
    generationStarted = true;
    used.open = false;
    showMemory(memBox.checked ? 'pending' : 'off', memBox.checked ? 'Memory …' : 'Memory off',
      memBox.checked ? 'Checking which saved preferences are applied to this draft.' : 'Saved preferences were disabled for this draft.');
    sendMessage({
      type: "chat",
      session: threadId(editable),
      message: buildPrompt(instruction, previousDraft),
      memory_enabled: memBox.checked,
    });
  });

  insertBtn.addEventListener("click", applyDraft);

  panel.querySelector(".memhub-reset").addEventListener("click", () => {
    sendMessage({ type: "reset", session: threadId(editable) });
  });
}

function scan() {
  for (const [editable, panel] of panels) {
    if (!editable.isConnected || !editable.matches(EDITABLE_SELECTOR)) {
      panel.remove();
      panels.delete(editable);
    }
  }
  document.querySelectorAll(EDITABLE_SELECTOR).forEach(attachPanel);
}

let timer;
function scheduleScan() {
  // Throttle: ongoing Gmail updates must not postpone attachment indefinitely.
  if (timer !== undefined) return;
  timer = setTimeout(() => { timer = undefined; scan(); }, 100);
}
new MutationObserver(scheduleScan).observe(document.body, {
  childList: true,
  characterData: true,
  subtree: true,
  attributes: true,
  attributeFilter: ['contenteditable', 'role', 'aria-label', 'aria-multiline', 'class'],
});
document.addEventListener('focusin', scheduleScan);
window.addEventListener('pageshow', scheduleScan);
window.addEventListener('hashchange', scheduleScan);
scan();
