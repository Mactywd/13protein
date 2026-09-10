export function formatDate(iso) {
  if (!iso) return '—';
  return new Date(iso).toLocaleString('it-IT',
    { day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' });
}

export function formatDuration(seconds) {
  if (seconds == null) return '—';
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return m > 0 ? `${m}m ${s}s` : `${s}s`;
}

export function formatCost(cost) {
  return `$${(cost || 0).toFixed(4)}`;
}

// Profilo dichiarato nella chat, in forma breve per la colonna Anteprima.
export const PROFILE_LABEL = {
  product_idea: 'Idea di prodotto',
  new_brand: 'Nuovo brand',
  supplement_brand: 'Brand esistente',
  manufacturing_partner: 'Partner produttivo',
};

export function profileLabel(c) {
  if (!c.profile) return null;
  return PROFILE_LABEL[c.profile] || c.profile;
}

export const STATUS_LABEL = { completata: 'Completata', in_corso: 'In corso', abbandonata: 'Abbandonata', inizializzata: 'Inizializzata' };
export const EVAL_LABEL = { done: 'Pronta', pending: 'In elaborazione', error: 'Errore' };
export const OUTCOME_LABEL = { completed: 'Completata', abandoned: 'Abbandonata', error: 'Errore' };
