// Posting-history endpoint (with timezone-aware day filtering).
import { withCors, jsonResponse } from '../http.js';
import { fetchSupabaseJson, fetchSettingsRows, rowsToSettings } from '../supabase.js';
import { boundedLimit } from '../validation.js';

export async function handleGetHistory(request, env, ao) {
  const url = new URL(request.url);
  const date = (url.searchParams.get('date') || '').trim();
  const q = (url.searchParams.get('q') || '').trim().replace(/[^\w\s:-]/g, '');
  const source = (url.searchParams.get('source') || '').trim();
  const limit = boundedLimit(url.searchParams.get('limit'), 30, 100);
  const offset = Math.max(0, Number(url.searchParams.get('offset') || 0));

  let path = `/rest/v1/bot_posting_history?select=id,card_code,card_name,status,source,created_at,telegram_message_id&order=created_at.desc&limit=${limit}&offset=${offset}`;

  if (source && source !== 'all') {
    path += `&source=eq.${encodeURIComponent(source)}`;
  }

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
