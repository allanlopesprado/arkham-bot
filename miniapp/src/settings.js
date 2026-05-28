// ─── Settings ─────────────────────────────────────────────────────────────────

import { WEEKDAYS, ALL_CARD_TYPES } from './i18n.js';

export const AI_TONES = [
  { value: 'random',       pt: 'Aleatório',    en: 'Random' },
  { value: 'misterioso',   pt: 'Misterioso',   en: 'Mysterious' },
  { value: 'tenso',        pt: 'Tenso',         en: 'Tense' },
  { value: 'epico',        pt: 'Épico',         en: 'Epic' },
  { value: 'sombrio',      pt: 'Sombrio',       en: 'Dark' },
  { value: 'reflexivo',    pt: 'Reflexivo',     en: 'Reflective' },
  { value: 'esperancoso',  pt: 'Esperançoso',   en: 'Hopeful' },
  { value: 'perturbador',  pt: 'Perturbador',   en: 'Disturbing' },
  { value: 'melancolico',  pt: 'Melancólico',   en: 'Melancholic' },
];

export const AI_PROVIDERS = [
  {
    value: 'gemini',
    labelPt: 'Google Gemini',
    labelEn: 'Google Gemini',
    models: [
      { value: 'gemini-2.5-flash',               label: 'Gemini 2.5 Flash ★' },
      { value: 'gemini-2.0-flash',               label: 'Gemini 2.0 Flash' },
      { value: 'gemini-2.5-flash-preview-05-20', label: 'Gemini 2.5 Flash Preview' },
      { value: 'gemini-2.5-pro',                 label: 'Gemini 2.5 Pro' },
    ],
  },
  {
    value: 'groq',
    labelPt: 'Groq',
    labelEn: 'Groq',
    models: [
      { value: 'llama-3.3-70b-versatile', label: 'Llama 3.3 70B ★' },
      { value: 'llama-3.1-8b-instant',    label: 'Llama 3.1 8B' },
      { value: 'mixtral-8x7b-32768',      label: 'Mixtral 8x7B' },
    ],
  },
  {
    value: 'mistral',
    labelPt: 'Mistral AI',
    labelEn: 'Mistral AI',
    models: [
      { value: 'mistral-small-latest',  label: 'Mistral Small' },
      { value: 'mistral-medium-latest', label: 'Mistral Medium' },
      { value: 'open-mistral-7b',       label: 'Mistral 7B' },
    ],
  },
  {
    value: 'openai',
    labelPt: 'OpenAI',
    labelEn: 'OpenAI',
    models: [
      { value: 'gpt-4o-mini',  label: 'GPT-4o Mini' },
      { value: 'gpt-4o',       label: 'GPT-4o' },
      { value: 'gpt-4.1-mini', label: 'GPT-4.1 Mini' },
      { value: 'gpt-4.1',      label: 'GPT-4.1' },
    ],
  },
];

// flat list for validation/fallback
export const AI_MODELS = AI_PROVIDERS.flatMap((p) => p.models);

export function _providerOfModel(modelValue) {
  return AI_PROVIDERS.find((p) => p.models.some((m) => m.value === modelValue))?.value ?? 'gemini';
}

const DEFAULT_CARD_TYPES = ALL_CARD_TYPES.map((t) => t.code);

export const DEFAULT_SETTINGS = {
  daily_post_enabled: true,
  daily_post_times: ['08:00'],
  daily_post_days: WEEKDAYS.map((d) => d.code),
  timezone: 'America/Sao_Paulo',
  telegram_chat_id: '',
  ai_enabled: true,
  ai_language: 'pt-BR',
  ai_tone: 'random',
  ai_auto_only: true,
  ai_pre_message_enabled: true,
  ai_pre_message_delay_seconds: 0,
  ai_post_question_enabled: true,
  ai_post_question_delay_seconds: 0,
  ai_model: 'gemini-2.5-flash',
  ai_creativity: 'default',
  include_spoilers: false,
  allowed_card_types: DEFAULT_CARD_TYPES,
  day_config: {},
  sync_schedule_enabled: false,
  sync_schedule_days: ['sun'],
  sync_schedule_time: '03:00',
};

export const SETTINGS_PATCH_KEYS = [
  'daily_post_enabled', 'daily_post_times', 'daily_post_days', 'timezone',
  'ai_enabled', 'ai_auto_only', 'ai_language', 'ai_tone', 'ai_pre_message_enabled',
  'ai_pre_message_delay_seconds', 'ai_post_question_enabled', 'ai_post_question_delay_seconds', 'ai_model', 'ai_creativity',
  'include_spoilers', 'allowed_card_types', 'day_config', 'telegram_chat_id',
  'sync_schedule_enabled', 'sync_schedule_days', 'sync_schedule_time',
];

export function parseJsonArray(v) {
  if (Array.isArray(v)) return v;
  if (typeof v === 'string') { try { const p = JSON.parse(v); if (Array.isArray(p)) return p; } catch {} }
  return null;
}

export function normalizeSettings(s = {}) {
  const times = parseJsonArray(s.daily_post_times);
  const days = parseJsonArray(s.daily_post_days);
  const types = parseJsonArray(s.allowed_card_types);
  return {
    daily_post_enabled: typeof s.daily_post_enabled === 'boolean' ? s.daily_post_enabled : DEFAULT_SETTINGS.daily_post_enabled,
    daily_post_times: times && times.length ? times : DEFAULT_SETTINGS.daily_post_times,
    daily_post_days: days ? days : DEFAULT_SETTINGS.daily_post_days,
    timezone: typeof s.timezone === 'string' && s.timezone.trim() ? s.timezone : DEFAULT_SETTINGS.timezone,
    ai_enabled: typeof s.ai_enabled === 'boolean' ? s.ai_enabled : DEFAULT_SETTINGS.ai_enabled,
    ai_language: s.ai_language === 'en-US' ? 'en-US' : 'pt-BR',
    ai_tone: AI_TONES.some((t) => t.value === s.ai_tone) ? s.ai_tone : 'random',
    ai_auto_only: typeof s.ai_auto_only === 'boolean' ? s.ai_auto_only : true,
    ai_pre_message_enabled: typeof s.ai_pre_message_enabled === 'boolean' ? s.ai_pre_message_enabled : true,
    ai_pre_message_delay_seconds: (() => { const n = Number(s.ai_pre_message_delay_seconds); return Number.isInteger(n) && n >= 0 && n <= 3600 ? n : 0; })(),
    ai_post_question_enabled: typeof s.ai_post_question_enabled === 'boolean' ? s.ai_post_question_enabled : true,
    ai_post_question_delay_seconds: (() => { const n = Number(s.ai_post_question_delay_seconds); return Number.isInteger(n) && n >= 0 && n <= 3600 ? n : 0; })(),
    ai_model: AI_MODELS.some((m) => m.value === s.ai_model) ? s.ai_model : 'gemini-2.5-flash',
    ai_creativity: ['conservative', 'default', 'creative'].includes(s.ai_creativity) ? s.ai_creativity : 'default',
    include_spoilers: typeof s.include_spoilers === 'boolean' ? s.include_spoilers : DEFAULT_SETTINGS.include_spoilers,
    allowed_card_types: types && types.length ? types : DEFAULT_CARD_TYPES,
    day_config: (() => { let dc = s.day_config; if (typeof dc === 'string') { try { dc = JSON.parse(dc); } catch {} } return (dc && typeof dc === 'object' && !Array.isArray(dc)) ? dc : {}; })(),
    telegram_chat_id: typeof s.telegram_chat_id === 'string' ? s.telegram_chat_id : '',
    sync_schedule_enabled: typeof s.sync_schedule_enabled === 'boolean' ? s.sync_schedule_enabled : false,
    sync_schedule_days: (() => { const d = parseJsonArray(s.sync_schedule_days); return d && d.length ? d : ['sun']; })(),
    sync_schedule_time: typeof s.sync_schedule_time === 'string' && /^\d{2}:\d{2}$/.test(s.sync_schedule_time) ? s.sync_schedule_time : '03:00',
  };
}

export function settingsPatchPayload(settings, times) {
  const normalized = normalizeSettings({
    ...settings,
    daily_post_times: times.map((t) => t.slice(0, 5)),
    timezone: settings.timezone.trim(),
  });
  return Object.fromEntries(SETTINGS_PATCH_KEYS.map((key) => [key, normalized[key]]));
}

export function isValidTimeValue(t) {
  if (typeof t !== 'string') return false;
  const clean = t.slice(0, 5);
  if (!/^\d{2}:\d{2}$/.test(clean)) return false;
  const [h, m] = clean.split(':').map(Number);
  return h >= 0 && h <= 23 && m >= 0 && m <= 59;
}

export function validateTimes(times) {
  return times.length > 0 && times.every(isValidTimeValue);
}

export function settingsEqual(a, b) {
  return JSON.stringify(a) === JSON.stringify(b);
}

export const DELAY_OPTIONS = [
  0, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60,
  120, 180, 240, 300, 360, 420, 480, 540, 600,
  900, 1200, 1500, 1800, 2100, 2400, 2700, 3000, 3300, 3600,
];

export function formatDelay(v, lang) {
  if (v === 0) return lang === 'pt' ? 'Sem delay' : 'No delay';
  if (v < 60) return `${v}s`;
  const m = Math.floor(v / 60);
  const s = v % 60;
  if (s === 0) return lang === 'pt' ? `${m} min` : `${m} min`;
  return `${m}min ${s}s`;
}
