// Bot runtime heartbeat endpoint.
import { withCors, jsonResponse } from '../http.js';
import { supabaseBase, supabaseHeaders } from '../supabase.js';

export async function handleBotRuntime(env, ao) {
  try {
    const url = `${supabaseBase(env)}/rest/v1/bot_settings?key=eq.last_heartbeat&select=value,updated_at&limit=1`;
    const resp = await fetch(url, { headers: supabaseHeaders(env) });
    if (!resp.ok) return withCors(jsonResponse({ ok: false, error: 'supabase_error' }, 502), ao);
    const rows = await resp.json();
    if (!rows.length) return withCors(jsonResponse({ ok: true, alive: false, last_seen: null, seconds_ago: null }), ao);
    const row = rows[0];
    let lastSeen;
    try {
      const ts = JSON.parse(row.value);
      const parsed = new Date(ts);
      lastSeen = !isNaN(parsed.getTime()) ? parsed : new Date(row.updated_at);
    } catch {
      lastSeen = new Date(row.updated_at);
    }
    const secondsAgo = Math.floor((Date.now() - lastSeen.getTime()) / 1000);
    const alive = secondsAgo < 180;
    return withCors(jsonResponse({ ok: true, alive, last_seen: lastSeen.toISOString(), seconds_ago: secondsAgo }), ao);
  } catch {
    return withCors(jsonResponse({ ok: false, error: 'network_error' }, 502), ao);
  }
}
