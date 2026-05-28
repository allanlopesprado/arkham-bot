// ─── Telegram helpers ─────────────────────────────────────────────────────────

export function tg() { return window.Telegram?.WebApp || null; }
export function initData() { return tg()?.initData || ''; }
export function tgUser() { return tg()?.initDataUnsafe?.user || null; }

export function haptic(type, value) {
  try {
    const hf = tg()?.HapticFeedback;
    if (!hf) return;
    if (type === 'notification') hf.notificationOccurred(value);
    else if (type === 'impact') hf.impactOccurred(value);
    else if (type === 'selection') hf.selectionChanged();
  } catch {}
}

export function tgShowPopup(params) {
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
