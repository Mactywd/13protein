import { describe, it, expect } from 'vitest';
import { detectDevice, detectBrowser } from './clientEnv.js';

// User-agent reali. `touch` è navigator.maxTouchPoints.
const UA = {
  iphoneSafari: 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1',
  ipadLegacy: 'Mozilla/5.0 (iPad; CPU OS 12_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/12.1 Mobile/15E148 Safari/604.1',
  macOrIpad: 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.6 Safari/605.1.15',
  androidPhone: 'Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Mobile Safari/537.36',
  androidTablet: 'Mozilla/5.0 (Linux; Android 13; SM-X200) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
  kindleSilk: 'Mozilla/5.0 (Linux; Android 9; KFMAWI) AppleWebKit/537.36 (KHTML, like Gecko) Silk/119.1.1 like Chrome/119.0.0.0 Safari/537.36',
  windowsChrome: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
  windowsEdge: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0',
  macFirefox: 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0',
  iosChrome: 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) CriOS/120.0.6099.119 Mobile/15E148 Safari/604.1',
  iosFirefox: 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) FxiOS/121.0 Mobile/15E148 Safari/605.1.15',
  samsung: 'Mozilla/5.0 (Linux; Android 13; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) SamsungBrowser/23.0 Chrome/115.0.0.0 Mobile Safari/537.36',
  operaDesktop: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 OPR/105.0.0.0',
};

describe('detectDevice', () => {
  it('riconosce un telefono iOS', () => {
    expect(detectDevice({ ua: UA.iphoneSafari })).toBe('mobile');
  });

  it('riconosce un iPad con user-agent classico', () => {
    expect(detectDevice({ ua: UA.ipadLegacy })).toBe('tablet');
  });

  it('riconosce un iPad che si dichiara Macintosh: lo tradisce il touch', () => {
    expect(detectDevice({ ua: UA.macOrIpad, maxTouchPoints: 5 })).toBe('tablet');
  });

  it('lo stesso user-agent senza touch è un Mac desktop', () => {
    expect(detectDevice({ ua: UA.macOrIpad, maxTouchPoints: 0 })).toBe('desktop');
  });

  it('su Android il token Mobile distingue telefono e tablet', () => {
    expect(detectDevice({ ua: UA.androidPhone })).toBe('mobile');
    expect(detectDevice({ ua: UA.androidTablet })).toBe('tablet');
  });

  it('riconosce un tablet Silk (Kindle Fire) prima della regola Android', () => {
    expect(detectDevice({ ua: UA.kindleSilk })).toBe('tablet');
  });

  it('riconosce i desktop', () => {
    expect(detectDevice({ ua: UA.windowsChrome })).toBe('desktop');
    expect(detectDevice({ ua: UA.macFirefox })).toBe('desktop');
  });

  it('senza user-agent utilizzabile ripiega su other', () => {
    expect(detectDevice({ ua: '' })).toBe('other');
    expect(detectDevice({})).toBe('other');
    expect(detectDevice()).toBe('other');
    expect(detectDevice({ ua: 'curl/8.4.0' })).toBe('other');
  });
});

describe('detectBrowser', () => {
  it('non scambia per Chrome i browser che ne contengono il token', () => {
    expect(detectBrowser(UA.windowsEdge)).toBe('edge');
    expect(detectBrowser(UA.operaDesktop)).toBe('opera');
    expect(detectBrowser(UA.samsung)).toBe('samsung');
  });

  it('riconosce Chrome, Firefox e Safari', () => {
    expect(detectBrowser(UA.windowsChrome)).toBe('chrome');
    expect(detectBrowser(UA.macFirefox)).toBe('firefox');
    expect(detectBrowser(UA.iphoneSafari)).toBe('safari');
  });

  it('su iOS distingue i browser dai token CriOS/FxiOS', () => {
    expect(detectBrowser(UA.iosChrome)).toBe('chrome');
    expect(detectBrowser(UA.iosFirefox)).toBe('firefox');
  });

  it('senza user-agent utilizzabile ripiega su other', () => {
    expect(detectBrowser('')).toBe('other');
    expect(detectBrowser(undefined)).toBe('other');
    expect(detectBrowser('curl/8.4.0')).toBe('other');
  });
});
