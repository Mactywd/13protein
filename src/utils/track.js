import { detectDevice, detectBrowser } from './clientEnv.js';
import { isTestingPath } from './route.js';

const VISITOR_KEY = 'agent13_visitor_id';

/**
 * Stable per-browser visitor id (localStorage). Created on first use.
 * Used to count unique visitors in the Resoconto report (dedupes refreshes).
 */
export function getVisitorId() {
  try {
    let id = localStorage.getItem(VISITOR_KEY);
    if (!id) {
      id = (crypto?.randomUUID?.() || `v-${Date.now()}-${Math.random().toString(36).slice(2)}`);
      localStorage.setItem(VISITOR_KEY, id);
    }
    return id;
  } catch {
    return 'unknown';
  }
}

/**
 * Fire-and-forget analytics event.
 * Never throws — any error is swallowed silently.
 * `testing` is derived from the /testing route so tester traffic can be excluded
 * from the funnel. keepalive:true ensures delivery on unmount (e.g. cta_click).
 * `device`/`browser` sono due etichette grossolane (vedi clientEnv.js): lo
 * user-agent grezzo non viene mai trasmesso.
 */
export function trackEvent(event, lang = 'unknown') {
  try {
    // Stessa normalizzazione del router (utils/route.js): "/en/testing" è la
    // route di test quanto "/testing", e il suo traffico non è produzione.
    const testing = typeof window !== 'undefined' && isTestingPath(window.location.pathname);
    fetch('/api/track', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        event,
        lang,
        testing,
        visitor_id: getVisitorId(),
        device: detectDevice({ ua: navigator?.userAgent, maxTouchPoints: navigator?.maxTouchPoints }),
        browser: detectBrowser(navigator?.userAgent),
      }),
      keepalive: true,
    }).catch(() => {});
  } catch {
    // ignore synchronous errors
  }
}
