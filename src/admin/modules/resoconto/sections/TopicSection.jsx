import SectionCard from './SectionCard';
import { formatInt, formatPct } from '../format';

// Pagine del knowledgebase più citate nelle risposte, e quota di conversazioni
// che sono arrivate a chiedere un preventivo.
export default function TopicSection({ title, stats }) {
  const top = stats?.top_topics;
  const quote = stats?.quote;
  if (!top?.length && !quote) return null;

  return (
    <SectionCard title={title}>
      {top?.length > 0 && (
        <>
          <h3>Pagine più citate</h3>
          <table className="resoconto-path-table">
            <thead><tr><th>Pagina</th><th>Citazioni</th></tr></thead>
            <tbody>
              {top.map((t) => (
                <tr key={t.doc}><td>{t.doc}</td><td>{formatInt(t.count)}</td></tr>
              ))}
            </tbody>
          </table>
        </>
      )}
      {quote && (
        <>
          <h3>Richieste di preventivo</h3>
          <table className="resoconto-path-table">
            <thead><tr><th></th><th>Conversazioni</th><th>Percentuale</th></tr></thead>
            <tbody>
              <tr>
                <td>Preventivo richiesto</td>
                <td>{formatInt(quote.requested)} su {formatInt(quote.qualified)}</td>
                <td>{formatPct(quote.rate)}</td>
              </tr>
            </tbody>
          </table>
        </>
      )}
    </SectionCard>
  );
}
