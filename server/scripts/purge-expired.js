#!/usr/bin/env node
/**
 * Purge di retention manuale, lato Node: il JSONL degli analytics. La metà su
 * Postgres sta nel backend: `python -m scripts.purge_expired`.
 *
 *   node server/scripts/purge-expired.js                 # dry run: solo conteggi
 *   node server/scripts/purge-expired.js --apply         # cancella davvero
 *   node server/scripts/purge-expired.js --analytics-days 400
 *
 * In docker:
 *   docker compose -f docker-compose.prod.yml exec app \
 *       node server/scripts/purge-expired.js
 *
 * Il dry run è il default: la cancellazione è definitiva e non raggiunge i
 * backup. Il server esegue lo stesso purge una volta al giorno da sé; questo
 * script serve a guardare i conteggi a mano.
 */
import { purgeAnalyticsFile, retentionConfig } from '../lib/retention.js';

const cfg = retentionConfig();

function flag(name, fallback) {
  const i = process.argv.indexOf(`--${name}`);
  if (i === -1) return fallback;
  const value = Number(process.argv[i + 1]);
  return Number.isFinite(value) && value > 0 ? value : fallback;
}

const apply = process.argv.includes('--apply');
// Termine segnaposto (14 mesi, esenzione analytics): da fissare con il titolare.
const analyticsDays = flag('analytics-days', cfg.analyticsDays);
const now = new Date();

const analytics = purgeAnalyticsFile(cfg.analyticsLog, {
  now, days: analyticsDays, dryRun: !apply,
});

console.log(`Righe ${apply ? 'ELIMINATE' : 'da eliminare (dry run)'}:`);
console.log(`  eventi analytics (>${analyticsDays}g)   ${analytics.removed}  (restano ${analytics.kept})`);
if (!apply) console.log('\nNulla è stato toccato. Rilancia con --apply per eseguire.');
