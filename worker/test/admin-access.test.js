import assert from 'node:assert/strict';
import { createHmac } from 'node:crypto';
import test from 'node:test';

import worker, { getAdminAccess } from '../src/index.js';

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

test('getAdminAccess blocks users not present in bot_admins', async (t) => {
  t.mock.method(globalThis, 'fetch', async (url) => {
    assert.match(String(url), /bot_admins/);
    return Response.json([]);
  });

  const access = await getAdminAccess(env(), 123);

  assert.equal(access.admin, false);
  assert.equal(access.role, 'none');
  assert.equal(access.source, 'supabase');
});

test('getAdminAccess accepts owner and admin roles only', async (t) => {
  t.mock.method(globalThis, 'fetch', async () => Response.json([{ role: 'viewer' }]));

  const viewer = await getAdminAccess(env(), 123);

  assert.equal(viewer.admin, false);
  assert.equal(viewer.role, 'viewer');

  globalThis.fetch.mock.mockImplementationOnce(async () => Response.json([{ role: 'admin' }]));
  const admin = await getAdminAccess(env(), 123);

  assert.equal(admin.admin, true);
  assert.equal(admin.role, 'admin');
});

test('env admin fallback is disabled unless explicitly enabled', async () => {
  const access = await getAdminAccess(env({
    SUPABASE_URL: '',
    SUPABASE_SERVICE_ROLE_KEY: '',
    ADMIN_TELEGRAM_USER_IDS: '123',
  }), 123);

  assert.equal(access.admin, false);
  assert.equal(access.source, 'none');
});

test('env admin fallback works only with ALLOW_ADMIN_ENV_FALLBACK=true', async () => {
  const access = await getAdminAccess(env({
    SUPABASE_URL: '',
    SUPABASE_SERVICE_ROLE_KEY: '',
    ADMIN_TELEGRAM_USER_IDS: '123',
    ALLOW_ADMIN_ENV_FALLBACK: 'true',
  }), 123);

  assert.equal(access.admin, true);
  assert.equal(access.source, 'env_fallback');
});

test('bot-command rejects invalid initData before Supabase insert', async (t) => {
  const fetchMock = t.mock.method(globalThis, 'fetch', async () => {
    throw new Error('fetch should not be called');
  });
  const request = new Request('https://worker.example/bot-command', {
    method: 'POST',
    headers: {
      origin: ORIGIN,
      'content-type': 'application/json',
      'x-telegram-init-data': 'invalid',
    },
    body: JSON.stringify({ command_type: 'post_now' }),
  });

  const response = await worker.fetch(request, env());

  assert.equal(response.status, 401);
  assert.equal(fetchMock.mock.callCount(), 0);
});

test('settings save exposes Supabase upsert details', async (t) => {
  t.mock.method(globalThis, 'fetch', async (url) => {
    const path = String(url);
    if (path.includes('/bot_admins')) {
      return Response.json([{ role: 'admin' }]);
    }
    if (path.includes('/bot_settings?on_conflict=key')) {
      return Response.json({ message: 'there is no unique constraint matching the ON CONFLICT specification' }, { status: 409 });
    }
    throw new Error(`unexpected fetch ${path}`);
  });

  const request = new Request('https://worker.example/settings', {
    method: 'PATCH',
    headers: {
      origin: ORIGIN,
      'content-type': 'application/json',
      'x-telegram-init-data': signedInitData(),
    },
    body: JSON.stringify({ daily_post_enabled: true }),
  });

  const response = await worker.fetch(request, env());
  const json = await response.json();

  assert.equal(response.status, 500);
  assert.equal(json.error, 'settings_upsert_failed');
  assert.equal(json.upstream_status, 409);
  assert.match(json.detail, /unique constraint/);
});

test('settings save accepts empty weekdays and disabled day filters', async (t) => {
  const upsertBodies = [];
  t.mock.method(globalThis, 'fetch', async (url, options = {}) => {
    const path = String(url);
    if (path.includes('/bot_admins')) {
      return Response.json([{ role: 'admin' }]);
    }
    if (path.includes('/bot_settings?on_conflict=key')) {
      upsertBodies.push(JSON.parse(options.body));
      return Response.json([]);
    }
    if (path.includes('/bot_settings?select=')) {
      return Response.json([]);
    }
    throw new Error(`unexpected fetch ${path}`);
  });

  const request = new Request('https://worker.example/settings', {
    method: 'PATCH',
    headers: {
      origin: ORIGIN,
      'content-type': 'application/json',
      'x-telegram-init-data': signedInitData(),
    },
    body: JSON.stringify({
      daily_post_days: [],
      day_config: { mon: { packs: ['__none__'], types: ['__none__'] } },
    }),
  });

  const response = await worker.fetch(request, env());

  assert.equal(response.status, 200);
  assert.deepEqual(upsertBodies[0].find((row) => row.key === 'daily_post_days').value, []);
  assert.deepEqual(upsertBodies[0].find((row) => row.key === 'day_config').value.mon.types, ['__none__']);
});
