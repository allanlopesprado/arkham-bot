// Settings/input validation: constants, value sets, and validators.

// AI provider catalogue (model metadata). Kept here with the other AI-settings
// constants; not referenced elsewhere in the Worker today.
export const AI_PROVIDERS = [
  { value: 'gemini', labelPt: 'Google Gemini', labelEn: 'Google Gemini', models: [
    { value: 'gemini-2.5-flash', label: 'Gemini 2.5 Flash ★' },
    { value: 'gemini-2.0-flash', label: 'Gemini 2.0 Flash' },
    { value: 'gemini-2.5-flash-preview-05-20', label: 'Gemini 2.5 Flash Preview' },
    { value: 'gemini-2.5-pro', label: 'Gemini 2.5 Pro' },
  ]},
  { value: 'groq', labelPt: 'Groq', labelEn: 'Groq', models: [
    { value: 'llama-3.3-70b-versatile', label: 'Llama 3.3 70B ★' },
    { value: 'llama-3.1-8b-instant', label: 'Llama 3.1 8B' },
    { value: 'mixtral-8x7b-32768', label: 'Mixtral 8x7B' },
  ]},
  { value: 'mistral', labelPt: 'Mistral AI', labelEn: 'Mistral AI', models: [
    { value: 'mistral-small-latest', label: 'Mistral Small' },
    { value: 'mistral-medium-latest', label: 'Mistral Medium' },
    { value: 'open-mistral-7b', label: 'Mistral 7B' },
  ]},
  { value: 'openai', labelPt: 'OpenAI', labelEn: 'OpenAI', models: [
    { value: 'gpt-4o-mini', label: 'GPT-4o Mini' },
    { value: 'gpt-4o', label: 'GPT-4o' },
    { value: 'gpt-4.1-mini', label: 'GPT-4.1 Mini' },
    { value: 'gpt-4.1', label: 'GPT-4.1' },
  ]},
];

export const SETTINGS_KEYS = new Set([
  'daily_post_enabled', 'daily_post_times', 'daily_post_days', 'timezone',
  'ai_enabled', 'ai_auto_only', 'ai_language', 'ai_tone', 'ai_pre_message_enabled',
  'ai_post_question_enabled', 'ai_pre_message_delay_seconds', 'ai_post_question_delay_seconds', 'ai_model', 'ai_creativity',
  'include_spoilers', 'allowed_card_types', 'day_config',
  'sync_schedule_enabled', 'sync_schedule_days', 'sync_schedule_time',
]);
export const AI_LANGUAGE_VALUES = new Set(['pt-BR', 'en-US']);
export const AI_TONES = new Set(['random','misterioso','tenso','epico','sombrio','reflexivo','esperancoso','perturbador','melancolico']);
export const AI_MODELS = new Set([
  'gemini-2.0-flash','gemini-2.5-flash','gemini-2.5-flash-preview-05-20','gemini-2.5-pro',
  'gpt-4o-mini','gpt-4o','gpt-4.1-mini','gpt-4.1','gpt-4-turbo',
  'llama-3.3-70b-versatile','llama-3.1-8b-instant','mixtral-8x7b-32768',
  'mistral-small-latest','mistral-medium-latest','open-mistral-7b',
]);
export const AI_CREATIVITY_VALUES = new Set(['conservative','default','creative']);
export const WEEKDAY_CODES = new Set(['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun', 'all']);
export const WEEKDAY_DAY_CODES = new Set(['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun']);
export const VALID_CARD_TYPES = new Set([
  'investigator', 'asset', 'event', 'skill',
  'enemy', 'location', 'treachery', 'act', 'agenda', 'story',
  '__none__',
]);

export function isValidTime(value) {
  if (typeof value !== 'string' || !/^\d{2}:\d{2}$/.test(value)) return false;
  const [hour, minute] = value.split(':').map(Number);
  return hour >= 0 && hour <= 23 && minute >= 0 && minute <= 59;
}

export function validateTimezone(value) {
  if (typeof value !== 'string' || !value.trim()) return null;
  const timezone = value.trim();
  try {
    new Intl.DateTimeFormat('en-US', { timeZone: timezone }).format(new Date());
    return timezone;
  } catch {
    return null;
  }
}

export function validateSettingsPatch(body) {
  if (!body || typeof body !== 'object' || Array.isArray(body)) {
    return { error: 'invalid_json' };
  }
  const settings = {};
  for (const [key, value] of Object.entries(body)) {
    if (!SETTINGS_KEYS.has(key)) {
      return { error: 'unsupported_setting', key, detail: `Unsupported setting: ${key}` };
    }
    if (key === 'daily_post_enabled') {
      if (typeof value !== 'boolean') return { error: 'invalid_setting_value', key };
      settings[key] = value;
    }
    if (key === 'daily_post_times') {
      if (!Array.isArray(value) || value.length === 0 || !value.every(isValidTime)) {
        return { error: 'invalid_setting_value', key };
      }
      settings[key] = value;
    }
    if (key === 'daily_post_days') {
      if (!Array.isArray(value) || !value.every((day) => WEEKDAY_DAY_CODES.has(day))) {
        return { error: 'invalid_setting_value', key };
      }
      settings[key] = value;
    }
    if (key === 'timezone') {
      const timezone = validateTimezone(value);
      if (!timezone) return { error: 'invalid_setting_value', key };
      settings[key] = timezone;
    }
    if (key === 'ai_enabled') {
      if (typeof value !== 'boolean') return { error: 'invalid_setting_value', key };
      settings[key] = value;
    }
    if (key === 'ai_language') {
      if (!AI_LANGUAGE_VALUES.has(value)) return { error: 'invalid_setting_value', key };
      settings[key] = value;
    }
    if (key === 'ai_tone') {
      if (!AI_TONES.has(value)) return { error: 'invalid_setting_value', key };
      settings[key] = value;
    }
    if (key === 'ai_pre_message_enabled' || key === 'ai_post_question_enabled' || key === 'ai_auto_only') {
      if (typeof value !== 'boolean') return { error: 'invalid_setting_value', key };
      settings[key] = value;
    }
    if (key === 'ai_pre_message_delay_seconds' || key === 'ai_post_question_delay_seconds') {
      const n = Number(value);
      if (!Number.isInteger(n) || n < 0 || n > 3600) return { error: 'invalid_setting_value', key };
      settings[key] = n;
    }
    if (key === 'ai_model') {
      if (!AI_MODELS.has(value)) return { error: 'invalid_setting_value', key };
      settings[key] = value;
    }
    if (key === 'ai_creativity') {
      if (!AI_CREATIVITY_VALUES.has(value)) return { error: 'invalid_setting_value', key };
      settings[key] = value;
    }
    if (key === 'include_spoilers') {
      if (typeof value !== 'boolean') return { error: 'invalid_setting_value', key };
      settings[key] = value;
    }
    if (key === 'allowed_card_types') {
      if (!Array.isArray(value) || value.length === 0 || !value.every((t) => VALID_CARD_TYPES.has(t))) {
        return { error: 'invalid_setting_value', key };
      }
      settings[key] = value;
    }
    if (key === 'sync_schedule_enabled') {
      if (typeof value !== 'boolean') return { error: 'invalid_setting_value', key };
      settings[key] = value;
    }
    if (key === 'sync_schedule_days') {
      if (!Array.isArray(value) || !value.every((d) => WEEKDAY_CODES.has(d))) {
        return { error: 'invalid_setting_value', key };
      }
      settings[key] = value;
    }
    if (key === 'sync_schedule_time') {
      if (!isValidTime(value)) return { error: 'invalid_setting_value', key };
      settings[key] = value;
    }
    if (key === 'day_config') {
      // { mon: { packs: ['core','dwl',...], types: ['investigator'] }, ... }
      if (typeof value !== 'object' || Array.isArray(value) || value === null) {
        return { error: 'invalid_setting_value', key };
      }
      for (const [day, cfg] of Object.entries(value)) {
        if (!WEEKDAY_CODES.has(day)) return { error: 'invalid_setting_value', key };
        if (cfg !== null && cfg !== undefined) {
          if (typeof cfg !== 'object' || Array.isArray(cfg)) return { error: 'invalid_setting_value', key };
          const { packs: p, types: t, times } = cfg;
          if (p !== undefined && (!Array.isArray(p) || !p.every((x) => typeof x === 'string' && x.length > 0))) {
            return { error: 'invalid_setting_value', key };
          }
          if (t !== undefined && (!Array.isArray(t) || !t.every((x) => VALID_CARD_TYPES.has(x)))) {
            return { error: 'invalid_setting_value', key };
          }
          if (times !== undefined && (!Array.isArray(times) || !times.every(isValidTime))) {
            return { error: 'invalid_setting_value', key };
          }
        }
      }
      settings[key] = value;
    }
  }
  if (Object.keys(settings).length === 0) return { error: 'settings_required' };
  return { settings };
}

export function boundedLimit(raw, fallback = 20, max = 50) {
  const value = Number(raw || fallback);
  if (!Number.isFinite(value)) return fallback;
  return Math.max(1, Math.min(Math.floor(value), max));
}
