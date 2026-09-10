import { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { authFetch } from '../../auth';
import { formatDate, formatDuration, formatCost, profileLabel, STATUS_LABEL, EVAL_LABEL } from './format';
import ProfileFilter from './ProfileFilter';
import { parseProfiles, serializeProfiles, matchesProfiles, matchesStatus } from './filters';
import '../../../globals.css';
import './ChatModule.css';

export default function ChatList() {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();

  const [chats, setChats] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [timeoutMin, setTimeoutMin] = useState('');
  const [savingTimeout, setSavingTimeout] = useState(false);
  const [timeoutSaved, setTimeoutSaved] = useState(false);

  const today = new Date().toISOString().slice(0, 10);
  const monthAgo = new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString().slice(0, 10);
  // Filters live in the URL so back/forward restores them; defaults are not written.
  const dateFrom = searchParams.get('from') || monthAgo;
  const dateTo = searchParams.get('to') || today;
  // `?completed=1` è il vecchio parametro della checkbox: letto come
  // `status=completed` così i segnalibri esistenti non degradano in silenzio.
  const status = searchParams.get('status') || (searchParams.get('completed') === '1' ? 'completed' : '');
  const profiles = parseProfiles(searchParams.get('profiles'));

  function setFilter(patch) {
    const next = new URLSearchParams(searchParams);
    for (const [key, value] of Object.entries(patch)) {
      if (value == null || value === '') next.delete(key);
      else next.set(key, value);
    }
    setSearchParams(next);
  }

  useEffect(() => {
    setLoading(true);
    setError('');
    authFetch(`/api/chats?date_from=${dateFrom}&date_to=${dateTo}`)
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(`Errore ${r.status}`))))
      .then(setChats)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [dateFrom, dateTo]);

  useEffect(() => {
    authFetch('/api/chat-settings')
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => { if (d) setTimeoutMin(String(d.abandon_timeout_minutes)); })
      .catch(() => {});
  }, []);

  async function saveTimeout(e) {
    e.preventDefault();
    setSavingTimeout(true);
    setTimeoutSaved(false);
    const r = await authFetch('/api/chat-settings', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ abandon_timeout_minutes: Number(timeoutMin) || 0 }),
    });
    setSavingTimeout(false);
    if (r.ok) { const d = await r.json(); setTimeoutMin(String(d.abandon_timeout_minutes)); setTimeoutSaved(true); }
  }

  const visibleChats = chats.filter((c) => matchesStatus(c, status) && matchesProfiles(c, profiles));

  return (
    <div className="chat-admin-page">
      <div className="chat-admin-container">
        <h1>Chat</h1>
        <p className="chat-admin-subtitle">Tutte le conversazioni registrate</p>
        <form className="chat-admin-settings" onSubmit={saveTimeout}>
          <label>
            Segna come abbandonate dopo
            <input
              type="number"
              min="0"
              value={timeoutMin}
              onChange={(e) => { setTimeoutMin(e.target.value); setTimeoutSaved(false); }}
            />
            minuti
          </label>
          <button type="submit" disabled={savingTimeout}>{savingTimeout ? 'Salvataggio…' : 'Salva'}</button>
          {timeoutSaved && <span className="chat-admin-settings-ok">Salvato</span>}
          <span className="chat-admin-settings-hint">(0 = disattivato)</span>
        </form>
        <div className="chat-admin-range">
          <label>Da <input type="date" value={dateFrom} onChange={(e) => setFilter({ from: e.target.value })} /></label>
          <label>A <input type="date" value={dateTo} onChange={(e) => setFilter({ to: e.target.value })} /></label>
          <label>
            Mostra
            <select
              value={status}
              onChange={(e) => setFilter({ status: e.target.value || null, completed: null })}
            >
              <option value="">Tutte</option>
              <option value="completed">Completate</option>
              <option value="quoted">Con preventivo</option>
            </select>
          </label>
          <ProfileFilter selected={profiles} onChange={(next) => setFilter({ profiles: serializeProfiles(next) })} />
          {!loading && !error && (
            <span className="chat-admin-range-summary">
              {visibleChats.length} conversazioni · Spesa totale: <b>{formatCost(visibleChats.reduce((sum, c) => sum + (c.total_cost || 0), 0))}</b>
            </span>
          )}
        </div>
        {loading && <p>Caricamento…</p>}
        {error && <p className="chat-admin-error">{error}</p>}
        {!loading && !error && (
          <table className="chat-admin-table">
            <thead>
              <tr><th>Data</th><th>Stato</th><th>Durata</th><th>Costo</th><th>Token</th><th>Eval</th><th>Test</th><th>Anteprima</th></tr>
            </thead>
            <tbody>
              {visibleChats.map((c) => (
                <tr key={c.session_id} onClick={() => navigate(`/chat/${encodeURIComponent(c.session_id)}`)} className="chat-admin-row">
                  <td>{formatDate(c.created_at)}</td>
                  <td>{STATUS_LABEL[c.status] || c.status}</td>
                  <td>{formatDuration(c.duration_seconds)}</td>
                  <td>{formatCost(c.total_cost)}</td>
                  <td>{c.prompt_tokens + c.completion_tokens}</td>
                  <td>{c.eval_status ? (EVAL_LABEL[c.eval_status] || c.eval_status) : '—'}</td>
                  <td>{c.is_testing ? <span className="chat-admin-testing-badge">TEST</span> : '—'}</td>
                  <td className="chat-admin-preview">{profileLabel(c) || c.preview || '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
