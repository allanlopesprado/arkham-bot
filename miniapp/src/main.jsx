import React, { useCallback, useEffect, useState } from 'react';
import { createRoot } from 'react-dom/client';
import './style.css';

function getTelegramWebApp() { return window.Telegram?.WebApp || null; }
function getTelegramInitData() { return getTelegramWebApp()?.initData || ''; }
function getTelegramUserUnsafe() { return getTelegramWebApp()?.initDataUnsafe?.user || null; }

function getApiBase() {
  const raw = import.meta.env.VITE_COMMANDS_API_URL || '';
  if (!raw) return '';
  try { return new URL(raw).origin; } catch { return raw; }
}

function buildApiUrl(path) {
  const base = getApiBase();
  return base ? `${base.replace(/\/$/, '')}${path}` : '';
}

function haptic(type, value) {
  try {
    const hf = getTelegramWebApp()?.HapticFeedback;
    if (!hf) return;
    if (type === 'notification') hf.notificationOccurred(value);
    else if (type === 'impact') hf.impactOccurred(value);
  } catch {}
}

const WEEKDAYS = [
  { code: 'mon', pt: 'Seg', en: 'Mon' },
  { code: 'tue', pt: 'Ter', en: 'Tue' },
  { code: 'wed', pt: 'Qua', en: 'Wed' },
  { code: 'thu', pt: 'Qui', en: 'Thu' },
  { code: 'fri', pt: 'Sex', en: 'Fri' },
  { code: 'sat', pt: 'Sab', en: 'Sat' },
  { code: 'sun', pt: 'Dom', en: 'Sun' },
];

const LANGUAGE_STORAGE_KEY = 'arkham-bot-miniapp-language';

const I18N = {
  pt: {
    locale: 'pt-BR',
    languageName: 'Portugues',
    languageCaption: 'Alternar para English',
    appSubtitle: 'Console Admin',
    settings: 'Configuracoes',
    outsideTelegram: 'Abra pelo Telegram para autenticar.',
    workerNotConfigured: 'Worker nao configurado.',
    defineCommandsApi: 'Defina VITE_COMMANDS_API_URL.',
    postCard: 'Postar carta',
    postCardCaption: 'Buscar carta, escolher destino e publicar',
    controls: 'Controles',
    controlsCaption: 'Pausar, sincronizar, resetar ciclo e limpar fila',
    schedule: 'Agenda',
    queue: 'Fila',
    queueCaption: 'Comandos recentes e cancelamento',
    health: 'Saude',
    healthCaption: 'Worker, acesso, cards e diagnostico',
    language: 'Idioma',
    searchByCodeOrName: 'Buscar por codigo ou nome',
    searchPlaceholder: '01001 ou Shrivelling',
    search: 'Buscar',
    selectedCard: 'Carta selecionada',
    selectedCardHint: 'Postar agora pode usar carta vazia para escolha automatica. Repostar e pular exigem codigo.',
    selectedCardPlaceholder: 'Codigo da carta, ex: 01001',
    destination: 'Destino',
    defaultChat: 'Chat padrao do bot',
    postNow: 'Postar agora',
    automaticChoice: 'Escolha automatica',
    card: 'Carta',
    repostCard: 'Repostar carta',
    skipCard: 'Pular carta',
    informCardCode: 'Informe o codigo da carta',
    modeSettings: 'Modos de operacao',
    dailyPost: 'Postagem diaria',
    automaticPosting: 'Publicacao automatica',
    automaticPostingCaption: 'Liga ou pausa a carta diaria',
    postTimes: 'Horarios de postagem',
    postTimesCaption: 'Use horarios de 24 horas separados por virgula',
    postDays: 'Dias da semana',
    postDaysCaption: 'Escolha quando a rotina pode publicar',
    timezoneLabel: 'Fuso horario',
    timezoneCaption: 'Padrao usado para calcular os horarios',
    dailyPostFooter: 'Ativa ou pausa a rotina automatica de carta diaria.',
    syncArkhamDB: 'Sincronizar ArkhamDB',
    syncCaption: 'Atualiza cartas e pacotes',
    resetCycle: 'Resetar ciclo',
    resetCaption: 'Permite repetir cartas ja usadas',
    clearQueue: 'Limpar fila',
    clearQueueCaption: 'Cancela comandos pendentes',
    scheduleTitle: 'Agenda de postagem',
    timesHint: 'Exemplo: 09:00, 21:30',
    reloadSettings: 'Recarregar configuracoes',
    saveSettings: 'Salvar configuracoes',
    settingsResult: 'Configuracoes',
    result: 'Resultado',
    success: 'Sucesso',
    error: 'Erro',
    details: 'Detalhes',
    commandQueue: 'Fila de comandos',
    refreshQueue: 'Atualizar fila',
    noRecentCommands: 'Nenhum comando recente',
    cancelCommand: 'Cancelar comando',
    summary: 'Resumo',
    worker: 'Worker',
    access: 'Acesso',
    cards: 'Cards',
    account: 'Conta',
    telegramWebApp: 'Telegram WebApp',
    initData: 'initData',
    admin: 'Admin',
    recheckAuth: 'Reverificar autenticacao',
    system: 'Sistema',
    packs: 'Packs',
    lastSync: 'Ultimo sync',
    refreshStatus: 'Atualizar status',
    diagnostic: 'Diagnostico',
    showDetails: 'Mostrar detalhes',
    apiConfigured: 'API configurada',
    apiBase: 'Endpoint base',
    userUnsafe: 'Usuario unsafe',
    initDataPresent: 'initData presente',
    initDataLength: 'initData length',
    role: 'Role',
    adminSource: 'Admin source',
    yes: 'sim',
    no: 'nao',
    checking: 'verificando',
    noApi: 'sem API',
    noNetwork: 'sem rede',
    pending: 'pendente',
    notConfigured: 'nao configurado',
    online: 'online',
    offline: 'offline',
    commandQueued: 'Comando enfileirado.',
    commandCancelled: 'Comando cancelado.',
    networkOverview: 'Falha de rede ao carregar gestao.',
    networkQueue: 'Falha de rede ao carregar fila.',
    networkCards: 'Falha de rede ao buscar cartas.',
    networkCancel: 'Falha de rede ao cancelar comando.',
    networkSettingsLoad: 'Falha de rede ao carregar configuracoes.',
    networkSettingsSave: 'Falha de rede ao salvar configuracoes.',
    networkWorker: 'Falha de rede ao chamar o Worker.',
    invalidTime: 'Horarios devem usar HH:MM.',
    selectAtLeastOneDay: 'Selecione pelo menos um dia.',
    timezoneRequired: 'Timezone obrigatorio.',
    settingsSaved: 'Configuracoes salvas.',
    unknownError: 'Erro desconhecido.',
    errors: {
      invalid_telegram_init_data: ['Abra pelo Telegram para autenticar.', 'initData invalido.'],
      unauthorized: ['Usuario sem permissao administrativa.', 'O Telegram ID nao esta cadastrado como admin.'],
      not_found: ['Endpoint nao encontrado.', 'Verifique VITE_COMMANDS_API_URL.'],
      origin_not_allowed: ['Origem nao autorizada.', 'Verifique ALLOWED_ORIGINS no Worker.'],
      bot_command_insert_failed: ['Falha ao criar comando.', 'Verifique Worker e Supabase.'],
      command_type_required: ['Tipo de comando nao informado.', 'command_type_required'],
      unsupported_command_type: ['Comando nao suportado.', 'unsupported_command_type'],
      method_not_allowed: ['Metodo HTTP nao permitido.', 'method_not_allowed'],
      settings_fetch_failed: ['Falha ao carregar configuracoes.', 'settings_fetch_failed'],
      settings_upsert_failed: ['Falha ao salvar configuracoes.', 'settings_upsert_failed'],
      invalid_setting_value: ['Configuracao invalida.', 'invalid_setting_value'],
      unsupported_setting: ['Configuracao nao suportada.', 'unsupported_setting'],
      settings_required: ['Nenhuma configuracao para salvar.', 'settings_required'],
      overview_fetch_failed: ['Falha ao carregar gestao.', 'overview_fetch_failed'],
      commands_fetch_failed: ['Falha ao carregar fila.', 'commands_fetch_failed'],
      cards_search_failed: ['Falha ao buscar cartas.', 'cards_search_failed'],
      command_cancel_failed: ['Falha ao cancelar comando.', 'command_cancel_failed'],
      command_not_cancellable: ['Comando nao pode mais ser cancelado.', 'command_not_cancellable'],
    },
  },
  en: {
    locale: 'en-US',
    languageName: 'English',
    languageCaption: 'Switch to Portugues',
    appSubtitle: 'Admin Console',
    settings: 'Settings',
    outsideTelegram: 'Open from Telegram to authenticate.',
    workerNotConfigured: 'Worker is not configured.',
    defineCommandsApi: 'Set VITE_COMMANDS_API_URL.',
    postCard: 'Post Card',
    postCardCaption: 'Search a card, choose target, and publish',
    controls: 'Controls',
    controlsCaption: 'Pause, sync, reset cycle, and clear queue',
    schedule: 'Schedule',
    queue: 'Queue',
    queueCaption: 'Recent commands and cancellation',
    health: 'Health',
    healthCaption: 'Worker, access, cards, and diagnostics',
    language: 'Language',
    searchByCodeOrName: 'Search by code or name',
    searchPlaceholder: '01001 or Shrivelling',
    search: 'Search',
    selectedCard: 'Selected card',
    selectedCardHint: 'Post now can use an empty card for automatic choice. Repost and skip require a code.',
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
    postTimesCaption: 'Use 24-hour times separated by commas',
    postDays: 'Weekdays',
    postDaysCaption: 'Choose when the routine may publish',
    timezoneLabel: 'Timezone',
    timezoneCaption: 'Default timezone used to calculate posting times',
    dailyPostFooter: 'Enables or pauses the automatic daily card routine.',
    syncArkhamDB: 'Sync ArkhamDB',
    syncCaption: 'Updates cards and packs',
    resetCycle: 'Reset cycle',
    resetCaption: 'Allows cards already used to repeat',
    clearQueue: 'Clear queue',
    clearQueueCaption: 'Cancels pending commands',
    scheduleTitle: 'Posting schedule',
    timesHint: 'Example: 09:00, 21:30',
    reloadSettings: 'Reload settings',
    saveSettings: 'Save settings',
    settingsResult: 'Settings',
    result: 'Result',
    success: 'Success',
    error: 'Error',
    details: 'Details',
    commandQueue: 'Command queue',
    refreshQueue: 'Refresh queue',
    noRecentCommands: 'No recent commands',
    cancelCommand: 'Cancel command',
    summary: 'Summary',
    worker: 'Worker',
    access: 'Access',
    cards: 'Cards',
    account: 'Account',
    telegramWebApp: 'Telegram WebApp',
    initData: 'initData',
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
    checking: 'checking',
    noApi: 'no API',
    noNetwork: 'no network',
    pending: 'pending',
    notConfigured: 'not configured',
    online: 'online',
    offline: 'offline',
    commandQueued: 'Command queued.',
    commandCancelled: 'Command cancelled.',
    networkOverview: 'Network failure while loading management data.',
    networkQueue: 'Network failure while loading queue.',
    networkCards: 'Network failure while searching cards.',
    networkCancel: 'Network failure while cancelling command.',
    networkSettingsLoad: 'Network failure while loading settings.',
    networkSettingsSave: 'Network failure while saving settings.',
    networkWorker: 'Network failure while calling the Worker.',
    invalidTime: 'Times must use HH:MM.',
    selectAtLeastOneDay: 'Select at least one day.',
    timezoneRequired: 'Timezone is required.',
    settingsSaved: 'Settings saved.',
    unknownError: 'Unknown error.',
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

function getInitialLanguage() {
  try {
    const stored = window.localStorage?.getItem(LANGUAGE_STORAGE_KEY);
    if (stored === 'en' || stored === 'pt') return stored;
  } catch {}
  const code = getTelegramUserUnsafe()?.language_code || navigator.language || '';
  return code.toLowerCase().startsWith('en') ? 'en' : 'pt';
}

const DEFAULT_SETTINGS = {
  daily_post_enabled: true,
  daily_post_times: ['08:00'],
  daily_post_days: WEEKDAYS.map((day) => day.code),
  timezone: 'America/Sao_Paulo',
};

function normalizeSettings(settings = {}) {
  return {
    daily_post_enabled: typeof settings.daily_post_enabled === 'boolean'
      ? settings.daily_post_enabled
      : DEFAULT_SETTINGS.daily_post_enabled,
    daily_post_times: Array.isArray(settings.daily_post_times) && settings.daily_post_times.length
      ? settings.daily_post_times
      : DEFAULT_SETTINGS.daily_post_times,
    daily_post_days: Array.isArray(settings.daily_post_days) && settings.daily_post_days.length
      ? settings.daily_post_days
      : DEFAULT_SETTINGS.daily_post_days,
    timezone: typeof settings.timezone === 'string' && settings.timezone.trim()
      ? settings.timezone
      : DEFAULT_SETTINGS.timezone,
  };
}

function parseTimesInput(value) {
  return value
    .split(',')
    .map((item) => item.trim())
    .filter(Boolean);
}

function validateTimes(times) {
  return times.length > 0 && times.every((time) => {
    if (!/^\d{2}:\d{2}$/.test(time)) return false;
    const [hour, minute] = time.split(':').map(Number);
    return hour >= 0 && hour <= 23 && minute >= 0 && minute <= 59;
  });
}

const icons = {
  bot: (
    <>
      <path d="M12 8V4" />
      <path d="M9 4h6" />
      <rect x="5" y="8" width="14" height="11" rx="4" />
      <path d="M9 13h.01" />
      <path d="M15 13h.01" />
      <path d="M10 17h4" />
    </>
  ),
  plug: (
    <>
      <path d="M8 2v5" />
      <path d="M16 2v5" />
      <path d="M7 7h10v4a5 5 0 0 1-10 0Z" />
      <path d="M12 16v6" />
    </>
  ),
  key: (
    <>
      <circle cx="7.5" cy="14.5" r="3.5" />
      <path d="M10 12 21 1" />
      <path d="M16 6h4v4" />
      <path d="M14 8h3" />
    </>
  ),
  shield: (
    <>
      <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10Z" />
      <path d="m9 12 2 2 4-5" />
    </>
  ),
  refresh: (
    <>
      <path d="M21 12a9 9 0 0 1-15.2 6.5" />
      <path d="M3 12A9 9 0 0 1 18.2 5.5" />
      <path d="M18 2v4h4" />
      <path d="M6 22v-4H2" />
    </>
  ),
  search: (
    <>
      <circle cx="11" cy="11" r="7" />
      <path d="m21 21-4.3-4.3" />
    </>
  ),
  queue: (
    <>
      <path d="M4 6h16" />
      <path d="M4 12h16" />
      <path d="M4 18h10" />
    </>
  ),
  chat: (
    <>
      <path d="M21 15a4 4 0 0 1-4 4H8l-5 3V7a4 4 0 0 1 4-4h10a4 4 0 0 1 4 4Z" />
    </>
  ),
  x: (
    <>
      <path d="M18 6 6 18" />
      <path d="m6 6 12 12" />
    </>
  ),
  save: (
    <>
      <path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2Z" />
      <path d="M17 21v-8H7v8" />
      <path d="M7 3v5h8" />
    </>
  ),
  repeat: (
    <>
      <path d="m17 2 4 4-4 4" />
      <path d="M3 11V9a3 3 0 0 1 3-3h15" />
      <path d="m7 22-4-4 4-4" />
      <path d="M21 13v2a3 3 0 0 1-3 3H3" />
    </>
  ),
  reset: (
    <>
      <path d="M3 12a9 9 0 1 0 3-6.7" />
      <path d="M3 3v6h6" />
    </>
  ),
  trash: (
    <>
      <path d="M3 6h18" />
      <path d="M8 6V4h8v2" />
      <path d="M19 6l-1 15H6L5 6" />
      <path d="M10 11v6" />
      <path d="M14 11v6" />
    </>
  ),
  settings: (
    <>
      <path d="M12 15.5A3.5 3.5 0 1 0 12 8a3.5 3.5 0 0 0 0 7.5Z" />
      <path d="M19.4 15a1.7 1.7 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.8-.3 1.7 1.7 0 0 0-1 1.5V21a2 2 0 1 1-4 0v-.2a1.7 1.7 0 0 0-1-1.5 1.7 1.7 0 0 0-1.8.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1A1.7 1.7 0 0 0 4.6 15a1.7 1.7 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.1a1.7 1.7 0 0 0 1.5-1 1.7 1.7 0 0 0-.3-1.8l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1A1.7 1.7 0 0 0 9 4.7a1.7 1.7 0 0 0 1-1.5V3a2 2 0 1 1 4 0v.2a1.7 1.7 0 0 0 1 1.5 1.7 1.7 0 0 0 1.8-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.8 1.7 1.7 0 0 0 1.5 1h.2a2 2 0 1 1 0 4h-.2a1.7 1.7 0 0 0-1.4 1Z" />
    </>
  ),
  server: (
    <>
      <rect x="3" y="4" width="18" height="6" rx="2" />
      <rect x="3" y="14" width="18" height="6" rx="2" />
      <path d="M7 7h.01" />
      <path d="M7 17h.01" />
    </>
  ),
  cards: (
    <>
      <rect x="7" y="3" width="10" height="14" rx="2" />
      <path d="M5 7 3.7 18.1a2 2 0 0 0 1.8 2.2l8.9 1" />
      <path d="M10 7h4" />
      <path d="M10 11h4" />
    </>
  ),
  packs: (
    <>
      <path d="m21 8-9-5-9 5 9 5 9-5Z" />
      <path d="M3 8v8l9 5 9-5V8" />
      <path d="M12 13v8" />
    </>
  ),
  clock: (
    <>
      <circle cx="12" cy="12" r="9" />
      <path d="M12 7v5l3 2" />
    </>
  ),
  send: (
    <>
      <path d="m22 2-7 20-4-9-9-4Z" />
      <path d="M22 2 11 13" />
    </>
  ),
  skip: (
    <>
      <path d="m5 4 8 8-8 8Z" />
      <path d="M19 5v14" />
    </>
  ),
  pause: (
    <>
      <path d="M8 5v14" />
      <path d="M16 5v14" />
    </>
  ),
  play: <path d="m7 4 13 8-13 8Z" />,
  sync: (
    <>
      <path d="M17 2v5h5" />
      <path d="M7 22v-5H2" />
      <path d="M20 11a8 8 0 0 0-13.5-5.8L2 9" />
      <path d="M4 13a8 8 0 0 0 13.5 5.8L22 15" />
    </>
  ),
  target: (
    <>
      <circle cx="12" cy="12" r="9" />
      <circle cx="12" cy="12" r="5" />
      <path d="M12 3v3" />
      <path d="M12 18v3" />
      <path d="M3 12h3" />
      <path d="M18 12h3" />
    </>
  ),
  result: <path d="M20 6 9 17l-5-5" />,
  info: (
    <>
      <circle cx="12" cy="12" r="9" />
      <path d="M12 11v5" />
      <path d="M12 8h.01" />
    </>
  ),
  language: (
    <>
      <circle cx="12" cy="12" r="9" />
      <path d="M3 12h18" />
      <path d="M12 3a13.5 13.5 0 0 1 0 18" />
      <path d="M12 3a13.5 13.5 0 0 0 0 18" />
    </>
  ),
  chevron: <path d="m9 18 6-6-6-6" />,
};

function Icon({ name, className = '' }) {
  return (
    <svg
      className={`tg-icon ${className}`.trim()}
      aria-hidden="true"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      {icons[name]}
    </svg>
  );
}

function resolveError(code, fallback, copy) {
  const localized = copy.errors[code];
  if (localized) return { friendly: localized[0], detail: localized[1] };
  return { friendly: fallback || copy.unknownError, detail: code || '' };
}

function buildDiag() {
  const tg = getTelegramWebApp();
  const initData = getTelegramInitData();
  const user = getTelegramUserUnsafe();
  const apiBase = getApiBase();
  return {
    webAppDetected: Boolean(tg),
    initDataPresent: Boolean(initData),
    initDataLength: initData.length,
    userDetectedViaUnsafe: Boolean(user),
    apiConfigured: Boolean(apiBase),
    apiBase: apiBase || '',
  };
}

function statusTone(ok) {
  if (ok === true) return 'ok';
  if (ok === false) return 'err';
  return '';
}

function Badge({ tone = '', children }) {
  return <span className={`tg-badge ${tone}`.trim()}>{children}</span>;
}

function Row({ icon, label, value, badgeTone = '', caption, mono = false }) {
  return (
    <div className="tg-row">
      {icon && <Icon name={icon} />}
      <div className="tg-row__main">
        <span className="tg-row__label">{label}</span>
        {caption && <span className="tg-row__caption">{caption}</span>}
      </div>
      {value !== undefined && (
        <span className={`tg-row__value ${mono ? 'mono' : ''}`}>
          {badgeTone ? <Badge tone={badgeTone}>{value}</Badge> : value}
        </span>
      )}
    </div>
  );
}

function ActionRow({ icon, label, caption, onClick, disabled, loading, danger }) {
  return (
    <button
      className={`tg-row tg-row--action ${danger ? 'danger' : ''}`.trim()}
      onClick={onClick}
      disabled={disabled || loading}
      type="button"
    >
      {icon && <Icon name={icon} />}
      <div className="tg-row__main">
        <span className="tg-row__label">{label}</span>
        {caption && <span className="tg-row__caption">{caption}</span>}
      </div>
      {loading ? <span className="spinner" /> : <Icon name="chevron" className="tg-chevron" />}
    </button>
  );
}

function MenuRow({ icon, label, caption, value, onClick, disabled }) {
  return (
    <button className="tg-row tg-row--action" onClick={onClick} disabled={disabled} type="button">
      {icon && <Icon name={icon} />}
      <div className="tg-row__main">
        <span className="tg-row__label">{label}</span>
        {caption && <span className="tg-row__caption">{caption}</span>}
      </div>
      {value !== undefined && <span className="tg-row__value">{value}</span>}
      <Icon name="chevron" className="tg-chevron" />
    </button>
  );
}

function Section({ title, footer, children }) {
  return (
    <section className="tg-section">
      {title && <div className="tg-section__title">{title}</div>}
      <div className="tg-list">{children}</div>
      {footer && <div className="tg-section__footer">{footer}</div>}
    </section>
  );
}

function Notice({ tone = 'warn', children }) {
  return <div className={`tg-notice ${tone}`.trim()}>{children}</div>;
}

function SummaryItem({ icon, label, value }) {
  return (
    <div className="tg-summary__item">
      <Icon name={icon} />
      <span className="tg-summary__label">{label}</span>
      <strong className="tg-summary__value">{value}</strong>
    </div>
  );
}

function TabButton({ active, onClick, children }) {
  return (
    <button className={`tg-tab ${active ? 'active' : ''}`.trim()} type="button" onClick={onClick}>
      {children}
    </button>
  );
}

function Field({ label, children, hint }) {
  return (
    <label className="tg-field">
      <span className="tg-field__label">{label}</span>
      {children}
      {hint && <span className="tg-field__hint">{hint}</span>}
    </label>
  );
}

function SelectField({ label, value, onChange, children, hint }) {
  return (
    <label className="tg-field">
      <span className="tg-field__label">{label}</span>
      <select className="tg-select" value={value} onChange={(event) => onChange(event.target.value)}>
        {children}
      </select>
      {hint && <span className="tg-field__hint">{hint}</span>}
    </label>
  );
}

function SwitchField({ label, checked, onChange, disabled = false }) {
  return (
    <label className="tg-switch-row">
      <span className="tg-row__label">{label}</span>
      <input type="checkbox" checked={checked} disabled={disabled} onChange={(event) => onChange(event.target.checked)} />
      <span className="tg-switch" aria-hidden="true" />
    </label>
  );
}

function SettingToggleRow({ label, caption, checked, onChange, disabled = false }) {
  return (
    <label className="tg-switch-row tg-switch-row--rich">
      <div className="tg-row__main">
        <span className="tg-row__label">{label}</span>
        {caption && <span className="tg-row__caption">{caption}</span>}
      </div>
      <input type="checkbox" checked={checked} disabled={disabled} onChange={(event) => onChange(event.target.checked)} />
      <span className="tg-switch" aria-hidden="true" />
    </label>
  );
}

function MiniButton({ icon, label, onClick, disabled, loading, danger }) {
  return (
    <button
      className={`tg-mini-button ${danger ? 'danger' : ''}`.trim()}
      type="button"
      onClick={onClick}
      disabled={disabled || loading}
    >
      {loading ? <span className="spinner" /> : icon && <Icon name={icon} />}
      <span>{label}</span>
    </button>
  );
}

function formatDateTime(value, locale) {
  if (!value) return '-';
  try {
    return new Date(value).toLocaleString(locale);
  } catch {
    return value;
  }
}

function commandCaption(command, locale) {
  const parts = [
    command.status,
    command.created_at ? formatDateTime(command.created_at, locale) : null,
    command.last_error || null,
  ].filter(Boolean);
  return parts.join(' | ');
}

function CommandRow({ command, onCancel, loading, copy }) {
  const cancellable = ['pending', 'retrying'].includes(command.status);
  return (
    <div className="tg-command-row">
      <div className="tg-command-row__main">
        <span className="tg-row__label">{command.command_type}</span>
        <span className="tg-row__caption">{commandCaption(command, copy.locale)}</span>
      </div>
      <Badge tone={command.status === 'failed' ? 'err' : command.status === 'executed' ? 'ok' : 'warn'}>
        {command.status}
      </Badge>
      {cancellable && (
        <button className="tg-icon-button" type="button" onClick={() => onCancel(command.id)} disabled={loading} aria-label={copy.cancelCommand}>
          {loading ? <span className="spinner" /> : <Icon name="x" />}
        </button>
      )}
    </div>
  );
}

function CardResult({ card, selected, onSelect }) {
  return (
    <button className={`tg-card-result ${selected ? 'active' : ''}`.trim()} type="button" onClick={() => onSelect(card)}>
      <span className="tg-card-result__code">{card.code}</span>
      <span className="tg-card-result__name">{card.name || card.real_name}</span>
      <span className="tg-card-result__meta">{[card.type_code, card.faction_name, card.pack_name].filter(Boolean).join(' | ')}</span>
    </button>
  );
}

function App() {
  const [language, setLanguage] = useState(getInitialLanguage);
  const copy = I18N[language];
  const [diag, setDiag] = useState(() => buildDiag());
  const [me, setMe] = useState(null);
  const [sysStatus, setSysStatus] = useState(null);
  const [result, setResult] = useState(null);
  const [cardCode, setCardCode] = useState('');
  const [loadingCmd, setLoadingCmd] = useState(null);
  const [loadingMe, setLoadingMe] = useState(false);
  const [loadingStatus, setLoadingStatus] = useState(false);
  const [activeTab, setActiveTab] = useState('menu');
  const [settings, setSettings] = useState(DEFAULT_SETTINGS);
  const [timesInput, setTimesInput] = useState(DEFAULT_SETTINGS.daily_post_times.join(', '));
  const [settingsResult, setSettingsResult] = useState(null);
  const [loadingSettings, setLoadingSettings] = useState(false);
  const [savingSettings, setSavingSettings] = useState(false);
  const [overview, setOverview] = useState(null);
  const [loadingOverview, setLoadingOverview] = useState(false);
  const [commands, setCommands] = useState([]);
  const [loadingCommands, setLoadingCommands] = useState(false);
  const [cancellingCommand, setCancellingCommand] = useState(null);
  const [cardQuery, setCardQuery] = useState('');
  const [cardResults, setCardResults] = useState([]);
  const [searchingCards, setSearchingCards] = useState(false);
  const [targetChatId, setTargetChatId] = useState('');

  function toggleLanguage() {
    const nextLanguage = language === 'pt' ? 'en' : 'pt';
    setLanguage(nextLanguage);
    try { window.localStorage?.setItem(LANGUAGE_STORAGE_KEY, nextLanguage); } catch {}
  }

  useEffect(() => {
    const tg = getTelegramWebApp();
    if (tg) {
      tg.ready?.();
      try { tg.setHeaderColor?.('secondary_bg_color'); } catch {}
      try { tg.setBackgroundColor?.('bg_color'); } catch {}
      try { tg.setBottomBarColor?.('secondary_bg_color'); } catch {}
    }
    setDiag(buildDiag());
  }, []);

  useEffect(() => {
    const backButton = getTelegramWebApp()?.BackButton;
    if (!backButton) return undefined;
    const goHome = () => setActiveTab('menu');
    if (activeTab === 'menu') {
      backButton.hide?.();
    } else {
      backButton.show?.();
      backButton.onClick?.(goHome);
    }
    return () => backButton.offClick?.(goHome);
  }, [activeTab]);

  useEffect(() => { fetchMe(); fetchStatus(); fetchSettings(); fetchOverview(); fetchCommands(); }, []);

  const isAdmin = me?.admin === true;
  const apiConfigured = diag.apiConfigured;
  const isOutsideTelegram = !diag.webAppDetected || !diag.initDataPresent;
  const actionsDisabled = !isAdmin || isOutsideTelegram || !apiConfigured || loadingCmd !== null;

  async function fetchMe() {
    const url = buildApiUrl('/me');
    if (!url) return;
    setLoadingMe(true);
    try {
      const resp = await fetch(url, { headers: { 'x-telegram-init-data': getTelegramInitData() } });
      setMe(await resp.json().catch(() => ({})));
    } catch {
      setMe({ ok: false, error: 'network_error' });
    } finally {
      setLoadingMe(false);
    }
  }

  async function fetchStatus() {
    const url = buildApiUrl('/status');
    if (!url) return;
    setLoadingStatus(true);
    try {
      const resp = await fetch(url, { headers: { 'x-telegram-init-data': getTelegramInitData() } });
      setSysStatus(await resp.json().catch(() => ({})));
    } catch {
      setSysStatus({ ok: false, error: 'network_error' });
    } finally {
      setLoadingStatus(false);
    }
  }

  async function fetchOverview() {
    const url = buildApiUrl('/overview');
    if (!url) return;
    setLoadingOverview(true);
    try {
      const resp = await fetch(url, { headers: { 'x-telegram-init-data': getTelegramInitData() } });
      const json = await resp.json().catch(() => ({}));
      if (!resp.ok) {
        const error = resolveError(json.error, `HTTP ${resp.status}`, copy);
        setResult({ ok: false, friendly: error.friendly, detail: error.detail, at: new Date() });
      } else {
        setOverview(json);
        if (json.settings) applySettings(json.settings);
      }
    } catch {
      setResult({ ok: false, friendly: copy.networkOverview, detail: '', at: new Date() });
    } finally {
      setLoadingOverview(false);
    }
  }

  async function fetchCommands(status = '') {
    const suffix = status ? `?status=${encodeURIComponent(status)}` : '';
    const url = buildApiUrl(`/commands${suffix}`);
    if (!url) return;
    setLoadingCommands(true);
    try {
      const resp = await fetch(url, { headers: { 'x-telegram-init-data': getTelegramInitData() } });
      const json = await resp.json().catch(() => ({}));
      if (!resp.ok) {
        const error = resolveError(json.error, `HTTP ${resp.status}`, copy);
        setResult({ ok: false, friendly: error.friendly, detail: error.detail, at: new Date() });
      } else {
        setCommands(json.commands || []);
      }
    } catch {
      setResult({ ok: false, friendly: copy.networkQueue, detail: '', at: new Date() });
    } finally {
      setLoadingCommands(false);
    }
  }

  async function searchCards() {
    const query = cardQuery.trim();
    if (query.length < 2) {
      setCardResults([]);
      return;
    }
    const url = buildApiUrl(`/cards?q=${encodeURIComponent(query)}`);
    if (!url) return;
    setSearchingCards(true);
    try {
      const resp = await fetch(url, { headers: { 'x-telegram-init-data': getTelegramInitData() } });
      const json = await resp.json().catch(() => ({}));
      if (!resp.ok) {
        const error = resolveError(json.error, `HTTP ${resp.status}`, copy);
        setResult({ ok: false, friendly: error.friendly, detail: error.detail, at: new Date() });
      } else {
        setCardResults(json.cards || []);
      }
    } catch {
      setResult({ ok: false, friendly: copy.networkCards, detail: '', at: new Date() });
    } finally {
      setSearchingCards(false);
    }
  }

  async function cancelCommand(commandId) {
    const url = buildApiUrl(`/commands/${commandId}`);
    if (!url) return;
    setCancellingCommand(commandId);
    try {
      const resp = await fetch(url, {
        method: 'PATCH',
        headers: { 'content-type': 'application/json', 'x-telegram-init-data': getTelegramInitData() },
        body: JSON.stringify({ status: 'cancelled' }),
      });
      const json = await resp.json().catch(() => ({}));
      if (!resp.ok) {
        haptic('notification', 'error');
        const error = resolveError(json.error, `HTTP ${resp.status}`, copy);
        setResult({ ok: false, friendly: error.friendly, detail: error.detail, at: new Date() });
      } else {
        haptic('notification', 'success');
        setResult({ ok: true, command_type: json.command?.command_type || 'cancel', friendly: copy.commandCancelled, detail: '', at: new Date() });
        fetchCommands();
        fetchOverview();
      }
    } catch {
      haptic('notification', 'error');
      setResult({ ok: false, friendly: copy.networkCancel, detail: '', at: new Date() });
    } finally {
      setCancellingCommand(null);
    }
  }

  function applySettings(nextSettings) {
    const normalized = normalizeSettings(nextSettings);
    setSettings(normalized);
    setTimesInput(normalized.daily_post_times.join(', '));
  }

  async function fetchSettings() {
    const url = buildApiUrl('/settings');
    if (!url) return;
    setLoadingSettings(true);
    try {
      const resp = await fetch(url, { headers: { 'x-telegram-init-data': getTelegramInitData() } });
      const json = await resp.json().catch(() => ({}));
      if (!resp.ok) {
        const error = resolveError(json.error, `HTTP ${resp.status}`, copy);
        setSettingsResult({ ok: false, friendly: error.friendly, detail: error.detail, at: new Date() });
      } else {
        applySettings(json.settings);
        setSettingsResult(null);
      }
    } catch {
      setSettingsResult({ ok: false, friendly: copy.networkSettingsLoad, detail: '', at: new Date() });
    } finally {
      setLoadingSettings(false);
    }
  }

  async function saveSettings() {
    const times = parseTimesInput(timesInput);
    if (!validateTimes(times)) {
      haptic('notification', 'error');
      setSettingsResult({ ok: false, friendly: copy.invalidTime, detail: copy.timesHint, at: new Date() });
      return;
    }
    if (!settings.daily_post_days.length) {
      haptic('notification', 'error');
      setSettingsResult({ ok: false, friendly: copy.selectAtLeastOneDay, detail: '', at: new Date() });
      return;
    }
    if (!settings.timezone.trim()) {
      haptic('notification', 'error');
      setSettingsResult({ ok: false, friendly: copy.timezoneRequired, detail: '', at: new Date() });
      return;
    }

    const url = buildApiUrl('/settings');
    if (!url) {
      setSettingsResult({ ok: false, friendly: copy.workerNotConfigured, detail: copy.defineCommandsApi, at: new Date() });
      return;
    }

    setSavingSettings(true);
    try {
      const resp = await fetch(url, {
        method: 'PATCH',
        headers: { 'content-type': 'application/json', 'x-telegram-init-data': getTelegramInitData() },
        body: JSON.stringify({ ...settings, daily_post_times: times, timezone: settings.timezone.trim() }),
      });
      const json = await resp.json().catch(() => ({}));
      if (!resp.ok) {
        haptic('notification', 'error');
        const error = resolveError(json.error, `HTTP ${resp.status}`, copy);
        setSettingsResult({
          ok: false,
          friendly: error.friendly,
          detail: [error.detail, json.key && `key: ${json.key}`].filter(Boolean).join('\n'),
          at: new Date(),
        });
      } else {
        haptic('notification', 'success');
        applySettings(json.settings);
        setSettingsResult({ ok: true, friendly: copy.settingsSaved, detail: '', at: new Date() });
      }
    } catch {
      haptic('notification', 'error');
      setSettingsResult({ ok: false, friendly: copy.networkSettingsSave, detail: '', at: new Date() });
    } finally {
      setSavingSettings(false);
    }
  }

  function toggleDay(code) {
    setSettings((current) => {
      const hasDay = current.daily_post_days.includes(code);
      return {
        ...current,
        daily_post_days: hasDay
          ? current.daily_post_days.filter((day) => day !== code)
          : [...current.daily_post_days, code],
      };
    });
  }

  const enqueue = useCallback(async (command_type, payload = {}) => {
    if (loadingCmd) return;
    haptic('impact', 'light');
    const url = buildApiUrl('/bot-command');
    if (!url) {
      setResult({ ok: false, friendly: copy.workerNotConfigured, detail: copy.defineCommandsApi, at: new Date() });
      return;
    }
    setLoadingCmd(command_type);
    try {
      const resp = await fetch(url, {
        method: 'POST',
        headers: { 'content-type': 'application/json', 'x-telegram-init-data': getTelegramInitData() },
        body: JSON.stringify({ command_type, payload, target_chat_id: targetChatId || null }),
      });
      const json = await resp.json().catch(() => ({}));
      if (!resp.ok) {
        haptic('notification', 'error');
        const error = resolveError(json.error, `HTTP ${resp.status}`, copy);
        setResult({
          ok: false,
          command_type,
          friendly: error.friendly,
          detail: [error.detail, json.role && `role: ${json.role}`, json.admin_source && `source: ${json.admin_source}`].filter(Boolean).join('\n'),
          at: new Date(),
        });
      } else {
        haptic('notification', 'success');
        setResult({
          ok: true,
          command_type: json.command?.command_type || command_type,
          friendly: copy.commandQueued,
          detail: json.command?.id ? `ID: ${json.command.id}` : '',
          at: new Date(),
        });
        fetchStatus();
        fetchCommands();
        fetchOverview();
      }
    } catch {
      haptic('notification', 'error');
      setResult({ ok: false, command_type, friendly: copy.networkWorker, detail: '', at: new Date() });
    } finally {
      setLoadingCmd(null);
    }
  }, [loadingCmd, targetChatId, copy]);

  const adminValue = loadingMe
    ? copy.checking
    : !apiConfigured
      ? copy.noApi
      : me?.ok && isAdmin
        ? me.role || 'admin'
        : me?.ok
          ? me.role || 'none'
          : me?.error === 'network_error'
            ? copy.noNetwork
            : copy.pending;

  const workerValue = loadingStatus ? '...' : sysStatus?.ok ? copy.online : copy.offline;
  const cardsValue = loadingOverview ? '...' : (overview?.counts?.cards ?? sysStatus?.total_cards ?? '-');
  const queueValue = loadingOverview ? '...' : (overview?.counts?.pending_commands ?? 0);
  const targetChats = overview?.target_chats?.filter((chat) => chat.enabled !== false) || [];

  return (
    <div className="app">
      <header className="tg-profile">
        <div className="tg-avatar" aria-hidden="true"><Icon name="bot" /></div>
        <div className="tg-profile__title">Arkham Bot</div>
        <div className="tg-profile__subtitle">{copy.appSubtitle}</div>
      </header>

      {isOutsideTelegram && <Notice>{copy.outsideTelegram}</Notice>}
      {!apiConfigured && <Notice tone="err">{copy.workerNotConfigured}</Notice>}

      {activeTab === 'menu' && (
        <>
          <Section title={copy.settings}>
            <MenuRow icon="send" label={copy.postCard} caption={copy.postCardCaption} onClick={() => setActiveTab('post')} />
            <MenuRow icon="settings" label={copy.controls} caption={copy.controlsCaption} onClick={() => setActiveTab('controls')} />
            <MenuRow icon="clock" label={copy.schedule} caption={`${settings.daily_post_times.join(', ')} | ${settings.timezone}`} onClick={() => setActiveTab('schedule')} />
            <MenuRow icon="queue" label={copy.queue} caption={copy.queueCaption} value={queueValue} onClick={() => setActiveTab('queue')} />
            <MenuRow icon="server" label={copy.health} caption={copy.healthCaption} value={workerValue} onClick={() => setActiveTab('status')} />
            <MenuRow icon="language" label={copy.language} caption={copy.languageCaption} value={copy.languageName} onClick={toggleLanguage} />
          </Section>
        </>
      )}


      {activeTab === 'post' && (
        <>
          <Section title={copy.postCard}>
            <div className="tg-form-row">
              <Field label={copy.searchByCodeOrName}>
                <div className="tg-search-line">
                  <input
                    className="tg-input tg-input--boxed"
                    type="text"
                    value={cardQuery}
                    onChange={(event) => setCardQuery(event.target.value)}
                    placeholder={copy.searchPlaceholder}
                    inputMode="text"
                  />
                  <MiniButton icon="search" label={copy.search} onClick={searchCards} loading={searchingCards} disabled={!isAdmin || isOutsideTelegram || !apiConfigured || cardQuery.trim().length < 2} />
                </div>
              </Field>
            </div>
            {cardResults.length > 0 && (
              <div className="tg-card-results">
                {cardResults.map((card) => (
                  <CardResult
                    key={card.code}
                    card={card}
                    selected={cardCode === card.code}
                    onSelect={(selected) => {
                      setCardCode(selected.code);
                      setCardQuery(`${selected.code} - ${selected.name || selected.real_name}`);
                    }}
                  />
                ))}
              </div>
            )}
            <div className="tg-form-row">
              <Field label={copy.selectedCard} hint={copy.selectedCardHint}>
                <input
                  className="tg-input tg-input--boxed"
                  type="text"
                  placeholder={copy.selectedCardPlaceholder}
                  value={cardCode}
                  onChange={(e) => setCardCode(e.target.value.trim())}
                  inputMode="text"
                />
              </Field>
            </div>
            {targetChats.length > 0 && (
              <div className="tg-form-row">
                <SelectField label={copy.destination} value={targetChatId} onChange={setTargetChatId}>
                  <option value="">{copy.defaultChat}</option>
                  {targetChats.map((chat) => (
                    <option key={chat.chat_id} value={chat.chat_id}>
                      {chat.title || chat.chat_id}
                    </option>
                  ))}
                </SelectField>
              </div>
            )}
            <ActionRow icon="send" label={copy.postNow} caption={cardCode ? `${copy.card} ${cardCode}` : copy.automaticChoice} onClick={() => enqueue('post_now', cardCode ? { card_code: cardCode } : {})} loading={loadingCmd === 'post_now'} disabled={actionsDisabled} />
            <ActionRow icon="repeat" label={copy.repostCard} caption={cardCode ? `${copy.card} ${cardCode}` : copy.informCardCode} onClick={() => enqueue('repost_card', { card_code: cardCode })} loading={loadingCmd === 'repost_card'} disabled={actionsDisabled || !cardCode} />
            <ActionRow icon="skip" label={copy.skipCard} caption={cardCode ? `${copy.card} ${cardCode}` : copy.informCardCode} onClick={() => enqueue('skip_card', { card_code: cardCode })} loading={loadingCmd === 'skip_card'} disabled={actionsDisabled || !cardCode} />
          </Section>
        </>
      )}

      {activeTab === 'controls' && (
        <>
          <Section title={copy.modeSettings}>
            <SwitchField
              label={copy.dailyPost}
              checked={settings.daily_post_enabled}
              disabled={actionsDisabled}
              onChange={(checked) => enqueue(checked ? 'resume_daily_post' : 'pause_daily_post')}
            />
            <div className="tg-section__footer">{copy.dailyPostFooter}</div>
            <ActionRow icon="sync" label={copy.syncArkhamDB} caption={copy.syncCaption} onClick={() => enqueue('sync_arkhamdb', { sync_faq: false })} loading={loadingCmd === 'sync_arkhamdb'} disabled={actionsDisabled} />
            <ActionRow icon="reset" label={copy.resetCycle} caption={copy.resetCaption} onClick={() => enqueue('reset_cycle')} loading={loadingCmd === 'reset_cycle'} disabled={actionsDisabled} danger />
            <ActionRow icon="trash" label={copy.clearQueue} caption={copy.clearQueueCaption} onClick={() => enqueue('clear_queue')} loading={loadingCmd === 'clear_queue'} disabled={actionsDisabled} danger />
          </Section>
        </>
      )}

      {activeTab === 'schedule' && (
        <>
          <Section title={copy.scheduleTitle}>
            <SettingToggleRow
              label={copy.automaticPosting}
              caption={copy.automaticPostingCaption}
              checked={settings.daily_post_enabled}
              onChange={(checked) => setSettings((current) => ({ ...current, daily_post_enabled: checked }))}
            />
            <div className="tg-form-row">
              <Field label={copy.postTimes} hint={`${copy.postTimesCaption}. ${copy.timesHint}`}>
                <input className="tg-input tg-input--boxed" type="text" value={timesInput} onChange={(event) => setTimesInput(event.target.value)} placeholder="09:00, 21:30" inputMode="text" />
              </Field>
            </div>
            <div className="tg-form-row">
              <span className="tg-field__label">{copy.postDays}</span>
              <span className="tg-field__hint">{copy.postDaysCaption}</span>
              <div className="tg-day-grid">
                {WEEKDAYS.map((day) => (
                  <button key={day.code} className={`tg-day ${settings.daily_post_days.includes(day.code) ? 'active' : ''}`.trim()} type="button" onClick={() => toggleDay(day.code)}>
                    {day[language]}
                  </button>
                ))}
              </div>
            </div>
            <div className="tg-form-row">
              <Field label={copy.timezoneLabel} hint={copy.timezoneCaption}>
                <input className="tg-input tg-input--boxed" type="text" value={settings.timezone} onChange={(event) => setSettings((current) => ({ ...current, timezone: event.target.value }))} placeholder="America/Sao_Paulo" inputMode="text" />
              </Field>
            </div>
            <ActionRow icon="refresh" label={copy.reloadSettings} onClick={fetchSettings} loading={loadingSettings} disabled={!apiConfigured} />
            <ActionRow icon="save" label={copy.saveSettings} onClick={saveSettings} loading={savingSettings} disabled={actionsDisabled} />
          </Section>

          {settingsResult && (
            <Section title={copy.settingsResult}>
              <Row icon="settings" label={settingsResult.ok ? copy.success : copy.error} value={settingsResult.ok ? 'ok' : 'error'} badgeTone={settingsResult.ok ? 'ok' : 'err'} caption={settingsResult.friendly} />
              {settingsResult.detail && (
                <details className="tg-details">
                  <summary>{copy.details}</summary>
                  <pre className="diag-pre">{settingsResult.detail}</pre>
                </details>
              )}
            </Section>
          )}
        </>
      )}

      {activeTab === 'queue' && (
        <>
          <Section title={copy.commandQueue}>
            <ActionRow icon="refresh" label={copy.refreshQueue} onClick={() => fetchCommands()} loading={loadingCommands} disabled={!apiConfigured} />
            {commands.length === 0 && <Row icon="queue" label={copy.noRecentCommands} value="-" />}
            {commands.map((command) => (
              <CommandRow key={command.id} command={command} onCancel={cancelCommand} loading={cancellingCommand === command.id} copy={copy} />
            ))}
          </Section>
        </>
      )}

      {activeTab === 'status' && (
        <>
          <Section title={copy.summary}>
            <Row icon="server" label={copy.worker} value={workerValue} badgeTone={sysStatus?.ok ? 'ok' : 'err'} />
            <Row icon="shield" label={copy.access} value={adminValue} badgeTone={isAdmin ? 'ok' : 'err'} />
            <Row icon="cards" label={copy.cards} value={cardsValue} />
            <Row icon="queue" label={copy.queue} value={queueValue} />
          </Section>

          <Section title={copy.account}>
            <Row icon="plug" label={copy.telegramWebApp} value={diag.webAppDetected ? copy.yes : copy.no} badgeTone={statusTone(diag.webAppDetected)} />
            <Row icon="key" label={copy.initData} value={diag.initDataPresent ? copy.yes : copy.no} badgeTone={statusTone(diag.initDataPresent)} />
            <Row icon="shield" label={copy.admin} value={adminValue} badgeTone={isAdmin ? 'ok' : 'err'} caption={me?.admin_source ? `source: ${me.admin_source}` : undefined} />
            <ActionRow icon="refresh" label={copy.recheckAuth} onClick={fetchMe} loading={loadingMe} disabled={!apiConfigured} />
          </Section>

          <Section title={copy.system}>
            <Row icon="server" label={copy.worker} value={sysStatus?.ok ? copy.online : copy.offline} badgeTone={statusTone(sysStatus?.ok)} />
            <Row icon="cards" label={copy.cards} value={loadingStatus ? '...' : (sysStatus?.total_cards ?? '-')} />
            <Row icon="packs" label={copy.packs} value={loadingStatus ? '...' : (sysStatus?.total_packs ?? '-')} />
            <Row icon="clock" label={copy.lastSync} value={(overview?.last_sync || sysStatus?.last_sync) ? new Date(overview?.last_sync || sysStatus.last_sync).toLocaleString(copy.locale) : '-'} mono />
            <ActionRow icon="refresh" label={copy.refreshStatus} onClick={() => { fetchStatus(); fetchOverview(); }} loading={loadingStatus || loadingOverview} disabled={!apiConfigured} />
          </Section>

          <Section title={copy.diagnostic}>
            <details className="tg-details">
              <summary><Icon name="info" />{copy.showDetails}</summary>
              <pre className="diag-pre">{[
                `${copy.telegramWebApp}: ${diag.webAppDetected}`,
                `${copy.initDataPresent}: ${diag.initDataPresent}`,
                `${copy.initDataLength}: ${diag.initDataLength}`,
                `${copy.userUnsafe}: ${diag.userDetectedViaUnsafe}`,
                `${copy.apiConfigured}: ${diag.apiConfigured}`,
                `${copy.apiBase}: ${diag.apiBase || copy.notConfigured}`,
                `${copy.admin}: ${Boolean(me?.admin)}`,
                `${copy.role}: ${me?.role || '-'}`,
                `${copy.adminSource}: ${me?.admin_source || '-'}`,
              ].join('\n')}</pre>
            </details>
          </Section>
        </>
      )}

      {result && activeTab !== 'status' && (
        <Section title={copy.result}>
          <Row
            icon="result"
            label={result.ok ? copy.success : copy.error}
            value={result.command_type || '-'}
            badgeTone={result.ok ? 'ok' : 'err'}
            caption={result.friendly}
          />
          {result.detail && (
            <details className="tg-details">
              <summary>{copy.details}</summary>
              <pre className="diag-pre">{result.detail}</pre>
            </details>
          )}
        </Section>
      )}
    </div>
  );
}

createRoot(document.getElementById('root')).render(<App />);
