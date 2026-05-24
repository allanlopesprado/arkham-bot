async function hmacSha256(keyBytes, data) {
  const key = await crypto.subtle.importKey('raw', keyBytes, { name: 'HMAC', hash: 'SHA-256' }, false, ['sign']);
  return new Uint8Array(await crypto.subtle.sign('HMAC', key, new TextEncoder().encode(data)));
}

function hex(bytes) {
  return [...bytes].map((b) => b.toString(16).padStart(2, '0')).join('');
}

async function validateTelegramInitData(initData, botToken) {
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
  return userRaw ? JSON.parse(userRaw) : null;
}

function jsonResponse(payload, status = 200) {
  return new Response(JSON.stringify(payload), {
    status,
    headers: { 'content-type': 'application/json; charset=utf-8' },
  });
}

function getAllowedOrigin(request, env) {
  const origin = request.headers.get('origin') || '';
  const allowed = String(env.ALLOWED_ORIGINS || '')
    .split(',')
    .map((item) => item.trim())
    .filter(Boolean);
  return allowed.includes(origin) ? origin : '';
}

function withCors(response, request, env) {
  const allowedOrigin = getAllowedOrigin(request, env);
  if (allowedOrigin) {
    response.headers.set('access-control-allow-origin', allowedOrigin);
    response.headers.set('vary', 'Origin');
  }
  return response;
}

function preflightResponse(request, env) {
  const allowedOrigin = getAllowedOrigin(request, env);
  if (!allowedOrigin) return jsonResponse({ error: 'origin_not_allowed' }, 403);
  return new Response(null, {
    status: 204,
    headers: {
      'access-control-allow-origin': allowedOrigin,
      'access-control-allow-methods': 'POST,OPTIONS',
      'access-control-allow-headers': 'content-type,x-telegram-init-data',
      'vary': 'Origin',
    },
  });
}

async function insertBotCommand(env, user, body) {
  const payload = {
    command_type: body.command_type,
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
    return jsonResponse({ error: await resp.text() }, 500);
  }
  return jsonResponse({ ok: true, command: (await resp.json())[0] });
}

export default {
  async fetch(request, env) {
    if (request.method === 'OPTIONS') return preflightResponse(request, env);
    if (!getAllowedOrigin(request, env)) return jsonResponse({ error: 'origin_not_allowed' }, 403);
    if (new URL(request.url).pathname !== '/bot-command') return withCors(jsonResponse({ error: 'not_found' }, 404), request, env);
    if (request.method !== 'POST') return withCors(jsonResponse({ error: 'method_not_allowed' }, 405), request, env);
    const initData = request.headers.get('x-telegram-init-data') || '';
    const user = await validateTelegramInitData(initData, env.TELEGRAM_BOT_TOKEN);
    if (!user) return withCors(jsonResponse({ error: 'invalid_telegram_init_data' }, 401), request, env);
    const body = await request.json();
    if (!body.command_type) return withCors(jsonResponse({ error: 'command_type_required' }, 400), request, env);
    const response = await insertBotCommand(env, user, body);
    return withCors(response, request, env);
  }
};
