import { useEffect, useState } from 'react';
import { authFetch } from '../auth';
import '../../globals.css';
import './UtentiModule.css';

const PERM_LABEL = {
	ricette: 'Ricette',
	chat: 'Chat',
	resoconto: 'Resoconto',
	'user-management': 'Gestione utenti',
};

function PermCheckboxes({ allPerms, value, onChange, idPrefix }) {
	return (
		<div className="utenti-perms">
			{allPerms.map((p) => (
				<label key={p} htmlFor={`${idPrefix}-${p}`} className="utenti-perm">
					<input
						id={`${idPrefix}-${p}`}
						type="checkbox"
						checked={value.includes(p)}
						onChange={(e) => {
							onChange(e.target.checked ? [...value, p] : value.filter((x) => x !== p));
						}}
					/>
					{PERM_LABEL[p] || p}
				</label>
			))}
		</div>
	);
}

export default function UtentiModule({ currentUser }) {
	const [users, setUsers] = useState([]);
	const [allPerms, setAllPerms] = useState([]);
	const [loading, setLoading] = useState(true);
	const [error, setError] = useState('');
	const [notice, setNotice] = useState('');

	// New-user form
	const [newUser, setNewUser] = useState('');
	const [newPassword, setNewPassword] = useState('');
	const [newPerms, setNewPerms] = useState([]);
	const [creating, setCreating] = useState(false);

	// Inline edit: username being edited + its draft state
	const [editing, setEditing] = useState(null);
	const [editPerms, setEditPerms] = useState([]);
	const [editPassword, setEditPassword] = useState('');
	const [saving, setSaving] = useState(false);

	async function refresh() {
		setLoading(true);
		setError('');
		try {
			const res = await authFetch('/api/admin/users');
			if (!res.ok) throw new Error((await res.json().catch(() => ({}))).error || 'Errore di caricamento');
			const data = await res.json();
			setUsers(data.users || []);
			setAllPerms(data.all_perms || []);
		} catch (err) {
			setError(err.message);
		} finally {
			setLoading(false);
		}
	}

	useEffect(() => { refresh(); }, []);

	function flash(msg) {
		setNotice(msg);
		setTimeout(() => setNotice(''), 4000);
	}

	async function handleCreate(e) {
		e.preventDefault();
		setCreating(true);
		setError('');
		try {
			const res = await authFetch('/api/admin/users', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ user: newUser.trim(), password: newPassword, perms: newPerms }),
			});
			const data = await res.json().catch(() => ({}));
			if (!res.ok) throw new Error(data.error || 'Creazione fallita');
			setNewUser('');
			setNewPassword('');
			setNewPerms([]);
			flash(`Utente '${data.user}' creato.`);
			await refresh();
		} catch (err) {
			setError(err.message);
		} finally {
			setCreating(false);
		}
	}

	function startEdit(u) {
		setEditing(u.user);
		setEditPerms(u.perms);
		setEditPassword('');
		setError('');
	}

	async function handleSave(e) {
		e.preventDefault();
		setSaving(true);
		setError('');
		try {
			const body = { perms: editPerms };
			if (editPassword) body.password = editPassword;
			const res = await authFetch(`/api/admin/users/${encodeURIComponent(editing)}`, {
				method: 'PUT',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify(body),
			});
			const data = await res.json().catch(() => ({}));
			if (!res.ok) throw new Error(data.error || 'Salvataggio fallito');
			flash(`Utente '${editing}' aggiornato${editPassword ? ' (password reimpostata)' : ''}.`);
			setEditing(null);
			await refresh();
		} catch (err) {
			setError(err.message);
		} finally {
			setSaving(false);
		}
	}

	async function handleDelete(user) {
		if (!window.confirm(`Eliminare l'utente '${user}'? L'operazione non è reversibile.`)) return;
		setError('');
		try {
			const res = await authFetch(`/api/admin/users/${encodeURIComponent(user)}`, { method: 'DELETE' });
			const data = await res.json().catch(() => ({}));
			if (!res.ok) throw new Error(data.error || 'Eliminazione fallita');
			flash(`Utente '${user}' eliminato.`);
			await refresh();
		} catch (err) {
			setError(err.message);
		}
	}

	return (
		<div className="utenti-module">
			<h2>Utenti amministratori</h2>
			<p className="utenti-hint">
				I permessi decidono quali sezioni l'utente vede. Le modifiche ai permessi hanno
				effetto dal prossimo accesso dell'utente.
			</p>

			{error && <div className="utenti-error" role="alert">{error}</div>}
			{notice && <div className="utenti-notice">{notice}</div>}

			{loading ? (
				<p>Caricamento…</p>
			) : (
				<table className="utenti-table">
					<thead>
						<tr>
							<th>Utente</th>
							<th>Permessi</th>
							<th></th>
						</tr>
					</thead>
					<tbody>
						{users.map((u) => (
							<tr key={u.user}>
								{editing === u.user ? (
									<td colSpan={3}>
										<form className="utenti-edit" onSubmit={handleSave}>
											<strong>{u.user}</strong>
											<PermCheckboxes
												allPerms={allPerms}
												value={editPerms}
												onChange={setEditPerms}
												idPrefix={`edit-${u.user}`}
											/>
											<input
												type="password"
												placeholder="Nuova password (lascia vuoto per non cambiarla)"
												value={editPassword}
												onChange={(e) => setEditPassword(e.target.value)}
												autoComplete="new-password"
											/>
											<div className="utenti-edit-actions">
												<button type="submit" disabled={saving}>
													{saving ? 'Salvataggio…' : 'Salva'}
												</button>
												<button type="button" onClick={() => setEditing(null)}>Annulla</button>
											</div>
										</form>
									</td>
								) : (
									<>
										<td>
											{u.user}
											{u.user === currentUser && <span className="utenti-you"> (tu)</span>}
										</td>
										<td>
											{u.perms.length
												? u.perms.map((p) => (
														<span key={p} className="utenti-badge">{PERM_LABEL[p] || p}</span>
												  ))
												: <em>nessun permesso</em>}
										</td>
										<td className="utenti-actions">
											<button type="button" onClick={() => startEdit(u)}>Modifica</button>
											{u.user !== currentUser && (
												<button type="button" className="utenti-danger" onClick={() => handleDelete(u.user)}>
													Elimina
												</button>
											)}
										</td>
									</>
								)}
							</tr>
						))}
					</tbody>
				</table>
			)}

			<h3>Nuovo utente</h3>
			<form className="utenti-create" onSubmit={handleCreate}>
				<input
					placeholder="Nome utente"
					value={newUser}
					onChange={(e) => setNewUser(e.target.value)}
					autoComplete="off"
				/>
				<input
					type="password"
					placeholder="Password (minimo 8 caratteri)"
					value={newPassword}
					onChange={(e) => setNewPassword(e.target.value)}
					autoComplete="new-password"
				/>
				<PermCheckboxes allPerms={allPerms} value={newPerms} onChange={setNewPerms} idPrefix="new" />
				<button type="submit" disabled={creating || !newUser.trim() || !newPassword}>
					{creating ? 'Creazione…' : 'Crea utente'}
				</button>
			</form>
		</div>
	);
}
