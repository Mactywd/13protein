// Proxies the chat SSE stream from the native Python backend to the browser.
// Single origin: the browser talks only to this Node server; we forward to BACKEND_URL.
export default async function chat(req, res) {
  const backendUrl = process.env.BACKEND_URL || 'http://localhost:8000';

  const { session_id, message, default_language, is_testing } = req.body || {};

  if (!session_id) {
    return res.status(400).json({ error: 'Missing session_id' });
  }

  console.log(`[${session_id}] Starting chat stream request`);

  // Idle-based timeout: abort only when the backend has been silent for 120s.
  // A fixed total deadline would kill legitimately long turns (the external-
  // fragrance branch chains web search + several LLM calls) while they are
  // still actively streaming.
  const IDLE_TIMEOUT_MS = 120000;
  const controller = new AbortController();
  let lastChunkTime = Date.now();
  const idleWatchdog = setInterval(() => {
    if (Date.now() - lastChunkTime > IDLE_TIMEOUT_MS) {
      console.error(`[${session_id}] Backend idle for ${IDLE_TIMEOUT_MS / 1000}s, aborting`);
      controller.abort();
    }
  }, 5000);

  let backendResponse;
  try {
    backendResponse = await fetch(`${backendUrl}/chat`, {
      method: 'POST',
      headers: {
        'Accept': 'text/event-stream',
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ session_id, message: message ?? '', default_language, is_testing }),
      signal: controller.signal,
    });
  } catch (fetchError) {
    clearInterval(idleWatchdog);
    console.error(`[${session_id}] Backend fetch failed:`, fetchError.message);
    if (fetchError.name === 'AbortError') {
      return res.status(504).json({ error: 'Backend timeout' });
    }
    return res.status(502).json({ error: 'Backend unreachable', message: fetchError.message });
  }

  if (!backendResponse.ok || !backendResponse.body) {
    clearInterval(idleWatchdog);
    const errorText = await backendResponse.text().catch(() => '');
    console.error(`[${session_id}] Backend error:`, backendResponse.status, errorText);
    return res.status(backendResponse.status || 502).json({
      error: `Backend error: ${backendResponse.status}`,
      details: errorText,
    });
  }

  // Set SSE headers
  res.writeHead(200, {
    'Content-Type': 'text/event-stream',
    'Cache-Control': 'no-cache',
    'Connection': 'keep-alive',
    'X-Accel-Buffering': 'no',
  });

  // Heartbeat to keep the connection alive through proxies
  const heartbeatInterval = setInterval(() => {
    if (Date.now() - lastChunkTime > 5000) {
      res.write(': heartbeat\n\n');
    }
  }, 5000);

  const reader = backendResponse.body.getReader();

  // Handle client disconnect
  req.on('close', () => {
    clearInterval(heartbeatInterval);
    reader.cancel().catch(() => {});
  });

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      lastChunkTime = Date.now();
      res.write(Buffer.from(value));
    }
  } catch (streamError) {
    console.error(`[${session_id}] Stream error:`, streamError.message);
  } finally {
    clearInterval(idleWatchdog);
    clearInterval(heartbeatInterval);
    res.end();
    console.log(`[${session_id}] Chat stream completed`);
  }
}
