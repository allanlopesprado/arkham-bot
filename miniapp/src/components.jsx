// ─── Components ───────────────────────────────────────────────────────────────

import React from 'react';
import { haptic, tg, initData, tgUser } from './telegram.js';
import { Icon } from './icons.jsx';
import { DELAY_OPTIONS, formatDelay } from './settings.js';

export function Spinner() { return <span className="spinner" aria-hidden="true" />; }

export function Badge({ tone = '', children }) {
  return <span className={`badge ${tone}`.trim()}>{children}</span>;
}

export function Notice({ tone = 'warn', children }) {
  return <div className={`notice ${tone}`}>{children}</div>;
}

export function Section({ title, footer, danger, bare, info, children }) {
  return (
    <section className="section">
      {title && (
        <div className={`section-title${danger ? ' danger' : ''}`}>
          {title}
          {info && <InfoTooltip text={info} />}
        </div>
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

export function MenuRow({ icon, label, caption, value, onClick, disabled, loading }) {
  return (
    <button className="row row-action" onClick={onClick} disabled={disabled || loading} type="button">
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
    <button className="row row-action danger" onClick={onClick} disabled={disabled || loading} type="button">
      {icon && <Icon name={icon} />}
      <span className="row-label">{label}</span>
      {loading ? <Spinner /> : <Icon name="chevron" className="chevron" />}
    </button>
  );
}

export function InfoTooltip({ text }) {
  const [open, setOpen] = React.useState(false);
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
        aria-label="info"
        onClick={(e) => { e.preventDefault(); e.stopPropagation(); haptic('selection'); setOpen((o) => !o); }}
      >ⓘ</button>
      {open && <span className="info-tooltip">{text}</span>}
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

export function InputRow({ label, value, onChange, placeholder, hint }) {
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

export function StackedInputRow({ label, value, onChange, placeholder, hint, inputMode }) {
  return (
    <div className="stacked-input-row">
      {label && <span className="row-label">{label}</span>}
      {hint && <span className="row-caption">{hint}</span>}
      <input
        className="block-input"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        inputMode={inputMode || 'text'}
        autoCorrect="off"
        autoCapitalize="none"
        spellCheck={false}
      />
    </div>
  );
}

export function ChatIdInputRow({ value, onChange, placeholder }) {
  function handleChange(e) {
    const digits = e.target.value.replace(/[^0-9]/g, '');
    onChange(digits ? `-${digits}` : '');
  }
  const displayValue = value.startsWith('-') ? value.slice(1) : value;
  return (
    <div className="stacked-input-row">
      <div className="chat-id-input-wrap">
        <span className="chat-id-prefix">-</span>
        <input
          className="block-input chat-id-input"
          value={displayValue}
          onChange={handleChange}
          placeholder="100123456789"
          inputMode="numeric"
          autoCorrect="off"
          autoCapitalize="none"
          spellCheck={false}
        />
      </div>
    </div>
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
    <div className="stacked-select-row">
      <span className="row-label">{label}</span>
      <select className="block-select" value={value} onChange={(e) => { haptic('selection'); onChange(e.target.value); }}>
        {children}
      </select>
    </div>
  );
}

export function DayScheduleRow({ label, subtitle, enabled, onToggle, onConfigure, disabled }) {
  return (
    <div className={`row${disabled ? ' row-disabled' : ''}`}>
      <div className="row-main">
        <span className="row-label">{label}</span>
        {subtitle && <span className="row-caption">{subtitle}</span>}
      </div>
      <button className="row-config-btn" type="button" onClick={onConfigure} aria-label="configurar" disabled={disabled}>
        <Icon name="settings" />
      </button>
      <label className={`day-toggle-wrap${disabled ? ' day-toggle-disabled' : ''}`}>
        <input type="checkbox" checked={enabled} disabled={disabled} onChange={(e) => { if (!disabled) { haptic('selection'); onToggle(e.target.checked); } }} />
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
