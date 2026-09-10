// Rilevamento grossolano di dispositivo e browser, lato client.
// Funzioni pure: ricevono i dati del browser come argomenti, così sono
// testabili in node senza DOM.
//
// Perché lato client e non dallo user-agent nella request: iPadOS 13+ si
// dichiara "Macintosh", quindi lato server un iPad è indistinguibile da un Mac
// desktop. Qui possiamo incrociare navigator.maxTouchPoints.
//
// Al server arrivano SOLO queste etichette, mai lo user-agent grezzo, che non
// viene né trasmesso né registrato (minimizzazione GDPR — vedi
// server/lib/segments.js per la whitelist lato server).

export function detectDevice({ ua, maxTouchPoints = 0 } = {}) {
  if (typeof ua !== 'string' || !ua) return 'other';
  // iPadOS 13+ si dichiara Macintosh: l'unico segnale rimasto è il touch.
  if (/iPad/.test(ua) || (/Macintosh/.test(ua) && maxTouchPoints > 1)) return 'tablet';
  // Silk (Kindle Fire) e PlayBook contengono "Android": vanno controllati prima.
  if (/Tablet|PlayBook|Silk/.test(ua)) return 'tablet';
  // Su Android il token "Mobile" è presente sui telefoni e assente sui tablet.
  if (/Android/.test(ua)) return /Mobile/.test(ua) ? 'mobile' : 'tablet';
  if (/Mobi|iPhone|iPod|Windows Phone/.test(ua)) return 'mobile';
  if (/Macintosh|Windows|CrOS|X11|Linux/.test(ua)) return 'desktop';
  return 'other';
}

export function detectBrowser(ua) {
  if (typeof ua !== 'string' || !ua) return 'other';
  // L'ordine è obbligatorio: Edge, Opera e Samsung Internet contengono tutti il
  // token "Chrome". Su iOS ogni browser è WebKit e si distingue solo dal token
  // proprietario (CriOS/FxiOS/EdgiOS).
  if (/\bEdg(A|iOS)?\//.test(ua)) return 'edge';
  if (/\bOPR\/|\bOPiOS\/|\bOpera\//.test(ua)) return 'opera';
  if (/SamsungBrowser\//.test(ua)) return 'samsung';
  if (/Firefox\/|FxiOS\//.test(ua)) return 'firefox';
  if (/CriOS\/|Chrome\/|Chromium\//.test(ua)) return 'chrome';
  if (/Safari\//.test(ua)) return 'safari';
  return 'other';
}
