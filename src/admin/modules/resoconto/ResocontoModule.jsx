import { useEffect, useRef, useState } from 'react';
import { authFetch } from '../../auth';
import { REPORT_SECTIONS } from './sections';
import { buildReportText } from './reportText';
import '../../../globals.css';
import './ResocontoModule.css';

export default function ResocontoModule() {
  const today = new Date().toISOString().slice(0, 10);
  const monthAgo = new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString().slice(0, 10);
  const [from, setFrom] = useState(monthAgo);
  const [to, setTo] = useState(today);

  // Parte deterministica: si aggiorna da sola al cambio date (debounce 400ms).
  const [statsData, setStatsData] = useState(null); // {funnel, stats}
  const [statsLoading, setStatsLoading] = useState(true);
  const [statsError, setStatsError] = useState('');

  // Report completo (con narrativa LLM), solo su richiesta.
  const [report, setReport] = useState(null);
  const [genLoading, setGenLoading] = useState(false);
  const [genError, setGenError] = useState('');

  // Token incrementato ad ogni cambio data e ad ogni generate(): una risposta
  // (stats o report) si applica solo se il token non è cambiato nel frattempo,
  // così una richiesta superata (date cambiate mentre era in volo) non
  // sovrascrive uno stato più fresco.
  const requestToken = useRef(0);

  useEffect(() => {
    requestToken.current += 1;
    const token = requestToken.current;
    let ignore = false;
    setReport(null); // il testo generato vale per le date con cui è stato chiesto
    setGenError('');
    setStatsLoading(true);
    setStatsError('');
    const t = setTimeout(() => {
      authFetch(`/api/report/stats?from=${from}&to=${to}`)
        .then((r) => (r.ok ? r.json() : Promise.reject(new Error(`Errore ${r.status}`))))
        .then((data) => {
          if (ignore || requestToken.current !== token) return;
          setStatsData(data);
        })
        .catch((e) => {
          if (ignore || requestToken.current !== token) return;
          setStatsError(e.message);
        })
        .finally(() => {
          if (ignore || requestToken.current !== token) return;
          setStatsLoading(false);
        });
    }, 400);
    return () => {
      ignore = true;
      clearTimeout(t);
    };
  }, [from, to]);

  async function generate() {
    requestToken.current += 1;
    const token = requestToken.current;
    const genFrom = from;
    const genTo = to;
    setGenLoading(true);
    setGenError('');
    setReport(null);
    try {
      const res = await authFetch(`/api/report?from=${genFrom}&to=${genTo}`);
      if (!res.ok) throw new Error(`Errore ${res.status}`);
      const json = await res.json();
      if (requestToken.current !== token) return; // le date sono cambiate durante la generazione
      setReport({ ...json, from: genFrom, to: genTo });
    } catch (err) {
      if (requestToken.current !== token) return;
      setGenError(err.message);
    } finally {
      setGenLoading(false);
    }
  }

  const text = report ? buildReportText(report) : '';

  return (
    <div className="resoconto-page">
      <div className="resoconto-container">
        <h1>Resoconto</h1>
        <p className="resoconto-subtitle">Statistiche del periodo e report periodico del funnel</p>

        <form className="resoconto-form" onSubmit={(e) => e.preventDefault()}>
          <label>Dal <input type="date" value={from} onChange={(e) => setFrom(e.target.value)} /></label>
          <label>Al <input type="date" value={to} onChange={(e) => setTo(e.target.value)} /></label>
          {statsLoading && <span className="resoconto-loading">Aggiornamento…</span>}
        </form>

        {statsError && <p className="resoconto-error">{statsError}</p>}

        {statsData && REPORT_SECTIONS.map((section) => {
          const { id, title, Component } = section;
          return <Component key={id} title={title} funnel={statsData.funnel} stats={statsData.stats} />;
        })}

        <div className="resoconto-generate">
          <button type="button" onClick={generate} disabled={genLoading || statsLoading}>
            {genLoading ? 'Generazione…' : 'Genera Report'}
          </button>
          {genError && <p className="resoconto-error">{genError}</p>}
          <div className="resoconto-text-block">
            {text && <button type="button" onClick={() => navigator.clipboard?.writeText(text)}>Copia</button>}
            <pre>{text || 'Premi "Genera Report" per generare il commento del periodo.'}</pre>
          </div>
        </div>
      </div>
    </div>
  );
}
