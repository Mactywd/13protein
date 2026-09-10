// Minimal in-memory sliding-window rate limiter for the public API routes.
// One Node process serves everything (no cluster), so a Map is enough — the
// goal is blunting brute-force logins and runaway/abusive clients, not
// precise quota accounting. Entries are pruned lazily on each hit and by a
// periodic sweep so the map can't grow unbounded.

const buckets = new Map(); // key -> [timestamps]

const SWEEP_INTERVAL_MS = 10 * 60 * 1000;
const sweeper = setInterval(() => {
  const now = Date.now();
  for (const [key, hits] of buckets) {
    // Windows are ≤ 15 min; anything older than that is dead weight.
    const alive = hits.filter((t) => now - t < 15 * 60 * 1000);
    if (alive.length === 0) buckets.delete(key);
    else buckets.set(key, alive);
  }
}, SWEEP_INTERVAL_MS);
sweeper.unref(); // don't keep the process alive for the sweeper

function clientIp(req) {
  // trust proxy is set in index.js, so req.ip is the Traefik-forwarded client IP.
  return req.ip || req.socket?.remoteAddress || 'unknown';
}

/**
 * rateLimit('login', { windowMs: 300000, max: 10 }) → Express middleware.
 * Responds 429 when the same IP exceeds `max` hits in the last `windowMs`.
 */
export function rateLimit(name, { windowMs, max }) {
  return (req, res, next) => {
    const key = `${name}:${clientIp(req)}`;
    const now = Date.now();
    const hits = (buckets.get(key) || []).filter((t) => now - t < windowMs);
    if (hits.length >= max) {
      buckets.set(key, hits);
      return res.status(429).json({ error: 'Troppe richieste, riprova tra poco.' });
    }
    hits.push(now);
    buckets.set(key, hits);
    next();
  };
}

// Test hook.
export function _resetRateLimits() {
  buckets.clear();
}
