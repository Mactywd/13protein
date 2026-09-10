import SectionCard from './SectionCard';
import { formatInt, formatPct, BREAKDOWN_LABELS, valueLabel } from '../format';

// Un blocco per colonna di qualificazione (profilo, categoria, formato):
// conversazioni, completate e tasso di completamento.
export default function QualificazioneSection({ title, stats }) {
  const blocks = Object.entries(BREAKDOWN_LABELS)
    .map(([key, meta]) => ({ key, meta, rows: stats?.[key] || [] }))
    .filter((b) => b.rows.length > 0);
  if (blocks.length === 0) return null;

  return (
    <SectionCard title={title}>
      {blocks.map(({ key, meta, rows }) => (
        <div key={key}>
          <h3>{meta.title}</h3>
          <table className="resoconto-path-table">
            <thead>
              <tr><th>{meta.title}</th><th>Conversazioni</th><th>Completate</th><th>Completamento</th></tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.value}>
                  <td>{valueLabel(key, r.value)}</td>
                  <td>{formatInt(r.total)}</td>
                  <td>{formatInt(r.completed)}</td>
                  <td>{formatPct(r.completion_rate)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ))}
    </SectionCard>
  );
}
