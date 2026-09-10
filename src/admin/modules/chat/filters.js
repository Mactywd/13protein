/**
 * I due filtri della lista Chat, come funzioni pure: qui non esiste jsdom,
 * quindi la logica che merita un test sta fuori dai componenti.
 *
 * Slug e valori dei parametri in inglese, etichette in italiano: la stessa
 * divisione dei parametri esistenti `from`/`to` e di `STATUS_LABEL`.
 */

/**
 * Le quattro voci del filtro profilo. `value` è quello che il backend scrive in
 * `sessions.profile` (slug del form del sito) ed è anche lo slug che finisce
 * nella URL; `label` è quello che legge l'admin.
 */
export const PROFILES = [
  { value: 'product_idea', label: 'Idea di prodotto' },
  { value: 'new_brand', label: 'Nuovo brand' },
  { value: 'supplement_brand', label: 'Brand esistente' },
  { value: 'manufacturing_partner', label: 'Partner produttivo' },
];

const BY_VALUE = new Map(PROFILES.map((p) => [p.value, p]));

/** Slug validi da `?profiles=a,b`. Una URL manomessa non deve far esplodere nulla. */
export function parseProfiles(param) {
  if (typeof param !== 'string' || !param) return [];
  const out = [];
  for (const raw of param.split(',')) {
    const slug = raw.trim();
    if (BY_VALUE.has(slug) && !out.includes(slug)) out.push(slug);
  }
  return out;
}

/**
 * Selezione → valore del parametro, o `null` per toglierlo dalla URL.
 * Selezionare tutte le voci equivale a non selezionarne nessuna: normalizzato a
 * vuoto, così la URL non si gonfia e l'etichetta torna a «tutti».
 */
export function serializeProfiles(slugs) {
  if (!slugs || slugs.length === 0 || slugs.length === PROFILES.length) return null;
  return slugs.join(',');
}

/** La chat appartiene a uno dei profili selezionati? Selezione vuota = nessun filtro. */
export function matchesProfiles(chat, slugs) {
  if (!slugs || slugs.length === 0) return true;
  return slugs.includes(chat.profile);
}

/** Filtro di stato. Valore assente o ignoto = nessun filtro. */
export function matchesStatus(chat, status) {
  if (status === 'completed') return chat.status === 'completata';
  if (status === 'quoted') return chat.quote_requested === true;
  return true;
}
