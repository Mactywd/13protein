/**
 * La lingua vive nel prefisso "/it" dell'URL (vedi LanguageContext): l'inglese
 * è il default e non ha prefisso. Ogni confronto sul percorso va quindi fatto
 * sulla forma *spogliata* del prefisso, altrimenti la stessa pagina si comporta
 * in due modi diversi nelle due lingue.
 *
 * Sta qui, e non dentro App.jsx, perché non è il router l'unico a doverlo
 * sapere: `track.js` decide da questo se un evento è traffico di test. Nella
 * repo di origine le due copie avevano divergito e "/en/testing" mandava
 * page_view, cta_click e chat_complete nel funnel di produzione: cima del
 * funnel gonfiata e conversione depressa.
 */

/** Percorso senza barra finale e senza il prefisso di lingua. */
export function normalizePath(pathname) {
  const path = String(pathname || '').replace(/\/+$/, '') || '/';
  if (path === '/it') return '/';
  if (path.startsWith('/it/')) return path.slice(3) || '/';
  return path;
}

/** La route di test, in una lingua qualsiasi. */
export function isTestingPath(pathname) {
  return normalizePath(pathname) === '/testing';
}
