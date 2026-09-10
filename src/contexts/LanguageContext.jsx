import { createContext, useContext } from "react";
import { translations } from "../i18n/translations";

const LanguageContext = createContext();

// L'inglese è la lingua di default e non ha prefisso; l'italiano vive sotto
// "/it". Il sito di 13protein.com è di fatto monolingua inglese: l'italiano è
// tradotto dall'agente, non è copy approvato dal cliente.
function getLanguageFromURL() {
	const path = window.location.pathname;
	return path === "/it" || path.startsWith("/it/") ? "it" : "en";
}

export function LanguageProvider({ children }) {
	const language = getLanguageFromURL();

	const t = translations[language];

	const toggleLanguage = (newLang) => {
		if (newLang === "it" && language !== "it") {
			window.location.href = "/it";
		} else if (newLang === "en" && language !== "en") {
			window.location.href = "/";
		}
	};

	/**
	 * Prefissa un percorso interno con la lingua corrente ("/privacy-policy" →
	 * "/it/privacy-policy"). Serve perché la lingua vive nell'URL: un link
	 * assoluto scritto a mano riporterebbe un utente italiano sulla versione
	 * inglese della pagina, che sull'informativa è un problema di trasparenza
	 * (art. 12.1 GDPR), non un dettaglio estetico.
	 */
	const localePath = (p) => (language === "it" ? `/it${p === "/" ? "" : p}` : p);

	return (
		<LanguageContext.Provider value={{ language, toggleLanguage, t, localePath }}>
			{children}
		</LanguageContext.Provider>
	);
}

// Il file esporta il provider e il suo hook: è la coppia canonica di un
// context, e separarli in due file per far contento il fast refresh non
// migliora nulla.
// eslint-disable-next-line react-refresh/only-export-components
export function useLanguage() {
	const context = useContext(LanguageContext);
	if (!context) {
		throw new Error("useLanguage must be used within a LanguageProvider");
	}
	return context;
}
