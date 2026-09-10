// Palette dei grafici admin (solo light: card bianche su crema).
// Valori dalla palette di riferimento validata CVD (dataviz): i primi 3 slot
// categorici passano il check all-pairs; la rampa funnel è ordinale blu.
export const SERIES = { blue: '#2a78d6', orange: '#eb6834', aqua: '#1baf7a' };

// Esiti conversazioni: identità portata da legenda+etichette, mai dal solo colore.
export const OUTCOME_COLORS = {
  completate: SERIES.blue,
  abbandonate: SERIES.orange,
  inizializzate: SERIES.aqua,
};

export const FUNNEL_RAMP = ['#86b6ef', '#6da7ec', '#3987e5', '#256abf', '#1c5cab'];

// Palette categorica per pie chart a più fette (taglie, percorsi, giorni della
// settimana): l'identità è sempre portata da etichette+legenda, mai dal solo colore.
export const PALETTE = [
  SERIES.blue, SERIES.orange, SERIES.aqua, '#8a5cd6',
  '#d64d8a', '#b7a11c', '#4d9fb8', '#8a8a8a',
];

export const INK = {
  text: '#333333',   // testo primario admin
  muted: '#8a8a8a',  // etichette assi
  grid: '#e1e0d9',   // hairline griglia
};
