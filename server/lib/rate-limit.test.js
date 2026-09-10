import { describe, it, expect, beforeEach } from 'vitest';
import { rateLimit, _resetRateLimits } from './rate-limit.js';

function makeReq(ip = '1.2.3.4') {
  return { ip, socket: { remoteAddress: ip } };
}

function makeRes() {
  const res = { statusCode: null, body: null };
  res.status = (code) => { res.statusCode = code; return res; };
  res.json = (body) => { res.body = body; return res; };
  return res;
}

describe('rateLimit', () => {
  beforeEach(() => _resetRateLimits());

  it('allows requests under the limit and blocks past it', () => {
    const mw = rateLimit('test', { windowMs: 60_000, max: 3 });
    let passed = 0;
    for (let i = 0; i < 3; i++) {
      mw(makeReq(), makeRes(), () => { passed += 1; });
    }
    expect(passed).toBe(3);

    const res = makeRes();
    let called = false;
    mw(makeReq(), res, () => { called = true; });
    expect(called).toBe(false);
    expect(res.statusCode).toBe(429);
  });

  it('tracks each IP separately', () => {
    const mw = rateLimit('test', { windowMs: 60_000, max: 1 });
    let passed = 0;
    mw(makeReq('1.1.1.1'), makeRes(), () => { passed += 1; });
    mw(makeReq('2.2.2.2'), makeRes(), () => { passed += 1; });
    expect(passed).toBe(2);

    const res = makeRes();
    mw(makeReq('1.1.1.1'), res, () => { passed += 1; });
    expect(passed).toBe(2);
    expect(res.statusCode).toBe(429);
  });

  it('keeps separate buckets per limiter name', () => {
    const a = rateLimit('a', { windowMs: 60_000, max: 1 });
    const b = rateLimit('b', { windowMs: 60_000, max: 1 });
    let passed = 0;
    a(makeReq(), makeRes(), () => { passed += 1; });
    b(makeReq(), makeRes(), () => { passed += 1; });
    expect(passed).toBe(2);
  });
});
