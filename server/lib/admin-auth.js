import crypto from 'crypto';
import fs from 'fs';
import path from 'path';
import { verifyCredentials, hasAnyUser } from './admin-users.js';

// Users live in the file store (server/lib/admin-users.js), Django-superuser
// style: the first one is created via the CLI (server/scripts/create-admin.js),
// further ones from the admin GUI's Utenti tab. No credentials in the repo or
// in env vars.
//
// The token-signing secret is not a human credential either — it only needs
// to exist and stay stable — so it is auto-generated on first boot and
// persisted next to the user store (the admin_data volume in docker).
// Regenerating it (e.g. after losing the volume) just invalidates active
// sessions; users and passwords are untouched. ADMIN_SECRET env overrides it
// for setups that prefer managing the secret explicitly.
function loadOrCreateSecret() {
  if (process.env.ADMIN_SECRET) return process.env.ADMIN_SECRET;
  const file = process.env.ADMIN_SECRET_FILE
    || path.join(path.dirname(process.env.ADMIN_USERS_FILE || './data/admin/users.json'), 'secret.key');
  try {
    const existing = fs.readFileSync(file, 'utf8').trim();
    if (existing) return existing;
  } catch { /* first boot: no file yet */ }
  const secret = crypto.randomBytes(32).toString('hex');
  fs.mkdirSync(path.dirname(file), { recursive: true });
  fs.writeFileSync(file, `${secret}\n`, { mode: 0o600 });
  return secret;
}

export const ADMIN_SECRET = loadOrCreateSecret();

if (!hasAnyUser()) {
  console.warn(
    '[admin-auth] No admin users exist yet — create the first superuser with: ' +
    'node server/scripts/create-admin.js <username>'
  );
}
const TOKEN_TTL_MS = 12 * 60 * 60 * 1000; // 12h

function b64url(buf) {
  return Buffer.from(buf).toString('base64').replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
}

// Returns { user, perms } on success, null otherwise.
export function authenticate(user, password) {
  return verifyCredentials(user, password);
}

// payload: { user, perms }. ttlMs override is used by tests to force expiry.
export function signToken(payload, secret = ADMIN_SECRET, ttlMs = TOKEN_TTL_MS) {
  const body = b64url(JSON.stringify({ ...payload, exp: Date.now() + ttlMs }));
  const sig = b64url(crypto.createHmac('sha256', secret).update(body).digest());
  return `${body}.${sig}`;
}

// Returns the payload object or null (bad shape / bad signature / expired).
export function verifyToken(token, secret = ADMIN_SECRET) {
  if (typeof token !== 'string' || !token.includes('.')) return null;
  const [body, sig] = token.split('.');
  if (!body || !sig) return null;
  const expected = b64url(crypto.createHmac('sha256', secret).update(body).digest());
  const a = Buffer.from(sig);
  const b = Buffer.from(expected);
  if (a.length !== b.length || !crypto.timingSafeEqual(a, b)) return null;
  let payload;
  try {
    payload = JSON.parse(Buffer.from(body.replace(/-/g, '+').replace(/_/g, '/'), 'base64').toString('utf8'));
  } catch {
    return null;
  }
  if (!payload || typeof payload.exp !== 'number' || payload.exp < Date.now()) return null;
  return payload;
}

// Express middleware factory. 401 if no/invalid token, 403 if perm missing.
export function requirePerm(perm, secret = ADMIN_SECRET) {
  return (req, res, next) => {
    const header = req.headers.authorization || '';
    const token = header.startsWith('Bearer ') ? header.slice(7) : '';
    const payload = verifyToken(token, secret);
    if (!payload) return res.status(401).json({ error: 'Non autenticato' });
    if (!Array.isArray(payload.perms) || !payload.perms.includes(perm)) {
      return res.status(403).json({ error: 'Permesso negato' });
    }
    req.adminUser = payload;
    next();
  };
}

// Express middleware factory: any valid (non-expired, correctly signed) admin
// token grants access, regardless of which perms it carries. Used to gate
// the /testing environment's own endpoints, which aren't part of the
// per-module admin permission model.
export function requireAuth(secret = ADMIN_SECRET) {
  return (req, res, next) => {
    const header = req.headers.authorization || '';
    const token = header.startsWith('Bearer ') ? header.slice(7) : '';
    const payload = verifyToken(token, secret);
    if (!payload) return res.status(401).json({ error: 'Non autenticato' });
    req.adminUser = payload;
    next();
  };
}

// POST /api/admin/login handler.
export function loginHandler(req, res) {
  const { user, password } = req.body || {};
  const auth = authenticate(user, password);
  if (!auth) return res.status(401).json({ error: 'Credenziali non valide' });
  const token = signToken(auth);
  res.json({ token, user: auth.user, perms: auth.perms });
}
