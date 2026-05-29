// Settings read/update endpoints.
import { withCors, jsonResponse } from '../http.js';
import { supabaseHeaders, supabaseErrorDetail, fetchSettingsRows, rowsToSettings } from '../supabase.js';
import { validateSettingsPatch } from '../validation.js';
import { writeAuditLog } from '../audit.js';

export async function handleGetSettings(env, ao) {
  try {
    const rows = await fetchSettingsRows(env);
    return withCors(jsonResponse({ ok: true, settings: rowsToSettings(rows), rows }), ao);
  } catch {
    return withCors(jsonResponse({ error: 'settings_fetch_failed' }, 500), ao);
  }
}

export async function handlePatchSettings(request, env, user, ao) {
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
    await writeAuditLog(env, user, 'settings_updated', { keys: rows.map(r => r.key) });
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
