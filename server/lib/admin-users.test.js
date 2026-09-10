import { describe, it, expect, beforeAll, afterAll } from 'vitest';
import fs from 'fs';
import os from 'os';
import path from 'path';

let store;
let dir;

beforeAll(async () => {
  dir = fs.mkdtempSync(path.join(os.tmpdir(), 'admin-users-'));
  process.env.ADMIN_USERS_FILE = path.join(dir, 'users.json');
  store = await import('./admin-users.js');
});
afterAll(() => fs.rmSync(dir, { recursive: true, force: true }));

describe('admin-users store', () => {
  it('starts empty', () => {
    expect(store.hasAnyUser()).toBe(false);
    expect(store.listUsers()).toEqual([]);
  });

  it('creates a user with hashed password and verifies credentials', () => {
    const created = store.createUser('mattia', 'super-secret-1', store.ALL_PERMS);
    expect(created.user).toBe('mattia');
    expect(created.perms).toEqual(store.ALL_PERMS);
    // No hash/salt leaks through the public shape.
    expect(created.hash).toBeUndefined();
    expect(created.salt).toBeUndefined();

    expect(store.verifyCredentials('mattia', 'super-secret-1')).toEqual({
      user: 'mattia',
      perms: store.ALL_PERMS,
    });
    expect(store.verifyCredentials('mattia', 'wrong-password')).toBeNull();
    expect(store.verifyCredentials('ghost', 'super-secret-1')).toBeNull();

    // The password is not stored in the clear.
    const raw = fs.readFileSync(process.env.ADMIN_USERS_FILE, 'utf8');
    expect(raw).not.toContain('super-secret-1');
  });

  it('rejects duplicates, bad usernames, short passwords and unknown perms', () => {
    expect(() => store.createUser('mattia', 'super-secret-1', [])).toThrow(/esistente/);
    expect(() => store.createUser('x', 'super-secret-1', [])).toThrow(/Nome utente/);
    expect(() => store.createUser('valido', 'short', [])).toThrow(/Password/);
    expect(() => store.createUser('valido', 'super-secret-1', ['root'])).toThrow(/Permessi/);
  });

  it('updates perms without touching the password', () => {
    store.createUser('editor', 'password-123', ['chat']);
    const updated = store.updateUser('editor', { perms: ['chat', 'resoconto'] });
    expect(updated.perms).toEqual(['chat', 'resoconto']);
    expect(store.verifyCredentials('editor', 'password-123')).not.toBeNull();
  });

  it('resets the password without touching perms', () => {
    store.updateUser('editor', { password: 'new-password-456' });
    expect(store.verifyCredentials('editor', 'password-123')).toBeNull();
    const verified = store.verifyCredentials('editor', 'new-password-456');
    expect(verified.perms).toEqual(['chat', 'resoconto']);
  });

  it('deletes a user', () => {
    store.deleteUser('editor');
    expect(store.getUser('editor')).toBeNull();
    expect(() => store.deleteUser('editor')).toThrow(/non trovato/);
  });
});
