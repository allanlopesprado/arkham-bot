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

const ERROR_MESSAGES = {
  invalid_telegram_init_data: { friendly: 'Abra pelo Telegram para autenticar.', detail: 'initData invalido.' },
  unauthorized: { friendly: 'Usuario sem permissao administrativa.', detail: 'O Telegram ID nao esta cadastrado como admin.' },
  not_found: { friendly: 'Endpoint nao encontrado.', detail: 'Verifique VITE_COMMANDS_API_URL.' },
  origin_not_allowed: { friendly: 'Origem nao autorizada.', detail: 'Verifique ALLOWED_ORIGINS no Worker.' },
  bot_command_insert_failed: { friendly: 'Falha ao criar comando.', detail: 'Verifique Worker e Supabase.' },
  command_type_required: { friendly: 'Tipo de comando nao informado.', detail: 'command_type_required' },
  unsupported_command_type: { friendly: 'Comando nao suportado.', detail: 'unsupported_command_type' },
  method_not_allowed: { friendly: 'Metodo HTTP nao permitido.', detail: 'method_not_allowed' },
  settings_fetch_failed: { friendly: 'Falha ao carregar configuracoes.', detail: 'settings_fetch_failed' },
  settings_upsert_failed: { friendly: 'Falha ao salvar configuracoes.', detail: 'settings_upsert_failed' },
  invalid_setting_value: { friendly: 'Configuracao invalida.', detail: 'invalid_setting_value' },
  unsupported_setting: { friendly: 'Configuracao nao suportada.', detail: 'unsupported_setting' },
  settings_required: { friendly: 'Nenhuma configuracao para salvar.', detail: 'settings_required' },
  overview_fetch_failed: { friendly: 'Falha ao carregar gestao.', detail: 'overview_fetch_failed' },
  commands_fetch_failed: { friendly: 'Falha ao carregar fila.', detail: 'commands_fetch_failed' },
  cards_search_failed: { friendly: 'Falha ao buscar cartas.', detail: 'cards_search_failed' },
  command_cancel_failed: { friendly: 'Falha ao cancelar comando.', detail: 'command_cancel_failed' },
  command_not_cancellable: { friendly: 'Comando nao pode mais ser cancelado.', detail: 'command_not_cancellable' },
};

const WEEKDAYS = [
  { code: 'mon', label: 'Seg' },
  { code: 'tue', label: 'Ter' },
  { code: 'wed', label: 'Qua' },
  { code: 'thu', label: 'Qui' },
  { code: 'fri', label: 'Sex' },
  { code: 'sat', label: 'Sab' },
  { code: 'sun', label: 'Dom' },
];

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

function resolveError(code, fallback) {
  return ERROR_MESSAGES[code] || { friendly: fallback || 'Erro desconhecido.', detail: code || '' };
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
    apiBase: apiBase || 'nao configurado',
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

function formatDateTime(value) {
  if (!value) return '-';
  try {
    return new Date(value).toLocaleString('pt-BR');
  } catch {
    return value;
  }
}

function commandCaption(command) {
  const parts = [
    command.status,
    command.created_at ? formatDateTime(command.created_at) : null,
    command.last_error || null,
  ].filter(Boolean);
  return parts.join(' | ');
}

function CommandRow({ command, onCancel, loading }) {
  const cancellable = ['pending', 'retrying'].includes(command.status);
  return (
    <div className="tg-command-row">
      <div className="tg-command-row__main">
        <span className="tg-row__label">{command.command_type}</span>
        <span className="tg-row__caption">{commandCaption(command)}</span>
      </div>
      <Badge tone={command.status === 'failed' ? 'err' : command.status === 'executed' ? 'ok' : 'warn'}>
        {command.status}
      </Badge>
      {cancellable && (
        <button className="tg-icon-button" type="button" onClick={() => onCancel(command.id)} disabled={loading} aria-label="Cancelar comando">
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
        const error = resolveError(json.error, `HTTP ${resp.status}`);
        setResult({ ok: false, friendly: error.friendly, detail: error.detail, at: new Date() });
      } else {
        setOverview(json);
        if (json.settings) applySettings(json.settings);
      }
    } catch {
      setResult({ ok: false, friendly: 'Falha de rede ao carregar gestao.', detail: '', at: new Date() });
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
        const error = resolveError(json.error, `HTTP ${resp.status}`);
        setResult({ ok: false, friendly: error.friendly, detail: error.detail, at: new Date() });
      } else {
        setCommands(json.commands || []);
      }
    } catch {
      setResult({ ok: false, friendly: 'Falha de rede ao carregar fila.', detail: '', at: new Date() });
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
        const error = resolveError(json.error, `HTTP ${resp.status}`);
        setResult({ ok: false, friendly: error.friendly, detail: error.detail, at: new Date() });
      } else {
        setCardResults(json.cards || []);
      }
    } catch {
      setResult({ ok: false, friendly: 'Falha de rede ao buscar cartas.', detail: '', at: new Date() });
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
        const error = resolveError(json.error, `HTTP ${resp.status}`);
        setResult({ ok: false, friendly: error.friendly, detail: error.detail, at: new Date() });
      } else {
        haptic('notification', 'success');
        setResult({ ok: true, command_type: json.command?.command_type || 'cancel', friendly: 'Comando cancelado.', detail: '', at: new Date() });
        fetchCommands();
        fetchOverview();
      }
    } catch {
      haptic('notification', 'error');
      setResult({ ok: false, friendly: 'Falha de rede ao cancelar comando.', detail: '', at: new Date() });
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
        const error = resolveError(json.error, `HTTP ${resp.status}`);
        setSettingsResult({ ok: false, friendly: error.friendly, detail: error.detail, at: new Date() });
      } else {
        applySettings(json.settings);
        setSettingsResult(null);
      }
    } catch {
      setSettingsResult({ ok: false, friendly: 'Falha de rede ao carregar configuracoes.', detail: '', at: new Date() });
    } finally {
      setLoadingSettings(false);
    }
  }

  async function saveSettings() {
    const times = parseTimesInput(timesInput);
    if (!validateTimes(times)) {
      haptic('notification', 'error');
      setSettingsResult({ ok: false, friendly: 'Horarios devem usar HH:MM.', detail: 'Exemplo: 09:00, 21:30', at: new Date() });
      return;
    }
    if (!settings.daily_post_days.length) {
      haptic('notification', 'error');
      setSettingsResult({ ok: false, friendly: 'Selecione pelo menos um dia.', detail: '', at: new Date() });
      return;
    }
    if (!settings.timezone.trim()) {
      haptic('notification', 'error');
      setSettingsResult({ ok: false, friendly: 'Timezone obrigatorio.', detail: '', at: new Date() });
      return;
    }

    const url = buildApiUrl('/settings');
    if (!url) {
      setSettingsResult({ ok: false, friendly: 'Worker nao configurado.', detail: 'Defina VITE_COMMANDS_API_URL.', at: new Date() });
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
        const error = resolveError(json.error, `HTTP ${resp.status}`);
        setSettingsResult({
          ok: false,
          friendly: error.friendly,
          detail: [error.detail, json.key && `key: ${json.key}`].filter(Boolean).join('\n'),
          at: new Date(),
        });
      } else {
        haptic('notification', 'success');
        applySettings(json.settings);
        setSettingsResult({ ok: true, friendly: 'Configuracoes salvas.', detail: '', at: new Date() });
      }
    } catch {
      haptic('notification', 'error');
      setSettingsResult({ ok: false, friendly: 'Falha de rede ao salvar configuracoes.', detail: '', at: new Date() });
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
      setResult({ ok: false, friendly: 'Worker nao configurado.', detail: 'Defina VITE_COMMANDS_API_URL.', at: new Date() });
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
        const error = resolveError(json.error, `HTTP ${resp.status}`);
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
          friendly: 'Comando enfileirado.',
          detail: json.command?.id ? `ID: ${json.command.id}` : '',
          at: new Date(),
        });
        fetchStatus();
        fetchCommands();
        fetchOverview();
      }
    } catch {
      haptic('notification', 'error');
      setResult({ ok: false, command_type, friendly: 'Falha de rede ao chamar o Worker.', detail: '', at: new Date() });
    } finally {
      setLoadingCmd(null);
    }
  }, [loadingCmd, targetChatId]);

  const adminValue = loadingMe
    ? 'verificando'
    : !apiConfigured
      ? 'sem API'
      : me?.ok && isAdmin
        ? me.role || 'admin'
        : me?.ok
          ? me.role || 'none'
          : me?.error === 'network_error'
            ? 'sem rede'
            : 'pendente';

  const workerValue = loadingStatus ? '...' : sysStatus?.ok ? 'online' : 'offline';
  const cardsValue = loadingOverview ? '...' : (overview?.counts?.cards ?? sysStatus?.total_cards ?? '-');
  const queueValue = loadingOverview ? '...' : (overview?.counts?.pending_commands ?? 0);
  const targetChats = overview?.target_chats?.filter((chat) => chat.enabled !== false) || [];

  return (
    <div className="app">
      <header className="tg-profile">
        <div className="tg-avatar" aria-hidden="true"><Icon name="bot" /></div>
        <div className="tg-profile__title">Arkham Bot</div>
        <div className="tg-profile__subtitle">Admin Console</div>
      </header>

      {isOutsideTelegram && <Notice>Abra pelo Telegram para autenticar.</Notice>}
      {!apiConfigured && <Notice tone="err">Worker nao configurado.</Notice>}

      {activeTab === 'menu' && (
        <>
          <Section title="Settings">
            <MenuRow icon="send" label="Postar carta" caption="Buscar carta, escolher destino e publicar" onClick={() => setActiveTab('post')} />
            <MenuRow icon="settings" label="Controles" caption="Pausar, sincronizar, resetar ciclo e limpar fila" onClick={() => setActiveTab('controls')} />
            <MenuRow icon="clock" label="Agenda" caption={`${settings.daily_post_times.join(', ')} | ${settings.timezone}`} onClick={() => setActiveTab('schedule')} />
            <MenuRow icon="queue" label="Fila" caption="Comandos recentes e cancelamento" value={queueValue} onClick={() => setActiveTab('queue')} />
            <MenuRow icon="server" label="Saude" caption="Worker, acesso, cards e diagnostico" value={workerValue} onClick={() => setActiveTab('status')} />
          </Section>
        </>
      )}


      {activeTab === 'post' && (
        <>
          <Section title="Postar carta">
            <div className="tg-form-row">
              <Field label="Buscar por codigo ou nome">
                <div className="tg-search-line">
                  <input
                    className="tg-input tg-input--boxed"
                    type="text"
                    value={cardQuery}
                    onChange={(event) => setCardQuery(event.target.value)}
                    placeholder="01001 ou Shrivelling"
                    inputMode="text"
                  />
                  <MiniButton icon="search" label="Buscar" onClick={searchCards} loading={searchingCards} disabled={!isAdmin || isOutsideTelegram || !apiConfigured || cardQuery.trim().length < 2} />
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
              <Field label="Carta selecionada" hint="Postar agora pode usar carta vazia para escolha automatica. Repostar e pular exigem codigo.">
                <input
                  className="tg-input tg-input--boxed"
                  type="text"
                  placeholder="Codigo da carta, ex: 01001"
                  value={cardCode}
                  onChange={(e) => setCardCode(e.target.value.trim())}
                  inputMode="text"
                />
              </Field>
            </div>
            {targetChats.length > 0 && (
              <div className="tg-form-row">
                <SelectField label="Destino" value={targetChatId} onChange={setTargetChatId}>
                  <option value="">Chat padrao do bot</option>
                  {targetChats.map((chat) => (
                    <option key={chat.chat_id} value={chat.chat_id}>
                      {chat.title || chat.chat_id}
                    </option>
                  ))}
                </SelectField>
              </div>
            )}
            <ActionRow icon="send" label="Postar agora" caption={cardCode ? `Carta ${cardCode}` : 'Escolha automatica'} onClick={() => enqueue('post_now', cardCode ? { card_code: cardCode } : {})} loading={loadingCmd === 'post_now'} disabled={actionsDisabled} />
            <ActionRow icon="repeat" label="Repostar carta" caption={cardCode ? `Carta ${cardCode}` : 'Informe o codigo da carta'} onClick={() => enqueue('repost_card', { card_code: cardCode })} loading={loadingCmd === 'repost_card'} disabled={actionsDisabled || !cardCode} />
            <ActionRow icon="skip" label="Pular carta" caption={cardCode ? `Carta ${cardCode}` : 'Informe o codigo da carta'} onClick={() => enqueue('skip_card', { card_code: cardCode })} loading={loadingCmd === 'skip_card'} disabled={actionsDisabled || !cardCode} />
          </Section>
        </>
      )}

      {activeTab === 'controls' && (
        <>
          <Section title="Mode Settings">
            <SwitchField
              label="Postagem diaria"
              checked={settings.daily_post_enabled}
              disabled={actionsDisabled}
              onChange={(checked) => enqueue(checked ? 'resume_daily_post' : 'pause_daily_post')}
            />
            <div className="tg-section__footer">Ativa ou pausa a rotina automatica de carta diaria.</div>
            <ActionRow icon="sync" label="Sincronizar ArkhamDB" caption="Atualiza cartas e pacotes" onClick={() => enqueue('sync_arkhamdb', { sync_faq: false })} loading={loadingCmd === 'sync_arkhamdb'} disabled={actionsDisabled} />
            <ActionRow icon="reset" label="Resetar ciclo" caption="Permite repetir cartas ja usadas" onClick={() => enqueue('reset_cycle')} loading={loadingCmd === 'reset_cycle'} disabled={actionsDisabled} danger />
            <ActionRow icon="trash" label="Limpar fila" caption="Cancela comandos pendentes" onClick={() => enqueue('clear_queue')} loading={loadingCmd === 'clear_queue'} disabled={actionsDisabled} danger />
          </Section>
        </>
      )}

      {activeTab === 'schedule' && (
        <>
          <Section title="Agenda de postagem">
            <SwitchField
              label="daily_post_enabled"
              checked={settings.daily_post_enabled}
              onChange={(checked) => setSettings((current) => ({ ...current, daily_post_enabled: checked }))}
            />
            <div className="tg-form-row">
              <Field label="daily_post_times" hint="Exemplo: 09:00, 21:30">
                <input className="tg-input tg-input--boxed" type="text" value={timesInput} onChange={(event) => setTimesInput(event.target.value)} placeholder="09:00, 21:30" inputMode="text" />
              </Field>
            </div>
            <div className="tg-form-row">
              <span className="tg-field__label">daily_post_days</span>
              <div className="tg-day-grid">
                {WEEKDAYS.map((day) => (
                  <button key={day.code} className={`tg-day ${settings.daily_post_days.includes(day.code) ? 'active' : ''}`.trim()} type="button" onClick={() => toggleDay(day.code)}>
                    {day.label}
                  </button>
                ))}
              </div>
            </div>
            <div className="tg-form-row">
              <Field label="timezone">
                <input className="tg-input tg-input--boxed" type="text" value={settings.timezone} onChange={(event) => setSettings((current) => ({ ...current, timezone: event.target.value }))} placeholder="America/Sao_Paulo" inputMode="text" />
              </Field>
            </div>
            <ActionRow icon="refresh" label="Recarregar configuracoes" onClick={fetchSettings} loading={loadingSettings} disabled={!apiConfigured} />
            <ActionRow icon="save" label="Salvar configuracoes" onClick={saveSettings} loading={savingSettings} disabled={actionsDisabled} />
          </Section>

          {settingsResult && (
            <Section title="Configuracoes">
              <Row icon="settings" label={settingsResult.ok ? 'Sucesso' : 'Erro'} value={settingsResult.ok ? 'ok' : 'erro'} badgeTone={settingsResult.ok ? 'ok' : 'err'} caption={settingsResult.friendly} />
              {settingsResult.detail && (
                <details className="tg-details">
                  <summary>Detalhes</summary>
                  <pre className="diag-pre">{settingsResult.detail}</pre>
                </details>
              )}
            </Section>
          )}
        </>
      )}

      {activeTab === 'queue' && (
        <>
          <Section title="Fila de comandos">
            <ActionRow icon="refresh" label="Atualizar fila" onClick={() => fetchCommands()} loading={loadingCommands} disabled={!apiConfigured} />
            {commands.length === 0 && <Row icon="queue" label="Nenhum comando recente" value="-" />}
            {commands.map((command) => (
              <CommandRow key={command.id} command={command} onCancel={cancelCommand} loading={cancellingCommand === command.id} />
            ))}
          </Section>
        </>
      )}

      {activeTab === 'status' && (
        <>
          <Section title="Resumo">
            <Row icon="server" label="Worker" value={workerValue} badgeTone={sysStatus?.ok ? 'ok' : 'err'} />
            <Row icon="shield" label="Acesso" value={adminValue} badgeTone={isAdmin ? 'ok' : 'err'} />
            <Row icon="cards" label="Cards" value={cardsValue} />
            <Row icon="queue" label="Fila" value={queueValue} />
          </Section>

          <Section title="Conta">
            <Row icon="plug" label="Telegram WebApp" value={diag.webAppDetected ? 'sim' : 'nao'} badgeTone={statusTone(diag.webAppDetected)} />
            <Row icon="key" label="initData" value={diag.initDataPresent ? 'presente' : 'ausente'} badgeTone={statusTone(diag.initDataPresent)} />
            <Row icon="shield" label="Admin" value={adminValue} badgeTone={isAdmin ? 'ok' : 'err'} caption={me?.admin_source ? `source: ${me.admin_source}` : undefined} />
            <ActionRow icon="refresh" label="Reverificar autenticacao" onClick={fetchMe} loading={loadingMe} disabled={!apiConfigured} />
          </Section>

          <Section title="Sistema">
            <Row icon="server" label="Worker" value={sysStatus?.ok ? 'online' : 'offline'} badgeTone={statusTone(sysStatus?.ok)} />
            <Row icon="cards" label="Cards" value={loadingStatus ? '...' : (sysStatus?.total_cards ?? '-')} />
            <Row icon="packs" label="Packs" value={loadingStatus ? '...' : (sysStatus?.total_packs ?? '-')} />
            <Row icon="clock" label="Ultimo sync" value={(overview?.last_sync || sysStatus?.last_sync) ? new Date(overview?.last_sync || sysStatus.last_sync).toLocaleString('pt-BR') : '-'} mono />
            <ActionRow icon="refresh" label="Atualizar status" onClick={() => { fetchStatus(); fetchOverview(); }} loading={loadingStatus || loadingOverview} disabled={!apiConfigured} />
          </Section>

          <Section title="Diagnostico">
            <details className="tg-details">
              <summary><Icon name="info" />Mostrar detalhes</summary>
              <pre className="diag-pre">{[
                `Telegram WebApp: ${diag.webAppDetected}`,
                `initData presente: ${diag.initDataPresent}`,
                `initData length: ${diag.initDataLength}`,
                `Usuario unsafe: ${diag.userDetectedViaUnsafe}`,
                `API configurada: ${diag.apiConfigured}`,
                `Endpoint base: ${diag.apiBase}`,
                `Admin: ${Boolean(me?.admin)}`,
                `Role: ${me?.role || '-'}`,
                `Admin source: ${me?.admin_source || '-'}`,
              ].join('\n')}</pre>
            </details>
          </Section>
        </>
      )}

      {result && activeTab !== 'status' && (
        <Section title="Resultado">
          <Row
            icon="result"
            label={result.ok ? 'Sucesso' : 'Erro'}
            value={result.command_type || '-'}
            badgeTone={result.ok ? 'ok' : 'err'}
            caption={result.friendly}
          />
          {result.detail && (
            <details className="tg-details">
              <summary>Detalhes</summary>
              <pre className="diag-pre">{result.detail}</pre>
            </details>
          )}
        </Section>
      )}
    </div>
  );
}

createRoot(document.getElementById('root')).render(<App />);
