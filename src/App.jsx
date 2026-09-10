import { useState, useEffect } from "react";
import "./App.css";

import { LanguageProvider } from "./contexts/LanguageContext";
import LandingPage from "./components/LandingPage/LandingPage";
import Journey from "./components/Journey/Journey";
import TestingGate from "./components/TestingGate/TestingGate";
import PrivacyPolicy from "./components/PrivacyPolicy/PrivacyPolicy";
import { normalizePath } from "./utils/route.js";

export default function App() {
	// Il percorso va spogliato del prefisso di lingua prima di confrontarlo:
	// senza, "/it/privacy-policy" non è nessuna delle route qui sotto e cade
	// sulla landing. La funzione è condivisa con track.js, vedi utils/route.js.
	const route = normalizePath(window.location.pathname);

	const isTesting = route === "/testing";
	const isPrivacy = route === "/privacy-policy";

	const [hasBegun, setHasBegun] = useState(
		() => sessionStorage.getItem("agent13_skipLanding") === "1"
	);

	useEffect(() => {
		if (sessionStorage.getItem("agent13_skipLanding") === "1") {
			sessionStorage.removeItem("agent13_skipLanding");
		}
	}, []);

	let content;
	if (isPrivacy) {
		content = <PrivacyPolicy />;
	} else if (isTesting) {
		content = <TestingGate />;
	} else if (hasBegun) {
		content = <Journey />;
	} else {
		content = <LandingPage setHasBegun={setHasBegun} />;
	}

	return <LanguageProvider>{content}</LanguageProvider>;
}
