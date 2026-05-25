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
};

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

function App() {
  const [diag, setDiag] = useState(() => buildDiag());
  const [me, setMe] = useState(null);
  const [sysStatus, setSysStatus] = useState(null);
  const [result, setResult] = useState(null);
  const [cardCode, setCardCode] = useState('');
  const [loadingCmd, setLoadingCmd] = useState(null);
  const [loadingMe, setLoadingMe] = useState(false);
  const [loadingStatus, setLoadingStatus] = useState(false);

  useEffect(() => {
    const tg = getTelegramWebApp();
    if (tg) {
      tg.ready?.();
      tg.expand?.();
      try { tg.setHeaderColor?.('secondary_bg_color'); } catch {}
      try { tg.setBackgroundColor?.('bg_color'); } catch {}
      try { tg.setBottomBarColor?.('secondary_bg_color'); } catch {}
    }
    setDiag(buildDiag());
  }, []);

  useEffect(() => { fetchMe(); fetchStatus(); }, []);

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
        body: JSON.stringify({ command_type, payload }),
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
      }
    } catch {
      haptic('notification', 'error');
      setResult({ ok: false, command_type, friendly: 'Falha de rede ao chamar o Worker.', detail: '', at: new Date() });
    } finally {
      setLoadingCmd(null);
    }
  }, [loadingCmd]);

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
  const cardsValue = loadingStatus ? '...' : (sysStatus?.total_cards ?? '-');
  const syncValue = sysStatus?.last_sync ? new Date(sysStatus.last_sync).toLocaleDateString('pt-BR') : '-';

  const actions = [
    { cmd: 'post_now', icon: 'send', label: 'Postar agora', caption: cardCode ? `Carta ${cardCode}` : 'Carta diaria' },
    { cmd: 'skip_card', icon: 'skip', label: 'Pular carta', caption: cardCode ? `Carta ${cardCode}` : 'Informe o codigo da carta', payload: cardCode ? { card_code: cardCode } : {} },
    { cmd: 'pause_daily_post', icon: 'pause', label: 'Pausar diario', caption: 'Desativa proximas postagens' },
    { cmd: 'resume_daily_post', icon: 'play', label: 'Retomar diario', caption: 'Reativa o agendamento' },
    { cmd: 'sync_arkhamdb', icon: 'sync', label: 'Sincronizar ArkhamDB', caption: 'Atualiza dados no Supabase', payload: { sync_faq: false } },
  ];

  return (
    <div className="app">
      <header className="tg-profile">
        <div className="tg-avatar" aria-hidden="true"><Icon name="bot" /></div>
        <div className="tg-profile__title">Arkham Bot</div>
        <div className="tg-profile__subtitle">Admin Console</div>
      </header>

      <section className="tg-summary" aria-label="Resumo">
        <SummaryItem icon="server" label="Worker" value={workerValue} />
        <SummaryItem icon="shield" label="Acesso" value={adminValue} />
        <SummaryItem icon="cards" label="Cards" value={cardsValue} />
        <SummaryItem icon="clock" label="Sync" value={syncValue} />
      </section>

      {isOutsideTelegram && <Notice>Abra pelo Telegram para autenticar.</Notice>}
      {!apiConfigured && <Notice tone="err">Worker nao configurado.</Notice>}

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
        <Row icon="clock" label="Ultimo sync" value={sysStatus?.last_sync ? new Date(sysStatus.last_sync).toLocaleString('pt-BR') : '-'} mono />
        <ActionRow icon="refresh" label="Atualizar status" onClick={fetchStatus} loading={loadingStatus} disabled={!apiConfigured} />
      </Section>

      <Section title="Carta alvo" footer="Usada por Postar agora e Pular carta.">
        <div className="tg-input-row">
          <Icon name="target" />
          <input
            className="tg-input"
            type="text"
            placeholder="Codigo da carta, ex: 01001"
            value={cardCode}
            onChange={(e) => setCardCode(e.target.value.trim())}
            inputMode="text"
          />
        </div>
      </Section>

      <Section title="Comandos" footer={!isAdmin && me && !isOutsideTelegram && apiConfigured ? 'Usuario sem permissao administrativa.' : undefined}>
        {actions.map(({ cmd, icon, label, caption, payload }) => (
          <ActionRow
            key={cmd}
            icon={icon}
            label={label}
            caption={caption}
            loading={loadingCmd === cmd}
            disabled={actionsDisabled || (cmd === 'skip_card' && !cardCode)}
            onClick={() => enqueue(cmd, payload || (cardCode ? { card_code: cardCode } : {}))}
          />
        ))}
      </Section>

      {result && (
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
    </div>
  );
}

createRoot(document.getElementById('root')).render(<App />);
