import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import fs from 'fs';
import os from 'os';
import path from 'path';
import {
  pruneAnalyticsLines,
  purgeAnalyticsFile,
  retentionConfig,
  purgeCycle,
} from './retention.js';

const NOW = new Date('2026-09-10T00:00:00.000Z');
const daysAgo = (n) => new Date(NOW.getTime() - n * 86400000).toISOString();

let dir;
beforeEach(() => { dir = fs.mkdtempSync(path.join(os.tmpdir(), 'retention-')); });
afterEach(() => { fs.rmSync(dir, { recursive: true, force: true }); });

describe('pruneAnalyticsLines', () => {
  it('drops events older than the cutoff and keeps the rest', () => {
    const lines = [
      JSON.stringify({ event: 'page_view', ts: daysAgo(500) }),
      JSON.stringify({ event: 'page_view', ts: daysAgo(10) }),
    ];
    const { kept, removed } = pruneAnalyticsLines(lines, { now: NOW, days: 425 });
    expect(removed).toBe(1);
    expect(kept).toHaveLength(1);
    expect(JSON.parse(kept[0]).ts).toBe(daysAgo(10));
  });

  it('keeps unparsable and undatable lines', () => {
    const lines = ['non-json', JSON.stringify({ event: 'page_view' })];
    const { kept, removed } = pruneAnalyticsLines(lines, { now: NOW, days: 425 });
    expect(removed).toBe(0);
    expect(kept).toHaveLength(2);
  });

  it('ignores blank lines without counting them', () => {
    const { kept, removed } = pruneAnalyticsLines(['', '   '], { now: NOW, days: 425 });
    expect(kept).toEqual([]);
    expect(removed).toBe(0);
  });
});

describe('purgeAnalyticsFile', () => {
  it('returns zeros when the file does not exist', () => {
    expect(purgeAnalyticsFile(path.join(dir, 'nope.jsonl'), { now: NOW, days: 425 }))
      .toEqual({ removed: 0, kept: 0 });
  });

  it('rewrites the file without expired events', () => {
    const file = path.join(dir, 'events.jsonl');
    fs.writeFileSync(file, [
      JSON.stringify({ event: 'page_view', ts: daysAgo(500) }),
      JSON.stringify({ event: 'cta_click', ts: daysAgo(1) }),
    ].join('\n') + '\n');
    const out = purgeAnalyticsFile(file, { now: NOW, days: 425 });
    expect(out).toEqual({ removed: 1, kept: 1 });
    expect(fs.readFileSync(file, 'utf8').trim().split('\n')).toHaveLength(1);
  });

  it('counts without touching the file in dry run', () => {
    const file = path.join(dir, 'events.jsonl');
    const original = JSON.stringify({ event: 'page_view', ts: daysAgo(500) }) + '\n';
    fs.writeFileSync(file, original);
    expect(purgeAnalyticsFile(file, { now: NOW, days: 425, dryRun: true }).removed).toBe(1);
    expect(fs.readFileSync(file, 'utf8')).toBe(original);
  });
});

describe('retentionConfig', () => {
  it('defaults to enabled and dry run', () => {
    const cfg = retentionConfig({});
    expect(cfg.enabled).toBe(true);
    expect(cfg.dryRun).toBe(true);          // termini segnaposto: non si cancella
    expect(cfg.analyticsDays).toBe(425);
  });

  it('reads the env gates', () => {
    const cfg = retentionConfig({
      RETENTION_ENABLED: 'false',
      RETENTION_DRY_RUN: 'false',
      RETENTION_ANALYTICS_DAYS: '30',
      ANALYTICS_LOG: '/tmp/x.jsonl',
    });
    expect(cfg.enabled).toBe(false);
    expect(cfg.dryRun).toBe(false);
    expect(cfg.analyticsDays).toBe(30);
    expect(cfg.analyticsLog).toBe('/tmp/x.jsonl');
  });

  it('falls back on a non-positive term', () => {
    expect(retentionConfig({ RETENTION_ANALYTICS_DAYS: '0' }).analyticsDays).toBe(425);
    expect(retentionConfig({ RETENTION_ANALYTICS_DAYS: 'x' }).analyticsDays).toBe(425);
  });
});

describe('purgeCycle', () => {
  it('returns null when disabled', () => {
    expect(purgeCycle({ enabled: false })).toBeNull();
  });

  it('purges the analytics log', () => {
    const file = path.join(dir, 'events.jsonl');
    fs.writeFileSync(file, JSON.stringify({ event: 'page_view', ts: daysAgo(500) }) + '\n');
    const out = purgeCycle(
      { enabled: true, dryRun: false, analyticsDays: 425, analyticsLog: file },
      { now: NOW },
    );
    expect(out.analytics.removed).toBe(1);
  });
});
