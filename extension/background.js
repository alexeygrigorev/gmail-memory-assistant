// mem-hub for Gmail - background service worker.
// Gmail's page CSP would block content-script fetches to localhost, so
// the panel asks this worker, which streams the SSE reply back over
// the port, one postMessage per event.

const SERVER = "http://localhost:8000";

chrome.runtime.onConnect.addListener((port) => {
  if (port.name !== "mem-hub") return;
  let disconnected = false;
  const requests = new Set();
  port.onDisconnect.addListener(() => {
    // Reading lastError acknowledges Chrome's expected disconnect notification.
    void chrome.runtime.lastError;
    disconnected = true;
    for (const controller of requests) controller.abort();
  });
  const channel = {
    send(event) {
      if (disconnected) return;
      try { port.postMessage(event); }
      catch { disconnected = true; for (const controller of requests) controller.abort(); }
    },
    async fetch(url, options) {
      const controller = new AbortController();
      requests.add(controller);
      try {
        const response = await fetch(url, { ...options, signal: controller.signal });
        return { response, release: () => requests.delete(controller) };
      } catch (error) { requests.delete(controller); throw error; }
    },
  };
  port.onMessage.addListener((msg) => {
    if (msg.type === "chat") streamChat(channel, msg);
    else if (msg.type === "reset") resetSession(channel, msg);
  });
});

async function streamChat(port, msg) {
  let release = () => {};
  try {
    const request = await port.fetch(`${SERVER}/api/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        session: msg.session,
        message: msg.message,
        memory_enabled: msg.memory_enabled,
      }),
    });
    const response = request.response;
    release = request.release;
    if (!response.ok || !response.body) {
      port.send({ type: "error", message: `Server returned ${response.status}` });
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
          port.send(JSON.parse(line.slice(6)));
        } catch {
          // not JSON - skip the frame
        }
      }
    }
  } catch (error) {
    if (error.name !== 'AbortError') port.send({
      type: "error",
      message: `Cannot reach ${SERVER} - is uvicorn running? (${error.message})`,
    });
  } finally {
    release();
    port.send({ type: "stream-end" });
  }
}

async function resetSession(port, msg) {
  try {
    const { response, release } = await port.fetch(`${SERVER}/api/session/${encodeURIComponent(msg.session)}`, { method: "DELETE" });
    release();
    if (!response.ok) throw new Error(`Server returned ${response.status}`);
    port.send({ type: "reset-ok" });
  } catch (error) {
    if (error.name !== 'AbortError') port.send({ type: "error", message: error.message });
  }
}
