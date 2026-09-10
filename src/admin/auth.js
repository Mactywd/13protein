// Admin session stored in sessionStorage. Bearer token sent on admin API calls.
const KEY = 'alchimista_admin_session';

let onAuthLost = null;
// AdminShell registers a callback so a 401 can bounce back to the login screen.
export function setOnAuthLost(fn) { onAuthLost = fn; }

export function getSession() {
  try { return JSON.parse(sessionStorage.getItem(KEY)) || null; }
  catch { return null; }
}

export function setSession(session) {
  sessionStorage.setItem(KEY, JSON.stringify(session));
}

export function clearSession() {
  sessionStorage.removeItem(KEY);
}

export function getPerms() {
  return getSession()?.perms || [];
}

// fetch wrapper that injects the bearer token and handles 401 by logging out.
export async function authFetch(url, opts = {}) {
  const token = getSession()?.token;
  const headers = { ...(opts.headers || {}) };
  if (token) headers.Authorization = `Bearer ${token}`;
  const res = await fetch(url, { ...opts, headers });
  if (res.status === 401) {
    clearSession();
    if (onAuthLost) onAuthLost();
  }
  return res;
}

// POST credentials, store the session on success. Returns { ok, error }.
export async function login(user, password) {
  const res = await fetch('/api/admin/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ user, password }),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    return { ok: false, error: body.error || 'Login fallito' };
  }
  setSession(await res.json());
  return { ok: true };
}
