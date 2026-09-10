export function formatInt(n) {
  return (n ?? 0).toLocaleString('it-IT');
}

export function formatPct(ratio) {
  return `${((ratio ?? 0) * 100).toFixed(1)}%`;
}

export function formatDuration(seconds) {
  if (seconds == null) return '—';
  const m = Math.floor(seconds / 60);
  const s = Math.round(seconds % 60);
  return m > 0 ? `${m}m ${s}s` : `${s}s`;
}

// Etichette dei valori di qualificazione (slug del form del sito). Un valore
// sconosciuto resta com'è: meglio uno slug grezzo di una riga che sparisce.
export const PROFILE_LABEL = {
  product_idea: 'Idea di prodotto',
  new_brand: 'Nuovo brand',
  supplement_brand: 'Brand esistente',
  manufacturing_partner: 'Partner produttivo',
};

export const CATEGORY_LABEL = {
  proteins: 'Proteine',
  performance_and_training: 'Performance e allenamento',
  health_and_wellness: 'Salute e benessere',
  weight_management_and_meal_solutions: 'Controllo del peso e pasti',
  drinks_shots_gels: 'Bevande, shot e gel',
  stick_packs_and_single_servings: 'Stick pack e monodose',
  skincare_and_cosmetics: 'Skincare e cosmetici',
  not_sure_yet: 'Non lo so ancora',
};

export const FORMAT_LABEL = {
  powders: 'Polveri',
  capsules_and_tablets: 'Capsule e compresse',
  softgels: 'Softgel',
  gummies: 'Gummies',
  stick_packs: 'Stick pack',
  rtds: 'Pronti da bere (RTD)',
  shots: 'Shot',
  not_sure_yet: 'Non lo so ancora',
};

export const BREAKDOWN_LABELS = {
  by_profile: { title: 'Profilo', labels: PROFILE_LABEL },
  by_category: { title: 'Categoria', labels: CATEGORY_LABEL },
  by_format: { title: 'Formato', labels: FORMAT_LABEL },
};

export function valueLabel(key, value) {
  return BREAKDOWN_LABELS[key]?.labels[value] || value;
}

export const WEEKDAY_LABEL = {
  1: 'Lunedì', 2: 'Martedì', 3: 'Mercoledì', 4: 'Giovedì',
  5: 'Venerdì', 6: 'Sabato', 7: 'Domenica',
};

// L'ordine di queste mappe è anche l'ordine delle fette nelle torte: tenendolo
// fisso, il colore di ogni categoria resta stabile al cambio delle date.
export const DEVICE_LABEL = {
  mobile: 'Telefono',
  tablet: 'Tablet',
  desktop: 'Computer',
  other: 'Altro',
};

export const BROWSER_LABEL = {
  chrome: 'Chrome',
  safari: 'Safari',
  firefox: 'Firefox',
  edge: 'Edge',
  opera: 'Opera',
  samsung: 'Samsung Internet',
  other: 'Altro',
};
