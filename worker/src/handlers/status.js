// Read-only status / identity / dashboard endpoints.
import { withCors, jsonResponse } from '../http.js';
import { fetchSettingsRows, fetchSupabaseJson, fetchCount, rowsToSettings } from '../supabase.js';
import { getAdminAccess } from '../auth.js';
import { safeLog } from '../audit.js';

const APP_VERSION = '1.3.0';

export async function handleMe(request, env, user, ao) {
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

export async function handleStatus(request, env, ao) {
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
  result.version = APP_VERSION;
  return withCors(jsonResponse(result), ao);
}

export async function handleOverview(request, env, user, ao) {
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
      fetchSupabaseJson(env, '/rest/v1/target_chats?select=chat_id,title,message_thread_id,enabled,updated_at&enabled=eq.true&order=created_at.desc&limit=20'),
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
