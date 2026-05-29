// Structured logging + audit-log writes.
import { supabaseBase, supabaseHeaders } from './supabase.js';

export function safeLog(data) {
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

export async function writeAuditLog(env, user, action_type, payload = {}) {
  try {
    await fetch(`${supabaseBase(env)}/rest/v1/audit_logs`, {
      method: 'POST',
      headers: { ...supabaseHeaders(env), 'content-type': 'application/json', 'Prefer': 'return=minimal' },
      body: JSON.stringify({
        actor_telegram_user_id: user.id,
        actor_name: user.name || '',
        action_type,
        source: 'mini_app',
        payload,
      }),
    });
  } catch {
    safeLog({ path: 'audit_log', method: 'POST', initData_present: null, initData_length: null, telegram_user_id_present: null, admin: null, status: 'write_failed' });
  }
}
