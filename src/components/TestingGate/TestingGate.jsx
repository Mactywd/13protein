import { useState, useEffect } from "react";
import { getSession, login, setOnAuthLost } from "../../admin/auth";
import LandingPage from "../LandingPage/LandingPage";
import Journey from "../Journey/Journey";
import "./TestingGate.css";

export default function TestingGate() {
	const [session, setSession] = useState(getSession());
	const [hasBegun, setHasBegun] = useState(false);

	const [user, setUser] = useState("");
	const [password, setPassword] = useState("");
	const [error, setError] = useState("");
	const [busy, setBusy] = useState(false);

	useEffect(() => {
		setOnAuthLost(() => setSession(null));
	}, []);

	async function handleLogin(e) {
		e.preventDefault();
		setBusy(true);
		setError("");
		const res = await login(user.trim(), password);
		setBusy(false);
		if (res.ok) {
			setSession(getSession());
			setPassword("");
		} else {
			setError(res.error);
		}
	}

	if (!session) {
		return (
			<div className="testing-gate-login">
				<form className="testing-gate-login-box" onSubmit={handleLogin}>
					<h1>13 Protein · Testing</h1>
					<input
						placeholder="User"
						value={user}
						onChange={(e) => setUser(e.target.value)}
						autoFocus
					/>
					<input
						type="password"
						placeholder="Password"
						value={password}
						onChange={(e) => setPassword(e.target.value)}
					/>
					{error && <div className="testing-gate-error">{error}</div>}
					<button type="submit" disabled={busy}>
						{busy ? "Signing in…" : "Sign in"}
					</button>
				</form>
			</div>
		);
	}

	return hasBegun ? (
		<Journey testingMode />
	) : (
		<LandingPage setHasBegun={setHasBegun} />
	);
}
