// ─── API ──────────────────────────────────────────────────────────────────────

import { initData } from './telegram.js';

export function getBotPhotoUrl() { return import.meta.env.VITE_BOT_PHOTO_URL || ''; }

export function getApiBase() {
  const raw = import.meta.env.VITE_COMMANDS_API_URL || '';
  if (!raw) return '';
  try { return new URL(raw).origin; } catch { return raw; }
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
  const json = await resp.json().catch(() => ({}));
  return { ok: resp.ok, status: resp.status, json };
}
