// Proxies the chat list/detail endpoints from the Python backend.
const backendUrl = () => process.env.BACKEND_URL || 'http://localhost:8000';

export async function listChats(req, res) {
  const qs = new URLSearchParams();
  if (req.query.date_from) qs.set('date_from', String(req.query.date_from));
  if (req.query.date_to) qs.set('date_to', String(req.query.date_to));
  const suffix = qs.size ? `?${qs}` : '';
  const r = await fetch(`${backendUrl()}/chats${suffix}`);
  if (!r.ok) return res.status(r.status).json({ error: 'Backend error' });
  res.json(await r.json());
}

export async function getChat(req, res) {
  const r = await fetch(`${backendUrl()}/chats/${encodeURIComponent(req.params.id)}`);
  if (r.status === 404) return res.status(404).json({ error: 'Chat not found' });
  if (!r.ok) return res.status(r.status).json({ error: 'Backend error' });
  res.json(await r.json());
}
