import React, { useCallback, useEffect, useRef, useState } from 'react';
import { createRoot } from 'react-dom/client';
import './style.css';

// ─── Telegram helpers ────────────────────────────────────────────────────────

function getTelegramWebApp() {
  return window.Telegram?.WebApp || null;
}

function getTelegramInitData() {
  return getTelegramWebApp()?.initData || '';
}

function getTelegramUserUnsafe() {
  return getTelegramWebApp()?.initDataUnsafe?.user || null;
}

function getTelegramTheme() {
  const tg = getTelegramWebApp();
  if (!tg) return {};
  return {
    bgColor: tg.backgroundColor || null,
    headerColor: tg.headerColor || null,
    themeParams: tg.themeParams || {},
  };
}

function getApiBase() {
  const raw = import.meta.env.VITE_COMMANDS_API_URL || '';
  if (!raw) return '';
  try {
    const url = new URL(raw);
    return url.origin;
  } catch {
    return raw;
  }
}

function buildApiUrl(path) {
  const base = getApiBase();
  if (!base) return '';
  return `${base.replace(/\/$/, '')}${path}`;
}

// ─── Haptic helpers ───────────────────────────────────────────────────────────

function haptic(type, value) {
  try {
    const hf = getTelegramWebApp()?.HapticFeedback;
    if (!hf) return;
    if (type === 'notification') hf.notificationOccurred(value);
    else if (type === 'impact') hf.impactOccurred(value);
  } catch {
    // ignore
  }
}

// ─── Error message map ────────────────────────────────────────────────────────

const ERROR_MESSAGES = {
  invalid_telegram_init_data: {
    friendly: 'Abra este painel pelo Telegram para autenticar.',
    detail: 'Worker rejeitou initData.',
  },
  unauthorized: {
    friendly: 'Usuário não autorizado para comandos administrativos.',
    detail: 'Seu Telegram user id não está cadastrado como admin.',
  },
  not_found: {
    friendly: 'Endpoint do Worker não encontrado.',
    detail: 'Verifique VITE_COMMANDS_API_URL.',
  },
  origin_not_allowed: {
    friendly: 'Origem não autorizada no Worker.',
    detail: 'Verifique ALLOWED_ORIGINS.',
  },
  bot_command_insert_failed: {
    friendly: 'Falha ao criar comando no Supabase.',
    detail: 'Verifique Worker secrets e tabela bot_commands.',
  },
  command_type_required: {
    friendly: 'Tipo de comando não informado.',
    detail: 'command_type_required',
  },
  unsupported_command_type: {
    friendly: 'Tipo de comando não suportado.',
    detail: 'unsupported_command_type',
  },
  method_not_allowed: {
    friendly: 'Método HTTP não permitido.',
    detail: 'method_not_allowed',
  },
};

function resolveError(errorCode, fallback) {
  const entry = ERROR_MESSAGES[errorCode];
  if (entry) return entry;
  return { friendly: fallback || 'Erro desconhecido.', detail: errorCode || '' };
}

// ─── Safe diagnostics (never prints initData raw) ────────────────────────────

function buildDiagnostics() {
  const tg = getTelegramWebApp();
  const initData = getTelegramInitData();
  const userUnsafe = getTelegramUserUnsafe();
  const apiBase = getApiBase();
  return {
    webAppDetected: Boolean(tg),
    initDataPresent: Boolean(initData),
    initDataLength: initData.length,
    userDetectedViaUnsafe: Boolean(userUnsafe),
    userIdDetected: Boolean(userUnsafe?.id),
    apiConfigured: Boolean(apiBase),
    apiBase: apiBase || '(não configurado)',
  };
}

// ─── Main App ─────────────────────────────────────────────────────────────────

function App() {
  const [diag, setDiag] = useState(() => buildDiagnostics());
  const [me, setMe] = useState(null);           // { ok, user, admin, role }
  const [sysStatus, setSysStatus] = useState(null); // /status response
  const [result, setResult] = useState(null);   // last action result
  const [cardCode, setCardCode] = useState('');
  const [loadingCmd, setLoadingCmd] = useState(null);
  const [loadingMe, setLoadingMe] = useState(false);
  const [loadingStatus, setLoadingStatus] = useState(false);
  const openedFora = useRef(false);

  // ─── Init Telegram SDK ──────────────────────────────────────────────────────
  useEffect(() => {
    const tg = getTelegramWebApp();
    if (tg) {
      tg.ready?.();
      tg.expand?.();
      if (tg.setHeaderColor) {
        try { tg.setHeaderColor('#0d0d12'); } catch {}
      }
      if (tg.setBackgroundColor) {
        try { tg.setBackgroundColor('#0d0d12'); } catch {}
      }
      if (tg.setBottomBarColor) {
        try { tg.setBottomBarColor('#0d0d12'); } catch {}
      }
    }
    setDiag(buildDiagnostics());
  }, []);

  // ─── Load /me + /status on mount ────────────────────────────────────────────
  useEffect(() => {
    fetchMe();
    fetchStatus();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const isAdmin = me?.admin === true;
  const isOutsideTelegram = !diag.webAppDetected || !diag.initDataPresent;

  // ─── /me ────────────────────────────────────────────────────────────────────
  async function fetchMe() {
    const url = buildApiUrl('/me');
    if (!url) return;
    setLoadingMe(true);
    try {
      const resp = await fetch(url, {
        headers: { 'x-telegram-init-data': getTelegramInitData() },
      });
      const json = await resp.json().catch(() => ({}));
      setMe(json);
    } catch {
      setMe({ ok: false, error: 'network_error' });
    } finally {
      setLoadingMe(false);
    }
  }

  // ─── /status ────────────────────────────────────────────────────────────────
  async function fetchStatus() {
    const url = buildApiUrl('/status');
    if (!url) return;
    setLoadingStatus(true);
    try {
      const resp = await fetch(url, {
        headers: { 'x-telegram-init-data': getTelegramInitData() },
      });
      const json = await resp.json().catch(() => ({}));
      setSysStatus(json);
    } catch {
      setSysStatus({ ok: false, error: 'network_error' });
    } finally {
      setLoadingStatus(false);
    }
  }

  // ─── Enqueue command ─────────────────────────────────────────────────────────
  const enqueue = useCallback(async (command_type, payload = {}) => {
    if (loadingCmd) return;
    haptic('impact', 'light');
    const url = buildApiUrl('/bot-command');
    if (!url) {
      setResult({ ok: false, friendly: 'VITE_COMMANDS_API_URL não configurado.', detail: '', at: new Date() });
      return;
    }
    setLoadingCmd(command_type);
    try {
      const resp = await fetch(url, {
        method: 'POST',
        headers: {
          'content-type': 'application/json',
          'x-telegram-init-data': getTelegramInitData(),
        },
        body: JSON.stringify({ command_type, payload }),
      });
      const json = await resp.json().catch(() => ({}));
      if (!resp.ok) {
        const { friendly, detail } = resolveError(json.error, `HTTP ${resp.status}`);
        haptic('notification', 'error');
        setResult({ ok: false, command_type, friendly, detail, at: new Date() });
      } else {
        haptic('notification', 'success');
        setResult({
          ok: true,
          command_type: json.command?.command_type || command_type,
          commandId: json.command?.id,
          friendly: `Comando enfileirado com sucesso.`,
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

  // ─── Render ──────────────────────────────────────────────────────────────────
  return (
    <div className="app">

      {/* Header */}
      <header className="app-header">
        <div className="header-eyebrow">Arkham Horror LCG</div>
        <h1>Arkham Bot Admin</h1>
        <p className="header-sub">Painel de controle Telegram</p>
      </header>

      {/* Aviso fora do Telegram */}
      {isOutsideTelegram && (
        <div className="card card--warn">
          <strong>⚠ Aberto fora do Telegram</strong>
          <p>Este painel requer autenticação via Telegram WebApp. initData não está disponível.</p>
        </div>
      )}

      {/* Card: Autenticação */}
      <div className="card">
        <h2>Autenticação</h2>
        <ul className="diag-list">
          <li>
            <span className="diag-label">Telegram WebApp detectado</span>
            <span className={`diag-val ${diag.webAppDetected ? 'ok' : 'err'}`}>
              {diag.webAppDetected ? 'sim' : 'não'}
            </span>
          </li>
          <li>
            <span className="diag-label">initData presente</span>
            <span className={`diag-val ${diag.initDataPresent ? 'ok' : 'err'}`}>
              {diag.initDataPresent ? 'sim' : 'não'} {diag.initDataPresent ? `(${diag.initDataLength} chars)` : ''}
            </span>
          </li>
          <li>
            <span className="diag-label">Usuário via initDataUnsafe</span>
            <span className={`diag-val ${diag.userDetectedViaUnsafe ? 'ok' : 'warn'}`}>
              {diag.userDetectedViaUnsafe ? 'sim' : 'não'}
            </span>
          </li>
          <li>
            <span className="diag-label">Admin validado (Worker)</span>
            <span className={`diag-val ${isAdmin ? 'ok' : me ? 'err' : 'warn'}`}>
              {loadingMe ? '…' : isAdmin ? `sim (${me?.role || 'admin'})` : me ? `não (${me?.role || 'none'})` : '—'}
            </span>
          </li>
          <li>
            <span className="diag-label">API configurada</span>
            <span className={`diag-val ${diag.apiConfigured ? 'ok' : 'err'}`}>
              {diag.apiConfigured ? 'sim' : 'não'}
            </span>
          </li>
          <li>
            <span className="diag-label">Endpoint base</span>
            <span className="diag-val mono">{diag.apiBase}</span>
          </li>
        </ul>
        <button className="btn btn--secondary btn--sm" onClick={fetchMe} disabled={loadingMe}>
          {loadingMe ? 'Verificando…' : 'Reverificar autenticação'}
        </button>
      </div>

      {/* Card: Sistema */}
      <div className="card">
        <h2>Sistema</h2>
        {loadingStatus && <p className="muted">Carregando…</p>}
        {sysStatus && (
          <ul className="diag-list">
            <li>
              <span className="diag-label">Worker</span>
              <span className={`diag-val ${sysStatus.ok ? 'ok' : 'err'}`}>
                {sysStatus.ok ? 'online' : 'offline'}
              </span>
            </li>
            <li>
              <span className="diag-label">Cards no Supabase</span>
              <span className="diag-val">{sysStatus.total_cards ?? '—'}</span>
            </li>
            <li>
              <span className="diag-label">Packs no Supabase</span>
              <span className="diag-val">{sysStatus.total_packs ?? '—'}</span>
            </li>
            <li>
              <span className="diag-label">Último sync</span>
              <span className="diag-val mono">{sysStatus.last_sync ?? '—'}</span>
            </li>
            <li>
              <span className="diag-label">Último comando</span>
              <span className="diag-val mono">{sysStatus.last_command ?? '—'}</span>
            </li>
          </ul>
        )}
        {!sysStatus && !loadingStatus && (
          <p className="muted">Não disponível. Verifique a URL do Worker.</p>
        )}
        <button className="btn btn--secondary btn--sm" onClick={fetchStatus} disabled={loadingStatus}>
          {loadingStatus ? 'Atualizando…' : 'Atualizar status'}
        </button>
      </div>

      {/* Card: Ações rápidas */}
      <div className="card">
        <h2>Ações rápidas</h2>
        {!isAdmin && !isOutsideTelegram && (
          <p className="hint">Botões desabilitados — usuário não é admin.</p>
        )}
        {isOutsideTelegram && (
          <p className="hint">Botões desabilitados — aberto fora do Telegram.</p>
        )}
        <div className="actions">
          {[
            { cmd: 'post_now', label: 'Postar agora', payload: cardCode ? { card_code: cardCode } : {} },
            { cmd: 'skip_card', label: 'Pular carta', payload: cardCode ? { card_code: cardCode } : {} },
            { cmd: 'pause_daily_post', label: 'Pausar diário' },
            { cmd: 'resume_daily_post', label: 'Retomar diário' },
            { cmd: 'sync_arkhamdb', label: 'Sync ArkhamDB', payload: { sync_faq: false } },
          ].map(({ cmd, label, payload }) => (
            <button
              key={cmd}
              className={`btn btn--primary ${loadingCmd === cmd ? 'btn--loading' : ''}`}
              disabled={!isAdmin || isOutsideTelegram || loadingCmd !== null}
              onClick={() => enqueue(cmd, payload || {})}
            >
              {loadingCmd === cmd ? `${label}…` : label}
            </button>
          ))}
        </div>
      </div>

      {/* Card: Carta */}
      <div className="card">
        <h2>Carta alvo</h2>
        <p className="hint">Código da carta (ex: <code>01001</code>). Usado por "Postar agora" e "Pular carta".</p>
        <input
          type="text"
          placeholder="01001"
          value={cardCode}
          onChange={(e) => setCardCode(e.target.value)}
          inputMode="text"
        />
      </div>

      {/* Card: Resultado */}
      {result && (
        <div className={`card ${result.ok ? 'card--ok' : 'card--err'}`}>
          <h2>Última ação</h2>
          <p className={`result-status ${result.ok ? 'ok' : 'err'}`}>
            {result.ok ? '✓ Sucesso' : '✗ Erro'}
          </p>
          <p>{result.friendly}</p>
          <p className="muted mono">{result.command_type}</p>
          <p className="muted">{result.at?.toLocaleTimeString('pt-BR')}</p>
          {result.detail && (
            <details>
              <summary>Detalhes técnicos</summary>
              <pre className="detail-pre">{result.detail}</pre>
            </details>
          )}
        </div>
      )}
    </div>
  );
}

createRoot(document.getElementById('root')).render(<App />);
