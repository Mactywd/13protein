import { describe, it, expect } from 'vitest';
import { buildReportText } from './reportText';

const base = {
  from: '2026-07-01',
  to: '2026-07-20',
  funnel: {
    page_views: 100, unique_visitors: 60, cta_clicks: 40,
    chat_completes: 10, quote_requests: 4,
  },
  stats: {
    total_sessions: 20,
    outcomes: {
      completed: 10, abandoned: 6, initialized: 4, in_progress: 0,
      decided_total: 20,
      completed_share: 0.5, abandoned_share: 0.3, initialized_share: 0.2,
    },
    by_profile: [
      { value: 'product_idea', total: 12, completed: 8, completion_rate: 8 / 12 },
    ],
    by_category: [
      { value: 'proteins', total: 9, completed: 6, completion_rate: 6 / 9 },
    ],
    by_format: [
      { value: 'powders', total: 7, completed: 5, completion_rate: 5 / 7 },
    ],
    quote: { requested: 5, qualified: 10, rate: 0.5 },
    duration: { median_seconds: 120, mean_seconds: 150 },
    by_weekday: [{ weekday: 1, count: 20, share: 1 }],
    top_topics: [{ doc: 'quality', count: 5 }],
  },
  narrative: {
    friction_text: 'Nessun attrito.',
    recommendations: ['fai X'],
  },
};

describe('buildReportText', () => {
  it('include la sezione esiti con le percentuali in colonna', () => {
    const text = buildReportText(base);
    expect(text).toContain('*Esiti delle conversazioni*');
    expect(text).toContain('Completate           10    50.0% del totale');
    expect(text).toContain('Abbandonate           6    30.0% del totale');
    expect(text).toContain('Inizializzate         4    20.0% del totale');
  });

  it('conta i preventivi nel funnel al posto degli acquisti', () => {
    const text = buildReportText(base);
    expect(text).toContain('Preventivi');
    expect(text).not.toContain('Add to cart');
  });

  it('rende un blocco per ogni colonna di qualificazione, con le etichette', () => {
    const text = buildReportText(base);
    expect(text).toContain('*Profilo*');
    expect(text).toContain('Idea di prodotto');
    expect(text).toContain('*Categoria*');
    expect(text).toContain('Proteine');
    expect(text).toContain('*Formato*');
    expect(text).toContain('Polveri');
  });

  it('elenca le pagine del knowledgebase citate', () => {
    expect(buildReportText(base)).toContain('• quality: 5');
  });

  it('riporta la quota di richieste di preventivo', () => {
    expect(buildReportText(base)).toContain('5 conversazioni su 10 qualificate (50.0%)');
  });

  it('interpola la narrativa senza produrre numeri propri', () => {
    const text = buildReportText(base);
    expect(text).toContain('Nessun attrito.');
    expect(text).toContain('• fai X');
  });

  it('sopravvive a stats e narrativa vuote', () => {
    const text = buildReportText({
      from: '2026-07-01', to: '2026-07-20',
      funnel: { page_views: 0, unique_visitors: 0, cta_clicks: 0, chat_completes: 0, quote_requests: 0 },
      stats: {}, narrative: {},
    });
    expect(text).toContain('*13 Protein*');
  });
});
