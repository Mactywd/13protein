// Proxies the admin-configurable settings (abandon timeout) to the Python backend.
const backendUrl = () => process.env.BACKEND_URL || 'http://localhost:8000';

export async function getChatSettings(req, res) {
  const r = await fetch(`${backendUrl()}/settings`);
  if (!r.ok) return res.status(r.status).json({ error: 'Backend error' });
  res.json(await r.json());
}

export async function putChatSettings(req, res) {
  const r = await fetch(`${backendUrl()}/settings`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(req.body || {}),
  });
  if (!r.ok) return res.status(r.status).json({ error: 'Backend error' });
  res.json(await r.json());
}
