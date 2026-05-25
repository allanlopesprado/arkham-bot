const ALLOWED_COMMAND_TYPES = new Set([
  'post_now',
  'skip_card',
  'pause_daily_post',
  'resume_daily_post',
  'sync_arkhamdb',
]);

const COMMAND_ALIASES = {
  pause_daily: 'pause_daily_post',
  resume_daily: 'resume_daily_post',
};

const ADMIN_ROLES = new Set(['owner', 'admin']);

async function hmacSha256(keyBytes, data) {
  const key = await crypto.subtle.importKey(
    'raw',
    keyBytes,
    { name: 'HMAC', hash: 'SHA-256' },
    false,
    ['sign'],
  );
  return new Uint8Array(await crypto.subtle.sign('HMAC', key, new TextEncoder().encode(data)));
}

function hex(bytes) {
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

function parseAdminIds(raw) {
  return String(raw || '')
    .split(',')
    .map((s) => s.trim())
    .filter(Boolean);
}

function envAdminFallbackEnabled(env) {
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

function jsonResponse(payload, status = 200, extraHeaders = {}) {
  return new Response(JSON.stringify(payload), {
    status,
    headers: { 'content-type': 'application/json; charset=utf-8', ...extraHeaders },
  });
}

function getAllowedOrigin(request, env) {
  const origin = request.headers.get('origin') || '';
  const allowed = String(env.ALLOWED_ORIGINS || '')
    .split(',')
    .map((s) => s.trim())
    .filter(Boolean);
  return allowed.includes(origin) ? origin : '';
}

function corsHeaders(allowedOrigin) {
  if (!allowedOrigin) return {};
  return {
    'access-control-allow-origin': allowedOrigin,
    'access-control-allow-methods': 'GET,POST,OPTIONS',
    'access-control-allow-headers': 'content-type,x-telegram-init-data',
    vary: 'Origin',
  };
}

function withCors(response, allowedOrigin) {
  const hdrs = corsHeaders(allowedOrigin);
  Object.entries(hdrs).forEach(([k, v]) => response.headers.set(k, v));
  return response;
}

function preflightResponse(allowedOrigin) {
  if (!allowedOrigin) return jsonResponse({ error: 'origin_not_allowed' }, 403);
  return new Response(null, { status: 204, headers: corsHeaders(allowedOrigin) });
}

function normalizeCommandType(raw) {
  const normalized = COMMAND_ALIASES[raw] || raw;
  return ALLOWED_COMMAND_TYPES.has(normalized) ? normalized : null;
}

function safeLog(data) {
  console.log(JSON.stringify({
    path: data.path,
    method: data.method,
    initData_present: data.initData_present,
    initData_length: data.initData_length,
    telegram_user_id_present: data.telegram_user_id_present,
    admin: data.admin,
    admin_source: data.admin_source || null,
    command_type: data.command_type || null,
    status: data.status,
  }));
}

async function handleMe(request, env, user, ao) {
  const access = await getAdminAccess(env, user.id);
  safeLog({
    path: '/me',
    method: 'GET',
    initData_present: true,
    initData_length: null,
    telegram_user_id_present: true,
    admin: access.admin,
    admin_source: access.source,
    status: 200,
  });
  return withCors(jsonResponse({
    ok: true,
    user: { id: user.id, first_name: user.first_name, username: user.username || null },
    admin: access.admin,
    role: access.role,
    admin_source: access.source,
  }), ao);
}

async function handleStatus(request, env, ao) {
  const result = { ok: true };
  try {
    if (env.SUPABASE_URL && env.SUPABASE_SERVICE_ROLE_KEY) {
      const base = env.SUPABASE_URL.replace(/\/$/, '');
      const headers = {
        apikey: env.SUPABASE_SERVICE_ROLE_KEY,
        authorization: `Bearer ${env.SUPABASE_SERVICE_ROLE_KEY}`,
        prefer: 'count=exact',
      };

      const cardsResp = await fetch(`${base}/rest/v1/arkham_cards?select=code&limit=1`, { headers });
      if (cardsResp.ok) {
        result.total_cards = parseInt(cardsResp.headers.get('content-range')?.split('/')[1] || '0', 10) || null;
      }

      const packsResp = await fetch(`${base}/rest/v1/arkham_packs?select=code&limit=1`, { headers });
      if (packsResp.ok) {
        result.total_packs = parseInt(packsResp.headers.get('content-range')?.split('/')[1] || '0', 10) || null;
      }

      const cmdResp = await fetch(
        `${base}/rest/v1/bot_commands?select=command_type,created_at&order=created_at.desc&limit=1`,
        { headers: { ...headers, prefer: '' } },
      );
      if (cmdResp.ok) {
        const cmds = await cmdResp.json();
        result.last_command = cmds[0]
          ? `${cmds[0].command_type} @ ${cmds[0].created_at}`
          : null;
      }

      const syncResp = await fetch(
        `${base}/rest/v1/bot_commands?select=created_at&command_type=eq.sync_arkhamdb&order=created_at.desc&limit=1`,
        { headers: { ...headers, prefer: '' } },
      );
      if (syncResp.ok) {
        const syncs = await syncResp.json();
        result.last_sync = syncs[0]?.created_at || null;
      }
    }
  } catch {
    result.ok = false;
    result.error = 'status_fetch_failed';
  }
  return withCors(jsonResponse(result), ao);
}

async function handleBotCommand(request, env, user, ao) {
  let body;
  try {
    body = await request.json();
  } catch {
    return withCors(jsonResponse({ error: 'invalid_json' }, 400), ao);
  }

  if (!body.command_type) {
    return withCors(jsonResponse({ error: 'command_type_required' }, 400), ao);
  }

  const commandType = normalizeCommandType(body.command_type);
  if (!commandType) {
    return withCors(jsonResponse({ error: 'unsupported_command_type' }, 400), ao);
  }

  const access = await getAdminAccess(env, user.id);
  safeLog({
    path: '/bot-command',
    method: 'POST',
    initData_present: true,
    initData_length: null,
    telegram_user_id_present: true,
    admin: access.admin,
    admin_source: access.source,
    command_type: commandType,
    status: access.admin ? 200 : 403,
  });

  if (!access.admin) {
    return withCors(jsonResponse({
      error: 'unauthorized',
      role: access.role,
      admin_source: access.source,
    }, 403), ao);
  }

  const payload = {
    command_type: commandType,
    payload: body.payload || {},
    requested_by_telegram_user_id: user.id,
    requested_by_name: [user.first_name, user.last_name].filter(Boolean).join(' ') || user.username || String(user.id),
    target_chat_id: body.target_chat_id || null,
  };

  const resp = await fetch(`${env.SUPABASE_URL.replace(/\/$/, '')}/rest/v1/bot_commands`, {
    method: 'POST',
    headers: {
      apikey: env.SUPABASE_SERVICE_ROLE_KEY,
      authorization: `Bearer ${env.SUPABASE_SERVICE_ROLE_KEY}`,
      'content-type': 'application/json',
      prefer: 'return=representation',
    },
    body: JSON.stringify(payload),
  });

  if (!resp.ok) {
    return withCors(jsonResponse({ error: 'bot_command_insert_failed' }, 500), ao);
  }

  const inserted = await resp.json();
  return withCors(jsonResponse({
    ok: true,
    command: {
      id: inserted[0]?.id,
      command_type: inserted[0]?.command_type || commandType,
      status: inserted[0]?.status || 'pending',
    },
  }), ao);
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const { pathname } = url;
    const ao = getAllowedOrigin(request, env);

    if (request.method === 'OPTIONS') return preflightResponse(ao);

    if (pathname === '/health' && request.method === 'GET') {
      return jsonResponse({ ok: true });
    }

    if (!ao) {
      return jsonResponse({ error: 'origin_not_allowed' }, 403);
    }

    if (pathname === '/status' && request.method === 'GET') {
      const initData = request.headers.get('x-telegram-init-data') || '';
      safeLog({
        path: '/status',
        method: 'GET',
        initData_present: Boolean(initData),
        initData_length: initData.length,
        telegram_user_id_present: null,
        admin: null,
        status: 200,
      });
      const user = await validateTelegramInitData(initData, env.TELEGRAM_BOT_TOKEN);
      if (!user) return withCors(jsonResponse({ error: 'invalid_telegram_init_data' }, 401), ao);
      return handleStatus(request, env, ao);
    }

    if (pathname === '/me' && request.method === 'GET') {
      const initData = request.headers.get('x-telegram-init-data') || '';
      const user = await validateTelegramInitData(initData, env.TELEGRAM_BOT_TOKEN);
      if (!user) return withCors(jsonResponse({ error: 'invalid_telegram_init_data' }, 401), ao);
      return handleMe(request, env, user, ao);
    }

    if ((pathname === '/bot-command' || pathname === '/') && request.method === 'POST') {
      const initData = request.headers.get('x-telegram-init-data') || '';
      safeLog({
        path: pathname,
        method: 'POST',
        initData_present: Boolean(initData),
        initData_length: initData.length,
        telegram_user_id_present: null,
        admin: null,
        status: null,
      });
      const user = await validateTelegramInitData(initData, env.TELEGRAM_BOT_TOKEN);
      if (!user) return withCors(jsonResponse({ error: 'invalid_telegram_init_data' }, 401), ao);
      return handleBotCommand(request, env, user, ao);
    }

    if (pathname === '/me' || pathname === '/status' || pathname === '/bot-command' || pathname === '/') {
      return withCors(jsonResponse({ error: 'method_not_allowed' }, 405), ao);
    }

    return withCors(jsonResponse({ error: 'not_found' }, 404), ao);
  },
};
