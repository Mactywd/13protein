import { formatInt, formatPct, formatDuration, WEEKDAY_LABEL, BREAKDOWN_LABELS, valueLabel } from './format';

// Testo esportabile del Resoconto (stile messaggio Slack: *bold* + :emoji:).
// Tutti i numeri sono deterministici (funnel + stats); la narrativa LLM copre
// solo i giudizi: friction_text e recommendations.
export function buildReportText({ funnel, stats, narrative, from, to }) {
  const fromLabel = new Date(from).toLocaleDateString('it-IT', { day: 'numeric', month: 'short', year: 'numeric' });
  const toLabel = new Date(to).toLocaleDateString('it-IT', { day: 'numeric', month: 'short', year: 'numeric' });

  // Colonne fisse (label / conteggio / percentuali) così i numeri e le
  // percentuali di righe diverse cadono sempre nella stessa colonna.
  const pct = (ratio) => formatPct(ratio).padStart(6);
  const count = (n) => formatInt(n).padStart(6);

  const funnelRow = (label, value, prev) => {
    const pcts = prev == null ? '' :
      `   ${pct(prev ? value / prev : 0)} del passo prec.   ${pct(funnel.page_views ? value / funnel.page_views : 0)} del totale`;
    return `${label.padEnd(17)}${count(value)}${pcts}`;
  };

  const topicLines = (stats.top_topics || [])
    .map((t) => `• ${t.doc}: ${formatInt(t.count)}`)
    .join('\n');

  const weekdayLines = (stats.by_weekday || [])
    .map((d) => `${String(WEEKDAY_LABEL[d.weekday] || d.weekday).padEnd(17)}${count(d.count)}   ${pct(d.share)} del totale`)
    .join('\n');

  const breakdownBlocks = Object.entries(BREAKDOWN_LABELS)
    .map(([key, meta]) => {
      const rows = stats[key] || [];
      if (rows.length === 0) return '';
      const lines = rows
        .map((r) => `\`${r.total}\` conversazioni (${formatPct(stats.total_sessions ? r.total / stats.total_sessions : 0)}) su _${valueLabel(key, r.value)}_, completate al \`${formatPct(r.completion_rate)}\`.`)
        .join('\n');
      return `\n*${meta.title}*\n${lines}`;
    })
    .join('\n');

  const recommendations = (narrative.recommendations || [])
    .map((r) => `• ${r}`)
    .join('\n');

  const o = stats.outcomes;
  const outcomesBlock = o ? `
*Esiti delle conversazioni*
${'Completate'.padEnd(17)}${count(o.completed)}   ${pct(o.completed_share)} del totale
${'Abbandonate'.padEnd(17)}${count(o.abandoned)}   ${pct(o.abandoned_share)} del totale
${'Inizializzate'.padEnd(17)}${count(o.initialized)}   ${pct(o.initialized_share)} del totale
` : '';

  const quote = stats.quote || { requested: 0, qualified: 0, rate: 0 };

  return `*13 Protein* — ${fromLabel} – ${toLabel} :calendar:

*Funnel*
${funnelRow('Page views', funnel.page_views)}    (visitatori unici: ${formatInt(funnel.unique_visitors)})
${funnelRow('CTA clicks', funnel.cta_clicks, funnel.page_views)}
${funnelRow('Chat completes', funnel.chat_completes, funnel.cta_clicks)}
${funnelRow('Preventivi', funnel.quote_requests, funnel.chat_completes)}
${outcomesBlock}
*Conversazioni per giorno della settimana* :calendar:
${weekdayLines}

*Pagine del knowledgebase più citate* :books:
${topicLines}

*Analisi del flusso* :bar_chart:
${breakdownBlocks}

*Richieste di preventivo*
${formatInt(quote.requested)} conversazioni su ${formatInt(quote.qualified)} qualificate (${formatPct(quote.rate)}) hanno chiesto un preventivo.

*Durata*
La durata mediana delle sessioni completate è di ${formatDuration(stats.duration?.median_seconds)}, mentre la media è ${formatDuration(stats.duration?.mean_seconds)}.

*Friction & bottleneck*
${narrative.friction_text || ''}

*Migliorie consigliate*
${recommendations}`;
}
