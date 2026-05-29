// Card search endpoint.
import { withCors, jsonResponse } from '../http.js';
import { fetchSupabaseJson } from '../supabase.js';
import { boundedLimit } from '../validation.js';

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

export async function handleCardsSearch(request, env, ao) {
  const path = cardSearchPath(request);
  if (!path) return withCors(jsonResponse({ ok: true, cards: [] }), ao);
  try {
    const rows = await fetchSupabaseJson(env, path);
    return withCors(jsonResponse({ ok: true, cards: rows }), ao);
  } catch {
    return withCors(jsonResponse({ error: 'cards_search_failed' }, 500), ao);
  }
}
