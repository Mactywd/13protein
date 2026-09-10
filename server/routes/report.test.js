import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import fs from 'fs';
import os from 'os';
import path from 'path';

// Originali: usano vi.stubEnv e vi.resetModules
let tmpFile;

async function loadReportModule() {
  vi.resetModules();
  return import('./report.js');
}

describe('GET /api/report funnel computation', () => {
  beforeEach(() => {
    tmpFile = path.join(os.tmpdir(), `report-test-${Date.now()}.jsonl`);
  });

  afterEach(() => {
    if (fs.existsSync(tmpFile)) fs.unlinkSync(tmpFile);
    vi.unstubAllEnvs();
  });

  it('counts events within the date range', async () => {
    const lines = [
      { ts: '2026-06-05T10:00:00.000Z', event: 'page_view' },
      { ts: '2026-06-05T10:01:00.000Z', event: 'cta_click' },
      { ts: '2026-06-05T10:02:00.000Z', event: 'chat_complete' },
      { ts: '2026-06-05T10:03:00.000Z', event: 'quote_request' },
      { ts: '2026-06-05T10:04:00.000Z', event: 'quote_request' },
      { ts: '2026-05-01T10:00:00.000Z', event: 'page_view' }, // out of range
    ];
    fs.writeFileSync(tmpFile, lines.map((l) => JSON.stringify(l)).join('\n') + '\n');
    vi.stubEnv('ANALYTICS_LOG', tmpFile);

    const { computeFunnel } = await loadReportModule();
    const funnel = await computeFunnel('2026-06-01', '2026-06-30');

    expect(funnel.page_views).toBe(1);
    expect(funnel.cta_clicks).toBe(1);
    expect(funnel.chat_completes).toBe(1);
    expect(funnel.quote_requests).toBe(2);
  });

  it('excludes testing events from all funnel counters', async () => {
    const lines = [
      { ts: '2026-06-05T10:00:00.000Z', event: 'page_view', visitor_id: 'a' },
      { ts: '2026-06-05T10:00:30.000Z', event: 'page_view', visitor_id: 'b', testing: true },
      { ts: '2026-06-05T10:01:00.000Z', event: 'chat_complete', testing: true },
      { ts: '2026-06-05T10:02:00.000Z', event: 'quote_request', testing: true },
    ];
    fs.writeFileSync(tmpFile, lines.map((l) => JSON.stringify(l)).join('\n') + '\n');
    vi.stubEnv('ANALYTICS_LOG', tmpFile);

    const { computeFunnel } = await loadReportModule();
    const funnel = await computeFunnel('2026-06-01', '2026-06-30');

    expect(funnel.page_views).toBe(1);
    expect(funnel.chat_completes).toBe(0);
    expect(funnel.quote_requests).toBe(0);
  });

  it('counts distinct visitor_id among non-testing page views', async () => {
    const lines = [
      { ts: '2026-06-05T10:00:00.000Z', event: 'page_view', visitor_id: 'a' },
      { ts: '2026-06-05T10:00:10.000Z', event: 'page_view', visitor_id: 'a' }, // refresh
      { ts: '2026-06-05T10:00:20.000Z', event: 'page_view', visitor_id: 'b' },
      { ts: '2026-06-05T10:00:30.000Z', event: 'page_view', visitor_id: 'c', testing: true }, // testing
    ];
    fs.writeFileSync(tmpFile, lines.map((l) => JSON.stringify(l)).join('\n') + '\n');
    vi.stubEnv('ANALYTICS_LOG', tmpFile);

    const { computeFunnel } = await loadReportModule();
    const funnel = await computeFunnel('2026-06-01', '2026-06-30');

    expect(funnel.page_views).toBe(3);       // a, a, b (raw events, testing 'c' excluded)
    expect(funnel.unique_visitors).toBe(2);  // distinct: a, b
  });

  it('returns zeroed funnel when the analytics file does not exist', async () => {
    vi.stubEnv('ANALYTICS_LOG', path.join(os.tmpdir(), 'does-not-exist.jsonl'));
    const { computeFunnel } = await loadReportModule();
    const funnel = await computeFunnel('2026-06-01', '2026-06-30');
    expect(funnel.page_views).toBe(0);
    expect(funnel.quote_requests).toBe(0);
  });
});

// Nuovi test per visitor_segments: usano mkdtempSync e process.env diretto
let dir;

const view = (visitor, extra = {}) => ({
  ts: '2026-08-10T10:00:00.000Z',
  event: 'page_view',
  visitor_id: visitor,
  device: 'mobile',
  browser: 'chrome',
  ...extra,
});

function writeLog(records) {
  const file = path.join(dir, 'events.jsonl');
  fs.writeFileSync(file, records.map((r) => JSON.stringify(r)).join('\n') + '\n', 'utf8');
  process.env.ANALYTICS_LOG = file;
}

describe('computeFunnel — visitor_segments', () => {
  beforeEach(() => {
    dir = fs.mkdtempSync(path.join(os.tmpdir(), 'report-test-'));
  });

  afterEach(() => {
    fs.rmSync(dir, { recursive: true, force: true });
    delete process.env.ANALYTICS_LOG;
  });

  it('conta una volta sola un visitatore che torna', async () => {
    writeLog([view('v1'), view('v1'), view('v1')]);
    const { computeFunnel } = await import('./report.js');
    const funnel = await computeFunnel('2026-08-01', '2026-08-31');
    expect(funnel.visitor_segments.base).toBe(1);
    expect(funnel.visitor_segments.device).toEqual({ mobile: 1 });
    expect(funnel.visitor_segments.browser).toEqual({ chrome: 1 });
  });

  it('tiene il primo page_view del visitatore (first-write-wins)', async () => {
    writeLog([
      view('v1', { device: 'desktop', browser: 'firefox' }),
      view('v1', { device: 'mobile', browser: 'chrome', ts: '2026-08-11T10:00:00.000Z' }),
    ]);
    const { computeFunnel } = await import('./report.js');
    const funnel = await computeFunnel('2026-08-01', '2026-08-31');
    expect(funnel.visitor_segments.device).toEqual({ desktop: 1 });
    expect(funnel.visitor_segments.browser).toEqual({ firefox: 1 });
  });

  it('somma visitatori distinti per categoria', async () => {
    writeLog([
      view('v1', { device: 'mobile', browser: 'safari' }),
      view('v2', { device: 'mobile', browser: 'chrome' }),
      view('v3', { device: 'tablet', browser: 'safari' }),
    ]);
    const { computeFunnel } = await import('./report.js');
    const funnel = await computeFunnel('2026-08-01', '2026-08-31');
    expect(funnel.visitor_segments.base).toBe(3);
    expect(funnel.visitor_segments.device).toEqual({ mobile: 2, tablet: 1 });
    expect(funnel.visitor_segments.browser).toEqual({ safari: 2, chrome: 1 });
  });

  it('esclude il traffico di test e quello fuori intervallo', async () => {
    writeLog([
      view('v1'),
      view('v2', { testing: true }),
      view('v3', { ts: '2026-07-01T10:00:00.000Z' }),
    ]);
    const { computeFunnel } = await import('./report.js');
    const funnel = await computeFunnel('2026-08-01', '2026-08-31');
    expect(funnel.visitor_segments.base).toBe(1);
    expect(funnel.unique_visitors).toBe(1);
  });

  it('tiene fuori dalla base le righe storiche senza i campi nuovi', async () => {
    writeLog([
      { ts: '2026-08-10T10:00:00.000Z', event: 'page_view', visitor_id: 'vecchio' },
      view('nuovo'),
    ]);
    const { computeFunnel } = await import('./report.js');
    const funnel = await computeFunnel('2026-08-01', '2026-08-31');
    expect(funnel.page_views).toBe(2);
    expect(funnel.unique_visitors).toBe(2);
    expect(funnel.visitor_segments.base).toBe(1); // la copertura è dichiarata in UI
  });

  it('degrada a other un valore fuori whitelist finito comunque nel log', async () => {
    writeLog([view('v1', { device: 'smartwatch', browser: 'netscape' })]);
    const { computeFunnel } = await import('./report.js');
    const funnel = await computeFunnel('2026-08-01', '2026-08-31');
    expect(funnel.visitor_segments.device).toEqual({ other: 1 });
    expect(funnel.visitor_segments.browser).toEqual({ other: 1 });
  });

  it("restituisce una base a zero quando non c'è nessun evento", async () => {
    writeLog([]);
    const { computeFunnel } = await import('./report.js');
    const funnel = await computeFunnel('2026-08-01', '2026-08-31');
    expect(funnel.visitor_segments).toEqual({ base: 0, device: {}, browser: {} });
  });
});
