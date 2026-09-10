import { useState, useEffect, useRef } from "react";
import Conversation from "../Conversation/Conversation";
import LeadSummary from "../LeadSummary/LeadSummary";
import { useLanguage } from "../../contexts/LanguageContext";
import { trackEvent } from "../../utils/track.js";

/**
 * Chat, poi riepilogo del lead. Nessun POST alla fine: il lead è già in
 * Postgres, scritto dal backend a ogni turno (`sessions.state`). L'unica cosa
 * che parte da qui è l'evento di funnel della richiesta di preventivo.
 */
export default function Journey({ testingMode = false }) {
	const { language } = useLanguage();
	const [chatEnded, setChatEnded] = useState(false);
	const [leadInfo, setLeadInfo] = useState(null);
	const summaryRef = useRef(null);
	const quoteTracked = useRef(false);

	const endChat = () => setChatEnded(true);

	useEffect(() => {
		if (!leadInfo || quoteTracked.current) return;
		if (leadInfo.quoteRequested) {
			quoteTracked.current = true;
			trackEvent("quote_request", language);
		}
	}, [leadInfo, language]);

	useEffect(() => {
		if (!chatEnded) return;
		const id = setTimeout(() => {
			summaryRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
		}, 150);
		return () => clearTimeout(id);
	}, [chatEnded]);

	return (
		<>
			<Conversation
				endChat={endChat}
				updateLeadInfo={setLeadInfo}
				testingMode={testingMode}
			/>
			{chatEnded && leadInfo && <LeadSummary scrollRef={summaryRef} leadInfo={leadInfo} />}
		</>
	);
}
