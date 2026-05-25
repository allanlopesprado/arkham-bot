import React, { useCallback, useEffect, useState } from 'react';
import { createRoot } from 'react-dom/client';
import './style.css';

// ─── Telegram helpers ─────────────────────────────────────────────────────────

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
  } catch { /* ignore */ }
}

// ─── Error messages ───────────────────────────────────────────────────────────

const ERROR_MESSAGES = {
  invalid_telegram_init_data: { friendly: 'Abra este painel pelo Telegram para autenticar.', detail: 'Worker rejeitou initData.' },
  unauthorized:               { friendly: 'Usuário não autorizado para comandos administrativos.', detail: 'Seu Telegram user id não está cadastrado como admin.' },
  not_found:                  { friendly: 'Endpoint do Worker não encontrado.', detail: 'Verifique VITE_COMMANDS_API_URL.' },
  origin_not_allowed:         { friendly: 'Origem não autorizada no Worker.', detail: 'Verifique ALLOWED_ORIGINS.' },
  bot_command_insert_failed:  { friendly: 'Falha ao criar comando no Supabase.', detail: 'Verifique Worker secrets e tabela bot_commands.' },
  command_type_required:      { friendly: 'Tipo de comando não informado.', detail: 'command_type_required' },
  unsupported_command_type:   { friendly: 'Tipo de comando não suportado.', detail: 'unsupported_command_type' },
  method_not_allowed:         { friendly: 'Método HTTP não permitido.', detail: 'method_not_allowed' },
};

function resolveError(code, fallback) {
  return ERROR_MESSAGES[code] || { friendly: fallback || 'Erro desconhecido.', detail: code || '' };
}

// ─── Diagnostics (safe — never exposes initData raw) ──────────────────────────

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
    apiBase: apiBase || '(não configurado)',
  };
}

// ─── Row components ───────────────────────────────────────────────────────────

function InfoRow({ icon, label, value, valueClass = '' }) {
  return (
    <div className="tg-row">
      {icon && <span className="tg-row__icon">{icon}</span>}
      <span className="tg-row__label" style={{ color: 'var(--tg-text)' }}>{label}</span>
      <span className={`tg-row__value ${valueClass}`}>{value}</span>
    </div>
  );
}

function ActionRow({ icon, label, onClick, disabled, loading, danger }) {
  return (
    <button
      className={`tg-row tg-row--action${danger ? ' danger' : ''}${loading ? ' tg-row--loading' : ''}`}
      onClick={onClick}
      disabled={disabled || loading}
      type="button"
    >
      {icon && <span className="tg-row__icon">{icon}</span>}
      <span className="tg-row__label">{label}</span>
      {loading ? <span className="spinner" /> : <span className="tg-row__chevron">›</span>}
    </button>
  );
}

// ─── App ──────────────────────────────────────────────────────────────────────

function App() {
  const [diag, setDiag] = useState(() => buildDiag());
  const [me, setMe] = useState(null);
  const [sysStatus, setSysStatus] = useState(null);
  const [result, setResult] = useState(null);
  const [cardCode, setCardCode] = useState('');
  const [loadingCmd, setLoadingCmd] = useState(null);
  const [loadingMe, setLoadingMe] = useState(false);
  const [loadingStatus, setLoadingStatus] = useState(false);

  // ─── Init Telegram SDK ──────────────────────────────────────────────────────
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

  useEffect(() => { fetchMe(); fetchStatus(); }, []); // eslint-disable-line

  const isAdmin = me?.admin === true;
  const apiConfigured = diag.apiConfigured;
  const isOutsideTelegram = !diag.webAppDetected || !diag.initDataPresent;
  const actionsDisabled = !isAdmin || isOutsideTelegram || !apiConfigured || loadingCmd !== null;

  // ─── /me ────────────────────────────────────────────────────────────────────
  async function fetchMe() {
    const url = buildApiUrl('/me');
    if (!url) return;
    setLoadingMe(true);
    try {
      const resp = await fetch(url, { headers: { 'x-telegram-init-data': getTelegramInitData() } });
      setMe(await resp.json().catch(() => ({})));
    } catch { setMe({ ok: false, error: 'network_error' }); }
    finally { setLoadingMe(false); }
  }

  // ─── /status ────────────────────────────────────────────────────────────────
  async function fetchStatus() {
    const url = buildApiUrl('/status');
    if (!url) return;
    setLoadingStatus(true);
    try {
      const resp = await fetch(url, { headers: { 'x-telegram-init-data': getTelegramInitData() } });
      setSysStatus(await resp.json().catch(() => ({})));
    } catch { setSysStatus({ ok: false, error: 'network_error' }); }
    finally { setLoadingStatus(false); }
  }

  // ─── Enqueue ─────────────────────────────────────────────────────────────────
  const enqueue = useCallback(async (command_type, payload = {}) => {
    if (loadingCmd) return;
    haptic('impact', 'light');
    const url = buildApiUrl('/bot-command');
    if (!url) {
      setResult({ ok: false, friendly: 'Painel sem conexão com Worker.', detail: 'Defina VITE_COMMANDS_API_URL e publique o Pages.', at: new Date() });
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
        setResult({ ok: false, command_type, ...resolveError(json.error, `HTTP ${resp.status}`), at: new Date() });
      } else {
        haptic('notification', 'success');
        setResult({
          ok: true, command_type: json.command?.command_type || command_type,
          friendly: 'Comando enfileirado com sucesso.',
          detail: json.command?.id ? `ID: ${json.command.id}` : '',
          at: new Date(),
        });
        fetchStatus();
      }
    } catch {
      haptic('notification', 'error');
      setResult({ ok: false, command_type, friendly: 'Falha de rede ao chamar o Worker.', detail: '', at: new Date() });
    } finally { setLoadingCmd(null); }
  }, [loadingCmd]);

  // ─── Helper: admin/connection status label ────────────────────────────────────
  function adminLabel() {
    if (loadingMe) return ['…', ''];
    if (!apiConfigured) return ['sem API', 'warn'];
    if (!me) return ['—', ''];
    if (me.error === 'network_error') return ['sem rede', 'err'];
    if (me.ok && isAdmin) return [`sim · ${me.role || 'admin'}`, 'ok'];
    if (me.ok && !isAdmin) return [`não · ${me.role || 'none'}`, 'err'];
    return ['não autenticado', 'err'];
  }

  const [adminVal, adminClass] = adminLabel();

  // ─── Actions list ─────────────────────────────────────────────────────────────
  const actions = [
    { cmd: 'post_now',        icon: '📤', label: 'Postar agora',   payload: cardCode ? { card_code: cardCode } : {} },
    { cmd: 'skip_card',       icon: '⏭',  label: 'Pular carta',    payload: cardCode ? { card_code: cardCode } : {} },
    { cmd: 'pause_daily_post',icon: '⏸',  label: 'Pausar diário' },
    { cmd: 'resume_daily_post',icon: '▶', label: 'Retomar diário' },
    { cmd: 'sync_arkhamdb',   icon: '🔄', label: 'Sync ArkhamDB',  payload: { sync_faq: false } },
  ];

  // ─── Render ───────────────────────────────────────────────────────────────────
  return (
    <div className="app">

      {/* Header */}
      <div className="tg-header">
        <div className="tg-header__title">Arkham Bot Admin</div>
        <div className="tg-header__sub">Painel de controle</div>
      </div>

      {/* Aviso fora do Telegram */}
      {isOutsideTelegram && (
        <div className="tg-notice">
          ⚠ Aberto fora do Telegram — initData indisponível. Autenticação não funcionará.
        </div>
      )}

      {/* Aviso sem API */}
      {!apiConfigured && (
        <div className="tg-notice">
          Worker não configurado. Defina VITE_COMMANDS_API_URL e publique o Pages.
        </div>
      )}

      {/* Seção: Conexão */}
      <div className="tg-section">
        <div className="tg-section__label">Conexão</div>
        <div className="tg-section__body">
          <InfoRow icon="✈️" label="Telegram WebApp" value={diag.webAppDetected ? 'sim' : 'não'} valueClass={diag.webAppDetected ? 'ok' : 'err'} />
          <InfoRow icon="🔑" label="initData"        value={diag.initDataPresent ? `sim · ${diag.initDataLength}c` : 'não'} valueClass={diag.initDataPresent ? 'ok' : 'err'} />
          <InfoRow icon="🛡" label="Admin"           value={adminVal} valueClass={adminClass} />
          <InfoRow icon="🌐" label="API"             value={diag.apiConfigured ? 'configurada' : 'não configurada'} valueClass={diag.apiConfigured ? 'ok' : 'err'} />
        </div>
        <div className="tg-section__body" style={{ marginTop: 1 }}>
          <button className="tg-btn-inline" onClick={fetchMe} disabled={loadingMe}>
            {loadingMe ? 'Verificando…' : '↺  Reverificar autenticação'}
          </button>
        </div>
      </div>

      {/* Seção: Sistema */}
      <div className="tg-section">
        <div className="tg-section__label">Sistema</div>
        <div className="tg-section__body">
          {loadingStatus && <div className="tg-row"><span className="tg-row__label" style={{color:'var(--tg-hint)'}}>Carregando…</span></div>}
          {sysStatus && !loadingStatus && <>
            <InfoRow icon="⚡" label="Worker"        value={sysStatus.ok ? 'online' : 'offline'} valueClass={sysStatus.ok ? 'ok' : 'err'} />
            <InfoRow icon="🃏" label="Cards"         value={sysStatus.total_cards ?? '—'} />
            <InfoRow icon="📦" label="Packs"         value={sysStatus.total_packs ?? '—'} />
            <InfoRow icon="🔄" label="Último sync"   value={sysStatus.last_sync ? new Date(sysStatus.last_sync).toLocaleString('pt-BR') : '—'} valueClass="mono" />
            <InfoRow icon="📋" label="Último cmd"    value={sysStatus.last_command ?? '—'} valueClass="mono" />
          </>}
          {!sysStatus && !loadingStatus && (
            <div className="tg-row"><span className="tg-row__value">Não disponível</span></div>
          )}
        </div>
        <div className="tg-section__body" style={{ marginTop: 1 }}>
          <button className="tg-btn-inline" onClick={fetchStatus} disabled={loadingStatus}>
            {loadingStatus ? 'Atualizando…' : '↺  Atualizar status'}
          </button>
        </div>
      </div>

      {/* Seção: Carta alvo */}
      <div className="tg-section">
        <div className="tg-section__label">Carta alvo</div>
        <div className="tg-section__body">
          <div className="tg-input-wrap">
            <input
              className="tg-input"
              type="text"
              placeholder="Código da carta, ex: 01001"
              value={cardCode}
              onChange={(e) => setCardCode(e.target.value)}
              inputMode="text"
            />
          </div>
        </div>
        <div className="tg-section__footer">Usado por "Postar agora" e "Pular carta".</div>
      </div>

      {/* Seção: Ações */}
      <div className="tg-section">
        <div className="tg-section__label">Ações</div>
        {!isAdmin && me && !isOutsideTelegram && apiConfigured && (
          <div className="tg-section__footer" style={{ paddingBottom: 6 }}>
            Usuário não é admin. Ações desabilitadas.
          </div>
        )}
        <div className="tg-section__body">
          {actions.map(({ cmd, icon, label, payload }) => (
            <ActionRow
              key={cmd}
              icon={icon}
              label={label}
              loading={loadingCmd === cmd}
              disabled={actionsDisabled}
              onClick={() => enqueue(cmd, payload || {})}
            />
          ))}
        </div>
      </div>

      {/* Resultado */}
      {result && (
        <div className="tg-section">
          <div className="tg-section__label">Última ação</div>
          <div className="tg-result">
            <div className={`tg-result__status ${result.ok ? 'ok' : 'err'}`}>
              {result.ok ? '✓ Sucesso' : '✗ Erro'}
              <span style={{ fontWeight: 400, fontSize: 13, marginLeft: 'auto', color: 'var(--tg-hint)' }}>
                {result.at?.toLocaleTimeString('pt-BR')}
              </span>
            </div>
            <div className="tg-result__body">{result.friendly}</div>
            {result.detail && (
              <details>
                <summary>Detalhes técnicos</summary>
                <pre className="diag-pre">{result.detail}</pre>
              </details>
            )}
          </div>
        </div>
      )}

      {/* Diagnóstico (recolhido por padrão) */}
      <div className="tg-section">
        <details>
          <summary>Diagnóstico</summary>
          <pre className="diag-pre">{[
            `Telegram WebApp: ${diag.webAppDetected}`,
            `initData presente: ${diag.initDataPresent}`,
            `initData length: ${diag.initDataLength}`,
            `Usuário unsafe: ${diag.userDetectedViaUnsafe}`,
            `API configurada: ${diag.apiConfigured}`,
            `Endpoint base: ${diag.apiBase}`,
          ].join('\n')}</pre>
        </details>
      </div>

    </div>
  );
}

createRoot(document.getElementById('root')).render(<App />);
