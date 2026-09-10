import { describe, it, expect } from 'vitest';
import { DEVICES, BROWSERS, normalizeSegment } from './segments.js';

describe('normalizeSegment', () => {
  it('lascia passare un valore della whitelist', () => {
    expect(normalizeSegment('tablet', DEVICES)).toBe('tablet');
    expect(normalizeSegment('firefox', BROWSERS)).toBe('firefox');
  });

  it('degrada a other qualunque valore non previsto', () => {
    expect(normalizeSegment('smartwatch', DEVICES)).toBe('other');
    expect(normalizeSegment('netscape', BROWSERS)).toBe('other');
  });

  it('degrada a other anche campo assente o di tipo sbagliato', () => {
    expect(normalizeSegment(undefined, DEVICES)).toBe('other');
    expect(normalizeSegment(null, DEVICES)).toBe('other');
    expect(normalizeSegment(42, DEVICES)).toBe('other');
    expect(normalizeSegment({ device: 'mobile' }, DEVICES)).toBe('other');
  });

  it('include other tra i valori ammessi di entrambe le liste', () => {
    expect(DEVICES).toContain('other');
    expect(BROWSERS).toContain('other');
  });
});
