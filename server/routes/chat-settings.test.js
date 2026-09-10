import { describe, it, expect, vi, afterEach } from 'vitest';
import { getChatSettings, putChatSettings } from './chat-settings.js';

function mockRes() {
  return { code: 200, body: null, status(c) { this.code = c; return this; }, json(b) { this.body = b; return this; } };
}

afterEach(() => vi.restoreAllMocks());

describe('getChatSettings', () => {
  it('proxies the backend settings payload', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => ({ ok: true, json: async () => ({ abandon_timeout_minutes: 30 }) })));
    const res = mockRes();
    await getChatSettings({}, res);
    expect(res.body).toEqual({ abandon_timeout_minutes: 30 });
  });
});

describe('putChatSettings', () => {
  it('forwards the body and returns the backend response', async () => {
    const fetchMock = vi.fn(async () => ({ ok: true, json: async () => ({ abandon_timeout_minutes: 15 }) }));
    vi.stubGlobal('fetch', fetchMock);
    const res = mockRes();
    await putChatSettings({ body: { abandon_timeout_minutes: 15 } }, res);
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining('/settings'),
      expect.objectContaining({ method: 'PUT' }),
    );
    expect(res.body).toEqual({ abandon_timeout_minutes: 15 });
  });

  it('propagates a backend error status', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => ({ ok: false, status: 500, json: async () => ({}) })));
    const res = mockRes();
    await putChatSettings({ body: {} }, res);
    expect(res.code).toBe(500);
  });
});
