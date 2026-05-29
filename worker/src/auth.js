// Telegram initData validation + admin/owner access checks and route guards.
import { jsonResponse, withCors } from './http.js';
import { safeLog } from './audit.js';

const ADMIN_ROLES = new Set(['owner', 'admin']);

export async function hmacSha256(keyBytes, data) {
  const key = await crypto.subtle.importKey(
    'raw',
    keyBytes,
    { name: 'HMAC', hash: 'SHA-256' },
    false,
    ['sign'],
  );
  return new Uint8Array(await crypto.subtle.sign('HMAC', key, new TextEncoder().encode(data)));
}

export function hex(bytes) {
  return [...bytes].map((b) => b.toString(16).padStart(2, '0')).join('');
}

export async function validateTelegramInitData(initData, botToken) {
  if (!initData || !botToken) return null;
  const params = new URLSearchParams(initData);
  const hash = params.get('hash');
  if (!hash) return null;
  params.delete('hash');
  const dataCheckString = [...params.entries()]
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([k, v]) => `${k}=${v}`)
    .join('\n');
  const secretKey = await hmacSha256(new TextEncoder().encode('WebAppData'), botToken);
  const calculated = hex(await hmacSha256(secretKey, dataCheckString));
  if (calculated !== hash) return null;
  const authDate = Number(params.get('auth_date') || 0);
  if (!authDate || Math.floor(Date.now() / 1000) - authDate > 86400) return null;
  const userRaw = params.get('user');
  try {
    return userRaw ? JSON.parse(userRaw) : null;
  } catch {
    return null;
  }
}

export function parseAdminIds(raw) {
  return String(raw || '')
    .split(',')
    .map((s) => s.trim())
    .filter(Boolean);
}

export function envAdminFallbackEnabled(env) {
  return String(env.ALLOW_ADMIN_ENV_FALLBACK || '').toLowerCase() === 'true';
}

export async function getAdminAccess(env, telegramUserId) {
  if (env.SUPABASE_URL && env.SUPABASE_SERVICE_ROLE_KEY) {
    try {
      const url = `${env.SUPABASE_URL.replace(/\/$/, '')}/rest/v1/bot_admins?telegram_user_id=eq.${telegramUserId}&enabled=eq.true&select=role`;
      const resp = await fetch(url, {
        headers: {
          apikey: env.SUPABASE_SERVICE_ROLE_KEY,
          authorization: `Bearer ${env.SUPABASE_SERVICE_ROLE_KEY}`,
        },
      });
      if (!resp.ok) {
        return { role: 'none', admin: false, source: 'supabase_error' };
      }
      const rows = await resp.json();
      const role = rows[0]?.role || 'none';
      return { role, admin: ADMIN_ROLES.has(role), source: 'supabase' };
    } catch {
      return { role: 'none', admin: false, source: 'supabase_error' };
    }
  }

  if (envAdminFallbackEnabled(env)) {
    const ids = parseAdminIds(env.ADMIN_TELEGRAM_USER_IDS);
    if (ids.includes(String(telegramUserId))) {
      return { role: 'admin', admin: true, source: 'env_fallback' };
    }
  }

  return { role: 'none', admin: false, source: 'none' };
}

export async function requireAuth(request, env, ao, path) {
  const initData = request.headers.get('x-telegram-init-data') || '';
  safeLog({
    path,
    method: request.method,
    initData_present: Boolean(initData),
    initData_length: initData.length,
    telegram_user_id_present: null,
    admin: null,
    status: null,
  });
  const user = await validateTelegramInitData(initData, env.TELEGRAM_BOT_TOKEN);
  if (!user) {
    return { response: withCors(jsonResponse({ error: 'invalid_telegram_init_data' }, 401), ao) };
  }
  return { user };
}

export async function requireAdmin(request, env, ao, path) {
  const initData = request.headers.get('x-telegram-init-data') || '';
  safeLog({
    path,
    method: request.method,
    initData_present: Boolean(initData),
    initData_length: initData.length,
    telegram_user_id_present: null,
    admin: null,
    status: null,
  });
  const user = await validateTelegramInitData(initData, env.TELEGRAM_BOT_TOKEN);
  if (!user) {
    return { response: withCors(jsonResponse({ error: 'invalid_telegram_init_data' }, 401), ao) };
  }
  const access = await getAdminAccess(env, user.id);
  safeLog({
    path,
    method: request.method,
    initData_present: true,
    initData_length: null,
    telegram_user_id_present: true,
    admin: access.admin,
    admin_source: access.source,
    status: access.admin ? 200 : 403,
  });
  if (!access.admin) {
    return {
      response: withCors(jsonResponse({
        error: 'unauthorized',
        role: access.role,
        admin_source: access.source,
      }, 403), ao),
    };
  }
  const enrichedUser = { ...user, role: access.role, name: [user.first_name, user.last_name].filter(Boolean).join(' ') || user.username || String(user.id) };
  return { user: enrichedUser, access };
}

export async function requireOwner(request, env, ao, path) {
  const auth = await requireAdmin(request, env, ao, path);
  if (auth.response) return auth;
  if (auth.access?.role !== 'owner') {
    return { response: withCors(jsonResponse({ ok: false, error: 'owner_required' }, 403), ao) };
  }
  // Attach role to user for convenience
  const user = { ...auth.user, role: auth.access.role, name: [auth.user.first_name, auth.user.last_name].filter(Boolean).join(' ') || auth.user.username || String(auth.user.id) };
  return { user, access: auth.access };
}
