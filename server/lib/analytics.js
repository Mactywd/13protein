import fs from 'fs';
import path from 'path';

const LOG_FILE = process.env.ANALYTICS_LOG || './data/analytics/events.jsonl';
const LOG_DIR = path.dirname(LOG_FILE);

// Ensure directory exists on startup (mirrors recipe-store.js)
if (!fs.existsSync(LOG_DIR)) {
  fs.mkdirSync(LOG_DIR, { recursive: true });
}

export function trackEvent(fields) {
  try {
    const record = { ts: new Date().toISOString(), ...fields };
    fs.appendFileSync(LOG_FILE, JSON.stringify(record) + '\n', 'utf8');
  } catch (err) {
    console.error('[analytics] write failed:', err.message);
  }
}
