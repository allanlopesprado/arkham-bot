// ─── Components ───────────────────────────────────────────────────────────────

import React from 'react';
import { haptic, tg, initData, tgUser } from './telegram.js';
import { Icon } from './icons.jsx';
import { DELAY_OPTIONS, formatDelay } from './settings.js';

export function Spinner() { return <span className="spinner" aria-hidden="true" />; }

export function LoadingRow({ label }) {
  return (
    <div className="row loading-row" role="status" aria-live="polite">
      <Spinner />
      <span className="row-label">{label}</span>
    </div>
  );
}

export function Badge({ tone = '', children }) {
  return <span className={`badge ${tone}`.trim()}>{children}</span>;
}

export function Notice({ tone = 'warn', children }) {
  return <div className={`notice ${tone}`} role={tone === 'err' ? 'alert' : 'status'}>{children}</div>;
}

export function Section({ title, footer, danger, bare, info, children }) {
  return (
    <section className="section">
      {title && (
        <h2 className={`section-title${danger ? ' danger' : ''}`}>
          {title}
          {info && <InfoTooltip text={info} />}
        </h2>
      )}
      {bare ? children : <div className="card">{children}</div>}
      {footer && <div className="section-footer">{footer}</div>}
    </section>
  );
}

export function Row({ icon, label, value, badgeTone = '', caption, mono = false, onClick }) {
  const Tag = onClick ? 'button' : 'div';
  return (
    <Tag className={`row${onClick ? ' row-action' : ''}`} onClick={onClick} type={onClick ? 'button' : undefined}>
      {icon && <Icon name={icon} />}
      <div className="row-main">
        <span className="row-label">{label}</span>
        {caption && <span className="row-caption">{caption}</span>}
      </div>
      {value !== undefined && value !== null && (
        <span className={`row-value ${mono ? 'mono' : ''}`.trim()}>
          {badgeTone ? <Badge tone={badgeTone}>{value}</Badge> : value}
        </span>
      )}
      {onClick && <Icon name="chevron" className="chevron" />}
    </Tag>
  );
}

export function MenuRow({ icon, label, caption, value, onClick, disabled, loading, accent }) {
  return (
    <button
      className={`row row-action${accent ? ' accent' : ''}`}
      onClick={onClick}
      disabled={disabled || loading}
      aria-busy={loading || undefined}
      type="button"
    >
      {icon && <Icon name={icon} />}
      <span className="row-label-wrap">
        <span className="row-label">{label}</span>
        {caption && <span className="row-caption">{caption}</span>}
      </span>
      {value !== undefined && <span className="row-value">{value}</span>}
      {loading ? <Spinner /> : <Icon name="chevron" className="chevron" />}
    </button>
  );
}

export function DangerRow({ icon, label, onClick, disabled, loading }) {
  return (
    <button className="row row-action danger" onClick={onClick} disabled={disabled || loading} aria-busy={loading || undefined} type="button">
      {icon && <Icon name={icon} />}
      <span className="row-label">{label}</span>
      {loading ? <Spinner /> : <Icon name="chevron" className="chevron" />}
    </button>
  );
}

/* Action feedback: success/error after an enqueue or save. Colored + announced
   to screen readers (status for success, alert for errors), with icon + text so
   the meaning does not rely on color alone. */
export function ResultRow({ result, copy }) {
  if (!result) return null;
  const caption = [result.friendly, result.detail].filter(Boolean).join(' — ');
  return (
    <div
      className={`row result-row ${result.ok ? 'ok' : 'err'}`}
      role={result.ok ? 'status' : 'alert'}
      aria-live={result.ok ? 'polite' : 'assertive'}
    >
      <Icon name={result.ok ? 'result' : 'info'} />
      <div className="row-main">
        <span className="row-label">{result.ok ? copy.success : copy.error}</span>
        {caption && <span className="row-caption">{caption}</span>}
      </div>
    </div>
  );
}

let _infoTooltipSeq = 0;
export function InfoTooltip({ text, label = 'info' }) {
  const [open, setOpen] = React.useState(false);
  const id = React.useMemo(() => `info-tip-${++_infoTooltipSeq}`, []);
  React.useEffect(() => {
    if (!open) return;
    const close = () => setOpen(false);
    window.addEventListener('scroll', close, { passive: true, capture: true });
    return () => window.removeEventListener('scroll', close, { capture: true });
  }, [open]);
  return (
    <span className="info-tooltip-wrap">
      <button
        className="info-btn"
        type="button"
        aria-label={label}
        aria-expanded={open}
        aria-describedby={open ? id : undefined}
        onClick={(e) => { e.preventDefault(); e.stopPropagation(); haptic('selection'); setOpen((o) => !o); }}
      >ⓘ</button>
      {open && <span className="info-tooltip" id={id} role="tooltip">{text}</span>}
    </span>
  );
}

export function ToggleRow({ label, checked, onChange, disabled = false, info }) {
  return (
    <label className="toggle-row">
      <span className="row-label">
        {label}
        {info && <InfoTooltip text={info} />}
      </span>
      <input type="checkbox" checked={checked} disabled={disabled} onChange={(e) => { haptic('selection'); onChange(e.target.checked); }} />
      <span className="toggle" aria-hidden="true" />
    </label>
  );
}

export function InputRow({ label, value, onChange, placeholder, hint, invalid }) {
  return (
    <label className="row input-row">
      <div className="row-main">
        <span className="row-label">{label}</span>
        <input className={`inline-input${invalid ? ' invalid' : ''}`} value={value} onChange={(e) => onChange(e.target.value)} placeholder={placeholder} inputMode="text" autoComplete="off" aria-invalid={invalid || undefined} />
      </div>
      {hint && <span className="row-caption-block">{hint}</span>}
    </label>
  );
}

export function StackedInputRow({ label, value, onChange, placeholder, hint, inputMode, invalid }) {
  return (
    <label className="stacked-input-row">
      {label && <span className="row-label">{label}</span>}
      {hint && <span className="row-caption">{hint}</span>}
      <input
        className={`block-input${invalid ? ' invalid' : ''}`}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        inputMode={inputMode || 'text'}
        autoComplete="off"
        autoCorrect="off"
        autoCapitalize="none"
        spellCheck={false}
        aria-invalid={invalid || undefined}
      />
    </label>
  );
}

export function ChatIdInputRow({ value, onChange, placeholder, label, loading, invalid }) {
  function handleChange(e) {
    const digits = e.target.value.replace(/[^0-9]/g, '');
    onChange(digits ? `-${digits}` : '');
  }
  const displayValue = value.startsWith('-') ? value.slice(1) : value;
  return (
    <label className="stacked-input-row">
      {label && <span className="row-label">{label}</span>}
      <div className={`chat-id-input-wrap${invalid ? ' invalid' : ''}`}>
        <span className="chat-id-prefix">-</span>
        <input
          className="block-input chat-id-input"
          value={displayValue}
          onChange={handleChange}
          placeholder={placeholder || "100123456789"}
          inputMode="numeric"
          autoComplete="off"
          autoCorrect="off"
          autoCapitalize="none"
          spellCheck={false}
          aria-invalid={invalid || undefined}
        />
        {loading && <Spinner />}
      </div>
    </label>
  );
}

export function SelectRow({ label, value, onChange, children }) {
  return (
    <label className="row select-row">
      <span className="row-label">{label}</span>
      <select className="inline-select" value={value} onChange={(e) => { haptic('selection'); onChange(e.target.value); }}>
        {children}
      </select>
    </label>
  );
}

export function StackedSelectRow({ label, value, onChange, children }) {
  return (
    <label className="stacked-select-row">
      <span className="row-label">{label}</span>
      <select className="block-select" value={value} onChange={(e) => { haptic('selection'); onChange(e.target.value); }}>
        {children}
      </select>
    </label>
  );
}

export function DayScheduleRow({ label, subtitle, enabled, onToggle, onConfigure, disabled, configureLabel }) {
  return (
    <div className={`row${disabled ? ' row-disabled' : ''}`}>
      <div className="row-main">
        <span className="row-label">{label}</span>
        {subtitle && <span className="row-caption">{subtitle}</span>}
      </div>
      <button className="row-config-btn" type="button" onClick={onConfigure} aria-label={configureLabel || 'Configure'} disabled={disabled}>
        <Icon name="settings" />
      </button>
      <label className={`day-toggle-wrap${disabled ? ' day-toggle-disabled' : ''}`}>
        <input type="checkbox" aria-label={label} checked={enabled} disabled={disabled} onChange={(e) => { if (!disabled) { haptic('selection'); onToggle(e.target.checked); } }} />
        <span className="toggle" aria-hidden="true" />
      </label>
    </div>
  );
}

export function CommandRow({ command, onCancel, loading, copy }) {
  const cancellable = ['pending', 'retrying'].includes(command.status);
  const tone = command.status === 'failed' ? 'err' : command.status === 'executed' ? 'ok' : 'warn';
  const friendlyStatus = copy.commandStatusLabels[command.status] || command.status;
  const friendlyType = copy.commandTypeLabels[command.command_type] || command.command_type;
  const parts = [
    command.command_type === 'daily_post' ? (command.payload?.card_name || command.payload?.card_code || null) : null,
    command.caption || null,
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

export function CardResult({ card, selected, onSelect }) {
  const fullName = card.name || card.real_name || card.code;
  return (
    <button
      className={`card-result ${selected ? 'active' : ''}`.trim()}
      type="button"
      onClick={() => onSelect(card)}
      title={fullName}
    >
      <span className="card-code">{card.code}</span>
      <div className="card-info">
        <span className="card-name">{fullName}</span>
        <span className="card-meta">{[card.type_code, card.faction_name, card.pack_name].filter(Boolean).join(' · ')}</span>
      </div>
    </button>
  );
}

export function GateScreen({ children }) {
  return <div className="gate"><div className="gate-inner">{children}</div></div>;
}

export function LoadingGate() {
  return <GateScreen><Spinner /></GateScreen>;
}

export function NoTelegramGate({ copy }) {
  return (
    <GateScreen>
      <Icon name="bot" className="gate-icon" />
      <p className="gate-title">Arkham Bot</p>
      <p className="gate-text">{copy.outsideTelegram}</p>
    </GateScreen>
  );
}

export function AuthErrorGate({ copy }) {
  return (
    <GateScreen>
      <Icon name="server" className="gate-icon" />
      <p className="gate-title">{copy.authErrorTitle}</p>
      <p className="gate-text">{copy.authErrorText}</p>
    </GateScreen>
  );
}

export function UnauthorizedGate({ copy }) {
  return (
    <GateScreen>
      <Icon name="shield" className="gate-icon" />
      <p className="gate-title">{copy.unauthorizedTitle}</p>
      <p className="gate-text">{copy.unauthorizedText}</p>
    </GateScreen>
  );
}

export function ApiNotConfiguredGate({ copy }) {
  return (
    <GateScreen>
      <Icon name="wrench" className="gate-icon" />
      <p className="gate-title">{copy.apiNotConfiguredTitle}</p>
      <p className="gate-text">{copy.apiNotConfiguredText}</p>
    </GateScreen>
  );
}
