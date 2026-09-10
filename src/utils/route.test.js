import { describe, it, expect } from 'vitest';
import { normalizePath, isTestingPath } from './route.js';

describe('normalizePath', () => {
  it('leaves an english (default, unprefixed) path alone', () => {
    expect(normalizePath('/privacy-policy')).toBe('/privacy-policy');
    expect(normalizePath('/testing')).toBe('/testing');
    expect(normalizePath('/')).toBe('/');
  });

  it('strips the italian language prefix', () => {
    expect(normalizePath('/it/privacy-policy')).toBe('/privacy-policy');
    expect(normalizePath('/it/testing')).toBe('/testing');
  });

  it('maps the italian home to the root', () => {
    expect(normalizePath('/it')).toBe('/');
    expect(normalizePath('/it/')).toBe('/');
  });

  it('drops trailing slashes', () => {
    expect(normalizePath('/privacy-policy/')).toBe('/privacy-policy');
    expect(normalizePath('/it/testing//')).toBe('/testing');
  });

  it('does not mistake a path that merely starts with the letters "it"', () => {
    expect(normalizePath('/italy')).toBe('/italy');
  });

  it('survives an empty or missing pathname', () => {
    expect(normalizePath('')).toBe('/');
    expect(normalizePath(undefined)).toBe('/');
  });
});

describe('isTestingPath', () => {
  // Regressione ereditata: il router spogliava il prefisso e track.js no,
  // quindi su una route di test prefissata gli eventi entravano nel funnel
  // di produzione con testing:false.
  it('recognises the testing route in both languages', () => {
    expect(isTestingPath('/testing')).toBe(true);
    expect(isTestingPath('/it/testing')).toBe(true);
    expect(isTestingPath('/testing/')).toBe(true);
  });

  it('is false everywhere else', () => {
    expect(isTestingPath('/')).toBe(false);
    expect(isTestingPath('/it')).toBe(false);
    expect(isTestingPath('/privacy-policy')).toBe(false);
  });
});
