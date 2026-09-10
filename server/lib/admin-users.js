// Admin user store — Django-superuser style. Users live in a JSON file
// (ADMIN_USERS_FILE, on the /data volume in docker) with scrypt-hashed
// passwords; the first user is created via the CLI
// (server/scripts/create-admin.js), further ones via the admin GUI's Utenti
// tab (perm 'user-management'). The file is read on every call (no cache) so
// the CLI and the running server never step on a stale copy.
import fs from 'fs';
import path from 'path';
import crypto from 'crypto';

const USERS_FILE = process.env.ADMIN_USERS_FILE || './data/admin/users.json';

export const ALL_PERMS = ['chat', 'resoconto', 'user-management'];

const USERNAME_RE = /^[a-zA-Z0-9_.-]{3,32}$/;
const MIN_PASSWORD_LEN = 8;

const SCRYPT_KEYLEN = 64;

function load() {
  try {
    const db = JSON.parse(fs.readFileSync(USERS_FILE, 'utf8'));
    return db && Array.isArray(db.users) ? db : { users: [] };
  } catch {
    return { users: [] };
  }
}

function save(db) {
  const dir = path.dirname(USERS_FILE);
  if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
  // Write-then-rename, same as recipe-store: a crash can't corrupt the file.
  const tmp = `${USERS_FILE}.tmp`;
  fs.writeFileSync(tmp, JSON.stringify(db, null, 2), 'utf8');
  fs.renameSync(tmp, USERS_FILE);
}

function hashPassword(password, salt = crypto.randomBytes(16).toString('hex')) {
  const hash = crypto.scryptSync(password, salt, SCRYPT_KEYLEN).toString('hex');
  return { salt, hash };
}

function validateUsername(user) {
  if (typeof user !== 'string' || !USERNAME_RE.test(user)) {
    throw new Error('Nome utente non valido (3-32 caratteri: lettere, numeri, . _ -)');
  }
}

function validatePassword(password) {
  if (typeof password !== 'string' || password.length < MIN_PASSWORD_LEN) {
    throw new Error(`Password troppo corta (minimo ${MIN_PASSWORD_LEN} caratteri)`);
  }
}

function validatePerms(perms) {
  if (!Array.isArray(perms) || perms.some((p) => !ALL_PERMS.includes(p))) {
    throw new Error(`Permessi non validi (disponibili: ${ALL_PERMS.join(', ')})`);
  }
}

function publicUser(u) {
  return { user: u.user, perms: u.perms, createdAt: u.createdAt, updatedAt: u.updatedAt };
}

export function listUsers() {
  return load().users.map(publicUser);
}

export function getUser(user) {
  const found = load().users.find((u) => u.user === user);
  return found ? publicUser(found) : null;
}

export function createUser(user, password, perms) {
  validateUsername(user);
  validatePassword(password);
  validatePerms(perms);
  const db = load();
  if (db.users.some((u) => u.user === user)) {
    throw new Error('Utente già esistente');
  }
  const now = new Date().toISOString();
  db.users.push({ user, ...hashPassword(password), perms, createdAt: now, updatedAt: now });
  save(db);
  return getUser(user);
}

// Update perms and/or reset the password. Only the provided fields change.
export function updateUser(user, { perms, password } = {}) {
  const db = load();
  const record = db.users.find((u) => u.user === user);
  if (!record) throw new Error('Utente non trovato');
  if (perms !== undefined) {
    validatePerms(perms);
    record.perms = perms;
  }
  if (password !== undefined) {
    validatePassword(password);
    Object.assign(record, hashPassword(password));
  }
  record.updatedAt = new Date().toISOString();
  save(db);
  return publicUser(record);
}

export function deleteUser(user) {
  const db = load();
  const before = db.users.length;
  db.users = db.users.filter((u) => u.user !== user);
  if (db.users.length === before) throw new Error('Utente non trovato');
  save(db);
}

// Login check. Returns { user, perms } on success, null otherwise.
export function verifyCredentials(user, password) {
  if (typeof user !== 'string' || typeof password !== 'string') return null;
  const record = load().users.find((u) => u.user === user);
  if (!record) return null;
  const candidate = crypto.scryptSync(password, record.salt, SCRYPT_KEYLEN);
  const stored = Buffer.from(record.hash, 'hex');
  if (candidate.length !== stored.length || !crypto.timingSafeEqual(candidate, stored)) {
    return null;
  }
  return { user: record.user, perms: record.perms };
}

export function hasAnyUser() {
  return load().users.length > 0;
}
