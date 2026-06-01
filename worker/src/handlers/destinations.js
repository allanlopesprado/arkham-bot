// Destination (target chat) management: list, add, pending review, resolve, edit, delete, test.
import { withCors, jsonResponse } from '../http.js';
import { supabaseBase, supabaseHeaders, fetchSupabaseJson } from '../supabase.js';
import { writeAuditLog } from '../audit.js';

function parseThreadId(value) {
  if (value === null || value === undefined || value === '') return null;
  const n = Number(value);
  return Number.isInteger(n) && n > 0 ? n : 'invalid';
}

export async function handleGetDestinations(env, ao) {
  try {
    const url = `${supabaseBase(env)}/rest/v1/target_chats?select=id,chat_id,title,message_thread_id,enabled,added_by_user_id,added_by_name,created_at,updated_at&enabled=eq.true&order=created_at.asc`;
    const resp = await fetch(url, { headers: supabaseHeaders(env) });
    if (!resp.ok) return withCors(jsonResponse({ ok: false, error: 'destinations_fetch_failed' }, 502), ao);
    const destinations = await resp.json();
    return withCors(jsonResponse({ ok: true, destinations }), ao);
  } catch {
    return withCors(jsonResponse({ ok: false, error: 'destinations_fetch_failed' }, 502), ao);
  }
}

export async function handleAddDestination(request, env, user, ao) {
  try {
    const body = await request.json().catch(() => ({}));
    const { chat_id, title = '', message_thread_id = null } = body;
    if (!chat_id) return withCors(jsonResponse({ ok: false, error: 'chat_id_required' }, 400), ao);
    if (!/^-?\d+$/.test(String(chat_id))) {
      return withCors(jsonResponse({ ok: false, error: 'invalid_chat_id' }, 400), ao);
    }
    const threadId = parseThreadId(message_thread_id);
    if (threadId === 'invalid') {
      return withCors(jsonResponse({ ok: false, error: 'invalid_message_thread_id' }, 400), ao);
    }
    const record = {
      chat_id: String(chat_id),
      title: String(title || '').slice(0, 200),
      message_thread_id: threadId,
      enabled: true,
      added_by_user_id: user.id,
      added_by_name: user.name || '',
      removed_by_user_id: null,
      removed_by_name: null,
      removed_at: null,
    };
    // Check for duplicate (chat_id, message_thread_id) pair before inserting.
    // on_conflict=chat_id,message_thread_id requires the composite UNIQUE constraint
    // applied in migration 20260528_telegram_topics_support.sql
    const threadFilter = record.message_thread_id != null
      ? `&message_thread_id=eq.${record.message_thread_id}`
      : `&message_thread_id=is.null`;
    const dupCheck = await fetchSupabaseJson(env,
      `/rest/v1/target_chats?select=id,enabled&chat_id=eq.${encodeURIComponent(record.chat_id)}${threadFilter}&limit=1`);
    if (dupCheck && dupCheck.length > 0) {
      const existing = dupCheck[0];
      if (existing.enabled) {
        return withCors(jsonResponse({ ok: false, error: 'destination_already_exists' }, 409), ao);
      }
      // Re-enable soft-deleted destination
      const reUrl = `${supabaseBase(env)}/rest/v1/target_chats?id=eq.${existing.id}`;
      const reResp = await fetch(reUrl, {
        method: 'PATCH',
        headers: { ...supabaseHeaders(env), 'content-type': 'application/json', 'Prefer': 'return=representation' },
        body: JSON.stringify({ enabled: true, removed_by_user_id: null, removed_by_name: null, removed_at: null,
          title: record.title, added_by_user_id: user.id, added_by_name: user.name || '' }),
      });
      if (!reResp.ok) return withCors(jsonResponse({ ok: false, error: 'destination_insert_failed' }, 502), ao);
      await writeAuditLog(env, user, 'destination_readded', { chat_id });
      const reResult = await reResp.json();
      return withCors(jsonResponse({ ok: true, destination: Array.isArray(reResult) ? reResult[0] : reResult }), ao);
    }
    const url = `${supabaseBase(env)}/rest/v1/target_chats`;
    const resp = await fetch(url, {
      method: 'POST',
      headers: { ...supabaseHeaders(env), 'content-type': 'application/json', 'Prefer': 'return=representation' },
      body: JSON.stringify(record),
    });
    if (!resp.ok) return withCors(jsonResponse({ ok: false, error: 'destination_insert_failed' }, 502), ao);
    await writeAuditLog(env, user, 'destination_added', { chat_id });
    const result = await resp.json();
    return withCors(jsonResponse({ ok: true, destination: Array.isArray(result) ? result[0] : result }), ao);
  } catch {
    return withCors(jsonResponse({ ok: false, error: 'destination_insert_failed' }, 502), ao);
  }
}

export async function handleGetPendingDestinations(env, ao) {
  try {
    const url = `${supabaseBase(env)}/rest/v1/pending_destinations?status=eq.pending&order=added_at.desc&limit=20`;
    const resp = await fetch(url, { headers: supabaseHeaders(env) });
    if (!resp.ok) return withCors(jsonResponse({ ok: false, error: 'fetch_failed' }, 502), ao);
    const rows = await resp.json();
    return withCors(jsonResponse({ ok: true, pending: rows }), ao);
  } catch {
    return withCors(jsonResponse({ ok: false, error: 'fetch_failed' }, 502), ao);
  }
}

export async function handleAcceptPendingDestination(request, env, user, ao, pendingId) {
  try {
    const body = await request.json().catch(() => ({}));
    const threadId = parseThreadId(body.message_thread_id);
    if (threadId === 'invalid') {
      return withCors(jsonResponse({ ok: false, error: 'invalid_message_thread_id' }, 400), ao);
    }
    // Fetch pending entry
    const pUrl = `${supabaseBase(env)}/rest/v1/pending_destinations?id=eq.${pendingId}&status=eq.pending&limit=1`;
    const pResp = await fetch(pUrl, { headers: supabaseHeaders(env) });
    const rows = await pResp.json().catch(() => []);
    if (!rows.length) return withCors(jsonResponse({ ok: false, error: 'pending_not_found' }, 404), ao);
    const { chat_id, chat_title } = rows[0];
    // Insert into target_chats (check for existing first)
    const checkUrl = `${supabaseBase(env)}/rest/v1/target_chats?chat_id=eq.${encodeURIComponent(chat_id)}&message_thread_id=${threadId == null ? 'is.null' : `eq.${threadId}`}&limit=1`;
    const checkResp = await fetch(checkUrl, { headers: supabaseHeaders(env) });
    const existing = await checkResp.json().catch(() => []);
    if (existing.length && existing[0].enabled) {
      return withCors(jsonResponse({ ok: false, error: 'destination_already_exists' }, 409), ao);
    }
    const destBody = { chat_id, title: chat_title, message_thread_id: threadId, enabled: true,
      added_by_user_id: user.id, added_by_name: user.name || '', removed_by_user_id: null, removed_by_name: null, removed_at: null };
    const insertResp = await fetch(`${supabaseBase(env)}/rest/v1/target_chats`, {
      method: 'POST', headers: { ...supabaseHeaders(env), 'content-type': 'application/json', 'Prefer': 'return=representation' },
      body: JSON.stringify(destBody),
    });
    if (!insertResp.ok) return withCors(jsonResponse({ ok: false, error: 'destination_insert_failed' }, 502), ao);
    // Mark pending as accepted
    await fetch(`${supabaseBase(env)}/rest/v1/pending_destinations?id=eq.${pendingId}`, {
      method: 'PATCH', headers: { ...supabaseHeaders(env), 'content-type': 'application/json' },
      body: JSON.stringify({ status: 'accepted' }),
    });
    await writeAuditLog(env, user, 'destination_added_from_pending', { chat_id, chat_title, message_thread_id: threadId });
    const result = await insertResp.json();
    return withCors(jsonResponse({ ok: true, destination: Array.isArray(result) ? result[0] : result }), ao);
  } catch {
    return withCors(jsonResponse({ ok: false, error: 'accept_failed' }, 502), ao);
  }
}

export async function handleDismissPendingDestination(env, user, ao, pendingId) {
  try {
    const resp = await fetch(`${supabaseBase(env)}/rest/v1/pending_destinations?id=eq.${pendingId}`, {
      method: 'PATCH', headers: { ...supabaseHeaders(env), 'content-type': 'application/json' },
      body: JSON.stringify({ status: 'dismissed' }),
    });
    if (!resp.ok) return withCors(jsonResponse({ ok: false, error: 'dismiss_failed' }, 502), ao);
    return withCors(jsonResponse({ ok: true }), ao);
  } catch {
    return withCors(jsonResponse({ ok: false, error: 'dismiss_failed' }, 502), ao);
  }
}

export async function handleResolveDestination(request, env, ao) {
  const url = new URL(request.url);
  const chatId = url.searchParams.get('chat_id');
  if (!chatId || !/^-?\d+$/.test(chatId)) {
    return withCors(jsonResponse({ ok: false, error: 'invalid_chat_id' }, 400), ao);
  }
  const botToken = env.TELEGRAM_BOT_TOKEN;
  if (!botToken) return withCors(jsonResponse({ ok: false, error: 'bot_token_not_configured' }, 500), ao);
  try {
    const tgResp = await fetch(`https://api.telegram.org/bot${botToken}/getChat?chat_id=${encodeURIComponent(chatId)}`);
    const tgJson = await tgResp.json().catch(() => ({}));
    if (!tgResp.ok || !tgJson.ok) {
      return withCors(jsonResponse({ ok: false, error: 'chat_not_found', detail: tgJson.description || '' }), ao);
    }
    const chat = tgJson.result || {};
    return withCors(jsonResponse({
      ok: true,
      name: chat.title || chat.username || chat.first_name || '',
      type: chat.type || '',
      username: chat.username || null,
    }), ao);
  } catch {
    return withCors(jsonResponse({ ok: false, error: 'resolve_failed' }, 502), ao);
  }
}

export async function handleUpdateDestination(request, env, user, ao, destId) {
  try {
    const body = await request.json().catch(() => ({}));
    const patch = {};
    if (typeof body.enabled === 'boolean') patch.enabled = body.enabled;
    if (typeof body.title === 'string') patch.title = body.title.slice(0, 200);
    if (!Object.keys(patch).length) return withCors(jsonResponse({ ok: false, error: 'no_fields' }, 400), ao);
    const url = `${supabaseBase(env)}/rest/v1/target_chats?id=eq.${destId}`;
    const resp = await fetch(url, {
      method: 'PATCH',
      headers: { ...supabaseHeaders(env), 'content-type': 'application/json', 'Prefer': 'return=representation' },
      body: JSON.stringify(patch),
    });
    if (!resp.ok) return withCors(jsonResponse({ ok: false, error: 'destination_update_failed' }, 502), ao);
    await writeAuditLog(env, user, 'destination_updated', { destination_id: destId, patch });
    return withCors(jsonResponse({ ok: true }), ao);
  } catch {
    return withCors(jsonResponse({ ok: false, error: 'destination_update_failed' }, 502), ao);
  }
}

export async function handleDeleteDestination(request, env, user, ao, destId) {
  try {
    const url = `${supabaseBase(env)}/rest/v1/target_chats?id=eq.${destId}`;
    const resp = await fetch(url, {
      method: 'PATCH',
      headers: { ...supabaseHeaders(env), 'content-type': 'application/json', prefer: 'return=minimal' },
      body: JSON.stringify({
        enabled: false,
        removed_by_user_id: user.id,
        removed_by_name: user.name || '',
        removed_at: new Date().toISOString(),
      }),
    });
    if (!resp.ok) return withCors(jsonResponse({ ok: false, error: 'destination_delete_failed' }, 502), ao);
    await writeAuditLog(env, user, 'destination_removed', { id: destId });
    return withCors(jsonResponse({ ok: true }), ao);
  } catch {
    return withCors(jsonResponse({ ok: false, error: 'destination_delete_failed' }, 502), ao);
  }
}

export async function handleTestDestination(request, env, user, ao, destId) {
  try {
    const dUrl = `${supabaseBase(env)}/rest/v1/target_chats?id=eq.${destId}&select=chat_id,message_thread_id&limit=1`;
    const dResp = await fetch(dUrl, { headers: supabaseHeaders(env) });
    if (!dResp.ok) return withCors(jsonResponse({ ok: false, error: 'destination_not_found' }, 404), ao);
    const rows = await dResp.json();
    if (!rows.length) return withCors(jsonResponse({ ok: false, error: 'destination_not_found' }, 404), ao);
    const { chat_id, message_thread_id } = rows[0];
    const botToken = env.TELEGRAM_BOT_TOKEN;
    if (!botToken) return withCors(jsonResponse({ ok: false, error: 'bot_token_not_configured' }, 500), ao);
    const body = await request.json().catch(() => ({}));
    const lang = body.language === 'en' ? 'en' : 'pt';
    const testText = lang === 'en'
      ? '✅ Test message from Arkham Bot Mini App.'
      : '✅ Mensagem de teste do Arkham Bot Mini App.';
    const msgBody = { chat_id, text: testText };
    if (message_thread_id) msgBody.message_thread_id = message_thread_id;
    const tgResp = await fetch(`https://api.telegram.org/bot${botToken}/sendMessage`, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify(msgBody),
    });
    const tgJson = await tgResp.json().catch(() => ({}));
    if (!tgResp.ok || !tgJson.ok) return withCors(jsonResponse({ ok: false, error: 'telegram_send_failed', detail: tgJson.description || '' }, 502), ao);
    return withCors(jsonResponse({ ok: true }), ao);
  } catch {
    return withCors(jsonResponse({ ok: false, error: 'test_failed' }, 502), ao);
  }
}
