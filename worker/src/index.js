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

const ADMIN_ROLES = new Set(['owner', 'admin']);
const SETTINGS_KEYS = new Set([
  'daily_post_enabled', 'daily_post_times', 'daily_post_days', 'timezone',
  'ai_enabled', 'ai_auto_only', 'ai_language', 'ai_tone', 'ai_pre_message_enabled',
  'ai_post_question_enabled', 'ai_pre_message_delay_seconds', 'ai_post_question_delay_seconds', 'ai_model', 'ai_creativity',
  'include_spoilers', 'allowed_card_types', 'day_config', 'telegram_chat_id',
  'sync_schedule_enabled', 'sync_schedule_days', 'sync_schedule_time',
]);
const AI_LANGUAGE_VALUES = new Set(['pt-BR', 'en-US']);
const AI_TONES = new Set(['random','misterioso','tenso','epico','sombrio','reflexivo','esperancoso','perturbador','melancolico']);
const AI_MODELS = new Set([
  'gemini-2.0-flash','gemini-2.5-flash','gemini-2.5-flash-preview-05-20','gemini-2.5-pro',
  'gpt-4o-mini','gpt-4o','gpt-4.1-mini','gpt-4.1','gpt-4-turbo',
  'llama-3.3-70b-versatile','llama-3.1-8b-instant','mixtral-8x7b-32768',
  'mistral-small-latest','mistral-medium-latest','open-mistral-7b',
]);
const AI_CREATIVITY_VALUES = new Set(['conservative','default','creative']);
const WEEKDAY_CODES = new Set(['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun', 'all']);
const VALID_CARD_TYPES = new Set([
  'investigator', 'asset', 'event', 'skill',
  'enemy', 'location', 'treachery', 'act', 'agenda', 'story',
]);

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
    'access-control-allow-methods': 'GET,POST,PATCH,OPTIONS',
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

function supabaseHeaders(env, extra = {}) {
  return {
    apikey: env.SUPABASE_SERVICE_ROLE_KEY,
    authorization: `Bearer ${env.SUPABASE_SERVICE_ROLE_KEY}`,
    ...extra,
  };
}

function supabaseBase(env) {
  return env.SUPABASE_URL.replace(/\/$/, '');
}

async function supabaseErrorDetail(resp) {
  const text = await resp.text().catch(() => '');
  if (!text) return `HTTP ${resp.status}`;
  try {
    const json = JSON.parse(text);
    return json.message || json.details || json.hint || text.slice(0, 300);
  } catch {
    return text.slice(0, 300);
  }
}

function boundedLimit(raw, fallback = 20, max = 50) {
  const value = Number(raw || fallback);
  if (!Number.isFinite(value)) return fallback;
  return Math.max(1, Math.min(Math.floor(value), max));
}

function contentRangeCount(resp) {
  return parseInt(resp.headers.get('content-range')?.split('/')[1] || '0', 10) || 0;
}

async function fetchSupabaseJson(env, path, options = {}) {
  const resp = await fetch(`${supabaseBase(env)}${path}`, {
    ...options,
    headers: supabaseHeaders(env, options.headers || {}),
  });
  if (!resp.ok) throw new Error('supabase_fetch_failed');
  return resp.json();
}

async function fetchCount(env, table, filters = '') {
  const resp = await fetch(`${supabaseBase(env)}/rest/v1/${table}?select=*&limit=1${filters}`, {
    headers: supabaseHeaders(env, { prefer: 'count=exact' }),
  });
  return resp.ok ? contentRangeCount(resp) : null;
}

function rowsToSettings(rows) {
  return Object.fromEntries((rows || []).map((row) => [row.key, row.value]));
}

async function fetchSettingsRows(env) {
  const resp = await fetch(
    `${supabaseBase(env)}/rest/v1/bot_settings?select=key,value,description,updated_by,updated_at&order=key.asc`,
    { headers: supabaseHeaders(env) },
  );
  if (!resp.ok) throw new Error('settings_fetch_failed');
  return resp.json();
}

function isValidTime(value) {
  if (typeof value !== 'string' || !/^\d{2}:\d{2}$/.test(value)) return false;
  const [hour, minute] = value.split(':').map(Number);
  return hour >= 0 && hour <= 23 && minute >= 0 && minute <= 59;
}

function validateTimezone(value) {
  if (typeof value !== 'string' || !value.trim()) return null;
  const timezone = value.trim();
  try {
    new Intl.DateTimeFormat('en-US', { timeZone: timezone }).format(new Date());
    return timezone;
  } catch {
    return null;
  }
}

function validateSettingsPatch(body) {
  if (!body || typeof body !== 'object' || Array.isArray(body)) {
    return { error: 'invalid_json' };
  }
  const settings = {};
  for (const [key, value] of Object.entries(body)) {
    if (!SETTINGS_KEYS.has(key)) {
      return { error: 'unsupported_setting', key, detail: `Unsupported setting: ${key}` };
    }
    if (key === 'daily_post_enabled') {
      if (typeof value !== 'boolean') return { error: 'invalid_setting_value', key };
      settings[key] = value;
    }
    if (key === 'daily_post_times') {
      if (!Array.isArray(value) || value.length === 0 || !value.every(isValidTime)) {
        return { error: 'invalid_setting_value', key };
      }
      settings[key] = value;
    }
    if (key === 'daily_post_days') {
      if (!Array.isArray(value) || !value.every((day) => WEEKDAY_CODES.has(day))) {
        return { error: 'invalid_setting_value', key };
      }
      settings[key] = value;
    }
    if (key === 'timezone') {
      const timezone = validateTimezone(value);
      if (!timezone) return { error: 'invalid_setting_value', key };
      settings[key] = timezone;
    }
    if (key === 'ai_enabled') {
      if (typeof value !== 'boolean') return { error: 'invalid_setting_value', key };
      settings[key] = value;
    }
    if (key === 'ai_language') {
      if (!AI_LANGUAGE_VALUES.has(value)) return { error: 'invalid_setting_value', key };
      settings[key] = value;
    }
    if (key === 'ai_tone') {
      if (!AI_TONES.has(value)) return { error: 'invalid_setting_value', key };
      settings[key] = value;
    }
    if (key === 'ai_pre_message_enabled' || key === 'ai_post_question_enabled' || key === 'ai_auto_only') {
      if (typeof value !== 'boolean') return { error: 'invalid_setting_value', key };
      settings[key] = value;
    }
    if (key === 'ai_pre_message_delay_seconds' || key === 'ai_post_question_delay_seconds') {
      const n = Number(value);
      if (!Number.isInteger(n) || n < 0 || n > 3600) return { error: 'invalid_setting_value', key };
      settings[key] = n;
    }
    if (key === 'ai_model') {
      if (!AI_MODELS.has(value)) return { error: 'invalid_setting_value', key };
      settings[key] = value;
    }
    if (key === 'ai_creativity') {
      if (!AI_CREATIVITY_VALUES.has(value)) return { error: 'invalid_setting_value', key };
      settings[key] = value;
    }
    if (key === 'include_spoilers') {
      if (typeof value !== 'boolean') return { error: 'invalid_setting_value', key };
      settings[key] = value;
    }
    if (key === 'allowed_card_types') {
      if (!Array.isArray(value) || value.length === 0 || !value.every((t) => VALID_CARD_TYPES.has(t))) {
        return { error: 'invalid_setting_value', key };
      }
      settings[key] = value;
    }
    if (key === 'telegram_chat_id') {
      if (typeof value !== 'string') return { error: 'invalid_setting_value', key };
      settings[key] = value.trim();
    }
    if (key === 'sync_schedule_enabled') {
      if (typeof value !== 'boolean') return { error: 'invalid_setting_value', key };
      settings[key] = value;
    }
    if (key === 'sync_schedule_days') {
      if (!Array.isArray(value) || !value.every((d) => WEEKDAY_CODES.has(d))) {
        return { error: 'invalid_setting_value', key };
      }
      settings[key] = value;
    }
    if (key === 'sync_schedule_time') {
      if (!isValidTime(value)) return { error: 'invalid_setting_value', key };
      settings[key] = value;
    }
    if (key === 'day_config') {
      // { mon: { packs: ['core','dwl',...], types: ['investigator'] }, ... }
      if (typeof value !== 'object' || Array.isArray(value) || value === null) {
        return { error: 'invalid_setting_value', key };
      }
      for (const [day, cfg] of Object.entries(value)) {
        if (!WEEKDAY_CODES.has(day)) return { error: 'invalid_setting_value', key };
        if (cfg !== null && cfg !== undefined) {
          if (typeof cfg !== 'object' || Array.isArray(cfg)) return { error: 'invalid_setting_value', key };
          const { packs: p, types: t, times } = cfg;
          if (p !== undefined && (!Array.isArray(p) || !p.every((x) => typeof x === 'string' && x.length > 0))) {
            return { error: 'invalid_setting_value', key };
          }
          if (t !== undefined && (!Array.isArray(t) || !t.every((x) => VALID_CARD_TYPES.has(x)))) {
            return { error: 'invalid_setting_value', key };
          }
          if (times !== undefined && (!Array.isArray(times) || !times.every(isValidTime))) {
            return { error: 'invalid_setting_value', key };
          }
        }
      }
      settings[key] = value;
    }
  }
  if (Object.keys(settings).length === 0) return { error: 'settings_required' };
  return { settings };
}

async function requireAdmin(request, env, ao, path) {
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
  return { user, access };
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

async function handleOverview(request, env, user, ao) {
  try {
    const [
      settingsRows,
      recentCommands,
      recentPosts,
      recentErrors,
      targetChats,
      cardsCount,
      packsCount,
      postedCount,
      pendingCount,
      retryingCount,
      processingCount,
      failedCount,
    ] = await Promise.all([
      fetchSettingsRows(env),
      fetchSupabaseJson(env, '/rest/v1/bot_commands?select=id,command_type,status,created_at,updated_at,executed_at,last_error,payload,result,requested_by_name&order=created_at.desc&limit=12'),
      fetchSupabaseJson(env, '/rest/v1/bot_posting_history?select=id,card_code,card_name,status,created_at,telegram_message_id&order=created_at.desc&limit=8'),
      fetchSupabaseJson(env, '/rest/v1/bot_errors?select=id,context,error_message,card_code,created_at&order=created_at.desc&limit=5'),
      fetchSupabaseJson(env, '/rest/v1/target_chats?select=chat_id,title,message_thread_id,enabled,updated_at&order=created_at.desc&limit=20'),
      fetchCount(env, 'arkham_cards'),
      fetchCount(env, 'arkham_packs'),
      fetchCount(env, 'bot_posted_cards'),
      fetchCount(env, 'bot_commands', '&status=eq.pending'),
      fetchCount(env, 'bot_commands', '&status=eq.retrying'),
      fetchCount(env, 'bot_commands', '&status=eq.processing'),
      fetchCount(env, 'bot_commands', '&status=eq.failed'),
    ]);

    const lastSync = recentCommands.find((cmd) => cmd.command_type === 'sync_arkhamdb')?.created_at || null;
    return withCors(jsonResponse({
      ok: true,
      settings: rowsToSettings(settingsRows),
      settings_rows: settingsRows,
      counts: {
        cards: cardsCount,
        packs: packsCount,
        posted_cards: postedCount,
        pending_commands: pendingCount,
        retrying_commands: retryingCount,
        processing_commands: processingCount,
        failed_commands: failedCount,
      },
      recent_commands: recentCommands,
      recent_posts: recentPosts,
      recent_errors: recentErrors,
      target_chats: targetChats,
      last_sync: lastSync,
      user: { id: user.id },
    }), ao);
  } catch {
    return withCors(jsonResponse({ error: 'overview_fetch_failed' }, 500), ao);
  }
}

async function handleCommands(request, env, ao) {
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

async function handleCancelCommand(request, env, user, ao, commandId) {
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
      }),
    });
    if (!resp.ok) return withCors(jsonResponse({ error: 'command_cancel_failed' }, 500), ao);
    const rows = await resp.json();
    if (!rows.length) return withCors(jsonResponse({ error: 'command_not_cancellable' }, 409), ao);
    return withCors(jsonResponse({ ok: true, command: rows[0] }), ao);
  } catch {
    return withCors(jsonResponse({ error: 'command_cancel_failed' }, 500), ao);
  }
}

async function handleBotInfo(env, ao) {
  const token = env.TELEGRAM_BOT_TOKEN;
  if (!token) return withCors(jsonResponse({ error: 'bot_token_not_configured' }, 500), ao);

  const tgApi = (path) =>
    fetch(`https://api.telegram.org/bot${token}/${path}`, { headers: { Accept: 'application/json' } })
      .then((r) => r.json());

  try {
    // getMe returns bot id, name, username + description/short_description (Bot API 6.7+)
    const meResp = await tgApi('getMe');
    if (!meResp.ok) return withCors(jsonResponse({ error: 'telegram_api_failed' }, 502), ao);

    const bot = meResp.result;
    let photo_url = null;

    // Fetch profile photos using the bot's own numeric id
    const photosResp = await tgApi(`getUserProfilePhotos?user_id=${bot.id}&limit=1`);
    const fileId = photosResp.result?.photos?.[0]?.at(-1)?.file_id;
    if (fileId) {
      const fileResp = await tgApi(`getFile?file_id=${fileId}`);
      if (fileResp.ok && fileResp.result?.file_path) {
        photo_url = `https://api.telegram.org/file/bot${token}/${fileResp.result.file_path}`;
      }
    }

    return withCors(jsonResponse({
      ok: true,
      name: bot.first_name || null,
      username: bot.username || null,
      description: bot.description || null,
      short_description: bot.short_description || null,
      photo_url,
    }), ao);
  } catch {
    return withCors(jsonResponse({ error: 'bot_info_fetch_failed' }, 500), ao);
  }
}

async function handleGetPacks(_env, ao) {
  try {
    const resp = await fetch('https://arkhamdb.com/api/public/packs/', {
      headers: { 'Accept': 'application/json' },
    });
    if (!resp.ok) throw new Error(`ArkhamDB returned ${resp.status}`);
    const raw = await resp.json();
    const packs = raw
      .map((p) => ({
        code: p.code,
        name: p.name,
        cycle_position: p.cycle_position ?? null,
        position: p.position ?? null,
        chapter: p.chapter ?? 1,
        total: p.total ?? 0,
      }))
      .sort((a, b) => (a.cycle_position ?? 99) - (b.cycle_position ?? 99) || (a.position ?? 99) - (b.position ?? 99));
    return withCors(jsonResponse({ ok: true, packs }), ao);
  } catch (err) {
    return withCors(jsonResponse({ error: 'packs_fetch_failed', detail: String(err) }, 500), ao);
  }
}

async function handleGetHistory(request, env, ao) {
  const url = new URL(request.url);
  const date = (url.searchParams.get('date') || '').trim();
  const q = (url.searchParams.get('q') || '').trim().replace(/[^\w\s:-]/g, '');
  const limit = boundedLimit(url.searchParams.get('limit'), 30, 100);
  const offset = Math.max(0, Number(url.searchParams.get('offset') || 0));

  let path = `/rest/v1/bot_posting_history?select=id,card_code,card_name,status,source,created_at,telegram_message_id&order=created_at.desc&limit=${limit}&offset=${offset}`;

  if (date && /^\d{4}-\d{2}-\d{2}$/.test(date)) {
    let tz = 'UTC';
    try {
      const settingsRows = await fetchSettingsRows(env);
      const settings = rowsToSettings(settingsRows);
      if (settings.timezone) tz = settings.timezone;
    } catch {}

    // Convert a local date string (YYYY-MM-DD) + time to a UTC Date in the given tz.
    // sv-SE locale produces "YYYY-MM-DD HH:MM:SS" which is easy to parse.
    const localToUTC = (d, time) => {
      const approx = new Date(`${d}T${time}Z`);
      const localStr = new Intl.DateTimeFormat('sv-SE', {
        timeZone: tz,
        year: 'numeric', month: '2-digit', day: '2-digit',
        hour: '2-digit', minute: '2-digit', second: '2-digit',
      }).format(approx).replace(' ', 'T');
      const offsetMs = approx.getTime() - new Date(localStr + 'Z').getTime();
      return new Date(new Date(`${d}T${time}Z`).getTime() + offsetMs);
    };

    const nextDay = new Date(Date.UTC(...date.split('-').map(Number).map((v, i) => i === 1 ? v - 1 : v)));
    nextDay.setUTCDate(nextDay.getUTCDate() + 1);
    const nextDayStr = nextDay.toISOString().slice(0, 10);

    const startUTC = localToUTC(date, '00:00:00');
    const endUTC   = localToUTC(nextDayStr, '00:00:00');

    path += `&created_at=gte.${startUTC.toISOString()}&created_at=lt.${endUTC.toISOString()}`;
  }

  if (q.length >= 2) {
    path += `&or=(card_code.ilike.*${encodeURIComponent(q)}*,card_name.ilike.*${encodeURIComponent(q)}*)`;
  }

  try {
    const rows = await fetchSupabaseJson(env, path);
    return withCors(jsonResponse({ ok: true, history: rows }), ao);
  } catch {
    return withCors(jsonResponse({ error: 'history_fetch_failed' }, 500), ao);
  }
}

function cardSearchPath(request) {
  const url = new URL(request.url);
  const query = (url.searchParams.get('q') || '').trim().replace(/[^\w\s:'-]/g, ' ');
  const limit = boundedLimit(url.searchParams.get('limit'), 15, 25);
  if (query.length < 2) return null;
  const params = new URLSearchParams({
    select: 'code,name,real_name,type_code,faction_name,pack_name,spoiler_level',
    or: `(code.ilike.*${query}*,name.ilike.*${query}*,real_name.ilike.*${query}*)`,
    order: 'code.asc',
    limit: String(limit),
  });
  return `/rest/v1/arkham_cards?${params.toString()}`;
}

async function handleCardsSearch(request, env, ao) {
  const path = cardSearchPath(request);
  if (!path) return withCors(jsonResponse({ ok: true, cards: [] }), ao);
  try {
    const rows = await fetchSupabaseJson(env, path);
    return withCors(jsonResponse({ ok: true, cards: rows }), ao);
  } catch {
    return withCors(jsonResponse({ error: 'cards_search_failed' }, 500), ao);
  }
}

async function handleGetSettings(env, ao) {
  try {
    const rows = await fetchSettingsRows(env);
    return withCors(jsonResponse({ ok: true, settings: rowsToSettings(rows), rows }), ao);
  } catch {
    return withCors(jsonResponse({ error: 'settings_fetch_failed' }, 500), ao);
  }
}

async function handlePatchSettings(request, env, user, ao) {
  if (!env.SUPABASE_URL || !env.SUPABASE_SERVICE_ROLE_KEY) {
    return withCors(jsonResponse({
      error: 'backend_not_configured',
      detail: 'SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY is missing in the Worker.',
    }, 500), ao);
  }

  let body;
  try {
    body = await request.json();
  } catch {
    return withCors(jsonResponse({ error: 'invalid_json' }, 400), ao);
  }

  const validation = validateSettingsPatch(body);
  if (validation.error) {
    return withCors(jsonResponse(validation, 400), ao);
  }

  const rows = Object.entries(validation.settings).map(([key, value]) => ({
    key,
    value,
    updated_by: String(user.id),
  }));

  try {
    const base = env.SUPABASE_URL.replace(/\/$/, '');
    const resp = await fetch(`${base}/rest/v1/bot_settings?on_conflict=key`, {
      method: 'POST',
      headers: supabaseHeaders(env, {
        'content-type': 'application/json',
        prefer: 'resolution=merge-duplicates,return=representation',
      }),
      body: JSON.stringify(rows),
    });
    if (!resp.ok) {
      const detail = await supabaseErrorDetail(resp);
      console.log(JSON.stringify({
        path: '/settings',
        method: 'PATCH',
        status: resp.status,
        error: 'settings_upsert_failed',
        detail,
      }));
      return withCors(jsonResponse({ error: 'settings_upsert_failed', detail, upstream_status: resp.status }, 500), ao);
    }
    const currentRows = await fetchSettingsRows(env);
    return withCors(jsonResponse({ ok: true, settings: rowsToSettings(currentRows), rows: currentRows }), ao);
  } catch (err) {
    const detail = err?.message || String(err);
    console.log(JSON.stringify({
      path: '/settings',
      method: 'PATCH',
      status: 500,
      error: 'settings_upsert_failed',
      detail,
    }));
    return withCors(jsonResponse({ error: 'settings_upsert_failed', detail }, 500), ao);
  }
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

    if (pathname === '/overview' && request.method === 'GET') {
      const auth = await requireAdmin(request, env, ao, '/overview');
      if (auth.response) return auth.response;
      return handleOverview(request, env, auth.user, ao);
    }

    if (pathname === '/settings' && (request.method === 'GET' || request.method === 'PATCH')) {
      const auth = await requireAdmin(request, env, ao, '/settings');
      if (auth.response) return auth.response;
      if (request.method === 'GET') return handleGetSettings(env, ao);
      return handlePatchSettings(request, env, auth.user, ao);
    }

    if (pathname === '/commands' && request.method === 'GET') {
      const auth = await requireAdmin(request, env, ao, '/commands');
      if (auth.response) return auth.response;
      return handleCommands(request, env, ao);
    }

    if (pathname.startsWith('/commands/') && request.method === 'PATCH') {
      const auth = await requireAdmin(request, env, ao, '/commands/:id');
      if (auth.response) return auth.response;
      const commandId = pathname.split('/').filter(Boolean)[1] || '';
      return handleCancelCommand(request, env, auth.user, ao, commandId);
    }

    if (pathname === '/cards' && request.method === 'GET') {
      const auth = await requireAdmin(request, env, ao, '/cards');
      if (auth.response) return auth.response;
      return handleCardsSearch(request, env, ao);
    }

    if (pathname === '/packs' && request.method === 'GET') {
      const auth = await requireAdmin(request, env, ao, '/packs');
      if (auth.response) return auth.response;
      return handleGetPacks(env, ao);
    }

    if (pathname === '/history' && request.method === 'GET') {
      const auth = await requireAdmin(request, env, ao, '/history');
      if (auth.response) return auth.response;
      return handleGetHistory(request, env, ao);
    }

    if (pathname === '/bot-info' && request.method === 'GET') {
      const auth = await requireAdmin(request, env, ao, '/bot-info');
      if (auth.response) return auth.response;
      return handleBotInfo(env, ao);
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

    if (pathname === '/me' || pathname === '/status' || pathname === '/overview' || pathname === '/settings' || pathname === '/commands' || pathname.startsWith('/commands/') || pathname === '/cards' || pathname === '/packs' || pathname === '/bot-info' || pathname === '/bot-command' || pathname === '/' || pathname === '/history') {
      return withCors(jsonResponse({ error: 'method_not_allowed' }, 405), ao);
    }

    return withCors(jsonResponse({ error: 'not_found' }, 404), ao);
  },
};
