// Admin user management endpoints, gated by requirePerm('user-management')
// at the route-registration layer (server/index.js). Backed by the file store
// in server/lib/admin-users.js.
//
// Lockout guards: you cannot delete your own account or drop your own
// 'user-management' perm — otherwise a lone superuser could lock everyone out
// of this very module.
import { listUsers, createUser, updateUser, deleteUser, ALL_PERMS } from '../lib/admin-users.js';

export function listAdminUsers(req, res) {
  res.json({ users: listUsers(), all_perms: ALL_PERMS });
}

export function createAdminUser(req, res) {
  const { user, password, perms } = req.body || {};
  try {
    const created = createUser(user, password, Array.isArray(perms) ? perms : []);
    res.status(201).json(created);
  } catch (err) {
    res.status(400).json({ error: err.message });
  }
}

export function updateAdminUser(req, res) {
  const target = req.params.user;
  const { perms, password } = req.body || {};
  if (
    target === req.adminUser.user &&
    perms !== undefined &&
    !(Array.isArray(perms) && perms.includes('user-management'))
  ) {
    return res.status(400).json({ error: 'Non puoi rimuovere il permesso di gestione utenti a te stesso' });
  }
  try {
    const updated = updateUser(target, {
      perms: perms === undefined ? undefined : perms,
      password: password === undefined || password === '' ? undefined : password,
    });
    res.json(updated);
  } catch (err) {
    res.status(400).json({ error: err.message });
  }
}

export function deleteAdminUser(req, res) {
  const target = req.params.user;
  if (target === req.adminUser.user) {
    return res.status(400).json({ error: 'Non puoi eliminare il tuo stesso account' });
  }
  try {
    deleteUser(target);
    res.json({ success: true });
  } catch (err) {
    res.status(400).json({ error: err.message });
  }
}
