// Admin management endpoints (owner-gated).
import { withCors, jsonResponse } from '../http.js';
import { supabaseBase, supabaseHeaders } from '../supabase.js';
import { writeAuditLog } from '../audit.js';

export async function handleGetAdmins(env, ao) {
  try {
    const url = `${supabaseBase(env)}/rest/v1/bot_admins?select=telegram_user_id,name,role,enabled,added_by_user_id,added_by_name,created_at,updated_at&order=created_at.asc`;
    const resp = await fetch(url, { headers: supabaseHeaders(env) });
    if (!resp.ok) return withCors(jsonResponse({ ok: false, error: 'admins_fetch_failed' }, 502), ao);
    const admins = await resp.json();
    return withCors(jsonResponse({ ok: true, admins }), ao);
  } catch {
    return withCors(jsonResponse({ ok: false, error: 'admins_fetch_failed' }, 502), ao);
  }
}

export async function handleAddAdmin(request, env, user, ao) {
  const body = await request.json().catch(() => ({}));
  const { telegram_user_id, name = '', role = 'admin' } = body;
  if (!telegram_user_id || !['owner', 'admin', 'viewer'].includes(role)) {
    return withCors(jsonResponse({ ok: false, error: 'invalid_admin_data' }, 400), ao);
  }
  const record = {
    telegram_user_id: Number(telegram_user_id),
    name: String(name || '').slice(0, 100),
    role,
    enabled: true,
    added_by_user_id: user.id,
    added_by_name: user.name || '',
  };
  const url = `${supabaseBase(env)}/rest/v1/bot_admins?on_conflict=telegram_user_id`;
  const resp = await fetch(url, {
    method: 'POST',
    headers: { ...supabaseHeaders(env), 'content-type': 'application/json', 'Prefer': 'resolution=merge-duplicates,return=representation' },
    body: JSON.stringify(record),
  });
  if (!resp.ok) return withCors(jsonResponse({ ok: false, error: 'admin_insert_failed' }), ao);
  await writeAuditLog(env, user, 'admin_added', { target_user_id: telegram_user_id, role });
  const result = await resp.json();
  return withCors(jsonResponse({ ok: true, admin: Array.isArray(result) ? result[0] : result }), ao);
}

export async function handleRemoveAdmin(request, env, user, ao, targetUserId) {
  try {
    const targetId = Number(targetUserId);
    if (!targetId) return withCors(jsonResponse({ ok: false, error: 'invalid_user_id' }, 400), ao);
    const checkUrl = `${supabaseBase(env)}/rest/v1/bot_admins?role=eq.owner&enabled=eq.true&select=telegram_user_id`;
    const checkResp = await fetch(checkUrl, { headers: supabaseHeaders(env) });
    if (!checkResp.ok) return withCors(jsonResponse({ ok: false, error: 'owner_check_failed' }, 502), ao);
    const owners = await checkResp.json();
    const isTargetOwner = owners.some((o) => o.telegram_user_id === targetId);
    if (isTargetOwner && owners.length <= 1) {
      return withCors(jsonResponse({ ok: false, error: 'cannot_remove_last_owner' }, 409), ao);
    }
    const url = `${supabaseBase(env)}/rest/v1/bot_admins?telegram_user_id=eq.${targetId}`;
    const resp = await fetch(url, {
      method: 'PATCH',
      headers: { ...supabaseHeaders(env), 'content-type': 'application/json' },
      body: JSON.stringify({ enabled: false, removed_by_user_id: user.id, removed_by_name: user.name || '', removed_at: new Date().toISOString() }),
    });
    if (!resp.ok) return withCors(jsonResponse({ ok: false, error: 'admin_remove_failed' }, 502), ao);
    await writeAuditLog(env, user, 'admin_removed', { target_user_id: targetId });
    return withCors(jsonResponse({ ok: true }), ao);
  } catch {
    return withCors(jsonResponse({ ok: false, error: 'admin_remove_failed' }, 502), ao);
  }
}
