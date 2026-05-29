import assert from 'node:assert/strict';
import { createHmac } from 'node:crypto';
import test from 'node:test';

import worker from '../src/index.js';

const ORIGIN = 'https://arkham-bot-miniapp.pages.dev';
const BOT_TOKEN = 'test-token';

function env(overrides = {}) {
  return {
    SUPABASE_URL: 'https://example.supabase.co',
    SUPABASE_SERVICE_ROLE_KEY: 'service-role',
    TELEGRAM_BOT_TOKEN: BOT_TOKEN,
    ALLOWED_ORIGINS: ORIGIN,
    ...overrides,
  };
}

function signedInitData(user = { id: 123, first_name: 'Admin' }) {
  const authDate = Math.floor(Date.now() / 1000);
  const params = new URLSearchParams({
    auth_date: String(authDate),
    user: JSON.stringify(user),
  });
  const dataCheckString = [...params.entries()]
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([k, v]) => `${k}=${v}`)
    .join('\n');
  const secret = createHmac('sha256', 'WebAppData').update(BOT_TOKEN).digest();
  const hash = createHmac('sha256', secret).update(dataCheckString).digest('hex');
  params.set('hash', hash);
  return params.toString();
}

/**
 * Drives GET /history?date=... through the real handler and returns the
 * bot_posting_history URL the worker fetched, so the computed UTC window can
 * be asserted. `timezone` is the value returned from the bot_settings query
 * (omit to simulate no configured timezone → UTC default).
 */
async function historyQueryUrl(t, date, timezone) {
  let historyUrl = '';
  t.mock.method(globalThis, 'fetch', async (url) => {
    const path = String(url);
    if (path.includes('/bot_admins')) return Response.json([{ role: 'admin' }]);
    if (path.includes('/bot_settings?select=')) {
      return Response.json(timezone ? [{ key: 'timezone', value: timezone }] : []);
    }
    if (path.includes('/bot_posting_history')) {
      historyUrl = path;
      return Response.json([]);
    }
    throw new Error(`unexpected fetch ${path}`);
  });

  const request = new Request(`https://worker.example/history?date=${date}`, {
    method: 'GET',
    headers: { origin: ORIGIN, 'x-telegram-init-data': signedInitData() },
  });
  const response = await worker.fetch(request, env());
  assert.equal(response.status, 200);
  return historyUrl;
}

test('history date filter defaults to UTC day boundaries when no timezone configured', async (t) => {
  const url = await historyQueryUrl(t, '2026-01-15', null);
  assert.match(url, /created_at=gte\.2026-01-15T00:00:00\.000Z/);
  assert.match(url, /created_at=lt\.2026-01-16T00:00:00\.000Z/);
});

test('history date filter shifts day boundaries for a negative-offset timezone', async (t) => {
  // America/Sao_Paulo is UTC-3 (no DST since 2019): local midnight is 03:00Z.
  const url = await historyQueryUrl(t, '2026-01-15', 'America/Sao_Paulo');
  assert.match(url, /created_at=gte\.2026-01-15T03:00:00\.000Z/);
  assert.match(url, /created_at=lt\.2026-01-16T03:00:00\.000Z/);
});

test('history date filter shifts day boundaries for a positive-offset timezone', async (t) => {
  // Asia/Tokyo is UTC+9: local midnight is the previous day at 15:00Z.
  const url = await historyQueryUrl(t, '2026-01-15', 'Asia/Tokyo');
  assert.match(url, /created_at=gte\.2026-01-14T15:00:00\.000Z/);
  assert.match(url, /created_at=lt\.2026-01-15T15:00:00\.000Z/);
});
