// Etichette ammesse per la segmentazione analytics (dispositivo / browser).
//
// Unica fonte di verità: usata in scrittura da routes/track.js e in lettura da
// routes/report.js. Il client (src/utils/clientEnv.js) fa solo la detection;
// qualunque valore non previsto — bundle vecchio in cache, client manomesso,
// campo assente — degrada a 'other'. Nel log finiscono quindi solo etichette di
// un insieme chiuso: lo user-agent grezzo viene letto solo localmente dal client
// per la detection, non viene mai trasmesso né scritto nel log.

export const DEVICES = ['mobile', 'tablet', 'desktop', 'other'];
export const BROWSERS = ['chrome', 'safari', 'firefox', 'edge', 'opera', 'samsung', 'other'];

export function normalizeSegment(value, allowed) {
  return allowed.includes(value) ? value : 'other';
}
