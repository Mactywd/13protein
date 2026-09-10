import "./LeadSummary.css";
import { useLanguage } from "../../contexts/LanguageContext";

// L'ordine è quello del flusso, non quello dell'oggetto: il riepilogo si legge
// come la conversazione appena fatta.
const ORDER = [
	"profile",
	"category",
	"format",
	"projectDescription",
	"questionsAsked",
	"topicsCited",
	"quoteRequested",
	"contact",
];

export default function LeadSummary({ scrollRef, leadInfo }) {
	const { t } = useLanguage();
	const labels = t.leadSummary.fields;

	function renderValue(key) {
		const value = leadInfo?.[key];
		if (key === "quoteRequested") return value ? t.leadSummary.yes : t.leadSummary.no;
		if (key === "contact") {
			const parts = [value?.name, value?.company, value?.email].filter(Boolean);
			return parts.length ? parts.join(" · ") : t.leadSummary.empty;
		}
		if (Array.isArray(value)) {
			return value.length ? (
				<ul className="lead-summary-list">
					{value.map((item, i) => (
						<li key={i}>{item}</li>
					))}
				</ul>
			) : (
				t.leadSummary.empty
			);
		}
		return value || t.leadSummary.empty;
	}

	return (
		<section className="lead-summary" ref={scrollRef}>
			<div className="container">
				<h2 className="lead-summary-title">{t.leadSummary.title}</h2>
				<p className="lead-summary-subtitle">{t.leadSummary.subtitle}</p>
				<dl className="lead-summary-grid">
					{ORDER.map((key) => (
						<div className="lead-summary-row" key={key}>
							<dt>{labels[key]}</dt>
							<dd>{renderValue(key)}</dd>
						</div>
					))}
				</dl>
			</div>
		</section>
	);
}
