#!/usr/bin/env node
// Create (or reset the password of) an admin user — Django createsuperuser
// style. The password is asked interactively (hidden input); for
// non-interactive use (scripts/CI) set it via the CREATE_ADMIN_PASSWORD env
// var instead of a flag, so it never lands in shell history.
//
//   node server/scripts/create-admin.js <username>                 # superuser (all perms)
//   node server/scripts/create-admin.js <username> --perms=chat,resoconto
//   node server/scripts/create-admin.js <username> --reset-password
//
// In docker:
//   docker compose -f docker-compose.prod.yml exec app \
//       node server/scripts/create-admin.js <username>
import { createUser, updateUser, getUser, ALL_PERMS } from '../lib/admin-users.js';

function usage() {
  console.log('Uso: node server/scripts/create-admin.js <username> [--perms=a,b,c] [--reset-password]');
  console.log(`Permessi disponibili: ${ALL_PERMS.join(', ')} (default: tutti — superuser)`);
  process.exit(1);
}

function promptHidden(query) {
  if (!process.stdin.isTTY) {
    // Piped input: read one line in the clear (no TTY to hide anything on).
    return new Promise((resolve) => {
      let buf = '';
      process.stdin.setEncoding('utf8');
      process.stdin.on('data', (chunk) => { buf += chunk; });
      process.stdin.on('end', () => resolve(buf.split('\n')[0]));
    });
  }
  process.stdout.write(query);
  return new Promise((resolve) => {
    const stdin = process.stdin;
    let buf = '';
    const onData = (data) => {
      const ch = data.toString('utf8');
      if (ch === '\n' || ch === '\r' || ch === '\u0004') {
        stdin.setRawMode(false);
        stdin.pause();
        stdin.removeListener('data', onData);
        process.stdout.write('\n');
        resolve(buf);
      } else if (ch === '\u0003') { // Ctrl+C
        process.stdout.write('\n');
        process.exit(1);
      } else if (ch === '\u007f' || ch === '\b') {
        buf = buf.slice(0, -1);
      } else {
        buf += ch;
      }
    };
    stdin.resume();
    stdin.setRawMode(true);
    stdin.on('data', onData);
  });
}

async function askPassword() {
  if (process.env.CREATE_ADMIN_PASSWORD) return process.env.CREATE_ADMIN_PASSWORD;
  const first = await promptHidden('Password: ');
  const second = await promptHidden('Conferma password: ');
  if (first !== second) {
    console.error('Le password non coincidono.');
    process.exit(1);
  }
  return first;
}

const args = process.argv.slice(2);
const username = args.find((a) => !a.startsWith('--'));
if (!username) usage();

const permsFlag = args.find((a) => a.startsWith('--perms='));
const perms = permsFlag
  ? permsFlag.slice('--perms='.length).split(',').map((p) => p.trim()).filter(Boolean)
  : ALL_PERMS;
const resetPassword = args.includes('--reset-password');

const existing = getUser(username);
if (existing && !resetPassword) {
  console.error(`L'utente '${username}' esiste già. Usa --reset-password per cambiarne la password.`);
  process.exit(1);
}
if (!existing && resetPassword) {
  console.error(`L'utente '${username}' non esiste.`);
  process.exit(1);
}

const password = await askPassword();

try {
  if (existing) {
    updateUser(username, { password });
    console.log(`Password aggiornata per '${username}' (permessi invariati: ${existing.perms.join(', ')}).`);
  } else {
    const created = createUser(username, password, perms);
    console.log(`Utente '${created.user}' creato con permessi: ${created.perms.join(', ')}.`);
  }
} catch (err) {
  console.error(err.message);
  process.exit(1);
}
