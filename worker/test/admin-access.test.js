import assert from 'node:assert/strict';
import test from 'node:test';

import worker, { getAdminAccess } from '../src/index.js';

const ORIGIN = 'https://arkham-bot-miniapp.pages.dev';

function env(overrides = {}) {
  return {
    SUPABASE_URL: 'https://example.supabase.co',
    SUPABASE_SERVICE_ROLE_KEY: 'service-role',
    TELEGRAM_BOT_TOKEN: 'test-token',
    ALLOWED_ORIGINS: ORIGIN,
    ...overrides,
  };
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
