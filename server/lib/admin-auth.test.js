import { describe, it, expect, beforeAll, afterAll } from 'vitest';
import fs from 'fs';
import os from 'os';
import path from 'path';

const SECRET = 'test-secret';

// admin-auth reads the user store, which resolves ADMIN_USERS_FILE at import
// time — so both modules are imported dynamically after pointing the store at
// a temp file seeded with two users.
let auth;
let dir;

beforeAll(async () => {
  dir = fs.mkdtempSync(path.join(os.tmpdir(), 'admin-auth-'));
  process.env.ADMIN_USERS_FILE = path.join(dir, 'users.json');
  const store = await import('./admin-users.js');
  store.createUser('utente1', 'password-1', ['chat']);
  store.createUser('utente2', 'password-2', ['chat', 'resoconto']);
  auth = await import('./admin-auth.js');
});
afterAll(() => fs.rmSync(dir, { recursive: true, force: true }));

describe('authenticate', () => {
  it('accepts valid credentials and returns perms', () => {
    expect(auth.authenticate('utente1', 'password-1')).toEqual({ user: 'utente1', perms: ['chat'] });
    expect(auth.authenticate('utente2', 'password-2')).toEqual({ user: 'utente2', perms: ['chat', 'resoconto'] });
  });
  it('rejects wrong password and unknown user', () => {
    expect(auth.authenticate('utente1', 'nope')).toBeNull();
    expect(auth.authenticate('ghost', 'password-1')).toBeNull();
  });
});

describe('signToken / verifyToken', () => {
  it('round-trips a payload', () => {
    const token = auth.signToken({ user: 'utente2', perms: ['chat', 'resoconto'] }, SECRET);
    const payload = auth.verifyToken(token, SECRET);
    expect(payload.user).toBe('utente2');
    expect(payload.perms).toEqual(['chat', 'resoconto']);
  });
  it('rejects a tampered token', () => {
    const token = auth.signToken({ user: 'utente1', perms: ['chat'] }, SECRET);
    expect(auth.verifyToken(token + 'x', SECRET)).toBeNull();
    expect(auth.verifyToken(token, 'other-secret')).toBeNull();
  });
  it('rejects an expired token', () => {
    const token = auth.signToken({ user: 'utente1', perms: ['chat'] }, SECRET, -1000);
    expect(auth.verifyToken(token, SECRET)).toBeNull();
  });
});

describe('requirePerm', () => {
  function mockRes() {
    return { code: 0, body: null, status(c) { this.code = c; return this; }, json(b) { this.body = b; return this; } };
  }
  it('401s without a valid token', () => {
    const res = mockRes(); let nexted = false;
    auth.requirePerm('chat', SECRET)({ headers: {} }, res, () => { nexted = true; });
    expect(res.code).toBe(401);
    expect(nexted).toBe(false);
  });
  it('403s when the perm is missing', () => {
    const token = auth.signToken({ user: 'utente1', perms: ['resoconto'] }, SECRET);
    const res = mockRes(); let nexted = false;
    auth.requirePerm('chat', SECRET)({ headers: { authorization: `Bearer ${token}` } }, res, () => { nexted = true; });
    expect(res.code).toBe(403);
    expect(nexted).toBe(false);
  });
  it('calls next and attaches req.adminUser when authorized', () => {
    const token = auth.signToken({ user: 'utente2', perms: ['chat', 'resoconto'] }, SECRET);
    const req = { headers: { authorization: `Bearer ${token}` } };
    const res = mockRes(); let nexted = false;
    auth.requirePerm('chat', SECRET)(req, res, () => { nexted = true; });
    expect(nexted).toBe(true);
    expect(req.adminUser.user).toBe('utente2');
  });
});

describe('requireAuth', () => {
  function mockRes() {
    return { code: 0, body: null, status(c) { this.code = c; return this; }, json(b) { this.body = b; return this; } };
  }
  it('401s without a valid token', () => {
    const res = mockRes(); let nexted = false;
    auth.requireAuth(SECRET)({ headers: {} }, res, () => { nexted = true; });
    expect(res.code).toBe(401);
    expect(nexted).toBe(false);
  });
  it('calls next for any valid token regardless of perms', () => {
    const token = auth.signToken({ user: 'utente1', perms: ['chat'] }, SECRET);
    const req = { headers: { authorization: `Bearer ${token}` } };
    const res = mockRes(); let nexted = false;
    auth.requireAuth(SECRET)(req, res, () => { nexted = true; });
    expect(nexted).toBe(true);
    expect(req.adminUser.user).toBe('utente1');
  });
});
