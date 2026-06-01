// Bot command queue: list, cancel, submit (+ rate limiting).
import { withCors, jsonResponse } from '../http.js';
import { supabaseBase, supabaseHeaders, fetchSupabaseJson } from '../supabase.js';
import { boundedLimit } from '../validation.js';
import { getAdminAccess } from '../auth.js';
import { safeLog, writeAuditLog } from '../audit.js';

const ALLOWED_COMMAND_TYPES = new Set([
  'post_now',
  'repost_card',
  'skip_card',
  'pause_daily_post',
  'resume_daily_post',
  'reset_cycle',
  'clear_queue',
  'update_setting',
  'sync_arkhamdb',
]);

const COMMAND_ALIASES = {
  pause_daily: 'pause_daily_post',
  resume_daily: 'resume_daily_post',
};

function normalizeCommandType(raw) {
  const normalized = COMMAND_ALIASES[raw] || raw;
  return ALLOWED_COMMAND_TYPES.has(normalized) ? normalized : null;
}

export async function handleCommands(request, env, ao) {
  const url = new URL(request.url);
  const status = url.searchParams.get('status') || '';
  const limit = boundedLimit(url.searchParams.get('limit'), 30, 50);
  const filters = status ? `&status=eq.${encodeURIComponent(status)}` : '';
  try {
    const rows = await fetchSupabaseJson(
      env,
      `/rest/v1/bot_commands?select=id,command_type,status,created_at,updated_at,executed_at,last_error,next_attempt_at,scheduled_for,attempt_count,max_attempts,payload,result,requested_by_name${filters}&order=created_at.desc&limit=${limit}`,
    );
    return withCors(jsonResponse({ ok: true, commands: rows }), ao);
  } catch {
    return withCors(jsonResponse({ error: 'commands_fetch_failed' }, 500), ao);
  }
}

export async function handleCancelCommand(request, env, user, ao, commandId) {
  if (!/^[0-9a-f-]{16,}$/i.test(commandId)) {
    return withCors(jsonResponse({ error: 'invalid_command_id' }, 400), ao);
  }

  try {
    const resp = await fetch(`${supabaseBase(env)}/rest/v1/bot_commands?id=eq.${encodeURIComponent(commandId)}&status=in.(pending,retrying)`, {
      method: 'PATCH',
      headers: supabaseHeaders(env, {
        'content-type': 'application/json',
        prefer: 'return=representation',
      }),
      body: JSON.stringify({
        status: 'cancelled',
        last_error: `Cancelled from Mini App by ${user.id}`,
        updated_at: new Date().toISOString(),
      }),
    });
    if (!resp.ok) return withCors(jsonResponse({ error: 'command_cancel_failed' }, 500), ao);
    const rows = await resp.json();
    if (!rows.length) return withCors(jsonResponse({ error: 'command_not_cancellable' }, 409), ao);
    await writeAuditLog(env, user, 'command_cancelled', { command_id: commandId });
    return withCors(jsonResponse({ ok: true, command: rows[0] }), ao);
  } catch {
    return withCors(jsonResponse({ error: 'command_cancel_failed' }, 500), ao);
  }
}

export async function handleBotCommand(request, env, user, ao) {
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

  if (!env.SUPABASE_URL || !env.SUPABASE_SERVICE_ROLE_KEY) {
    return withCors(jsonResponse({ error: 'backend_not_configured', detail: 'SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY is missing.' }, 500), ao);
  }

  const rateLimited = await checkRateLimit(env, user, commandType);
  if (rateLimited) {
    return withCors(new Response(JSON.stringify({ ok: false, error: 'rate_limited', detail: 'Command already pending' }), { status: 429, headers: { 'content-type': 'application/json' } }), ao);
  }

  // Whitelist allowed payload fields per command type to prevent injection
  const PAYLOAD_SCHEMA = {
    post_now:          ['card_code'],
    repost_card:       ['card_code'],
    skip_card:         ['card_code'],
    pause_daily_post:  [],
    resume_daily_post: [],
    reset_cycle:       [],
    clear_queue:       [],
    update_setting:    ['key', 'value'],
    sync_arkhamdb:     ['sync_faq', 'faq_limit'],
  };
  const allowedFields = PAYLOAD_SCHEMA[commandType] || [];
  const rawPayload = (body.payload && typeof body.payload === 'object' && !Array.isArray(body.payload))
    ? body.payload : {};
  const sanitizedPayload = Object.fromEntries(
    Object.entries(rawPayload).filter(([k]) => allowedFields.includes(k))
  );

  const payload = {
    command_type: commandType,
    payload: sanitizedPayload,
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
  await writeAuditLog(env, user, 'command_submitted', { command_type: commandType, command_id: inserted[0]?.id });
  return withCors(jsonResponse({
    ok: true,
    command: {
      id: inserted[0]?.id,
      command_type: inserted[0]?.command_type || commandType,
      status: inserted[0]?.status || 'pending',
    },
  }), ao);
}

async function checkRateLimit(env, user, command_type) {
  try {
    const since = new Date(Date.now() - 10000).toISOString();
    const url = `${supabaseBase(env)}/rest/v1/bot_commands?requested_by_telegram_user_id=eq.${user.id}&command_type=eq.${encodeURIComponent(command_type)}&status=in.(pending,processing)&created_at=gt.${encodeURIComponent(since)}&select=id&limit=1`;
    const resp = await fetch(url, { headers: supabaseHeaders(env) });
    if (!resp.ok) return false;
    const rows = await resp.json();
    return rows.length > 0;
  } catch {
    return false;
  }
}
