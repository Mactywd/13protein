import { useEffect } from "react";
import "./LandingPage.css";
import { useLanguage } from "../../contexts/LanguageContext";
import { trackEvent } from "../../utils/track.js";

/**
 * Landing segnaposto: una schermata sola, il minimo per entrare in chat e per
 * assolvere l'informativa. La landing vera va progettata con il cliente.
 */
export default function LandingPage({ setHasBegun }) {
	const { language, t, toggleLanguage, localePath } = useLanguage();

	useEffect(() => {
		trackEvent("page_view", language);
	}, []); // eslint-disable-line react-hooks/exhaustive-deps

	const handleStart = () => {
		trackEvent("cta_click", language);
		setHasBegun(true);
	};

	return (
		<div className="landing-page">
			<button
				type="button"
				className="landing-lang"
				onClick={() => toggleLanguage(language === "it" ? "en" : "it")}
			>
				{t.landing.langLabel}
			</button>
			<main className="landing-main">
				<h1 className="landing-title">{t.landing.title}</h1>
				<p className="landing-subtitle">{t.landing.subtitle}</p>
				<button type="button" className="landing-cta" onClick={handleStart}>
					{t.landing.start}
				</button>
				<p className="landing-disclosure">
					{t.chat.aiDisclosure}{" "}
					<a href={localePath("/privacy-policy")} target="_blank" rel="noopener noreferrer">
						{t.chat.aiDisclosureLink}
					</a>
				</p>
				<p className="landing-placeholder">{t.landing.disclaimer}</p>
			</main>
		</div>
	);
}
