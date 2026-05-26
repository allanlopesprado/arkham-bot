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
    else if (type === 'selection') hf.selectionChanged();
  } catch {}
}

function tgShowPopup(params) {
  return new Promise((resolve) => {
    const app = tg();
    if (app?.showPopup) {
      try { app.showPopup(params, (id) => resolve(id)); return; } catch {}
    }
    // fallback for dev/browser
    const ok = window.confirm(`${params.title ? params.title + '\n' : ''}${params.message || ''}`);
    resolve(ok ? (params.buttons?.find((b) => b.type !== 'cancel')?.id ?? 'ok') : null);
  });
}

// ─── API ─────────────────────────────────────────────────────────────────────

function getBotPhotoUrl() { return import.meta.env.VITE_BOT_PHOTO_URL || ''; }

function getApiBase() {
  const raw = import.meta.env.VITE_COMMANDS_API_URL || '';
  if (!raw) return '';
  try { return new URL(raw).origin; } catch { return raw; }
}

function apiUrl(path) {
  const base = getApiBase();
  return base ? `${base.replace(/\/$/, '')}${path}` : '';
}

function authHeaders() { return { 'x-telegram-init-data': initData() }; }

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
  { code: 'mon', pt: 'Segunda-feira', en: 'Monday' },
  { code: 'tue', pt: 'Terça-feira',   en: 'Tuesday' },
  { code: 'wed', pt: 'Quarta-feira',  en: 'Wednesday' },
  { code: 'thu', pt: 'Quinta-feira',  en: 'Thursday' },
  { code: 'fri', pt: 'Sexta-feira',   en: 'Friday' },
  { code: 'sat', pt: 'Sábado',        en: 'Saturday' },
  { code: 'sun', pt: 'Domingo',       en: 'Sunday' },
];

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

// Cycle names derived dynamically from fetched packs (first pack per cycle_position)
function deriveCycles(packs) {
  const map = new Map();
  for (const p of packs) {
    const pos = p.cycle_position ?? 99;
    if (!map.has(pos) || p.position < map.get(pos).position) map.set(pos, p);
  }
  return [...map.entries()]
    .sort(([a], [b]) => a - b)
    .map(([pos, first]) => ({ position: pos, name: first.name }));
}

const TIMEZONES = [
  { value: 'America/Sao_Paulo',              label: 'São Paulo (UTC−3)' },
  { value: 'America/Manaus',                 label: 'Manaus (UTC−4)' },
  { value: 'America/Belem',                  label: 'Belém (UTC−3)' },
  { value: 'America/Fortaleza',              label: 'Fortaleza (UTC−3)' },
  { value: 'America/Recife',                 label: 'Recife (UTC−3)' },
  { value: 'America/Bahia',                  label: 'Salvador (UTC−3)' },
  { value: 'America/Noronha',                label: 'Noronha (UTC−2)' },
  { value: 'America/Rio_Branco',             label: 'Rio Branco (UTC−5)' },
  { value: 'America/Argentina/Buenos_Aires', label: 'Buenos Aires (UTC−3)' },
  { value: 'America/Bogota',                 label: 'Bogotá (UTC−5)' },
  { value: 'America/Lima',                   label: 'Lima (UTC−5)' },
  { value: 'America/Santiago',               label: 'Santiago (UTC−4/−3)' },
  { value: 'America/Caracas',                label: 'Caracas (UTC−4)' },
  { value: 'America/Mexico_City',            label: 'Cidade do México (UTC−6/−5)' },
  { value: 'America/New_York',               label: 'Nova York (UTC−5/−4)' },
  { value: 'America/Chicago',                label: 'Chicago (UTC−6/−5)' },
  { value: 'America/Denver',                 label: 'Denver (UTC−7/−6)' },
  { value: 'America/Los_Angeles',            label: 'Los Angeles (UTC−8/−7)' },
  { value: 'America/Toronto',                label: 'Toronto (UTC−5/−4)' },
  { value: 'Europe/Lisbon',                  label: 'Lisboa (UTC+0/+1)' },
  { value: 'Europe/London',                  label: 'Londres (UTC+0/+1)' },
  { value: 'Europe/Paris',                   label: 'Paris (UTC+1/+2)' },
  { value: 'Europe/Berlin',                  label: 'Berlim (UTC+1/+2)' },
  { value: 'Europe/Madrid',                  label: 'Madrid (UTC+1/+2)' },
  { value: 'Europe/Rome',                    label: 'Roma (UTC+1/+2)' },
  { value: 'Europe/Moscow',                  label: 'Moscou (UTC+3)' },
  { value: 'Asia/Dubai',                     label: 'Dubai (UTC+4)' },
  { value: 'Asia/Kolkata',                   label: 'Mumbai (UTC+5:30)' },
  { value: 'Asia/Shanghai',                  label: 'Xangai (UTC+8)' },
  { value: 'Asia/Singapore',                 label: 'Singapura (UTC+8)' },
  { value: 'Asia/Tokyo',                     label: 'Tóquio (UTC+9)' },
  { value: 'Australia/Sydney',               label: 'Sydney (UTC+10/+11)' },
  { value: 'Pacific/Auckland',               label: 'Auckland (UTC+12/+13)' },
  { value: 'UTC',                            label: 'UTC (UTC+0)' },
];

const I18N = {
  pt: {
    locale: 'pt-BR',
    langName: 'Português',
    subtitle: 'Console Admin',
    outsideTelegram: 'Abra pelo Telegram para autenticar.',
    workerNotConfigured: 'Worker não configurado. Defina VITE_COMMANDS_API_URL.',
    // tabs
    postCard: 'Postar carta',
    settings: 'Configurações',
    maintenance: 'Manutenção',
    queue: 'Fila',
    health: 'Saúde',
    language: 'Idioma',
    // post
    searchPlaceholder: '01001 ou Shrivelling',
    noCardSelected: 'Nenhuma carta selecionada',
    automaticChoice: 'Escolha automática pela IA',
    card: 'Carta',
    postNow: 'Postar agora',
    repostCard: 'Repostar carta',
    skipCard: 'Pular carta',
    informCardCode: 'Informe um código de carta para repostar ou pular',
    destination: 'Destino',
    defaultChat: 'Chat padrão',
    // settings sections
    dailyPost: 'Postagem diária',
    automaticPosting: 'Postagem automática',
    postTimes: 'Horários (24h, separados por vírgula)',
    postDays: 'Dias da semana',
    timezoneLabel: 'Fuso horário',
    cardFilter: 'Filtro de cartas',
    cardTypes: 'Tipos permitidos',
    includeSpoilers: 'Incluir spoilers',
    includeSpoilersCaption: 'Permite cartas marcadas como spoiler',
    aiSection: 'Inteligência Artificial',
    aiEnabled: 'IA habilitada',
    aiEnabledCaption: 'Seleciona e comenta cartas automaticamente',
    aiLanguage: 'Idioma da IA',
    aiLanguagePt: 'Português (pt-BR)',
    aiLanguageEn: 'English (en-US)',
    // weekly schedule
    weeklySchedule: 'Programação semanal',
    weeklyScheduleCaption: 'Configure ciclos e tipos de carta por dia da semana',
    configureDay: 'Configurar',
    dayDetail: 'Configuração do dia',
    cyclesToday: 'Ciclos permitidos',
    typesToday: 'Tipos de carta',
    allCardsAllowed: 'Todas as cartas',
    loadingPacks: 'Carregando expansões…',
    packsFailed: 'Falha ao carregar expansões. Verifique a conexão.',
    noCycleConfig: 'Sem filtro — todas as cartas',
    cyclesSelected: (n) => `${n} ciclo${n !== 1 ? 's' : ''}`,
    typesSelected: (n) => `${n} tipo${n !== 1 ? 's' : ''}`,
    // bot identity
    botDescription: 'Órfã. Investigadora. Sobrevivente. Wendy enfrenta o desconhecido com coragem e seu amuleto da sorte.',
    // home sections
    overviewTitle: 'Visão geral',
    actionsTitle: 'Painel',
    // history
    historyTab: 'Histórico',
    historyTitle: 'Histórico de postagens',
    postedCardsCount: 'Cartas postadas no ciclo',
    noHistory: 'Nenhuma postagem recente',
    // command type labels (friendly)
    commandTypeLabels: {
      post_now: 'Postar carta',
      repost_card: 'Repostar carta',
      skip_card: 'Pular carta',
      sync_arkhamdb: 'Sincronizar ArkhamDB',
      reset_cycle: 'Resetar ciclo',
      clear_queue: 'Limpar fila',
      update_setting: 'Configurar',
      pause_daily_post: 'Pausar postagem',
      resume_daily_post: 'Retomar postagem',
    },
    commandStatusLabels: {
      pending: 'pendente',
      retrying: 'tentando novamente',
      processing: 'processando',
      executed: 'executado',
      failed: 'falhou',
      cancelled: 'cancelado',
    },
    postStatusLabels: {
      POSTED_FRONT_SUCCESS: 'Postada',
      POSTED_BACK: 'Com verso',
      POSTED_BACK_TEXT_ONLY: 'Verso (texto)',
      FAILED_DOWNLOAD: 'Falha no download',
      SUCCESS: 'Sucesso',
    },
    roleLabels: {
      owner: 'proprietário',
      admin: 'administrador',
      administrator: 'administrador',
      member: 'membro',
      creator: 'criador',
    },
    // maintenance
    syncArkhamDB: 'Sincronizar ArkhamDB',
    syncCaption: 'Atualiza cartas e pacotes do banco de dados',
    lastSyncAt: 'Último sincronismo',
    neverSynced: 'Nunca sincronizado',
    syncSuccess: 'bem-sucedido',
    syncUnknown: 'status desconhecido',
    resetCycle: 'Resetar ciclo de cartas',
    resetCaption: 'Permite repetir cartas já postadas',
    clearQueue: 'Limpar fila de comandos',
    clearQueueCaption: 'Cancela todos os comandos pendentes',
    // queue
    commandQueue: 'Fila de comandos',
    refreshQueue: 'Atualizar',
    noRecentCommands: 'Nenhum comando recente',
    cancelCommand: 'Cancelar',
    // health
    summary: 'Resumo',
    worker: 'Servidor',
    access: 'Acesso',
    cards: 'Cartas',
    packs: 'Pacotes',
    lastSync: 'Última sincronização',
    account: 'Conta',
    telegramWebApp: 'Telegram',
    initDataLabel: 'Sessão ativa',
    admin: 'Administrador',
    recheckAuth: 'Atualizar status',
    system: 'Sistema',
    diagnostic: 'Diagnóstico técnico',
    showDetails: 'Mostrar detalhes',
    apiConfigured: 'API configurada',
    apiBase: 'Endpoint',
    userUnsafe: 'Usuário',
    initDataPresent: 'Sessão presente',
    initDataLength: 'Tamanho da sessão',
    role: 'Papel',
    adminSource: 'Origem da permissão',
    adminSourcePrefix: 'origem',
    // language
    chooseLanguage: 'Idioma do aplicativo',
    portuguese: 'Português',
    englishLang: 'English',
    // common
    saveSettings: 'Salvar configurações',
    reloadSettings: 'Recarregar',
    result: 'Resultado',
    success: 'Sucesso',
    error: 'Erro',
    details: 'Detalhes',
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
    // popup messages
    confirmPostNow: (code) => `Postar ${code ? `carta ${code}` : 'carta automática'} agora?`,
    confirmRepost: (code) => `Repostar carta ${code}?`,
    confirmSkip: (code) => `Pular carta ${code} do ciclo?`,
    confirmSync: 'Sincronizar cartas e pacotes com ArkhamDB?',
    confirmReset: 'Resetar o ciclo? Cartas já postadas poderão ser repetidas.',
    confirmClear: 'Limpar toda a fila de comandos pendentes?',
    confirmCancel: (type) => `Cancelar comando "${type}"?`,
    popupConfirm: 'Confirmar',
    popupCancel: 'Cancelar',
    errors: {
      invalid_telegram_init_data: ['Abra pelo Telegram para autenticar.', 'initData inválido.'],
      unauthorized: ['Acesso negado.', 'Seu Telegram ID não tem permissão de administrador.'],
      not_found: ['Endpoint não encontrado.', 'Verifique VITE_COMMANDS_API_URL.'],
      origin_not_allowed: ['Origem não autorizada.', 'Verifique ALLOWED_ORIGINS no Worker.'],
      bot_command_insert_failed: ['Falha ao criar comando.', 'Verifique Worker e Supabase.'],
      command_type_required: ['Tipo de comando não informado.', ''],
      unsupported_command_type: ['Comando não suportado.', ''],
      method_not_allowed: ['Método HTTP não permitido.', ''],
      settings_fetch_failed: ['Falha ao carregar configurações.', ''],
      settings_upsert_failed: ['Falha ao salvar configurações.', ''],
      invalid_setting_value: ['Configuração inválida.', ''],
      unsupported_setting: ['Configuração não suportada.', ''],
      settings_required: ['Nenhuma configuração para salvar.', ''],
      overview_fetch_failed: ['Falha ao carregar painel.', ''],
      commands_fetch_failed: ['Falha ao carregar fila.', ''],
      cards_search_failed: ['Falha ao buscar cartas.', ''],
      command_cancel_failed: ['Falha ao cancelar.', ''],
      command_not_cancellable: ['Comando não pode mais ser cancelado.', ''],
    },
  },
  en: {
    locale: 'en-US',
    langName: 'English',
    subtitle: 'Admin Console',
    outsideTelegram: 'Open from Telegram to authenticate.',
    workerNotConfigured: 'Worker not configured. Set VITE_COMMANDS_API_URL.',
    postCard: 'Post Card',
    settings: 'Settings',
    maintenance: 'Maintenance',
    queue: 'Queue',
    health: 'Health',
    language: 'Language',
    searchPlaceholder: '01001 or Shrivelling',
    noCardSelected: 'No card selected',
    automaticChoice: 'Automatic AI choice',
    card: 'Card',
    postNow: 'Post now',
    repostCard: 'Repost card',
    skipCard: 'Skip card',
    informCardCode: 'Enter a card code to repost or skip',
    destination: 'Destination',
    defaultChat: 'Default chat',
    dailyPost: 'Daily post',
    automaticPosting: 'Automatic posting',
    postTimes: 'Times (24h, comma-separated)',
    postDays: 'Weekdays',
    timezoneLabel: 'Timezone',
    cardFilter: 'Card filter',
    cardTypes: 'Allowed types',
    includeSpoilers: 'Include spoilers',
    includeSpoilersCaption: 'Allow cards marked as spoilers',
    aiSection: 'Artificial Intelligence',
    aiEnabled: 'AI enabled',
    aiEnabledCaption: 'Automatically selects and comments on cards',
    aiLanguage: 'AI language',
    aiLanguagePt: 'Português (pt-BR)',
    aiLanguageEn: 'English (en-US)',
    // weekly schedule
    weeklySchedule: 'Weekly schedule',
    weeklyScheduleCaption: 'Configure cycles and card types per day of the week',
    configureDay: 'Configure',
    dayDetail: 'Day configuration',
    cyclesToday: 'Allowed cycles',
    typesToday: 'Card types',
    allCardsAllowed: 'All cards',
    loadingPacks: 'Loading expansions…',
    packsFailed: 'Failed to load expansions. Check connection.',
    noCycleConfig: 'No filter — all cards',
    cyclesSelected: (n) => `${n} cycle${n !== 1 ? 's' : ''}`,
    typesSelected: (n) => `${n} type${n !== 1 ? 's' : ''}`,
    // bot identity
    botDescription: 'Orphan. Investigator. Survivor. Wendy faces the unknown with courage and her lucky charm.',
    // home sections
    overviewTitle: 'Overview',
    actionsTitle: 'Dashboard',
    // history
    historyTab: 'History',
    historyTitle: 'Posting history',
    postedCardsCount: 'Cards posted in cycle',
    noHistory: 'No recent posts',
    // command type labels (friendly)
    commandTypeLabels: {
      post_now: 'Post card',
      repost_card: 'Repost card',
      skip_card: 'Skip card',
      sync_arkhamdb: 'Sync ArkhamDB',
      reset_cycle: 'Reset cycle',
      clear_queue: 'Clear queue',
      update_setting: 'Update setting',
      pause_daily_post: 'Pause posting',
      resume_daily_post: 'Resume posting',
    },
    commandStatusLabels: {
      pending: 'pending',
      retrying: 'retrying',
      processing: 'processing',
      executed: 'executed',
      failed: 'failed',
      cancelled: 'cancelled',
    },
    postStatusLabels: {
      POSTED_FRONT_SUCCESS: 'Posted',
      POSTED_BACK: 'With back',
      POSTED_BACK_TEXT_ONLY: 'Back (text)',
      FAILED_DOWNLOAD: 'Download failed',
      SUCCESS: 'Success',
    },
    roleLabels: {
      owner: 'owner',
      admin: 'admin',
      administrator: 'administrator',
      member: 'member',
      creator: 'creator',
    },
    syncArkhamDB: 'Sync ArkhamDB',
    syncCaption: 'Updates cards and packs from the database',
    lastSyncAt: 'Last sync',
    neverSynced: 'Never synced',
    syncSuccess: 'successful',
    syncUnknown: 'unknown status',
    resetCycle: 'Reset card cycle',
    resetCaption: 'Allows already-posted cards to repeat',
    clearQueue: 'Clear command queue',
    clearQueueCaption: 'Cancels all pending commands',
    commandQueue: 'Command queue',
    refreshQueue: 'Refresh',
    noRecentCommands: 'No recent commands',
    cancelCommand: 'Cancel',
    summary: 'Summary',
    worker: 'Server',
    access: 'Access',
    cards: 'Cards',
    packs: 'Packs',
    lastSync: 'Last sync',
    account: 'Account',
    telegramWebApp: 'Telegram',
    initDataLabel: 'Active session',
    admin: 'Administrator',
    recheckAuth: 'Refresh status',
    system: 'System',
    diagnostic: 'Technical diagnostic',
    showDetails: 'Show details',
    apiConfigured: 'API configured',
    apiBase: 'Endpoint',
    userUnsafe: 'User',
    initDataPresent: 'Session present',
    initDataLength: 'Session length',
    role: 'Role',
    adminSource: 'Permission source',
    adminSourcePrefix: 'source',
    // language
    chooseLanguage: 'App language',
    portuguese: 'Português',
    englishLang: 'English',
    saveSettings: 'Save settings',
    reloadSettings: 'Reload',
    result: 'Result',
    success: 'Success',
    error: 'Error',
    details: 'Details',
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
    confirmPostNow: (code) => `Post ${code ? `card ${code}` : 'automatic card'} now?`,
    confirmRepost: (code) => `Repost card ${code}?`,
    confirmSkip: (code) => `Skip card ${code} from cycle?`,
    confirmSync: 'Sync cards and packs with ArkhamDB?',
    confirmReset: 'Reset cycle? Previously posted cards may repeat.',
    confirmClear: 'Clear all pending commands from the queue?',
    confirmCancel: (type) => `Cancel command "${type}"?`,
    popupConfirm: 'Confirm',
    popupCancel: 'Cancel',
    errors: {
      invalid_telegram_init_data: ['Open from Telegram to authenticate.', 'Invalid initData.'],
      unauthorized: ['Access denied.', 'Your Telegram ID has no admin permission.'],
      not_found: ['Endpoint not found.', 'Check VITE_COMMANDS_API_URL.'],
      origin_not_allowed: ['Origin not allowed.', 'Check ALLOWED_ORIGINS in Worker.'],
      bot_command_insert_failed: ['Failed to create command.', 'Check Worker and Supabase.'],
      command_type_required: ['Command type not provided.', ''],
      unsupported_command_type: ['Unsupported command.', ''],
      method_not_allowed: ['HTTP method not allowed.', ''],
      settings_fetch_failed: ['Failed to load settings.', ''],
      settings_upsert_failed: ['Failed to save settings.', ''],
      invalid_setting_value: ['Invalid setting.', ''],
      unsupported_setting: ['Unsupported setting.', ''],
      settings_required: ['No settings to save.', ''],
      overview_fetch_failed: ['Failed to load dashboard.', ''],
      commands_fetch_failed: ['Failed to load queue.', ''],
      cards_search_failed: ['Failed to search cards.', ''],
      command_cancel_failed: ['Failed to cancel.', ''],
      command_not_cancellable: ['Command can no longer be cancelled.', ''],
    },
  },
};

function resolveError(code, fallback, copy, payload = {}) {
  const loc = copy.errors[code];
  const detail = payload.detail || payload.message || '';
  if (loc) return { friendly: loc[0], detail: detail || loc[1] };
  return { friendly: fallback || copy.unknownError, detail: detail || code || '' };
}

// ─── Language persistence ─────────────────────────────────────────────────────

function readLangStorage(cb) {
  const cs = tg()?.CloudStorage;
  if (cs) {
    cs.getItem(LANGUAGE_KEY, (err, val) => { if (!err && (val === 'en' || val === 'pt')) cb(val); });
  } else {
    try { const v = localStorage.getItem(LANGUAGE_KEY); if (v === 'en' || v === 'pt') cb(v); } catch {}
  }
}

function writeLangStorage(lang) {
  const cs = tg()?.CloudStorage;
  if (cs) { cs.setItem(LANGUAGE_KEY, lang, () => {}); }
  else { try { localStorage.setItem(LANGUAGE_KEY, lang); } catch {} }
}

function getInitialLanguage() {
  try { const s = localStorage.getItem(LANGUAGE_KEY); if (s === 'en' || s === 'pt') return s; } catch {}
  const code = tgUser()?.language_code || navigator.language || '';
  return code.toLowerCase().startsWith('en') ? 'en' : 'pt';
}

// ─── Settings ────────────────────────────────────────────────────────────────

const DEFAULT_SETTINGS = {
  daily_post_enabled: true,
  daily_post_times: ['08:00'],
  daily_post_days: WEEKDAYS.map((d) => d.code),
  timezone: 'America/Sao_Paulo',
  ai_enabled: true,
  ai_language: 'pt-BR',
  include_spoilers: false,
  allowed_card_types: DEFAULT_CARD_TYPES,
  // day_config: per-day cycle+type config { mon: { packs: [], types: [] }, ... }
  // empty packs = all packs; empty types = all types
  day_config: {},
};

function normalizeSettings(s = {}) {
  return {
    daily_post_enabled: typeof s.daily_post_enabled === 'boolean' ? s.daily_post_enabled : DEFAULT_SETTINGS.daily_post_enabled,
    daily_post_times: Array.isArray(s.daily_post_times) && s.daily_post_times.length ? s.daily_post_times : DEFAULT_SETTINGS.daily_post_times,
    daily_post_days: Array.isArray(s.daily_post_days) && s.daily_post_days.length ? s.daily_post_days : DEFAULT_SETTINGS.daily_post_days,
    timezone: typeof s.timezone === 'string' && s.timezone.trim() ? s.timezone : DEFAULT_SETTINGS.timezone,
    ai_enabled: typeof s.ai_enabled === 'boolean' ? s.ai_enabled : DEFAULT_SETTINGS.ai_enabled,
    ai_language: s.ai_language === 'en-US' ? 'en-US' : 'pt-BR',
    include_spoilers: typeof s.include_spoilers === 'boolean' ? s.include_spoilers : DEFAULT_SETTINGS.include_spoilers,
    allowed_card_types: Array.isArray(s.allowed_card_types) && s.allowed_card_types.length ? s.allowed_card_types : DEFAULT_CARD_TYPES,
    day_config: (s.day_config && typeof s.day_config === 'object' && !Array.isArray(s.day_config)) ? s.day_config : {},
  };
}

function parseTimesInput(v) { return v.split(',').map((t) => t.trim()).filter(Boolean); }
function validateTimes(times) {
  return times.length > 0 && times.every((t) => {
    if (!/^\d{2}:\d{2}$/.test(t)) return false;
    const [h, m] = t.split(':').map(Number);
    return h >= 0 && h <= 23 && m >= 0 && m <= 59;
  });
}

function settingsEqual(a, b) {
  return JSON.stringify(a) === JSON.stringify(b);
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
  wrench: <><path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z" /></>,
  ai: <><path d="M12 2a2 2 0 0 1 2 2c0 .74-.4 1.39-1 1.73V7h1a7 7 0 0 1 7 7h1a1 1 0 0 1 0 2h-1v1a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2v-1H1a1 1 0 0 1 0-2h1a7 7 0 0 1 7-7h1V5.73A2 2 0 0 1 10 4a2 2 0 0 1 2-2M7.5 13a4.5 4.5 0 0 0 0 9h9a4.5 4.5 0 0 0 0-9h-9M9 16.5a1.5 1.5 0 1 1 0 3 1.5 1.5 0 0 1 0-3M15 16.5a1.5 1.5 0 1 1 0 3 1.5 1.5 0 0 1 0-3" /></>,
};

function Icon({ name, className = '' }) {
  return (
    <svg className={`icon ${className}`.trim()} aria-hidden="true" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      {ICON_PATHS[name]}
    </svg>
  );
}

// ─── Primitives ───────────────────────────────────────────────────────────────

function Spinner() { return <span className="spinner" aria-hidden="true" />; }

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

function MenuRow({ icon, label, value, onClick, disabled, loading }) {
  return (
    <button className="row row-action" onClick={onClick} disabled={disabled || loading} type="button">
      {icon && <Icon name={icon} />}
      <span className="row-label">{label}</span>
      {value !== undefined && <span className="row-value">{value}</span>}
      {loading ? <Spinner /> : <Icon name="chevron" className="chevron" />}
    </button>
  );
}

function DangerRow({ icon, label, onClick, disabled, loading }) {
  return (
    <button className="row row-action danger" onClick={onClick} disabled={disabled || loading} type="button">
      {icon && <Icon name={icon} />}
      <span className="row-label">{label}</span>
      {loading ? <Spinner /> : <Icon name="chevron" className="chevron" />}
    </button>
  );
}

function ToggleRow({ label, checked, onChange, disabled = false }) {
  return (
    <label className="toggle-row">
      <span className="row-label">{label}</span>
      <input type="checkbox" checked={checked} disabled={disabled} onChange={(e) => { haptic('selection'); onChange(e.target.checked); }} />
      <span className="toggle" aria-hidden="true" />
    </label>
  );
}

function InputRow({ label, value, onChange, placeholder, hint }) {
  return (
    <div className="row input-row">
      <div className="row-main">
        <span className="row-label">{label}</span>
        <input className="inline-input" value={value} onChange={(e) => onChange(e.target.value)} placeholder={placeholder} inputMode="text" />
      </div>
      {hint && <span className="row-caption-block">{hint}</span>}
    </div>
  );
}

function SelectRow({ label, value, onChange, children }) {
  return (
    <label className="row select-row">
      <span className="row-label">{label}</span>
      <select className="inline-select" value={value} onChange={(e) => { haptic('selection'); onChange(e.target.value); }}>
        {children}
      </select>
    </label>
  );
}

function DayScheduleRow({ label, subtitle, enabled, onToggle, onConfigure }) {
  return (
    <div className="row">
      <div className="row-main">
        <span className="row-label">{label}</span>
        {subtitle && <span className="row-caption">{subtitle}</span>}
      </div>
      {enabled && (
        <button className="row-config-btn" type="button" onClick={onConfigure} aria-label="configurar">
          <Icon name="settings" />
        </button>
      )}
      <label className="day-toggle-wrap">
        <input type="checkbox" checked={enabled} onChange={(e) => { haptic('selection'); onToggle(e.target.checked); }} />
        <span className="toggle" aria-hidden="true" />
      </label>
    </div>
  );
}

function CommandRow({ command, onCancel, loading, copy }) {
  const cancellable = ['pending', 'retrying'].includes(command.status);
  const tone = command.status === 'failed' ? 'err' : command.status === 'executed' ? 'ok' : 'warn';
  const friendlyStatus = copy.commandStatusLabels[command.status] || command.status;
  const friendlyType = copy.commandTypeLabels[command.command_type] || command.command_type;
  const parts = [
    command.created_at ? new Date(command.created_at).toLocaleString(copy.locale) : null,
    command.last_error || null,
  ].filter(Boolean);
  return (
    <div className="command-row">
      <div className="row-main">
        <span className="row-label">{friendlyType}</span>
        <span className="row-caption">{parts.join(' · ')}</span>
      </div>
      <Badge tone={tone}>{friendlyStatus}</Badge>
      {cancellable && (
        <button className="icon-btn" type="button" onClick={() => onCancel(command)} disabled={loading} aria-label={copy.cancelCommand}>
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
  return <div className="gate"><div className="gate-inner">{children}</div></div>;
}

function LoadingGate() {
  return <GateScreen><Spinner /></GateScreen>;
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

  const [authState, setAuthState] = useState('loading');
  const [me, setMe] = useState(null);
  const [sysStatus, setSysStatus] = useState(null);
  const [overview, setOverview] = useState(null);
  const [commands, setCommands] = useState([]);

  // Settings state: current (edited) and saved (last confirmed from server)
  const [settings, setSettings] = useState(DEFAULT_SETTINGS);
  const [savedSettings, setSavedSettings] = useState(DEFAULT_SETTINGS);
  const [timesInput, setTimesInput] = useState(DEFAULT_SETTINGS.daily_post_times.join(', '));

  const [result, setResult] = useState(null);
  const [settingsResult, setSettingsResult] = useState(null);
  const [cardCode, setCardCode] = useState('');
  const [cardQuery, setCardQuery] = useState('');
  const [cardResults, setCardResults] = useState([]);
  const [targetChatId, setTargetChatId] = useState('');
  const [activeTab, setActiveTab] = useState('home');
  const [activeDayCode, setActiveDayCode] = useState(null);
  const [packs, setPacks] = useState([]);
  const [packsLoading, setPacksLoading] = useState(false);
  const [packsError, setPacksError] = useState(false);

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
  const settingsDirty = !settingsEqual(settings, savedSettings);

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

    // SettingsButton in Telegram header → jump to settings tab
    try {
      const sb = app.SettingsButton;
      if (sb) {
        sb.show?.();
        sb.onClick?.(() => setActiveTab('settings'));
      }
    } catch {}

    return () => {
      app.offEvent?.('themeChanged', applyColors);
      app.offEvent?.('viewportChanged', onViewportChanged);
    };
  }, []);

  // ── MainButton: shows "Save" when settings are dirty ───────────────────────
  useEffect(() => {
    const app = tg();
    const btn = app?.MainButton;
    if (!btn) return;

    if (activeTab === 'settings' && settingsDirty && !savingSettings) {
      btn.setText(copy.saveSettings);
      btn.show?.();
      const handler = () => saveSettings();
      btn.onClick?.(handler);
      return () => { btn.offClick?.(handler); btn.hide?.(); };
    } else {
      btn.hide?.();
    }
  }, [activeTab, settingsDirty, savingSettings, copy.saveSettings]);

  // ── BackButton ──────────────────────────────────────────────────────────────
  const PARENT_TAB = { day_detail: 'settings', language: 'home' };
  useEffect(() => {
    const btn = tg()?.BackButton;
    if (!btn) return;
    const goBack = () => setActiveTab(PARENT_TAB[activeTab] || 'home');
    if (activeTab === 'home') {
      btn.hide?.();
    } else {
      btn.show?.();
      btn.onClick?.(goBack);
    }
    return () => btn.offClick?.(goBack);
  }, [activeTab]);

  // ── Load packs when entering day_detail tab ─────────────────────────────────
  useEffect(() => {
    if (activeTab === 'day_detail' && packs.length === 0 && !packsLoading) {
      setPacksLoading(true);
      setPacksError(false);
      apiFetch('/packs').then(({ ok, json }) => {
        if (ok && Array.isArray(json.packs)) setPacks(json.packs);
        else setPacksError(true);
      }).catch(() => setPacksError(true)).finally(() => setPacksLoading(false));
    }
  }, [activeTab]);

  // ── CloudStorage language sync ──────────────────────────────────────────────
  useEffect(() => { readLangStorage((lang) => setLanguage(lang)); }, []);

  // ── Auth gate ───────────────────────────────────────────────────────────────
  useEffect(() => {
    if (!tg() || !initData()) { setAuthState('no_telegram'); return; }
    if (!apiConfigured) { setAuthState('ready'); return; }

    apiFetch('/me').then(({ ok, json }) => {
      if (ok && json?.admin === true) {
        setMe(json);
        setAuthState('ready');
        fetchStatus();
        fetchOverview();
        fetchCommands();
      } else {
        const msg = copy.errors.unauthorized?.[0] || 'Access denied.';
        const app = tg();
        if (app?.showAlert) app.showAlert(msg, () => app.close?.());
        else app?.close?.();
        setAuthState('unauthorized');
      }
    }).catch(() => setAuthState('ready'));
  }, []);

  // ── Auto-load settings when entering settings tab ───────────────────────────
  useEffect(() => {
    if (activeTab === 'settings') fetchSettings();
  }, [activeTab]);

  // ── API calls ───────────────────────────────────────────────────────────────

  async function fetchStatus() {
    if (!apiConfigured) return;
    setLoadingStatus(true);
    try { const { json } = await apiFetch('/status'); setSysStatus(json); }
    catch { setSysStatus({ ok: false }); }
    finally { setLoadingStatus(false); }
  }

  async function fetchOverview() {
    if (!apiConfigured) return;
    setLoadingOverview(true);
    try {
      const { ok, status, json } = await apiFetch('/overview');
      if (ok) { setOverview(json); if (json.settings) applySettings(json.settings); }
      else setResult({ ok: false, ...resolveError(json.error, `HTTP ${status}`, copy, json) });
    } catch { setResult({ ok: false, friendly: copy.networkError, detail: '' }); }
    finally { setLoadingOverview(false); }
  }

  async function fetchCommands() {
    if (!apiConfigured) return;
    setLoadingCommands(true);
    try {
      const { ok, status, json } = await apiFetch('/commands');
      if (ok) setCommands(json.commands || []);
      else setResult({ ok: false, ...resolveError(json.error, `HTTP ${status}`, copy, json) });
    } catch { setResult({ ok: false, friendly: copy.networkError, detail: '' }); }
    finally { setLoadingCommands(false); }
  }

  async function fetchSettings() {
    if (!apiConfigured) return;
    setLoadingSettings(true);
    setSettingsResult(null);
    try {
      const { ok, status, json } = await apiFetch('/settings');
      if (ok) { applySettings(json.settings); }
      else setSettingsResult({ ok: false, ...resolveError(json.error, `HTTP ${status}`, copy, json) });
    } catch { setSettingsResult({ ok: false, friendly: copy.networkError, detail: '' }); }
    finally { setLoadingSettings(false); }
  }

  async function saveSettings() {
    const times = parseTimesInput(timesInput);
    if (!validateTimes(times)) { haptic('notification', 'error'); setSettingsResult({ ok: false, friendly: copy.invalidTime, detail: '' }); return; }
    if (!settings.daily_post_days.length) { haptic('notification', 'error'); setSettingsResult({ ok: false, friendly: copy.selectAtLeastOneDay, detail: '' }); return; }
    if (!settings.timezone.trim()) { haptic('notification', 'error'); setSettingsResult({ ok: false, friendly: copy.timezoneRequired, detail: '' }); return; }

    setSavingSettings(true);
    tg()?.MainButton?.showProgress?.(false);
    try {
      const body = { ...settings, daily_post_times: times, timezone: settings.timezone.trim() };
      const { ok, status, json } = await apiFetch('/settings', {
        method: 'PATCH',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify(body),
      });
      if (!ok) {
        haptic('notification', 'error');
        setSettingsResult({ ok: false, ...resolveError(json.error, `HTTP ${status}`, copy, json) });
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
      tg()?.MainButton?.hideProgress?.();
    }
  }

  async function cancelCommand(command) {
    const confirmed = await tgShowPopup({
      title: copy.cancelCommand,
      message: copy.confirmCancel(command.command_type),
      buttons: [
        { id: 'confirm', type: 'destructive', text: copy.popupConfirm },
        { id: 'cancel', type: 'cancel', text: copy.popupCancel },
      ],
    });
    if (confirmed !== 'confirm') return;

    setCancellingCommand(command.id);
    try {
      const { ok, status, json } = await apiFetch(`/commands/${command.id}`, {
        method: 'PATCH',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ status: 'cancelled' }),
      });
      if (!ok) { haptic('notification', 'error'); setResult({ ok: false, ...resolveError(json.error, `HTTP ${status}`, copy, json) }); }
      else { haptic('notification', 'success'); setResult({ ok: true, friendly: copy.commandCancelled, detail: '' }); fetchCommands(); fetchOverview(); }
    } catch { haptic('notification', 'error'); setResult({ ok: false, friendly: copy.networkError, detail: '' }); }
    finally { setCancellingCommand(null); }
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
        setResult({ ok: false, command_type, ...resolveError(json.error, `HTTP ${status}`, copy, json) });
      } else {
        haptic('notification', 'success');
        setResult({ ok: true, command_type: json.command?.command_type || command_type, friendly: copy.commandQueued, detail: json.command?.id ? `ID: ${json.command.id}` : '' });
        fetchStatus(); fetchCommands(); fetchOverview();
      }
    } catch { haptic('notification', 'error'); setResult({ ok: false, command_type, friendly: copy.networkError, detail: '' }); }
    finally { setLoadingCmd(null); }
  }, [loadingCmd, targetChatId, copy]);

  async function confirmEnqueue(message, command_type, payload = {}) {
    const confirmed = await tgShowPopup({
      message,
      buttons: [
        { id: 'confirm', type: 'default', text: copy.popupConfirm },
        { id: 'cancel', type: 'cancel', text: copy.popupCancel },
      ],
    });
    if (confirmed === 'confirm') enqueue(command_type, payload);
  }

  function applySettings(next) {
    const n = normalizeSettings(next);
    setSettings(n);
    setSavedSettings(n);
    setTimesInput(n.daily_post_times.join(', '));
  }

  function updateSetting(key, value) {
    haptic('selection');
    setSettings((cur) => ({ ...cur, [key]: value }));
  }

  function toggleDay(code) {
    setSettings((cur) => {
      const next = cur.daily_post_days.includes(code)
        ? cur.daily_post_days.filter((d) => d !== code)
        : [...cur.daily_post_days, code];
      return { ...cur, daily_post_days: next.length ? next : cur.daily_post_days };
    });
    haptic('selection');
  }

  function toggleCardType(code) {
    setSettings((cur) => {
      const next = cur.allowed_card_types.includes(code)
        ? cur.allowed_card_types.filter((t) => t !== code)
        : [...cur.allowed_card_types, code];
      return { ...cur, allowed_card_types: next.length ? next : cur.allowed_card_types };
    });
    haptic('selection');
  }

  // ── Day config helpers ──────────────────────────────────────────────────────

  function getDayConfig(dayCode) {
    return settings.day_config[dayCode] || { packs: [], types: [] };
  }

  function isCycleSelectedForDay(dayCode, cyclePos) {
    const { packs: dp } = getDayConfig(dayCode);
    const cyclePacks = packs.filter((p) => p.cycle_position === cyclePos).map((p) => p.code);
    if (!cyclePacks.length) return false;
    return dp.length === 0 || cyclePacks.every((pc) => dp.includes(pc));
  }

  function isTypeSelectedForDay(dayCode, typeCode) {
    const { types: dt } = getDayConfig(dayCode);
    return dt.length === 0 || dt.includes(typeCode);
  }

  function toggleCycleForDay(dayCode, cyclePos) {
    haptic('selection');
    const cyclePacks = packs.filter((p) => p.cycle_position === cyclePos).map((p) => p.code);
    setSettings((cur) => {
      const cfg = cur.day_config[dayCode] || { packs: [], types: [] };
      const dp = cfg.packs;
      const allSelected = dp.length === 0 || cyclePacks.every((pc) => dp.includes(pc));
      let nextPacks;
      if (allSelected) {
        const base = dp.length === 0 ? packs.map((p) => p.code) : dp;
        nextPacks = base.filter((pc) => !cyclePacks.includes(pc));
      } else {
        const base = dp.length === 0 ? packs.map((p) => p.code) : dp;
        nextPacks = [...new Set([...base, ...cyclePacks])];
        if (nextPacks.length === packs.length) nextPacks = [];
      }
      return { ...cur, day_config: { ...cur.day_config, [dayCode]: { ...cfg, packs: nextPacks } } };
    });
  }

  function toggleTypeForDay(dayCode, typeCode) {
    haptic('selection');
    setSettings((cur) => {
      const cfg = cur.day_config[dayCode] || { packs: [], types: [] };
      const dt = cfg.types;
      let nextTypes;
      if (dt.length === 0) {
        // All selected → exclude this one
        nextTypes = ALL_CARD_TYPES.map((t) => t.code).filter((c) => c !== typeCode);
      } else if (dt.includes(typeCode)) {
        nextTypes = dt.filter((c) => c !== typeCode);
        if (nextTypes.length === ALL_CARD_TYPES.length) nextTypes = [];
      } else {
        nextTypes = [...dt, typeCode];
        if (nextTypes.length === ALL_CARD_TYPES.length) nextTypes = [];
      }
      return { ...cur, day_config: { ...cur.day_config, [dayCode]: { ...cfg, types: nextTypes } } };
    });
  }

  function dayConfigSummary(dayCode, copy) {
    const { packs: dp, types: dt } = getDayConfig(dayCode);
    const cycles = deriveCycles(packs);
    const activeCycles = dp.length === 0 ? 0 : cycles.filter((c) =>
      packs.filter((p) => p.cycle_position === c.position).some((p) => dp.includes(p.code))
    ).length;
    const parts = [];
    if (dp.length > 0 && activeCycles > 0) parts.push(copy.cyclesSelected(activeCycles));
    if (dt.length > 0) parts.push(copy.typesSelected(dt.length));
    return parts.length ? parts.join(' · ') : copy.noCycleConfig;
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
      if (ok) setCardResults(json.cards || []);
      else setResult({ ok: false, ...resolveError(json.error, `HTTP ${status}`, copy, json) });
    } catch { setResult({ ok: false, friendly: copy.networkError, detail: '' }); }
    finally { setSearchingCards(false); }
  }

  // ── Derived ─────────────────────────────────────────────────────────────────

  const workerValue = loadingStatus ? '…' : sysStatus?.ok ? copy.online : copy.offline;
  const workerTone = sysStatus?.ok ? 'ok' : 'err';
  const cardsValue = loadingOverview ? '…' : (overview?.counts?.cards ?? sysStatus?.total_cards ?? '-');
  const queueValue = loadingOverview ? '…' : (overview?.counts?.pending_commands ?? 0);
  const targetChats = overview?.target_chats?.filter((c) => c.enabled !== false) || [];

  // ── Auth gate ───────────────────────────────────────────────────────────────

  if (authState === 'loading' || authState === 'unauthorized') return <LoadingGate />;
  if (authState === 'no_telegram') return <NoTelegramGate copy={copy} />;

  // ── Render ──────────────────────────────────────────────────────────────────

  return (
    <div className="app">

      {/* Header */}
      <header className="app-header">
        <div className="avatar">
          {getBotPhotoUrl()
            ? <img src={getBotPhotoUrl()} alt="Wendy Adams" className="avatar-img" />
            : <Icon name="bot" />}
        </div>
        <div className="header-title">Wendy Adams</div>
        <div className="header-subtitle">{copy.subtitle}</div>
        <div className="header-description">{copy.botDescription}</div>
      </header>

      {!apiConfigured && <Notice tone="err">{copy.workerNotConfigured}</Notice>}

      {/* ── HOME ── */}
      {activeTab === 'home' && (
        <>
          <Section title={copy.overviewTitle}>
            <Row icon="server" label={copy.worker} value={workerValue} badgeTone={workerTone} />
            <Row icon="cards" label={copy.cards} value={`${cardsValue} / ${overview?.counts?.posted_cards ?? '-'}`} />
            <Row icon="queue" label={copy.queue} value={queueValue} badgeTone={queueValue > 0 ? 'warn' : ''} />
          </Section>

          <Section title={copy.actionsTitle}>
            <MenuRow icon="send"     label={copy.postCard}    onClick={() => setActiveTab('post')} />
            <MenuRow icon="settings" label={copy.settings}    onClick={() => setActiveTab('settings')} />
            <MenuRow icon="wrench"   label={copy.maintenance} onClick={() => setActiveTab('maintenance')} />
            <MenuRow icon="clock"    label={copy.historyTab}  onClick={() => setActiveTab('history')} />
            <MenuRow icon="queue"    label={copy.queue}       value={queueValue > 0 ? String(queueValue) : undefined} onClick={() => setActiveTab('queue')} />
            <MenuRow icon="server"   label={copy.health}      value={workerValue} onClick={() => setActiveTab('health')} />
            <MenuRow icon="language" label={copy.language}    value={copy.langName} onClick={() => setActiveTab('language')} />
          </Section>
        </>
      )}

      {/* ── POST CARD ── */}
      {activeTab === 'post' && (
        <>
          <Section title={copy.postCard}>
            <div className="row search-row">
              <Icon name="search" />
              <input
                className="search-input"
                type="search"
                value={cardQuery}
                onChange={handleSearchChange}
                placeholder={copy.searchPlaceholder}
                inputMode="text"
              />
              {searchingCards && <Spinner />}
            </div>

            {cardResults.length > 0 && cardResults.map((card) => (
              <CardResult
                key={card.code}
                card={card}
                selected={cardCode === card.code}
                onSelect={(sel) => {
                  setCardCode(sel.code);
                  setCardQuery(`${sel.code} – ${sel.name || sel.real_name}`);
                  setCardResults([]);
                  haptic('impact', 'light');
                }}
              />
            ))}
          </Section>

          {targetChats.length > 0 && (
            <Section title={copy.destination}>
              <SelectRow label={copy.destination} value={targetChatId} onChange={setTargetChatId}>
                <option value="">{copy.defaultChat}</option>
                {targetChats.map((chat) => (
                  <option key={chat.chat_id} value={chat.chat_id}>{chat.title || chat.chat_id}</option>
                ))}
              </SelectRow>
            </Section>
          )}

          <Section footer={!cardCode ? copy.automaticChoice : undefined}>
            <MenuRow
              icon="send"
              label={copy.postNow}
              value={cardCode || undefined}
              loading={loadingCmd === 'post_now'}
              disabled={actionsDisabled}
              onClick={() => confirmEnqueue(copy.confirmPostNow(cardCode), 'post_now', cardCode ? { card_code: cardCode } : {})}
            />
            <MenuRow
              icon="repeat"
              label={copy.repostCard}
              value={cardCode || undefined}
              loading={loadingCmd === 'repost_card'}
              disabled={actionsDisabled || !cardCode}
              onClick={() => confirmEnqueue(copy.confirmRepost(cardCode), 'repost_card', { card_code: cardCode })}
            />
            <MenuRow
              icon="skip"
              label={copy.skipCard}
              value={cardCode || undefined}
              loading={loadingCmd === 'skip_card'}
              disabled={actionsDisabled || !cardCode}
              onClick={() => confirmEnqueue(copy.confirmSkip(cardCode), 'skip_card', { card_code: cardCode })}
            />
          </Section>

          {result && (
            <Section>
              <Row icon={result.ok ? 'result' : 'info'} label={result.ok ? copy.success : copy.error} value={result.ok ? 'ok' : 'err'} badgeTone={result.ok ? 'ok' : 'err'} caption={result.friendly} />
            </Section>
          )}
        </>
      )}

      {/* ── SETTINGS ── */}
      {activeTab === 'settings' && (
        <>
          {/* Daily post */}
          <Section title={copy.dailyPost}>
            <ToggleRow label={copy.automaticPosting} checked={settings.daily_post_enabled} onChange={(v) => updateSetting('daily_post_enabled', v)} />
            {settings.daily_post_enabled && (
              <>
                <div className="row form-block">
                  <div className="row-main">
                    <span className="row-label">{copy.postTimes}</span>
                    <input className="inline-input" value={timesInput} onChange={(e) => setTimesInput(e.target.value)} placeholder="08:00, 21:30" inputMode="text" />
                  </div>
                </div>
                {/* days are now configured in the weekly schedule section below */}
                <SelectRow label={copy.timezoneLabel} value={settings.timezone} onChange={(v) => updateSetting('timezone', v)}>
                  {TIMEZONES.map((tz) => (
                    <option key={tz.value} value={tz.value}>{tz.label}</option>
                  ))}
                </SelectRow>
              </>
            )}
          </Section>

          {/* Card filter */}
          <Section title={copy.cardFilter}>
            <ToggleRow label={copy.includeSpoilers} checked={settings.include_spoilers} onChange={(v) => updateSetting('include_spoilers', v)} />
          </Section>

          {/* Weekly schedule */}
          <Section title={copy.weeklySchedule} footer={copy.weeklyScheduleCaption}>
            {WEEKDAYS.map((day) => {
              const lang = language === 'pt' ? 'pt' : 'en';
              const enabled = settings.daily_post_days.includes(day.code);
              return (
                <DayScheduleRow
                  key={day.code}
                  label={day[lang]}
                  subtitle={enabled ? dayConfigSummary(day.code, copy) : undefined}
                  enabled={enabled}
                  onToggle={(v) => {
                    setSettings((cur) => {
                      const next = v
                        ? [...cur.daily_post_days, day.code]
                        : cur.daily_post_days.filter((d) => d !== day.code);
                      return { ...cur, daily_post_days: next.length ? next : cur.daily_post_days };
                    });
                    haptic('selection');
                  }}
                  onConfigure={() => { setActiveDayCode(day.code); setActiveTab('day_detail'); }}
                />
              );
            })}
          </Section>

          {/* AI */}
          <Section title={copy.aiSection}>
            <ToggleRow label={copy.aiEnabled} checked={settings.ai_enabled} onChange={(v) => updateSetting('ai_enabled', v)} />
            {settings.ai_enabled && (
              <SelectRow label={copy.aiLanguage} value={settings.ai_language} onChange={(v) => updateSetting('ai_language', v)}>
                <option value="pt-BR">{copy.aiLanguagePt}</option>
                <option value="en-US">{copy.aiLanguageEn}</option>
              </SelectRow>
            )}
          </Section>

          {settingsResult && (
            <Section>
              <Row icon={settingsResult.ok ? 'result' : 'info'} label={settingsResult.ok ? copy.success : copy.error} value={settingsResult.ok ? 'ok' : 'err'} badgeTone={settingsResult.ok ? 'ok' : 'err'} caption={settingsResult.friendly} />
            </Section>
          )}

          {loadingSettings && (
            <Section><div className="row"><Spinner /><span className="row-label" style={{ marginLeft: 8 }}>{copy.checking}</span></div></Section>
          )}
        </>
      )}

      {/* ── MAINTENANCE ── */}
      {activeTab === 'maintenance' && (
        <>
          <Section title={copy.maintenance} footer={copy.syncCaption}>
            <MenuRow icon="sync" label={copy.syncArkhamDB} loading={loadingCmd === 'sync_arkhamdb'} disabled={actionsDisabled} onClick={() => confirmEnqueue(copy.confirmSync, 'sync_arkhamdb', { sync_faq: false })} />
            {(() => {
              const syncDate = overview?.last_sync || sysStatus?.last_sync;
              const label = syncDate
                ? `${copy.lastSyncAt}: ${new Date(syncDate).toLocaleString(copy.locale)}`
                : copy.neverSynced;
              return <Row icon="clock" label={label} />;
            })()}
          </Section>

          <Section footer={copy.resetCaption}>
            <DangerRow icon="reset" label={copy.resetCycle} loading={loadingCmd === 'reset_cycle'} disabled={actionsDisabled} onClick={() => confirmEnqueue(copy.confirmReset, 'reset_cycle')} />
          </Section>

          <Section footer={copy.clearQueueCaption}>
            <DangerRow icon="trash" label={copy.clearQueue} loading={loadingCmd === 'clear_queue'} disabled={actionsDisabled} onClick={() => confirmEnqueue(copy.confirmClear, 'clear_queue')} />
          </Section>

          {result && (
            <Section>
              <Row icon={result.ok ? 'result' : 'info'} label={result.ok ? copy.success : copy.error} value={result.ok ? 'ok' : 'err'} badgeTone={result.ok ? 'ok' : 'err'} caption={result.friendly} />
            </Section>
          )}
        </>
      )}

      {/* ── QUEUE ── */}
      {activeTab === 'queue' && (
        <>
          <Section title={copy.commandQueue}>
            <MenuRow icon="refresh" label={copy.refreshQueue} loading={loadingCommands} disabled={!apiConfigured} onClick={fetchCommands} />
            {commands.length === 0 && !loadingCommands && <Row icon="queue" label={copy.noRecentCommands} />}
            {commands.map((cmd) => (
              <CommandRow key={cmd.id} command={cmd} onCancel={cancelCommand} loading={cancellingCommand === cmd.id} copy={copy} />
            ))}
          </Section>
        </>
      )}

      {/* ── DAY DETAIL ── */}
      {activeTab === 'day_detail' && activeDayCode && (() => {
        const lang = language === 'pt' ? 'pt' : 'en';
        const dayLabel = WEEKDAYS.find((d) => d.code === activeDayCode)?.[lang] || activeDayCode;
        const cycles = deriveCycles(packs);
        return (
          <>
            <header className="section-header-standalone">{dayLabel}</header>

            {/* Cycles */}
            <Section title={copy.cyclesToday}>
              {packsLoading && <div className="row"><Spinner /><span className="row-label" style={{ marginLeft: 8 }}>{copy.loadingPacks}</span></div>}
              {packsError && !packsLoading && <Row icon="info" label={copy.packsFailed} />}
              {!packsLoading && !packsError && cycles.map((cycle) => (
                <ToggleRow
                  key={cycle.position}
                  label={cycle.name}
                  checked={isCycleSelectedForDay(activeDayCode, cycle.position)}
                  onChange={() => toggleCycleForDay(activeDayCode, cycle.position)}
                />
              ))}
            </Section>

            {/* Card types */}
            <Section title={copy.typesToday}>
              {ALL_CARD_TYPES.map((type) => (
                <ToggleRow
                  key={type.code}
                  label={type[lang]}
                  checked={isTypeSelectedForDay(activeDayCode, type.code)}
                  onChange={() => toggleTypeForDay(activeDayCode, type.code)}
                />
              ))}
            </Section>
          </>
        );
      })()}

      {/* ── HISTORY ── */}
      {activeTab === 'history' && (
        <>
          <Section title={copy.historyTitle} footer={`${copy.postedCardsCount}: ${overview?.counts?.posted_cards ?? '—'}`}>
            {loadingOverview && <div className="row"><Spinner /><span className="row-label" style={{ marginLeft: 8 }}>{copy.checking}</span></div>}
            {!loadingOverview && (!overview?.recent_posts || overview.recent_posts.length === 0) && (
              <Row icon="cards" label={copy.noHistory} />
            )}
            {(overview?.recent_posts || []).map((post) => {
              const friendlyStatus = copy.postStatusLabels[post.status] || post.status;
              const tone = post.status?.startsWith('POSTED') ? 'ok' : post.status?.startsWith('FAIL') ? 'err' : '';
              return (
                <div key={post.id} className="row">
                  <div className="row-main">
                    <span className="row-label">{post.card_name || post.card_code}</span>
                    <span className="row-caption">
                      {[post.card_code, post.created_at ? new Date(post.created_at).toLocaleString(copy.locale) : null].filter(Boolean).join(' · ')}
                    </span>
                  </div>
                  <Badge tone={tone}>{friendlyStatus}</Badge>
                </div>
              );
            })}
          </Section>
          <Section>
            <MenuRow icon="refresh" label={copy.refreshQueue} loading={loadingOverview} disabled={!apiConfigured} onClick={fetchOverview} />
          </Section>
        </>
      )}

      {/* ── LANGUAGE ── */}
      {activeTab === 'language' && (
        <Section title={copy.chooseLanguage}>
          <ToggleRow
            label={copy.portuguese}
            checked={language === 'pt'}
            onChange={(checked) => { if (checked) { setLanguage('pt'); writeLangStorage('pt'); haptic('selection'); } }}
          />
          <ToggleRow
            label={copy.englishLang}
            checked={language === 'en'}
            onChange={(checked) => { if (checked) { setLanguage('en'); writeLangStorage('en'); haptic('selection'); } }}
          />
        </Section>
      )}

      {/* ── HEALTH ── */}
      {activeTab === 'health' && (
        <>
          <Section title={copy.summary}>
            <Row icon="server" label={copy.worker} value={workerValue} badgeTone={workerTone} />
            <Row icon="shield" label={copy.access} value={copy.roleLabels[me?.role] || me?.role || copy.admin} badgeTone="ok" />
            <Row icon="cards"  label={copy.cards}  value={cardsValue} />
            <Row icon="packs"  label={copy.packs}  value={loadingOverview ? '…' : (overview?.counts?.packs ?? sysStatus?.total_packs ?? '-')} />
            <Row icon="clock"  label={copy.lastSync} value={(overview?.last_sync || sysStatus?.last_sync) ? new Date(overview?.last_sync || sysStatus?.last_sync).toLocaleString(copy.locale) : '-'} mono />
            <Row icon="queue"  label={copy.queue}  value={queueValue} badgeTone={queueValue > 0 ? 'warn' : ''} />
          </Section>

          <Section title={copy.account}>
            <Row icon="plug"   label={copy.telegramWebApp} value={tg() ? copy.yes : copy.no} badgeTone={tg() ? 'ok' : 'err'} />
            <Row icon="key"    label={copy.initDataLabel}  value={initData() ? copy.yes : copy.no} badgeTone={initData() ? 'ok' : 'err'} />
            <Row icon="shield" label={copy.admin}          value={copy.roleLabels[me?.role] || me?.role || '-'} badgeTone="ok" caption={me?.admin_source ? `${copy.adminSourcePrefix}: ${me.admin_source}` : undefined} />
          </Section>

          <Section title={copy.system}>
            <MenuRow icon="refresh" label={copy.recheckAuth} loading={loadingStatus || loadingOverview} disabled={!apiConfigured} onClick={() => { fetchStatus(); fetchOverview(); }} />
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

    </div>
  );
}

createRoot(document.getElementById('root')).render(<App />);
