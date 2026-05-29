// Supabase REST helpers (service-role key).

export function supabaseHeaders(env, extra = {}) {
  return {
    apikey: env.SUPABASE_SERVICE_ROLE_KEY,
    authorization: `Bearer ${env.SUPABASE_SERVICE_ROLE_KEY}`,
    ...extra,
  };
}

export function supabaseBase(env) {
  return env.SUPABASE_URL.replace(/\/$/, '');
}

export async function supabaseErrorDetail(resp) {
  const text = await resp.text().catch(() => '');
  if (!text) return `HTTP ${resp.status}`;
  try {
    const json = JSON.parse(text);
    return json.message || json.details || json.hint || text.slice(0, 300);
  } catch {
    return text.slice(0, 300);
  }
}

export function contentRangeCount(resp) {
  return parseInt(resp.headers.get('content-range')?.split('/')[1] || '0', 10) || 0;
}

export async function fetchSupabaseJson(env, path, options = {}) {
  const resp = await fetch(`${supabaseBase(env)}${path}`, {
    ...options,
    headers: supabaseHeaders(env, options.headers || {}),
  });
  if (!resp.ok) throw new Error('supabase_fetch_failed');
  return resp.json();
}

export async function fetchCount(env, table, filters = '') {
  const resp = await fetch(`${supabaseBase(env)}/rest/v1/${table}?select=*&limit=1${filters}`, {
    headers: supabaseHeaders(env, { prefer: 'count=exact' }),
  });
  return resp.ok ? contentRangeCount(resp) : null;
}

export function rowsToSettings(rows) {
  return Object.fromEntries((rows || []).map((row) => [row.key, row.value]));
}

export async function fetchSettingsRows(env) {
  const resp = await fetch(
    `${supabaseBase(env)}/rest/v1/bot_settings?select=key,value,description,updated_by,updated_at&order=key.asc`,
    { headers: supabaseHeaders(env) },
  );
  if (!resp.ok) throw new Error('settings_fetch_failed');
  return resp.json();
}
