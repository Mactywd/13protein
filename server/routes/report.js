import fs from 'fs';
import readline from 'readline';
import { DEVICES, BROWSERS, normalizeSegment } from '../lib/segments.js';

const backendUrl = () => process.env.BACKEND_URL || 'http://localhost:8000';
const analyticsLog = () => process.env.ANALYTICS_LOG || './data/analytics/events.jsonl';

export async function computeFunnel(from, to) {
  const funnel = {
    page_views: 0,
    unique_visitors: 0,
    cta_clicks: 0,
    chat_completes: 0,
    quote_requests: 0,
    // Distribuzione dei visitatori unici per dispositivo e browser. `base` è il
    // numero di visitatori per cui il dato esiste: gli eventi precedenti al
    // rilascio della feature non hanno i campi e restano fuori (nessun backfill).
    visitor_segments: { base: 0, device: {}, browser: {} },
  };
  const file = analyticsLog();
  if (!fs.existsSync(file)) return funnel;

  const fromTs = new Date(`${from}T00:00:00.000Z`).getTime();
  const toTs = new Date(`${to}T23:59:59.999Z`).getTime();
  const visitors = new Set();
  const segments = new Map(); // visitor_id → {device, browser}, vince il primo page_view

  const rl = readline.createInterface({ input: fs.createReadStream(file) });
  for await (const line of rl) {
    if (!line.trim()) continue;
    let rec;
    try { rec = JSON.parse(line); } catch { continue; }
    const ts = new Date(rec.ts).getTime();
    if (Number.isNaN(ts) || ts < fromTs || ts > toTs) continue;
    if (rec.testing === true) continue; // exclude tester traffic (parity with backend is_testing filter)
    if (rec.event === 'page_view') {
      funnel.page_views += 1;
      if (rec.visitor_id) {
        visitors.add(rec.visitor_id);
        if (rec.device && rec.browser && !segments.has(rec.visitor_id)) {
          segments.set(rec.visitor_id, {
            device: normalizeSegment(rec.device, DEVICES),
            browser: normalizeSegment(rec.browser, BROWSERS),
          });
        }
      }
    }
    else if (rec.event === 'cta_click') funnel.cta_clicks += 1;
    else if (rec.event === 'chat_complete') funnel.chat_completes += 1;
    else if (rec.event === 'quote_request') funnel.quote_requests += 1;
  }
  funnel.unique_visitors = visitors.size;
  for (const { device, browser } of segments.values()) {
    funnel.visitor_segments.device[device] = (funnel.visitor_segments.device[device] || 0) + 1;
    funnel.visitor_segments.browser[browser] = (funnel.visitor_segments.browser[browser] || 0) + 1;
  }
  funnel.visitor_segments.base = segments.size;
  return funnel;
}

// Solo la parte deterministica (funnel JSONL + stats SQL del backend), senza
// narrativa LLM: alimenta l'aggiornamento istantaneo del Resoconto al cambio date.
export async function reportStats(req, res) {
  const { from, to } = req.query;
  if (!from || !to) return res.status(400).json({ error: 'Parametri from/to richiesti (YYYY-MM-DD)' });

  const [funnel, backendRes] = await Promise.all([
    computeFunnel(from, to),
    fetch(`${backendUrl()}/report?from=${encodeURIComponent(from)}&to=${encodeURIComponent(to)}&narrative=false`),
  ]);
  if (!backendRes.ok) return res.status(backendRes.status).json({ error: 'Errore dal backend' });
  const { stats } = await backendRes.json();
  res.json({ funnel, stats });
}

export default async function report(req, res) {
  const { from, to } = req.query;
  if (!from || !to) return res.status(400).json({ error: 'Parametri from/to richiesti (YYYY-MM-DD)' });

  const [funnel, backendRes] = await Promise.all([
    computeFunnel(from, to),
    fetch(`${backendUrl()}/report?from=${encodeURIComponent(from)}&to=${encodeURIComponent(to)}`),
  ]);
  if (!backendRes.ok) return res.status(backendRes.status).json({ error: 'Errore dal backend' });
  const { stats, narrative } = await backendRes.json();
  res.json({ funnel, stats, narrative });
}
