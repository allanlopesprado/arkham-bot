import React, { useCallback, useEffect, useRef, useState } from 'react';
import { createRoot } from 'react-dom/client';
import './style.css';

// ─── Telegram helpers ────────────────────────────────────────────────────────

function tg() { return window.Telegram?.WebApp || null; }
function initData() { return tg()?.initData || ''; }
function tgUser() { return tg()?.initDataUnsafe?.user || null; }

function haptic(type, value) {
  try {
    const hf = tg()?.HapticFeedback;
    if (!hf) return;
    if (type === 'notification') hf.notificationOccurred(value);
    else if (type === 'impact') hf.impactOccurred(value);
  } catch {}
}

// ─── API ─────────────────────────────────────────────────────────────────────

function getBotPhotoUrl() {
  return import.meta.env.VITE_BOT_PHOTO_URL || '';
}

function getApiBase() {
  const raw = import.meta.env.VITE_COMMANDS_API_URL || '';
  if (!raw) return '';
  try { return new URL(raw).origin; } catch { return raw; }
}

function apiUrl(path) {
  const base = getApiBase();
  return base ? `${base.replace(/\/$/, '')}${path}` : '';
}

function authHeaders() {
  return { 'x-telegram-init-data': initData() };
}

async function apiFetch(path, options = {}) {
  const url = apiUrl(path);
  if (!url) throw new Error('no_api');
  const resp = await fetch(url, {
    ...options,
    headers: { ...authHeaders(), ...(options.headers || {}) },
  });
  const json = await resp.json().catch(() => ({}));
  return { ok: resp.ok, status: resp.status, json };
}

// ─── i18n ────────────────────────────────────────────────────────────────────

const LANGUAGE_KEY = 'arkham-bot-lang';

const WEEKDAYS = [
  { code: 'mon', pt: 'Seg', en: 'Mon' },
  { code: 'tue', pt: 'Ter', en: 'Tue' },
  { code: 'wed', pt: 'Qua', en: 'Wed' },
  { code: 'thu', pt: 'Qui', en: 'Thu' },
  { code: 'fri', pt: 'Sex', en: 'Fri' },
  { code: 'sat', pt: 'Sab', en: 'Sat' },
  { code: 'sun', pt: 'Dom', en: 'Sun' },
];

const I18N = {
  pt: {
    locale: 'pt-BR',
    langName: 'Português',
    langToggle: 'Switch to English',
    subtitle: 'Console Admin',
    outsideTelegram: 'Abra pelo Telegram para autenticar.',
    workerNotConfigured: 'Worker não configurado.',
    defineApiUrl: 'Defina VITE_COMMANDS_API_URL.',
    postCard: 'Postar carta',
    postCardCaption: 'Buscar carta, escolher destino e publicar',
    controls: 'Controles',
    controlsCaption: 'Pausar, sincronizar, resetar ciclo e limpar fila',
    schedule: 'Agenda',
    scheduleCaption: 'Horários e dias de postagem',
    queue: 'Fila',
    queueCaption: 'Comandos recentes e cancelamento',
    health: 'Saúde',
    healthCaption: 'Worker, acesso, cards e diagnóstico',
    language: 'Idioma',
    searchByCodeOrName: 'Buscar por código ou nome',
    searchPlaceholder: '01001 ou Shrivelling',
    search: 'Buscar',
    selectedCard: 'Carta selecionada',
    selectedCardHint: 'Postar agora aceita código vazio (escolha automática). Repostar e pular exigem código.',
    selectedCardPlaceholder: 'Código da carta, ex: 01001',
    destination: 'Destino',
    defaultChat: 'Chat padrão do bot',
    postNow: 'Postar agora',
    automaticChoice: 'Escolha automática',
    card: 'Carta',
    repostCard: 'Repostar carta',
    skipCard: 'Pular carta',
    informCardCode: 'Informe o código da carta',
    modeSettings: 'Modos de operação',
    dailyPost: 'Postagem diária',
    automaticPosting: 'Publicação automática',
    automaticPostingCaption: 'Liga ou pausa a carta diária',
    postTimes: 'Horários de postagem',
    postTimesCaption: 'Horários 24h separados por vírgula. Ex: 09:00, 21:30',
    postDays: 'Dias da semana',
    postDaysCaption: 'Escolha quando a rotina pode publicar',
    timezoneLabel: 'Fuso horário',
    timezoneCaption: 'Padrão usado para calcular os horários',
    aiLanguage: 'Idioma da IA',
    aiLanguageCaption: 'Idioma usado nos comentários gerados pela IA',
    aiLanguagePt: 'Português (pt-BR)',
    aiLanguageEn: 'English (en-US)',
    cardTypes: 'Tipos de carta',
    cardTypesCaption: 'Selecione quais tipos de carta podem ser postados',
    syncArkhamDB: 'Sincronizar ArkhamDB',
    syncCaption: 'Atualiza cartas e pacotes',
    resetCycle: 'Resetar ciclo',
    resetCaption: 'Permite repetir cartas já usadas',
    clearQueue: 'Limpar fila',
    clearQueueCaption: 'Cancela comandos pendentes',
    maintenance: 'Manutenção',
    dangerZone: 'Zona de risco',
    reloadSettings: 'Recarregar configurações',
    saveSettings: 'Salvar configurações',
    result: 'Resultado',
    success: 'Sucesso',
    error: 'Erro',
    details: 'Detalhes',
    commandQueue: 'Fila de comandos',
    refreshQueue: 'Atualizar fila',
    noRecentCommands: 'Nenhum comando recente',
    cancelCommand: 'Cancelar',
    summary: 'Resumo',
    worker: 'Worker',
    access: 'Acesso',
    cards: 'Cards',
    account: 'Conta',
    telegramWebApp: 'Telegram WebApp',
    initDataLabel: 'initData',
    admin: 'Admin',
    recheckAuth: 'Reverificar autenticação',
    system: 'Sistema',
    packs: 'Packs',
    lastSync: 'Último sync',
    refreshStatus: 'Atualizar status',
    diagnostic: 'Diagnóstico',
    showDetails: 'Mostrar detalhes',
    apiConfigured: 'API configurada',
    apiBase: 'Endpoint base',
    userUnsafe: 'Usuário unsafe',
    initDataPresent: 'initData presente',
    initDataLength: 'initData length',
    role: 'Role',
    adminSource: 'Admin source',
    yes: 'sim',
    no: 'não',
    checking: 'verificando…',
    noApi: 'sem API',
    noNetwork: 'sem rede',
    pending: 'pendente',
    notConfigured: 'não configurado',
    online: 'online',
    offline: 'offline',
    commandQueued: 'Comando enfileirado.',
    commandCancelled: 'Comando cancelado.',
    networkError: 'Falha de rede.',
    invalidTime: 'Horários devem usar HH:MM.',
    selectAtLeastOneDay: 'Selecione pelo menos um dia.',
    timezoneRequired: 'Fuso horário obrigatório.',
    settingsSaved: 'Configurações salvas.',
    unknownError: 'Erro desconhecido.',
    confirmPause: 'Pausar a postagem diária?',
    confirmResume: 'Reativar a postagem diária?',
    confirmReset: 'Resetar o ciclo de cartas? Cartas já usadas poderão ser repetidas.',
    confirmClear: 'Limpar toda a fila de comandos?',
    confirm: 'Confirmar',
    cancel: 'Cancelar',
    errors: {
      invalid_telegram_init_data: ['Abra pelo Telegram para autenticar.', 'initData inválido.'],
      unauthorized: ['Usuário sem permissão administrativa.', 'O Telegram ID não está cadastrado como admin.'],
      not_found: ['Endpoint não encontrado.', 'Verifique VITE_COMMANDS_API_URL.'],
      origin_not_allowed: ['Origem não autorizada.', 'Verifique ALLOWED_ORIGINS no Worker.'],
      bot_command_insert_failed: ['Falha ao criar comando.', 'Verifique Worker e Supabase.'],
      command_type_required: ['Tipo de comando não informado.', 'command_type_required'],
      unsupported_command_type: ['Comando não suportado.', 'unsupported_command_type'],
      method_not_allowed: ['Método HTTP não permitido.', 'method_not_allowed'],
      settings_fetch_failed: ['Falha ao carregar configurações.', 'settings_fetch_failed'],
      settings_upsert_failed: ['Falha ao salvar configurações.', 'settings_upsert_failed'],
      invalid_setting_value: ['Configuração inválida.', 'invalid_setting_value'],
      unsupported_setting: ['Configuração não suportada.', 'unsupported_setting'],
      settings_required: ['Nenhuma configuração para salvar.', 'settings_required'],
      overview_fetch_failed: ['Falha ao carregar gestão.', 'overview_fetch_failed'],
      commands_fetch_failed: ['Falha ao carregar fila.', 'commands_fetch_failed'],
      cards_search_failed: ['Falha ao buscar cartas.', 'cards_search_failed'],
      command_cancel_failed: ['Falha ao cancelar comando.', 'command_cancel_failed'],
      command_not_cancellable: ['Comando não pode mais ser cancelado.', 'command_not_cancellable'],
    },
  },
  en: {
    locale: 'en-US',
    langName: 'English',
    langToggle: 'Mudar para Português',
    subtitle: 'Admin Console',
    outsideTelegram: 'Open from Telegram to authenticate.',
    workerNotConfigured: 'Worker is not configured.',
    defineApiUrl: 'Set VITE_COMMANDS_API_URL.',
    postCard: 'Post Card',
    postCardCaption: 'Search a card, choose target, and publish',
    controls: 'Controls',
    controlsCaption: 'Pause, sync, reset cycle, and clear queue',
    schedule: 'Schedule',
    scheduleCaption: 'Posting times and days',
    queue: 'Queue',
    queueCaption: 'Recent commands and cancellation',
    health: 'Health',
    healthCaption: 'Worker, access, cards, and diagnostics',
    language: 'Language',
    searchByCodeOrName: 'Search by code or name',
    searchPlaceholder: '01001 or Shrivelling',
    search: 'Search',
    selectedCard: 'Selected card',
    selectedCardHint: 'Post now accepts an empty code (automatic choice). Repost and skip require a code.',
    selectedCardPlaceholder: 'Card code, e.g. 01001',
    destination: 'Destination',
    defaultChat: 'Bot default chat',
    postNow: 'Post now',
    automaticChoice: 'Automatic choice',
    card: 'Card',
    repostCard: 'Repost card',
    skipCard: 'Skip card',
    informCardCode: 'Enter the card code',
    modeSettings: 'Mode Settings',
    dailyPost: 'Daily post',
    automaticPosting: 'Automatic posting',
    automaticPostingCaption: 'Turns the daily card on or off',
    postTimes: 'Posting times',
    postTimesCaption: '24h times separated by commas. E.g. 09:00, 21:30',
    postDays: 'Weekdays',
    postDaysCaption: 'Choose when the routine may publish',
    timezoneLabel: 'Timezone',
    timezoneCaption: 'Timezone used to calculate posting times',
    aiLanguage: 'AI Language',
    aiLanguageCaption: 'Language used in AI-generated commentary',
    aiLanguagePt: 'Português (pt-BR)',
    aiLanguageEn: 'English (en-US)',
    cardTypes: 'Card types',
    cardTypesCaption: 'Select which card types may be posted',
    syncArkhamDB: 'Sync ArkhamDB',
    syncCaption: 'Updates cards and packs',
    resetCycle: 'Reset cycle',
    resetCaption: 'Allows cards already used to repeat',
    clearQueue: 'Clear queue',
    clearQueueCaption: 'Cancels pending commands',
    maintenance: 'Maintenance',
    dangerZone: 'Danger zone',
    reloadSettings: 'Reload settings',
    saveSettings: 'Save settings',
    result: 'Result',
    success: 'Success',
    error: 'Error',
    details: 'Details',
    commandQueue: 'Command queue',
    refreshQueue: 'Refresh queue',
    noRecentCommands: 'No recent commands',
    cancelCommand: 'Cancel',
    summary: 'Summary',
    worker: 'Worker',
    access: 'Access',
    cards: 'Cards',
    account: 'Account',
    telegramWebApp: 'Telegram WebApp',
    initDataLabel: 'initData',
    admin: 'Admin',
    recheckAuth: 'Recheck authentication',
    system: 'System',
    packs: 'Packs',
    lastSync: 'Last sync',
    refreshStatus: 'Refresh status',
    diagnostic: 'Diagnostic',
    showDetails: 'Show details',
    apiConfigured: 'API configured',
    apiBase: 'Base endpoint',
    userUnsafe: 'Unsafe user',
    initDataPresent: 'initData present',
    initDataLength: 'initData length',
    role: 'Role',
    adminSource: 'Admin source',
    yes: 'yes',
    no: 'no',
    checking: 'checking…',
    noApi: 'no API',
    noNetwork: 'no network',
    pending: 'pending',
    notConfigured: 'not configured',
    online: 'online',
    offline: 'offline',
    commandQueued: 'Command queued.',
    commandCancelled: 'Command cancelled.',
    networkError: 'Network failure.',
    invalidTime: 'Times must use HH:MM.',
    selectAtLeastOneDay: 'Select at least one day.',
    timezoneRequired: 'Timezone is required.',
    settingsSaved: 'Settings saved.',
    unknownError: 'Unknown error.',
    confirmPause: 'Pause the daily posting?',
    confirmResume: 'Resume the daily posting?',
    confirmReset: 'Reset the card cycle? Previously posted cards may repeat.',
    confirmClear: 'Clear the entire command queue?',
    confirm: 'Confirm',
    cancel: 'Cancel',
    errors: {
      invalid_telegram_init_data: ['Open from Telegram to authenticate.', 'Invalid initData.'],
      unauthorized: ['User has no admin permission.', 'The Telegram ID is not registered as admin.'],
      not_found: ['Endpoint not found.', 'Check VITE_COMMANDS_API_URL.'],
      origin_not_allowed: ['Origin is not allowed.', 'Check ALLOWED_ORIGINS in the Worker.'],
      bot_command_insert_failed: ['Failed to create command.', 'Check Worker and Supabase.'],
      command_type_required: ['Command type was not provided.', 'command_type_required'],
      unsupported_command_type: ['Unsupported command.', 'unsupported_command_type'],
      method_not_allowed: ['HTTP method is not allowed.', 'method_not_allowed'],
      settings_fetch_failed: ['Failed to load settings.', 'settings_fetch_failed'],
      settings_upsert_failed: ['Failed to save settings.', 'settings_upsert_failed'],
      invalid_setting_value: ['Invalid setting.', 'invalid_setting_value'],
      unsupported_setting: ['Unsupported setting.', 'unsupported_setting'],
      settings_required: ['No settings to save.', 'settings_required'],
      overview_fetch_failed: ['Failed to load management data.', 'overview_fetch_failed'],
      commands_fetch_failed: ['Failed to load queue.', 'commands_fetch_failed'],
      cards_search_failed: ['Failed to search cards.', 'cards_search_failed'],
      command_cancel_failed: ['Failed to cancel command.', 'command_cancel_failed'],
      command_not_cancellable: ['Command can no longer be cancelled.', 'command_not_cancellable'],
    },
  },
};

function resolveError(code, fallback, copy) {
  const loc = copy.errors[code];
  if (loc) return { friendly: loc[0], detail: loc[1] };
  return { friendly: fallback || copy.unknownError, detail: code || '' };
}

// ─── Language persistence via CloudStorage with localStorage fallback ─────────

function readLangStorage(cb) {
  const cs = tg()?.CloudStorage;
  if (cs) {
    cs.getItem(LANGUAGE_KEY, (err, val) => {
      if (!err && (val === 'en' || val === 'pt')) cb(val);
    });
  } else {
    try {
      const val = localStorage.getItem(LANGUAGE_KEY);
      if (val === 'en' || val === 'pt') cb(val);
    } catch {}
  }
}

function writeLangStorage(lang) {
  const cs = tg()?.CloudStorage;
  if (cs) {
    cs.setItem(LANGUAGE_KEY, lang, () => {});
  } else {
    try { localStorage.setItem(LANGUAGE_KEY, lang); } catch {}
  }
}

function getInitialLanguage() {
  try {
    const stored = localStorage.getItem(LANGUAGE_KEY);
    if (stored === 'en' || stored === 'pt') return stored;
  } catch {}
  const code = tgUser()?.language_code || navigator.language || '';
  return code.toLowerCase().startsWith('en') ? 'en' : 'pt';
}

// ─── Settings ────────────────────────────────────────────────────────────────

const ALL_CARD_TYPES = [
  { code: 'investigator', pt: 'Investigador', en: 'Investigator' },
  { code: 'asset',        pt: 'Recurso',      en: 'Asset' },
  { code: 'event',        pt: 'Evento',        en: 'Event' },
  { code: 'skill',        pt: 'Habilidade',    en: 'Skill' },
  { code: 'enemy',        pt: 'Inimigo',       en: 'Enemy' },
  { code: 'location',     pt: 'Localização',   en: 'Location' },
  { code: 'treachery',    pt: 'Traição',       en: 'Treachery' },
  { code: 'act',          pt: 'Ato',           en: 'Act' },
  { code: 'agenda',       pt: 'Agenda',        en: 'Agenda' },
  { code: 'story',        pt: 'História',      en: 'Story' },
];

const DEFAULT_CARD_TYPES = ALL_CARD_TYPES.map((t) => t.code);

const DEFAULT_SETTINGS = {
  daily_post_enabled: true,
  daily_post_times: ['08:00'],
  daily_post_days: WEEKDAYS.map((d) => d.code),
  timezone: 'America/Sao_Paulo',
  ai_language: 'pt-BR',
  allowed_card_types: DEFAULT_CARD_TYPES,
};

function normalizeSettings(s = {}) {
  return {
    daily_post_enabled: typeof s.daily_post_enabled === 'boolean'
      ? s.daily_post_enabled : DEFAULT_SETTINGS.daily_post_enabled,
    daily_post_times: Array.isArray(s.daily_post_times) && s.daily_post_times.length
      ? s.daily_post_times : DEFAULT_SETTINGS.daily_post_times,
    daily_post_days: Array.isArray(s.daily_post_days) && s.daily_post_days.length
      ? s.daily_post_days : DEFAULT_SETTINGS.daily_post_days,
    timezone: typeof s.timezone === 'string' && s.timezone.trim()
      ? s.timezone : DEFAULT_SETTINGS.timezone,
    ai_language: s.ai_language === 'en-US' ? 'en-US' : 'pt-BR',
    allowed_card_types: Array.isArray(s.allowed_card_types) && s.allowed_card_types.length
      ? s.allowed_card_types : DEFAULT_CARD_TYPES,
  };
}

function parseTimesInput(value) {
  return value.split(',').map((t) => t.trim()).filter(Boolean);
}

function validateTimes(times) {
  return times.length > 0 && times.every((t) => {
    if (!/^\d{2}:\d{2}$/.test(t)) return false;
    const [h, m] = t.split(':').map(Number);
    return h >= 0 && h <= 23 && m >= 0 && m <= 59;
  });
}

// ─── Icons ───────────────────────────────────────────────────────────────────

const ICON_PATHS = {
  bot: <><path d="M12 8V4" /><path d="M9 4h6" /><rect x="5" y="8" width="14" height="11" rx="4" /><path d="M9 13h.01" /><path d="M15 13h.01" /><path d="M10 17h4" /></>,
  plug: <><path d="M8 2v5" /><path d="M16 2v5" /><path d="M7 7h10v4a5 5 0 0 1-10 0Z" /><path d="M12 16v6" /></>,
  key: <><circle cx="7.5" cy="14.5" r="3.5" /><path d="M10 12 21 1" /><path d="M16 6h4v4" /><path d="M14 8h3" /></>,
  shield: <><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10Z" /><path d="m9 12 2 2 4-5" /></>,
  refresh: <><path d="M21 12a9 9 0 0 1-15.2 6.5" /><path d="M3 12A9 9 0 0 1 18.2 5.5" /><path d="M18 2v4h4" /><path d="M6 22v-4H2" /></>,
  search: <><circle cx="11" cy="11" r="7" /><path d="m21 21-4.3-4.3" /></>,
  queue: <><path d="M4 6h16" /><path d="M4 12h16" /><path d="M4 18h10" /></>,
  x: <><path d="M18 6 6 18" /><path d="m6 6 12 12" /></>,
  save: <><path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2Z" /><path d="M17 21v-8H7v8" /><path d="M7 3v5h8" /></>,
  repeat: <><path d="m17 2 4 4-4 4" /><path d="M3 11V9a3 3 0 0 1 3-3h15" /><path d="m7 22-4-4 4-4" /><path d="M21 13v2a3 3 0 0 1-3 3H3" /></>,
  reset: <><path d="M3 12a9 9 0 1 0 3-6.7" /><path d="M3 3v6h6" /></>,
  trash: <><path d="M3 6h18" /><path d="M8 6V4h8v2" /><path d="M19 6l-1 15H6L5 6" /><path d="M10 11v6" /><path d="M14 11v6" /></>,
  settings: <><path d="M12 15.5A3.5 3.5 0 1 0 12 8a3.5 3.5 0 0 0 0 7.5Z" /><path d="M19.4 15a1.7 1.7 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.8-.3 1.7 1.7 0 0 0-1 1.5V21a2 2 0 1 1-4 0v-.2a1.7 1.7 0 0 0-1-1.5 1.7 1.7 0 0 0-1.8.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1A1.7 1.7 0 0 0 4.6 15a1.7 1.7 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.1a1.7 1.7 0 0 0 1.5-1 1.7 1.7 0 0 0-.3-1.8l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1A1.7 1.7 0 0 0 9 4.7a1.7 1.7 0 0 0 1-1.5V3a2 2 0 1 1 4 0v.2a1.7 1.7 0 0 0 1 1.5 1.7 1.7 0 0 0 1.8-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.8 1.7 1.7 0 0 0 1.5 1h.2a2 2 0 1 1 0 4h-.2a1.7 1.7 0 0 0-1.4 1Z" /></>,
  server: <><rect x="3" y="4" width="18" height="6" rx="2" /><rect x="3" y="14" width="18" height="6" rx="2" /><path d="M7 7h.01" /><path d="M7 17h.01" /></>,
  cards: <><rect x="7" y="3" width="10" height="14" rx="2" /><path d="M5 7 3.7 18.1a2 2 0 0 0 1.8 2.2l8.9 1" /><path d="M10 7h4" /><path d="M10 11h4" /></>,
  packs: <><path d="m21 8-9-5-9 5 9 5 9-5Z" /><path d="M3 8v8l9 5 9-5V8" /><path d="M12 13v8" /></>,
  clock: <><circle cx="12" cy="12" r="9" /><path d="M12 7v5l3 2" /></>,
  send: <><path d="m22 2-7 20-4-9-9-4Z" /><path d="M22 2 11 13" /></>,
  skip: <><path d="m5 4 8 8-8 8Z" /><path d="M19 5v14" /></>,
  sync: <><path d="M17 2v5h5" /><path d="M7 22v-5H2" /><path d="M20 11a8 8 0 0 0-13.5-5.8L2 9" /><path d="M4 13a8 8 0 0 0 13.5 5.8L22 15" /></>,
  result: <path d="M20 6 9 17l-5-5" />,
  info: <><circle cx="12" cy="12" r="9" /><path d="M12 11v5" /><path d="M12 8h.01" /></>,
  language: <><circle cx="12" cy="12" r="9" /><path d="M3 12h18" /><path d="M12 3a13.5 13.5 0 0 1 0 18" /><path d="M12 3a13.5 13.5 0 0 0 0 18" /></>,
  chevron: <path d="m9 18 6-6-6-6" />,
  pause: <><path d="M8 5v14" /><path d="M16 5v14" /></>,
  play: <path d="m7 4 13 8-13 8Z" />,
};

function Icon({ name, className = '' }) {
  return (
    <svg
      className={`icon ${className}`.trim()}
      aria-hidden="true"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      {ICON_PATHS[name]}
    </svg>
  );
}

// ─── Primitives ───────────────────────────────────────────────────────────────

function Spinner() {
  return <span className="spinner" aria-hidden="true" />;
}

function Badge({ tone = '', children }) {
  return <span className={`badge ${tone}`.trim()}>{children}</span>;
}

function Notice({ tone = 'warn', children }) {
  return <div className={`notice ${tone}`}>{children}</div>;
}

function Section({ title, footer, danger, children }) {
  return (
    <section className="section">
      {title && <div className={`section-title${danger ? ' danger' : ''}`}>{title}</div>}
      <div className="card">{children}</div>
      {footer && <div className="section-footer">{footer}</div>}
    </section>
  );
}

// ─── Row components ───────────────────────────────────────────────────────────

function Row({ icon, label, value, badgeTone = '', caption, mono = false }) {
  return (
    <div className="row">
      {icon && <Icon name={icon} />}
      <div className="row-main">
        <span className="row-label">{label}</span>
        {caption && <span className="row-caption">{caption}</span>}
      </div>
      {value !== undefined && (
        <span className={`row-value ${mono ? 'mono' : ''}`.trim()}>
          {badgeTone ? <Badge tone={badgeTone}>{value}</Badge> : value}
        </span>
      )}
    </div>
  );
}

function ActionRow({ icon, label, caption, onClick, disabled, loading, danger }) {
  return (
    <button
      className={`row row-action ${danger ? 'danger' : ''}`.trim()}
      onClick={onClick}
      disabled={disabled || loading}
      type="button"
    >
      {icon && <Icon name={icon} />}
      <div className="row-main">
        <span className="row-label">{label}</span>
        {caption && <span className="row-caption">{caption}</span>}
      </div>
      {loading ? <Spinner /> : <Icon name="chevron" className="chevron" />}
    </button>
  );
}

function MenuRow({ icon, label, value, onClick, disabled }) {
  return (
    <button className="row row-action" onClick={onClick} disabled={disabled} type="button">
      {icon && <Icon name={icon} />}
      <span className="row-label">{label}</span>
      {value !== undefined && <span className="row-value">{value}</span>}
      <Icon name="chevron" className="chevron" />
    </button>
  );
}

function ToggleRow({ label, checked, onChange, disabled = false }) {
  return (
    <label className="toggle-row">
      <span className="row-label">{label}</span>
      <input type="checkbox" checked={checked} disabled={disabled} onChange={(e) => onChange(e.target.checked)} />
      <span className="toggle" aria-hidden="true" />
    </label>
  );
}

function Field({ label, hint, children }) {
  return (
    <label className="field">
      <span className="field-label">{label}</span>
      {children}
      {hint && <span className="field-hint">{hint}</span>}
    </label>
  );
}

function SelectField({ label, value, onChange, hint, children }) {
  return (
    <label className="field">
      {label && <span className="field-label">{label}</span>}
      <select className="input" value={value} onChange={(e) => onChange(e.target.value)}>
        {children}
      </select>
      {hint && <span className="field-hint">{hint}</span>}
    </label>
  );
}

function CommandRow({ command, onCancel, loading, copy }) {
  const cancellable = ['pending', 'retrying'].includes(command.status);
  const tone = command.status === 'failed' ? 'err' : command.status === 'executed' ? 'ok' : 'warn';
  const parts = [command.status, command.created_at ? new Date(command.created_at).toLocaleString(copy.locale) : null, command.last_error || null].filter(Boolean);
  return (
    <div className="command-row">
      <div className="row-main">
        <span className="row-label">{command.command_type}</span>
        <span className="row-caption">{parts.join(' · ')}</span>
      </div>
      <Badge tone={tone}>{command.status}</Badge>
      {cancellable && (
        <button className="icon-btn" type="button" onClick={() => onCancel(command.id)} disabled={loading} aria-label={copy.cancelCommand}>
          {loading ? <Spinner /> : <Icon name="x" />}
        </button>
      )}
    </div>
  );
}

function CardResult({ card, selected, onSelect }) {
  return (
    <button className={`card-result ${selected ? 'active' : ''}`.trim()} type="button" onClick={() => onSelect(card)}>
      <span className="card-code">{card.code}</span>
      <div className="card-info">
        <span className="card-name">{card.name || card.real_name}</span>
        <span className="card-meta">{[card.type_code, card.faction_name, card.pack_name].filter(Boolean).join(' · ')}</span>
      </div>
    </button>
  );
}

// ─── Auth gate screens ────────────────────────────────────────────────────────

function GateScreen({ children }) {
  return (
    <div className="gate">
      <div className="gate-inner">{children}</div>
    </div>
  );
}

function LoadingGate() {
  return (
    <GateScreen>
      <Spinner />
    </GateScreen>
  );
}

function NoTelegramGate({ copy }) {
  return (
    <GateScreen>
      <Icon name="bot" className="gate-icon" />
      <p className="gate-title">Arkham Bot</p>
      <p className="gate-text">{copy.outsideTelegram}</p>
    </GateScreen>
  );
}

// ─── App ──────────────────────────────────────────────────────────────────────

function App() {
  const [language, setLanguage] = useState(getInitialLanguage);
  const copy = I18N[language];

  // 'loading' | 'no_telegram' | 'unauthorized' | 'ready'
  const [authState, setAuthState] = useState('loading');

  const [me, setMe] = useState(null);
  const [sysStatus, setSysStatus] = useState(null);
  const [overview, setOverview] = useState(null);
  const [commands, setCommands] = useState([]);
  const [settings, setSettings] = useState(DEFAULT_SETTINGS);
  const [timesInput, setTimesInput] = useState(DEFAULT_SETTINGS.daily_post_times.join(', '));
  const [result, setResult] = useState(null);
  const [settingsResult, setSettingsResult] = useState(null);
  const [cardCode, setCardCode] = useState('');
  const [cardQuery, setCardQuery] = useState('');
  const [cardResults, setCardResults] = useState([]);
  const [targetChatId, setTargetChatId] = useState('');
  const [activeTab, setActiveTab] = useState('menu');

  const [loadingCmd, setLoadingCmd] = useState(null);
  const [loadingStatus, setLoadingStatus] = useState(false);
  const [loadingOverview, setLoadingOverview] = useState(false);
  const [loadingCommands, setLoadingCommands] = useState(false);
  const [loadingSettings, setLoadingSettings] = useState(false);
  const [savingSettings, setSavingSettings] = useState(false);
  const [searchingCards, setSearchingCards] = useState(false);
  const [cancellingCommand, setCancellingCommand] = useState(null);

  const searchTimerRef = useRef(null);

  const apiConfigured = Boolean(getApiBase());
  const isAdmin = me?.admin === true;
  const actionsDisabled = !isAdmin || !apiConfigured || loadingCmd !== null;

  // ── Telegram setup ──────────────────────────────────────────────────────────
  useEffect(() => {
    const app = tg();
    if (!app) return;
    app.ready?.();
    app.expand?.();
    try { app.setHeaderColor?.('secondary_bg_color'); } catch {}
    try { app.setBackgroundColor?.('bg_color'); } catch {}
    try { app.setBottomBarColor?.('secondary_bg_color'); } catch {}

    const applyColors = () => {
      try { app.setHeaderColor?.('secondary_bg_color'); } catch {}
      try { app.setBackgroundColor?.('bg_color'); } catch {}
      try { app.setBottomBarColor?.('secondary_bg_color'); } catch {}
    };

    const onViewportChanged = ({ isStateStable }) => { if (isStateStable) app.expand?.(); };

    app.onEvent?.('themeChanged', applyColors);
    app.onEvent?.('viewportChanged', onViewportChanged);
    app.onEvent?.('safeAreaChanged', () => {});
    app.onEvent?.('contentSafeAreaChanged', () => {});

    return () => {
      app.offEvent?.('themeChanged', applyColors);
      app.offEvent?.('viewportChanged', onViewportChanged);
    };
  }, []);

  // ── BackButton ──────────────────────────────────────────────────────────────
  useEffect(() => {
    const btn = tg()?.BackButton;
    if (!btn) return;
    const goHome = () => setActiveTab('menu');
    if (activeTab === 'menu') {
      btn.hide?.();
    } else {
      btn.show?.();
      btn.onClick?.(goHome);
    }
    return () => btn.offClick?.(goHome);
  }, [activeTab]);

  // ── CloudStorage language sync ──────────────────────────────────────────────
  useEffect(() => {
    readLangStorage((lang) => setLanguage(lang));
  }, []);

  // ── Auth gate: check before loading anything else ───────────────────────────
  useEffect(() => {
    if (!tg() || !initData()) {
      setAuthState('no_telegram');
      return;
    }
    if (!apiConfigured) {
      // No API configured — still show UI in dev mode but warn
      setAuthState('ready');
      return;
    }
    apiFetch('/me').then(({ ok, json }) => {
      if (ok && json?.admin === true) {
        setMe(json);
        setAuthState('ready');
        fetchStatus();
        fetchOverview();
        fetchCommands();
      } else {
        // Unauthorized: show native alert then close per Telegram docs
        const msg = copy.errors.unauthorized?.[0] || 'Access denied.';
        const app = tg();
        if (app?.showAlert) {
          app.showAlert(msg, () => app.close?.());
        } else {
          app?.close?.();
        }
        setAuthState('unauthorized');
      }
    }).catch(() => {
      setAuthState('ready'); // network error: degrade gracefully, let UI handle it
    });
  }, []);

  // ── API calls ───────────────────────────────────────────────────────────────

  async function fetchMe() {
    if (!apiConfigured) return;
    try {
      const { json } = await apiFetch('/me');
      setMe(json);
    } catch {}
  }

  async function fetchStatus() {
    if (!apiConfigured) return;
    setLoadingStatus(true);
    try {
      const { json } = await apiFetch('/status');
      setSysStatus(json);
    } catch {
      setSysStatus({ ok: false });
    } finally {
      setLoadingStatus(false);
    }
  }

  async function fetchOverview() {
    if (!apiConfigured) return;
    setLoadingOverview(true);
    try {
      const { ok, status, json } = await apiFetch('/overview');
      if (!ok) {
        const err = resolveError(json.error, `HTTP ${status}`, copy);
        setResult({ ok: false, friendly: err.friendly, detail: err.detail });
      } else {
        setOverview(json);
        if (json.settings) applySettings(json.settings);
      }
    } catch {
      setResult({ ok: false, friendly: copy.networkError, detail: '' });
    } finally {
      setLoadingOverview(false);
    }
  }

  async function fetchCommands() {
    if (!apiConfigured) return;
    setLoadingCommands(true);
    try {
      const { ok, status, json } = await apiFetch('/commands');
      if (!ok) {
        const err = resolveError(json.error, `HTTP ${status}`, copy);
        setResult({ ok: false, friendly: err.friendly, detail: err.detail });
      } else {
        setCommands(json.commands || []);
      }
    } catch {
      setResult({ ok: false, friendly: copy.networkError, detail: '' });
    } finally {
      setLoadingCommands(false);
    }
  }

  async function fetchSettings() {
    if (!apiConfigured) return;
    setLoadingSettings(true);
    try {
      const { ok, status, json } = await apiFetch('/settings');
      if (!ok) {
        const err = resolveError(json.error, `HTTP ${status}`, copy);
        setSettingsResult({ ok: false, friendly: err.friendly, detail: err.detail });
      } else {
        applySettings(json.settings);
        setSettingsResult(null);
      }
    } catch {
      setSettingsResult({ ok: false, friendly: copy.networkError, detail: '' });
    } finally {
      setLoadingSettings(false);
    }
  }

  async function saveSettings() {
    const times = parseTimesInput(timesInput);
    if (!validateTimes(times)) {
      haptic('notification', 'error');
      setSettingsResult({ ok: false, friendly: copy.invalidTime, detail: '' });
      return;
    }
    if (!settings.daily_post_days.length) {
      haptic('notification', 'error');
      setSettingsResult({ ok: false, friendly: copy.selectAtLeastOneDay, detail: '' });
      return;
    }
    if (!settings.timezone.trim()) {
      haptic('notification', 'error');
      setSettingsResult({ ok: false, friendly: copy.timezoneRequired, detail: '' });
      return;
    }
    setSavingSettings(true);
    try {
      const body = { ...settings, daily_post_times: times, timezone: settings.timezone.trim() };
      const { ok, status, json } = await apiFetch('/settings', {
        method: 'PATCH',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify(body),
      });
      if (!ok) {
        haptic('notification', 'error');
        const err = resolveError(json.error, `HTTP ${status}`, copy);
        setSettingsResult({ ok: false, friendly: err.friendly, detail: [err.detail, json.key && `key: ${json.key}`].filter(Boolean).join('\n') });
      } else {
        haptic('notification', 'success');
        applySettings(json.settings);
        setSettingsResult({ ok: true, friendly: copy.settingsSaved, detail: '' });
      }
    } catch {
      haptic('notification', 'error');
      setSettingsResult({ ok: false, friendly: copy.networkError, detail: '' });
    } finally {
      setSavingSettings(false);
    }
  }

  async function cancelCommand(commandId) {
    setCancellingCommand(commandId);
    try {
      const { ok, status, json } = await apiFetch(`/commands/${commandId}`, {
        method: 'PATCH',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ status: 'cancelled' }),
      });
      if (!ok) {
        haptic('notification', 'error');
        const err = resolveError(json.error, `HTTP ${status}`, copy);
        setResult({ ok: false, friendly: err.friendly, detail: err.detail });
      } else {
        haptic('notification', 'success');
        setResult({ ok: true, friendly: copy.commandCancelled, detail: '' });
        fetchCommands();
        fetchOverview();
      }
    } catch {
      haptic('notification', 'error');
      setResult({ ok: false, friendly: copy.networkError, detail: '' });
    } finally {
      setCancellingCommand(null);
    }
  }

  const enqueue = useCallback(async (command_type, payload = {}) => {
    if (loadingCmd) return;
    haptic('impact', 'light');
    setLoadingCmd(command_type);
    try {
      const { ok, status, json } = await apiFetch('/bot-command', {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ command_type, payload, target_chat_id: targetChatId || null }),
      });
      if (!ok) {
        haptic('notification', 'error');
        const err = resolveError(json.error, `HTTP ${status}`, copy);
        setResult({
          ok: false,
          command_type,
          friendly: err.friendly,
          detail: [err.detail, json.role && `role: ${json.role}`, json.admin_source && `source: ${json.admin_source}`].filter(Boolean).join('\n'),
        });
      } else {
        haptic('notification', 'success');
        setResult({
          ok: true,
          command_type: json.command?.command_type || command_type,
          friendly: copy.commandQueued,
          detail: json.command?.id ? `ID: ${json.command.id}` : '',
        });
        fetchStatus();
        fetchCommands();
        fetchOverview();
      }
    } catch {
      haptic('notification', 'error');
      setResult({ ok: false, command_type, friendly: copy.networkError, detail: '' });
    } finally {
      setLoadingCmd(null);
    }
  }, [loadingCmd, targetChatId, copy]);

  function applySettings(next) {
    const n = normalizeSettings(next);
    setSettings(n);
    setTimesInput(n.daily_post_times.join(', '));
  }

  function toggleDay(code) {
    setSettings((cur) => ({
      ...cur,
      daily_post_days: cur.daily_post_days.includes(code)
        ? cur.daily_post_days.filter((d) => d !== code)
        : [...cur.daily_post_days, code],
    }));
  }

  function toggleLanguage() {
    const next = language === 'pt' ? 'en' : 'pt';
    setLanguage(next);
    writeLangStorage(next);
  }

  function handleSearchChange(e) {
    const val = e.target.value;
    setCardQuery(val);
    clearTimeout(searchTimerRef.current);
    if (val.trim().length < 2) { setCardResults([]); return; }
    searchTimerRef.current = setTimeout(() => doSearchCards(val.trim()), 500);
  }

  async function doSearchCards(query) {
    if (!apiConfigured) return;
    setSearchingCards(true);
    try {
      const { ok, status, json } = await apiFetch(`/cards?q=${encodeURIComponent(query)}`);
      if (!ok) {
        const err = resolveError(json.error, `HTTP ${status}`, copy);
        setResult({ ok: false, friendly: err.friendly, detail: err.detail });
      } else {
        setCardResults(json.cards || []);
      }
    } catch {
      setResult({ ok: false, friendly: copy.networkError, detail: '' });
    } finally {
      setSearchingCards(false);
    }
  }

  function confirmThenEnqueue(message, command_type, payload = {}) {
    const app = tg();
    if (app?.showConfirm) {
      app.showConfirm(message, (confirmed) => { if (confirmed) enqueue(command_type, payload); });
    } else if (window.confirm(message)) {
      enqueue(command_type, payload);
    }
  }

  // ── Derived values ──────────────────────────────────────────────────────────

  const adminValue = !apiConfigured ? copy.noApi
    : me?.ok && isAdmin ? (me.role || 'admin')
    : me?.ok ? (me.role || 'none')
    : copy.pending;

  const workerValue = loadingStatus ? '…' : sysStatus?.ok ? copy.online : copy.offline;
  const cardsValue = loadingOverview ? '…' : (overview?.counts?.cards ?? sysStatus?.total_cards ?? '-');
  const queueValue = loadingOverview ? '…' : (overview?.counts?.pending_commands ?? 0);
  const targetChats = overview?.target_chats?.filter((c) => c.enabled !== false) || [];

  // ── Auth gate ───────────────────────────────────────────────────────────────

  if (authState === 'loading' || authState === 'unauthorized') return <LoadingGate />;
  if (authState === 'no_telegram') return <NoTelegramGate copy={copy} />;

  // ── Render ──────────────────────────────────────────────────────────────────

  return (
    <div className="app">

      {/* Header — centered, BotFather-style */}
      <header className="app-header">
        <div className="avatar">
          {getBotPhotoUrl()
            ? <img src={getBotPhotoUrl()} alt="Arkham Bot" className="avatar-img" />
            : <Icon name="bot" />}
        </div>
        <div className="header-title">Arkham Bot</div>
        <div className="header-subtitle">{copy.subtitle}</div>
      </header>

      {!apiConfigured && <Notice tone="err">{copy.workerNotConfigured} {copy.defineApiUrl}</Notice>}

      {/* ── MENU ── */}
      {activeTab === 'menu' && (
        <Section>
          <MenuRow icon="send" label={copy.postCard} caption={copy.postCardCaption} onClick={() => setActiveTab('post')} />
          <MenuRow icon="settings" label={copy.controls} caption={copy.controlsCaption} onClick={() => setActiveTab('controls')} />
          <MenuRow icon="clock" label={copy.schedule} caption={copy.scheduleCaption} onClick={() => setActiveTab('schedule')} />
          <MenuRow icon="queue" label={copy.queue} caption={copy.queueCaption} value={queueValue > 0 ? String(queueValue) : undefined} onClick={() => setActiveTab('queue')} />
          <MenuRow icon="server" label={copy.health} caption={copy.healthCaption} value={workerValue} onClick={() => setActiveTab('status')} />
          <MenuRow icon="language" label={copy.language} caption={copy.langToggle} value={copy.langName} onClick={toggleLanguage} />
        </Section>
      )}

      {/* ── POST CARD ── */}
      {activeTab === 'post' && (
        <Section title={copy.postCard}>
          <div className="form-row">
            <Field label={copy.searchByCodeOrName}>
              <div className="search-line">
                <input
                  className="input"
                  type="search"
                  value={cardQuery}
                  onChange={handleSearchChange}
                  placeholder={copy.searchPlaceholder}
                  inputMode="text"
                />
                {searchingCards && <Spinner />}
              </div>
            </Field>
          </div>

          {cardResults.length > 0 && (
            <div className="card-results">
              {cardResults.map((card) => (
                <CardResult
                  key={card.code}
                  card={card}
                  selected={cardCode === card.code}
                  onSelect={(sel) => {
                    setCardCode(sel.code);
                    setCardQuery(`${sel.code} – ${sel.name || sel.real_name}`);
                    setCardResults([]);
                  }}
                />
              ))}
            </div>
          )}

          <div className="form-row">
            <Field label={copy.selectedCard} hint={copy.selectedCardHint}>
              <input
                className="input"
                type="text"
                placeholder={copy.selectedCardPlaceholder}
                value={cardCode}
                onChange={(e) => setCardCode(e.target.value.trim())}
                inputMode="text"
              />
            </Field>
          </div>

          {targetChats.length > 0 && (
            <div className="form-row">
              <SelectField label={copy.destination} value={targetChatId} onChange={setTargetChatId}>
                <option value="">{copy.defaultChat}</option>
                {targetChats.map((chat) => (
                  <option key={chat.chat_id} value={chat.chat_id}>{chat.title || chat.chat_id}</option>
                ))}
              </SelectField>
            </div>
          )}

          <ActionRow
            icon="send"
            label={copy.postNow}
            caption={cardCode ? `${copy.card} ${cardCode}` : copy.automaticChoice}
            onClick={() => enqueue('post_now', cardCode ? { card_code: cardCode } : {})}
            loading={loadingCmd === 'post_now'}
            disabled={actionsDisabled}
          />
          <ActionRow
            icon="repeat"
            label={copy.repostCard}
            caption={cardCode ? `${copy.card} ${cardCode}` : copy.informCardCode}
            onClick={() => enqueue('repost_card', { card_code: cardCode })}
            loading={loadingCmd === 'repost_card'}
            disabled={actionsDisabled || !cardCode}
          />
          <ActionRow
            icon="skip"
            label={copy.skipCard}
            caption={cardCode ? `${copy.card} ${cardCode}` : copy.informCardCode}
            onClick={() => enqueue('skip_card', { card_code: cardCode })}
            loading={loadingCmd === 'skip_card'}
            disabled={actionsDisabled || !cardCode}
          />
        </Section>
      )}

      {/* ── CONTROLS ── */}
      {activeTab === 'controls' && (
        <>
          <Section title={copy.modeSettings} footer={copy.automaticPostingCaption}>
            <ToggleRow
              label={copy.automaticPosting}
              checked={settings.daily_post_enabled}
              disabled={actionsDisabled}
              onChange={(checked) => confirmThenEnqueue(
                checked ? copy.confirmResume : copy.confirmPause,
                checked ? 'resume_daily_post' : 'pause_daily_post'
              )}
            />
          </Section>

          <Section title={copy.maintenance} footer={copy.syncCaption}>
            <ActionRow icon="sync" label={copy.syncArkhamDB} onClick={() => enqueue('sync_arkhamdb', { sync_faq: false })} loading={loadingCmd === 'sync_arkhamdb'} disabled={actionsDisabled} />
          </Section>

          <Section title={copy.dangerZone} danger>
            <ActionRow icon="reset" label={copy.resetCycle} onClick={() => confirmThenEnqueue(copy.confirmReset, 'reset_cycle')} loading={loadingCmd === 'reset_cycle'} disabled={actionsDisabled} danger />
            <ActionRow icon="trash" label={copy.clearQueue} onClick={() => confirmThenEnqueue(copy.confirmClear, 'clear_queue')} loading={loadingCmd === 'clear_queue'} disabled={actionsDisabled} danger />
          </Section>
        </>
      )}

      {/* ── SCHEDULE ── */}
      {activeTab === 'schedule' && (
        <>
          <Section title={copy.scheduleTitle || copy.schedule} footer={copy.automaticPostingCaption}>
            <ToggleRow
              label={copy.automaticPosting}
              checked={settings.daily_post_enabled}
              onChange={(checked) => setSettings((cur) => ({ ...cur, daily_post_enabled: checked }))}
            />
            <div className="form-row">
              <Field label={copy.postTimes} hint={copy.postTimesCaption}>
                <input className="input" type="text" value={timesInput} onChange={(e) => setTimesInput(e.target.value)} placeholder="09:00, 21:30" inputMode="text" />
              </Field>
            </div>
            <div className="form-row">
              <span className="field-label">{copy.postDays}</span>
              <span className="field-hint">{copy.postDaysCaption}</span>
              <div className="day-grid">
                {WEEKDAYS.map((day) => (
                  <button
                    key={day.code}
                    className={`day-btn ${settings.daily_post_days.includes(day.code) ? 'active' : ''}`.trim()}
                    type="button"
                    onClick={() => toggleDay(day.code)}
                  >
                    {day[language]}
                  </button>
                ))}
              </div>
            </div>
            <div className="form-row">
              <Field label={copy.timezoneLabel} hint={copy.timezoneCaption}>
                <input className="input" type="text" value={settings.timezone} onChange={(e) => setSettings((cur) => ({ ...cur, timezone: e.target.value }))} placeholder="America/Sao_Paulo" inputMode="text" />
              </Field>
            </div>
          </Section>

          <Section title={copy.aiLanguage} footer={copy.aiLanguageCaption}>
            <div className="form-row">
              <SelectField
                value={settings.ai_language}
                onChange={(val) => setSettings((cur) => ({ ...cur, ai_language: val }))}
              >
                <option value="pt-BR">{copy.aiLanguagePt}</option>
                <option value="en-US">{copy.aiLanguageEn}</option>
              </SelectField>
            </div>
          </Section>

          <Section title={copy.cardTypes} footer={copy.cardTypesCaption}>
            <div className="form-row">
              <div className="type-grid">
                {ALL_CARD_TYPES.map((type) => {
                  const active = settings.allowed_card_types.includes(type.code);
                  return (
                    <button
                      key={type.code}
                      type="button"
                      className={`type-btn ${active ? 'active' : ''}`.trim()}
                      onClick={() => setSettings((cur) => {
                        const next = active
                          ? cur.allowed_card_types.filter((t) => t !== type.code)
                          : [...cur.allowed_card_types, type.code];
                        return { ...cur, allowed_card_types: next.length ? next : cur.allowed_card_types };
                      })}
                    >
                      {type[language]}
                    </button>
                  );
                })}
              </div>
            </div>
          </Section>

          <Section>
            <ActionRow icon="refresh" label={copy.reloadSettings} onClick={fetchSettings} loading={loadingSettings} disabled={!apiConfigured} />
            <ActionRow icon="save" label={copy.saveSettings} onClick={saveSettings} loading={savingSettings} disabled={actionsDisabled} />
          </Section>

          {settingsResult && (
            <Section>
              <Row
                icon={settingsResult.ok ? 'result' : 'info'}
                label={settingsResult.ok ? copy.success : copy.error}
                value={settingsResult.ok ? 'ok' : 'err'}
                badgeTone={settingsResult.ok ? 'ok' : 'err'}
                caption={settingsResult.friendly}
              />
              {settingsResult.detail && (
                <details className="details">
                  <summary>{copy.details}</summary>
                  <pre className="details-pre">{settingsResult.detail}</pre>
                </details>
              )}
            </Section>
          )}
        </>
      )}

      {/* ── QUEUE ── */}
      {activeTab === 'queue' && (
        <Section title={copy.commandQueue}>
          <ActionRow icon="refresh" label={copy.refreshQueue} onClick={fetchCommands} loading={loadingCommands} disabled={!apiConfigured} />
          {commands.length === 0 && !loadingCommands && <Row icon="queue" label={copy.noRecentCommands} />}
          {commands.map((cmd) => (
            <CommandRow key={cmd.id} command={cmd} onCancel={cancelCommand} loading={cancellingCommand === cmd.id} copy={copy} />
          ))}
        </Section>
      )}

      {/* ── HEALTH ── */}
      {activeTab === 'status' && (
        <>
          <Section title={copy.summary}>
            <Row icon="server" label={copy.worker} value={workerValue} badgeTone={sysStatus?.ok ? 'ok' : 'err'} />
            <Row icon="shield" label={copy.access} value={adminValue} badgeTone={isAdmin ? 'ok' : 'err'} />
            <Row icon="cards" label={copy.cards} value={cardsValue} />
            <Row icon="queue" label={copy.queue} value={queueValue} />
          </Section>

          <Section title={copy.account}>
            <Row icon="plug" label={copy.telegramWebApp} value={tg() ? copy.yes : copy.no} badgeTone={tg() ? 'ok' : 'err'} />
            <Row icon="key" label={copy.initDataLabel} value={initData() ? copy.yes : copy.no} badgeTone={initData() ? 'ok' : 'err'} />
            <Row icon="shield" label={copy.admin} value={adminValue} badgeTone={isAdmin ? 'ok' : 'err'} caption={me?.admin_source ? `source: ${me.admin_source}` : undefined} />
            <ActionRow icon="refresh" label={copy.recheckAuth} onClick={fetchMe} loading={loadingMe} disabled={!apiConfigured} />
          </Section>

          <Section title={copy.system}>
            <Row icon="server" label={copy.worker} value={sysStatus?.ok ? copy.online : copy.offline} badgeTone={sysStatus?.ok ? 'ok' : 'err'} />
            <Row icon="cards" label={copy.cards} value={loadingStatus ? '…' : (sysStatus?.total_cards ?? '-')} />
            <Row icon="packs" label={copy.packs} value={loadingStatus ? '…' : (sysStatus?.total_packs ?? '-')} />
            <Row icon="clock" label={copy.lastSync} value={(overview?.last_sync || sysStatus?.last_sync) ? new Date(overview?.last_sync || sysStatus?.last_sync).toLocaleString(copy.locale) : '-'} mono />
            <ActionRow icon="refresh" label={copy.refreshStatus} onClick={() => { fetchStatus(); fetchOverview(); }} loading={loadingStatus || loadingOverview} disabled={!apiConfigured} />
          </Section>

          <Section title={copy.diagnostic}>
            <details className="details">
              <summary><Icon name="info" />{copy.showDetails}</summary>
              <pre className="details-pre">{[
                `${copy.telegramWebApp}: ${Boolean(tg())}`,
                `${copy.initDataPresent}: ${Boolean(initData())}`,
                `${copy.initDataLength}: ${initData().length}`,
                `${copy.userUnsafe}: ${Boolean(tgUser())}`,
                `${copy.apiConfigured}: ${apiConfigured}`,
                `${copy.apiBase}: ${getApiBase() || copy.notConfigured}`,
                `${copy.admin}: ${Boolean(me?.admin)}`,
                `${copy.role}: ${me?.role || '-'}`,
                `${copy.adminSource}: ${me?.admin_source || '-'}`,
              ].join('\n')}</pre>
            </details>
          </Section>
        </>
      )}

      {/* ── RESULT TOAST ── */}
      {result && activeTab !== 'status' && (
        <Section>
          <Row
            icon={result.ok ? 'result' : 'info'}
            label={result.ok ? copy.success : copy.error}
            value={result.command_type || (result.ok ? 'ok' : 'err')}
            badgeTone={result.ok ? 'ok' : 'err'}
            caption={result.friendly}
          />
          {result.detail && (
            <details className="details">
              <summary>{copy.details}</summary>
              <pre className="details-pre">{result.detail}</pre>
            </details>
          )}
        </Section>
      )}

    </div>
  );
}

createRoot(document.getElementById('root')).render(<App />);
