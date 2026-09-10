import { useEffect, useMemo, useState } from 'react';
import { Routes, Route, Navigate, NavLink } from 'react-router-dom';
import ChatList from './modules/chat/ChatList';
import ChatDetail from './modules/chat/ChatDetail';
import ResocontoModule from './modules/resoconto/ResocontoModule';
import UtentiModule from './modules/UtentiModule';
import { getSession, getPerms, clearSession, login, setOnAuthLost } from './auth';
import '../globals.css';
import './AdminShell.css';

// One nav tab + route section per perm; 'user-management' lives at /utenti.
const PERM_TO_PATH = { chat: 'chat', resoconto: 'resoconto', 'user-management': 'utenti' };
const MODULE_LABEL = { chat: 'Chat', resoconto: 'Resoconto', 'user-management': 'Utenti' };

export default function AdminShell() {
  const [session, setSession] = useState(getSession());

  // login form state
  const [user, setUser] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    setOnAuthLost(() => setSession(null));
  }, []);

  const perms = useMemo(() => (session ? getPerms() : []), [session]);
  const homePath = perms.length ? `/${PERM_TO_PATH[perms[0]]}` : null;

  async function handleLogin(e) {
    e.preventDefault();
    setBusy(true);
    setError('');
    const res = await login(user.trim(), password);
    setBusy(false);
    if (res.ok) { setSession(getSession()); setPassword(''); }
    else setError(res.error);
  }

  function handleLogout() {
    clearSession();
    setSession(null);
  }

  // Redirect to the first allowed section unless the token carries the perm.
  function guard(perm, element) {
    return perms.includes(perm) ? element : <Navigate to={homePath} replace />;
  }

  if (!session) {
    return (
      <div className="admin-shell-login">
        <form className="admin-shell-login-box" onSubmit={handleLogin}>
          <h1>13 Protein · Admin</h1>
          <input placeholder="Utente" value={user} onChange={(e) => setUser(e.target.value)} autoFocus />
          <input type="password" placeholder="Password" value={password} onChange={(e) => setPassword(e.target.value)} />
          {error && <div className="admin-shell-error">{error}</div>}
          <button type="submit" disabled={busy}>{busy ? 'Accesso…' : 'Accedi'}</button>
        </form>
      </div>
    );
  }

  if (!homePath) {
    return (
      <div className="admin-shell-login">
        <div className="admin-shell-login-box">
          <h1>13 Protein · Admin</h1>
          <p>Nessun permesso associato a questo utente.</p>
          <button onClick={handleLogout}>Esci</button>
        </div>
      </div>
    );
  }

  return (
    <div className="admin-shell">
      <nav className="admin-shell-nav">
        <div className="admin-shell-brand">13 Protein</div>
        <div className="admin-shell-tabs">
          {perms.map((p) => (
            <NavLink
              key={p}
              to={`/${PERM_TO_PATH[p]}`}
              className={({ isActive }) => (isActive ? 'admin-shell-tab active' : 'admin-shell-tab')}
            >
              {MODULE_LABEL[p] || p}
            </NavLink>
          ))}
        </div>
        <div className="admin-shell-user">
          <span>{session.user}</span>
          <button onClick={handleLogout}>Esci</button>
        </div>
      </nav>
      <main className="admin-shell-main">
        <Routes>
          <Route path="/" element={<Navigate to={homePath} replace />} />
          <Route path="/chat" element={guard('chat', <ChatList />)} />
          <Route path="/chat/:id" element={guard('chat', <ChatDetail />)} />
          <Route path="/resoconto" element={guard('resoconto', <ResocontoModule />)} />
          <Route path="/utenti" element={guard('user-management', <UtentiModule currentUser={session.user} />)} />
          <Route path="*" element={<Navigate to={homePath} replace />} />
        </Routes>
      </main>
    </div>
  );
}
