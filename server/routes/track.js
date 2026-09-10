import { trackEvent } from '../lib/analytics.js';
import { DEVICES, BROWSERS, normalizeSegment } from '../lib/segments.js';

const ALLOWED_EVENTS = new Set(['page_view', 'cta_click', 'chat_complete', 'quote_request']);

export default function track(req, res) {
  // Respond immediately — never block the client
  res.sendStatus(204);

  try {
    const { event, lang, testing, visitor_id, device, browser } = req.body;

    if (!ALLOWED_EVENTS.has(event)) return;

    // Data minimization (GDPR): no IP, no user-agent — il funnel usa l'evento,
    // il visitor_id casuale, la lingua e due etichette grossolane di
    // dispositivo/browser prese da un insieme chiuso (lib/segments.js).
    trackEvent({
      event,
      lang: lang || 'unknown',
      testing: testing === true,
      visitor_id: typeof visitor_id === 'string' ? visitor_id : null,
      device: normalizeSegment(device, DEVICES),
      browser: normalizeSegment(browser, BROWSERS),
    });
  } catch (err) {
    console.error('[analytics] track handler error:', err.message);
  }
}
