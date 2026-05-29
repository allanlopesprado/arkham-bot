// HTTP response, CORS, and allowed-origin helpers shared across handlers.

export function jsonResponse(payload, status = 200, extraHeaders = {}) {
  return new Response(JSON.stringify(payload), {
    status,
    headers: { 'content-type': 'application/json; charset=utf-8', ...extraHeaders },
  });
}

export function getAllowedOrigin(request, env) {
  const origin = request.headers.get('origin') || '';
  const allowed = String(env.ALLOWED_ORIGINS || '')
    .split(',')
    .map((s) => s.trim())
    .filter(Boolean);
  return allowed.includes(origin) ? origin : '';
}

export function corsHeaders(allowedOrigin) {
  if (!allowedOrigin) return {};
  return {
    'access-control-allow-origin': allowedOrigin,
    'access-control-allow-methods': 'GET,POST,PATCH,DELETE,OPTIONS',
    'access-control-allow-headers': 'content-type,x-telegram-init-data',
    'x-content-type-options': 'nosniff',
    'x-frame-options': 'DENY',
    'strict-transport-security': 'max-age=31536000; includeSubDomains',
    vary: 'Origin',
  };
}

export function withCors(response, allowedOrigin) {
  const hdrs = corsHeaders(allowedOrigin);
  Object.entries(hdrs).forEach(([k, v]) => response.headers.set(k, v));
  return response;
}

export function preflightResponse(allowedOrigin) {
  if (!allowedOrigin) return jsonResponse({ error: 'origin_not_allowed' }, 403);
  return new Response(null, { status: 204, headers: corsHeaders(allowedOrigin) });
}

export function notFound(ao) {
  return withCors(jsonResponse({ error: 'not_found' }, 404), ao);
}
