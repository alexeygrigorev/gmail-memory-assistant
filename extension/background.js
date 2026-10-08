// mem-hub for Gmail - background service worker.
// Gmail's page CSP would block content-script fetches to localhost, so
// the panel asks this worker, which streams the SSE reply back over
// the port, one postMessage per event.

const SERVER = "http://localhost:8000";

chrome.runtime.onConnect.addListener((port) => {
  if (port.name !== "mem-hub") return;
  port.onMessage.addListener((msg) => {
    if (msg.type === "chat") streamChat(port, msg);
    else if (msg.type === "reset") resetSession(port, msg);
  });
});

async function streamChat(port, msg) {
  try {
    const response = await fetch(`${SERVER}/api/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        session: msg.session,
        message: msg.message,
        memory_enabled: msg.memory_enabled,
      }),
    });
    if (!response.ok || !response.body) {
      port.postMessage({ type: "error", message: `Server returned ${response.status}` });
      return;
    }
    // MV3 service workers have no EventSource: read the body and split
    // the `data: {...}` frames ourselves, like web/main.js does.
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    for (;;) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      let index;
      while ((index = buffer.indexOf("\n\n")) !== -1) {
        const frame = buffer.slice(0, index);
        buffer = buffer.slice(index + 2);
        const line = frame.split("\n").find((l) => l.startsWith("data: "));
        if (!line) continue;
        try {
          port.postMessage(JSON.parse(line.slice(6)));
        } catch {
          // not JSON - skip the frame
        }
      }
    }
  } catch (error) {
    port.postMessage({
      type: "error",
      message: `Cannot reach ${SERVER} - is uvicorn running? (${error.message})`,
    });
  } finally {
    port.postMessage({ type: "stream-end" });
  }
}

async function resetSession(port, msg) {
  try {
    await fetch(`${SERVER}/api/session/${encodeURIComponent(msg.session)}`, { method: "DELETE" });
    port.postMessage({ type: "reset-ok" });
  } catch (error) {
    port.postMessage({ type: "error", message: error.message });
  }
}
