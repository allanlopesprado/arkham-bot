// ─── API ──────────────────────────────────────────────────────────────────────

import { initData } from './telegram.js';

export function getBotPhotoUrl() { return import.meta.env.VITE_BOT_PHOTO_URL || ''; }

export function getApiBase() {
  const raw = import.meta.env.VITE_COMMANDS_API_URL || '';
  if (!raw) return '';
  try {
    const url = new URL(raw);
    return `${url.origin}${url.pathname.replace(/\/$/, '')}`;
  } catch {
    return raw.replace(/\/$/, '');
  }
}

export function apiUrl(path) {
  const base = getApiBase();
  return base ? `${base.replace(/\/$/, '')}${path}` : '';
}

export function authHeaders() { return { 'x-telegram-init-data': initData() }; }

export async function apiFetch(path, options = {}) {
  const url = apiUrl(path);
  if (!url) return { ok: false, status: 0, json: { error: 'no_api' } };
  const resp = await fetch(url, {
    ...options,
    headers: { ...authHeaders(), ...(options.headers || {}) },
  });
  const text = await resp.text();
  let json = {};
  try {
    json = text ? JSON.parse(text) : {};
  } catch {
    json = { error: 'non_json_response', detail: text.slice(0, 300) };
  }
  return { ok: resp.ok, status: resp.status, json };
}
