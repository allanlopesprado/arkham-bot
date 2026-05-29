// Pack catalogue endpoint (Supabase first, ArkhamDB fallback, in-memory cache).
import { withCors, jsonResponse } from '../http.js';
import { supabaseBase } from '../supabase.js';
import { safeLog } from '../audit.js';

const _packsCache = { payload: null, ts: 0 };
const PACKS_CACHE_TTL_MS = 3_600_000; // 1 hour

export async function handleGetPacks(env, ao) {
  const now = Date.now();
  if (_packsCache.payload && now - _packsCache.ts < PACKS_CACHE_TTL_MS) {
    return withCors(jsonResponse(_packsCache.payload), ao);
  }

  // Try Supabase first
  if (env.SUPABASE_URL && env.SUPABASE_SERVICE_ROLE_KEY) {
    try {
      const url = `${supabaseBase(env)}/rest/v1/arkham_packs?select=code,name,cycle_position,position,chapter,total&order=cycle_position.asc,position.asc&limit=500`;
      const resp = await fetch(url, {
        headers: {
          'apikey': env.SUPABASE_SERVICE_ROLE_KEY,
          'Authorization': `Bearer ${env.SUPABASE_SERVICE_ROLE_KEY}`,
          'Accept': 'application/json',
        },
      });
      if (resp.ok) {
        const raw = await resp.json();
        if (Array.isArray(raw) && raw.length > 0) {
          const packs = raw.sort((a, b) => (a.cycle_position ?? 99) - (b.cycle_position ?? 99) || (a.position ?? 99) - (b.position ?? 99));
          _packsCache.payload = { ok: true, packs, source: 'supabase' };
          _packsCache.ts = now;
          return withCors(jsonResponse(_packsCache.payload), ao);
        }
      }
    } catch (err) {
      safeLog({ path: '/packs', method: 'GET', initData_present: null, initData_length: null, telegram_user_id_present: null, admin: null, status: 'supabase_fallback', error: String(err?.message || err) });
    }
  }

  // Fallback: ArkhamDB public API
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
    _packsCache.payload = { ok: true, packs, source: 'arkhamdb' };
    _packsCache.ts = now;
    return withCors(jsonResponse(_packsCache.payload), ao);
  } catch (err) {
    return withCors(jsonResponse({ error: 'packs_fetch_failed', detail: String(err) }, 500), ao);
  }
}
