// Proxies the skip-conversation request to the Python backend. Testing-only
// feature, gated by requireAuth at the route-registration layer (server/index.js).
export default async function chatSkip(req, res) {
  const backendUrl = process.env.BACKEND_URL || 'http://localhost:8000';
  const { session_id } = req.body || {};

  if (!session_id) {
    return res.status(400).json({ error: 'Missing session_id' });
  }

  let backendResponse;
  try {
    backendResponse = await fetch(`${backendUrl}/chat/${encodeURIComponent(session_id)}/skip`, {
      method: 'POST',
    });
  } catch (fetchError) {
    return res.status(502).json({ error: 'Backend unreachable', message: fetchError.message });
  }

  if (!backendResponse.ok) {
    const errorText = await backendResponse.text().catch(() => '');
    return res.status(backendResponse.status || 502).json({
      error: `Backend error: ${backendResponse.status}`,
      details: errorText,
    });
  }

  const data = await backendResponse.json();
  res.json(data);
}
