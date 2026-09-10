/**
 * Retention purge, lato Node — art. 5.1.e GDPR.
 *
 * Il backend Python fa la sua parte su Postgres (transcript, stato di sessione,
 * valutazioni); qui si copre l'unico archivio che vive su disco: il JSONL degli
 * analytics. Stesse regole di retention.py: si contano le righe, non si logga
 * mai il contenuto, e in caso di dubbio si conserva — una riga che non si
 * riesce a leggere o a datare resta dov'è, perché cancellare a intuito è
 * peggio che tenere.
 *
 * `retentionConfig`/`purgeCycle` rispecchiano `retention.purge_cycle` del
 * backend: stessa variabile d'ambiente, stesso default, così le due metà del
 * purge si accendono con una decisione sola invece che con due.
 *
 * I termini sono **segnaposto** finché non li fissa il titolare: per questo il
 * default qui è il dry run, a differenza dell'Alchimista dove erano approvati.
 */
import fs from 'fs';

const cutoffOf = ({ now, days }) => new Date((now ?? new Date()).getTime() - days * 86400000);

/** Divide le righe JSONL fra quelle da tenere e il conteggio di quelle scartate. */
export function pruneAnalyticsLines(lines, { now, days }) {
  const cutoff = cutoffOf({ now, days });
  const kept = [];
  let removed = 0;

  for (const line of lines) {
    if (!line.trim()) continue;
    let event;
    try {
      event = JSON.parse(line);
    } catch {
      kept.push(line);                             // illeggibile → si tiene
      continue;
    }
    const ts = event && event.ts ? new Date(event.ts) : null;
    if (!ts || Number.isNaN(ts.getTime()) || ts >= cutoff) {
      kept.push(line);
    } else {
      removed++;
    }
  }
  return { kept, removed };
}

/**
 * Riscrive il log analytics senza gli eventi scaduti.
 * Scrittura su temporaneo e rename: un crash a metà purge non deve troncare il log.
 */
export function purgeAnalyticsFile(file, { now, days, dryRun = false } = {}) {
  if (!fs.existsSync(file)) return { removed: 0, kept: 0 };

  const lines = fs.readFileSync(file, 'utf8').split('\n');
  const { kept, removed } = pruneAnalyticsLines(lines, { now, days });

  if (!dryRun && removed > 0) {
    const tmp = `${file}.tmp`;
    fs.writeFileSync(tmp, kept.length ? kept.join('\n') + '\n' : '', 'utf8');
    fs.renameSync(tmp, file);
  }
  return { removed, kept: kept.length };
}

const bool = (value, fallback) => {
  if (value === undefined || value === '') return fallback;
  return !['false', '0', 'no', 'off'].includes(String(value).trim().toLowerCase());
};

const days = (value, fallback) => {
  const n = Number(value);
  return Number.isFinite(n) && n > 0 ? n : fallback;
};

/**
 * Termini **segnaposto**, da fissare con il titolare prima di pubblicare
 * un'informativa. Stesso cancello del backend (`RETENTION_ENABLED` /
 * `RETENTION_DRY_RUN`): finché i termini sono provvisori il default è contare
 * senza cancellare.
 */
export function retentionConfig(env = process.env) {
  return {
    enabled: bool(env.RETENTION_ENABLED, true),
    dryRun: bool(env.RETENTION_DRY_RUN, true),
    analyticsDays: days(env.RETENTION_ANALYTICS_DAYS, 425),  // 14 mesi, esenzione analytics
    analyticsLog: env.ANALYTICS_LOG || './data/analytics/events.jsonl',
  };
}

/** Una passata sul JSONL. Restituisce null quando è disabilitato; solo conteggi. */
export function purgeCycle(cfg = retentionConfig(), { now } = {}) {
  if (!cfg.enabled) return null;
  const analytics = purgeAnalyticsFile(cfg.analyticsLog, {
    now, days: cfg.analyticsDays, dryRun: cfg.dryRun,
  });
  return { analytics };
}

const PURGE_INTERVAL_MS = 24 * 60 * 60 * 1000;

/**
 * Purge giornaliero, avviato al boot: rispecchia `_retention_purge_loop` in
 * main.py. Logga conteggi, mai contenuto. Un errore non deve buttare giù il server.
 */
export function startRetentionLoop({ intervalMs = PURGE_INTERVAL_MS, env = process.env } = {}) {
  const run = () => {
    try {
      const cfg = retentionConfig(env);
      const counts = purgeCycle(cfg);
      if (!counts) return;
      console.log(
        `retention purge (${cfg.dryRun ? 'dry-run' : 'applied'}): ` +
        `analytics=${counts.analytics.removed}`,
      );
    } catch (err) {
      console.error('retention purge failed:', err.message);
    }
  };

  // La prima passata non gira dentro la callback di `listen`: è I/O sincrono
  // sull'intero JSONL e lì bloccherebbe l'avvio proprio mentre il server
  // comincia ad accettare connessioni. Rimandata al tick successivo, il boot
  // resta pulito. Resta sincrona dentro: analytics.js scrive con
  // appendFileSync, e quella sincronia è ciò che impedisce a un evento di
  // finire nel file vecchio e sparire al rename.
  const first = setTimeout(run, 0);
  first.unref?.();
  const timer = setInterval(run, intervalMs);
  timer.unref?.();
  return timer;
}
